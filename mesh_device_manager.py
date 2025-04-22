#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RL62M02 Mesh 裝置管理工具
提供單一循序綁定、解除所有裝置綁定、以及自動重新綁定功能
"""

import os
import sys
import json
import time
import logging
import argparse
from typing import Dict, List, Optional, Any

# 引入 rl62m02 套件
try:
    from rl62m02 import create_provisioner, Provisioner
except ImportError:
    # 如果安裝了套件但無法直接導入，嘗試從相對路徑導入
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if (current_dir not in sys.path):
        sys.path.append(current_dir)
    from rl62m02 import create_provisioner, Provisioner

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s][%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class MeshDeviceManager:
    """Mesh 設備管理類別，提供綁定、解綁、自動重綁等功能"""
    
    # 預設群組地址，用於訂閱和推播
    DEFAULT_GROUP_ADDR = "0xC000"
    # 預設裝置記錄檔案路徑
    DEFAULT_DEVICE_FILE = "mesh_devices_config.json"
    # 裝置綁定的起始 unicast 地址
    START_UNICAST_ADDR = 0x0100
    
    def __init__(self, port: str, baudrate: int = 115200, device_file: str = DEFAULT_DEVICE_FILE):
        """
        初始化 MeshDeviceManager
        
        Args:
            port (str): 串口名稱，如 COM3
            baudrate (int): 串口鮑率
            device_file (str): 裝置記錄檔案路徑
        """
        self.port = port
        self.baudrate = baudrate
        self.device_file = device_file
        self.serial_at = None
        self.provisioner = None
        self.devices = []
        self.current_unicast = self.START_UNICAST_ADDR
        
        # 連接設備
        self._connect()
        
        # 載入現有的裝置記錄
        self._load_devices()
    
    def _connect(self):
        """連接 RL62M02 裝置"""
        try:
            logger.info(f"正在連接 {self.port} (鮑率: {self.baudrate})...")
            self.serial_at, self.provisioner, _ = create_provisioner(self.port, self.baudrate)
            version = self.provisioner.get_version()
            if version:
                logger.info(f"成功連接到 RL62M02 裝置，版本訊息: {version}")
            else:
                logger.warning("連接到裝置，但無法取得版本訊息")
        except Exception as e:
            logger.error(f"連接失敗: {str(e)}")
            raise
    
    def _load_devices(self):
        """載入裝置記錄檔"""
        if os.path.exists(self.device_file):
            try:
                with open(self.device_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.devices = data.get("devices", [])
                    logger.info(f"已載入 {len(self.devices)} 個裝置記錄")
            except Exception as e:
                logger.error(f"載入裝置記錄檔失敗: {str(e)}")
                self.devices = []
        else:
            logger.info(f"找不到裝置記錄檔 {self.device_file}，將建立新檔案")
            self.devices = []
    
    def _save_devices(self):
        """儲存裝置記錄到檔案"""
        try:
            data = {"devices": self.devices}
            with open(self.device_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"已儲存 {len(self.devices)} 個裝置記錄到 {self.device_file}")
        except Exception as e:
            logger.error(f"儲存裝置記錄檔失敗: {str(e)}")
    
    def _find_device_by_uuid(self, uuid: str):
        """
        根據 UUID 查找裝置
        
        Args:
            uuid (str): 裝置 UUID
            
        Returns:
            dict: 裝置資訊，如未找到則返回 None
        """
        for device in self.devices:
            if device.get("uuid") == uuid:
                return device
        return None
    
    def _get_next_unicast_addr(self):
        """
        取得下一個可用的 unicast 地址
        
        Returns:
            str: 十六進位的 unicast 地址 (如 "0x0101")
        """
        # 檢查裝置列表中已用的最大地址
        max_addr = self.START_UNICAST_ADDR
        for device in self.devices:
            if "unicast_addr" in device:
                try:
                    addr_int = int(device["unicast_addr"], 16)
                    if addr_int > max_addr:
                        max_addr = addr_int
                except ValueError:
                    pass
        
        # 返回最大地址 + 1
        next_addr = max_addr + 1
        return f"0x{next_addr:04X}"
    
    def scan_devices(self, scan_time: float = 5.0):
        """
        掃描周圍的 Mesh 裝置
        
        Args:
            scan_time (float): 掃描時間，單位為秒
            
        Returns:
            list: 掃描到的裝置列表
        """
        logger.info(f"正在掃描 Mesh 裝置 ({scan_time} 秒)...")
        devices = self.provisioner.scan_nodes(scan_time=scan_time)
        logger.info(f"找到 {len(devices)} 個裝置")
        for i, device in enumerate(devices):
            logger.info(f"{i+1}. MAC: {device.get('mac address', '未知')}, UUID: {device.get('uuid', '未知')}")
        return devices
    
    def provision_device(self, uuid: str, device_name: str, 
                        subscribe_uid: str = None, publish_uid: str = None):
        """
        綁定單一裝置，設定訂閱 UID 與推播 UID
        
        Args:
            uuid (str): 裝置 UUID
            device_name (str): 裝置名稱
            subscribe_uid (str): 訂閱的 UID，如果為 None 則使用預設群組地址
            publish_uid (str): 推播的 UID，如果為 None 則使用預設群組地址
            
        Returns:
            dict: 綁定結果，包含成功或失敗資訊
        """
        if subscribe_uid is None:
            subscribe_uid = self.DEFAULT_GROUP_ADDR
        if publish_uid is None:
            publish_uid = self.DEFAULT_GROUP_ADDR
        
        # 檢查裝置是否已經綁定
        existing_device = self._find_device_by_uuid(uuid)
        if (existing_device):
            logger.warning(f"裝置 {uuid} 已經存在，將覆蓋原有設定")
        
        # 取得下一個可用的 unicast 地址
        next_addr = self._get_next_unicast_addr()
        
        # 掃描取得 MAC 地址
        logger.info(f"掃描裝置 {uuid} 的 MAC 地址...")
        devices = self.provisioner.scan_nodes(scan_time=2.0)
        mac_address = "未知"
        for device in devices:
            if device.get("uuid") == uuid:
                mac_address = device.get("mac address", "未知")
                break
        
        # 進行裝置綁定
        logger.info(f"正在綁定裝置 {uuid}...")
        result = self.provisioner.auto_provision_node(uuid)
        
        if result.get("result") != "success":
            logger.error(f"綁定失敗: {result}")
            return {"success": False, "message": f"綁定失敗: {result.get('step')}"}
        
        unicast_addr = result.get("unicast_addr")
        logger.info(f"綁定成功，unicast 地址: {unicast_addr}")
        
        # 設定訂閱和推播
        logger.info(f"設定訂閱地址: {subscribe_uid}")
        sub_result = self.provisioner.subscribe_group(unicast_addr, subscribe_uid)
        logger.info(f"訂閱結果: {sub_result}")
        
        logger.info(f"設定推播地址: {publish_uid}")
        pub_result = self.provisioner.publish_to_target(unicast_addr, publish_uid)
        logger.info(f"推播設定結果: {pub_result}")
        
        # 記錄裝置資訊
        device_info = {
            "uuid": uuid,
            "mac_address": mac_address,
            "device_name": device_name,
            "unicast_addr": unicast_addr,
            "subscribe_uid": subscribe_uid,
            "publish_uid": publish_uid,
            "binding_time": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 更新或新增裝置記錄
        if existing_device:
            # 移除舊記錄
            self.devices = [d for d in self.devices if d.get("uuid") != uuid]
        
        self.devices.append(device_info)
        
        # 儲存到檔案
        self._save_devices()
        
        return {
            "success": True, 
            "message": f"裝置 {device_name} 綁定成功，unicast 地址: {unicast_addr}",
            "device": device_info
        }
    
    def unprovision_all_devices(self):
        """
        解除所有裝置的綁定
        
        Returns:
            dict: 解綁結果，包含成功解綁的裝置數量和失敗列表
        """
        if not self.devices:
            logger.info("沒有已綁定的裝置")
            return {"success": True, "message": "沒有已綁定的裝置", "unprovision_count": 0}
        
        success_count = 0
        failed_devices = []
        
        # 取得當前已綁定的節點列表
        node_list = self.provisioner.get_node_list()
        bound_addresses = []
        print("已綁定 :",node_list)
        # 解析節點列表
        for node in node_list:
            if node.startswith('NL-MSG'):
                parts = node.split(" ")
                if len(parts) >= 3:
                    addr = parts[2]
                    bound_addresses.append(addr)
        
        logger.info(f"發現 {len(bound_addresses)} 個已綁定的節點")
        
        
        # 解綁所有裝置
        for addr in bound_addresses:
            logger.info(f"解綁裝置 {addr}...")
            resp = self.provisioner._send_and_wait(f'AT+NR {addr}', timeout=3.0)
            
            if resp and resp.startswith('NR-MSG SUCCESS'):
                logger.info(f"裝置 {addr} 解綁成功")
                success_count += 1
            else:
                logger.warning(f"裝置 {addr} 解綁失敗: {resp}")
                failed_devices.append({"addr": addr, "error": str(resp)})
        
        return {
            "success": len(failed_devices) == 0,
            "message": f"已解綁 {success_count} 個裝置，失敗 {len(failed_devices)} 個",
            "unprovision_count": success_count,
            "failed_devices": failed_devices
        }
    
    def auto_provision_from_json(self):
        """
        從 JSON 檔案自動綁定裝置
        
        Returns:
            dict: 綁定結果，包含成功和失敗的裝置清單
        """
        if not self.devices:
            logger.info("記錄檔中沒有裝置資訊")
            return {"success": True, "message": "沒有裝置需要綁定", "success_count": 0}
        
        # 先掃描周圍裝置
        logger.info("掃描周圍可用裝置...")
        available_devices = self.provisioner.scan_nodes(scan_time=5.0)
        available_uuids = [d.get("uuid") for d in available_devices]
                
        success_devices = []
        failed_devices = []
        
        # 依序綁定記錄檔中的裝置
        for device in self.devices:
            uuid = device.get("uuid")
            device_name = device.get("device_name", f"Device-{uuid[-6:]}")
            subscribe_uid = device.get("subscribe_uid", self.DEFAULT_GROUP_ADDR)
            publish_uid = device.get("publish_uid", self.DEFAULT_GROUP_ADDR)
            
            if uuid not in available_uuids:
                logger.warning(f"裝置 {uuid} ({device_name}) 不在掃描範圍內，跳過")
                failed_devices.append({
                    "uuid": uuid,
                    "device_name": device_name,
                    "error": "裝置不在掃描範圍內"
                })
                break
            
            # 進行裝置綁定
            result = self.provisioner.auto_provision_node(uuid)
            
            if result.get("result") != "success":
                logger.error(f"綁定失敗: {result}")
                failed_devices.append({
                    "uuid": uuid,
                    "device_name": device_name,
                    "error": f"綁定失敗: {result.get('step')}"
                })
                continue
            
            unicast_addr = result.get("unicast_addr")
            logger.info(f"綁定成功，unicast 地址: {unicast_addr}")
            
            # 設定訂閱和推播
            logger.info(f"設定訂閱地址: {subscribe_uid}")
            sub_result = self.provisioner.subscribe_group(unicast_addr, subscribe_uid)
            
            logger.info(f"設定推播地址: {publish_uid}")
            pub_result = self.provisioner.publish_to_target(unicast_addr, publish_uid)
            
            # 更新裝置記錄
            device["unicast_addr"] = unicast_addr
            device["binding_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            success_devices.append({
                "uuid": uuid,
                "device_name": device_name,
                "unicast_addr": unicast_addr
            })
        
        # 儲存更新後的裝置記錄
        self._save_devices()
        
        return {
            "success": len(failed_devices) == 0,
            "message": f"成功綁定 {len(success_devices)} 個裝置，失敗 {len(failed_devices)} 個",
            "success_count": len(success_devices),
            "success_devices": success_devices,
            "failed_devices": failed_devices
        }
    
    def reset_and_bind(self, uuid: str, device_name: str, 
                       subscribe_uid: str = None, publish_uid: str = None):
        """
        先解除所有裝置綁定，然後進行單一裝置綁定
        
        Args:
            uuid (str): 裝置 UUID
            device_name (str): 裝置名稱
            subscribe_uid (str): 訂閱的 UID，如果為 None 則使用預設群組地址
            publish_uid (str): 推播的 UID，如果為 None 則使用預設群組地址
            
        Returns:
            dict: 綁定結果，包含成功或失敗資訊
        """
        # 步驟1: 解除所有裝置綁定
        logger.info("步驟 1: 解除所有裝置綁定")
        unbind_result = self.unprovision_all_devices()
        if not unbind_result.get("success"):
            logger.warning("無法解除所有裝置綁定，但仍將繼續綁定新裝置")
        
        # 重置 unicast 地址計數器到起始值
        self.current_unicast = self.START_UNICAST_ADDR
        
        # 步驟2: 掃描裝置
        logger.info(f"步驟 2: 掃描尋找裝置 {uuid}")
        devices = self.scan_devices(scan_time=3.0)
        found = False
        for device in devices:
            if device.get("uuid") == uuid:
                found = True
                break
                
        if not found:
            return {
                "success": False,
                "message": f"無法找到裝置 UUID: {uuid}，請確認裝置已開啟並在範圍內"
            }
        
        # 步驟3: 指定 unicast 地址進行單一裝置綁定
        logger.info(f"步驟 3: 綁定裝置 {uuid} 到地址 0x{self.current_unicast:04X}")
        
        if subscribe_uid is None:
            subscribe_uid = self.DEFAULT_GROUP_ADDR
        if publish_uid is None:
            publish_uid = self.DEFAULT_GROUP_ADDR
            
        # 準備下一個 unicast 地址（確保從 0x0100 開始）
        unicast_addr = f"0x{self.current_unicast:04X}"
        
        # 掃描取得 MAC 地址
        mac_address = "未知"
        for device in devices:
            if device.get("uuid") == uuid:
                mac_address = device.get("mac address", "未知")
                break
        
        # 進行裝置綁定
        logger.info(f"正在綁定裝置 {uuid} 到地址 {unicast_addr}...")
        result = self.provisioner.auto_provision_node(uuid)
        
        if result.get("result") != "success":
            logger.error(f"綁定失敗: {result}")
            return {"success": False, "message": f"綁定失敗: {result.get('step')}"}
        
        actual_addr = result.get("unicast_addr")
        logger.info(f"綁定成功，unicast 地址: {actual_addr}")
        
        # 設定訂閱和推播
        logger.info(f"設定訂閱地址: {subscribe_uid}")
        sub_result = self.provisioner.subscribe_group(actual_addr, subscribe_uid)
        logger.info(f"訂閱結果: {sub_result}")
        
        logger.info(f"設定推播地址: {publish_uid}")
        pub_result = self.provisioner.publish_to_target(actual_addr, publish_uid)
        logger.info(f"推播設定結果: {pub_result}")
        
        # 記錄裝置資訊
        device_info = {
            "uuid": uuid,
            "mac_address": mac_address,
            "device_name": device_name,
            "unicast_addr": actual_addr,
            "subscribe_uid": subscribe_uid,
            "publish_uid": publish_uid,
            "binding_time": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 清除所有現有裝置記錄，只保留新綁定的裝置
        self.devices = [device_info]
        
        # 儲存到檔案
        self._save_devices()
        
        # 更新 unicast 計數器
        self.current_unicast += 1
        
        return {
            "success": True, 
            "message": f"已解除所有裝置綁定並綁定裝置 {device_name}，unicast 地址: {actual_addr}",
            "device": device_info
        }
    
    def scan_and_bind(self, scan_time: float = 5.0, subscribe_uid: str = None, publish_uid: str = None):
        """
        掃描可用裝置，讓用戶選擇要綁定的裝置，進行綁定和設定
        
        Args:
            scan_time (float): 掃描時間，單位為秒
            subscribe_uid (str): 訂閱的 UID，如果為 None 則使用預設群組地址
            publish_uid (str): 推播的 UID，如果為 None 則使用預設群組地址
            
        Returns:
            dict: 綁定結果
        """
        # 設定預設值
        if subscribe_uid is None:
            subscribe_uid = self.DEFAULT_GROUP_ADDR
        if publish_uid is None:
            publish_uid = self.DEFAULT_GROUP_ADDR
            
        # 步驟1: 掃描裝置
        logger.info(f"步驟 1: 掃描可用裝置 ({scan_time} 秒)...")
        devices = self.provisioner.scan_nodes(scan_time=scan_time)
        
        if not devices:
            logger.error("沒有找到可用裝置")
            return {"success": False, "message": "沒有找到可用裝置"}
        
        # 顯示找到的裝置
        print(f"\n找到 {len(devices)} 個可用裝置:")
        for i, device in enumerate(devices):
            print(f"{i+1}. UUID: {device.get('uuid', '未知')}, MAC: {device.get('mac address', '未知')}")
        
        # 步驟2: 選擇要綁定的裝置
        while True:
            try:
                choice = int(input("\n請選擇要綁定的裝置 (輸入編號): "))
                if 1 <= choice <= len(devices):
                    selected_device = devices[choice-1]
                    break
                else:
                    print(f"請輸入 1 到 {len(devices)} 之間的數字")
            except ValueError:
                print("請輸入有效的數字")
        
        # 取得選擇的裝置 UUID
        uuid = selected_device.get("uuid")
        if not uuid:
            logger.error("選擇的裝置沒有 UUID")
            return {"success": False, "message": "選擇的裝置沒有 UUID"}
        
        # 步驟3: 設置裝置名稱
        device_name = input("\n請輸入裝置名稱: ")
        if not device_name:
            device_name = f"Device-{uuid[-6:]}"
            print(f"使用預設名稱: {device_name}")
        
        # 步驟4: 進行裝置綁定和設定
        print(f"\n開始綁定裝置 {uuid} ({device_name})...")
        print(f"訂閱 UID: {subscribe_uid}")
        print(f"推撥 UID: {publish_uid}")
        
        # 重置 unicast 地址計數器到起始值，確保從 0x0100 開始綁定
        self.current_unicast = self.START_UNICAST_ADDR
        
        # 準備下一個 unicast 地址
        unicast_addr = f"0x{self.current_unicast:04X}"
        
        # 取得 MAC 地址
        mac_address = selected_device.get("mac address", "未知")
        
        # 進行裝置綁定
        logger.info(f"正在綁定裝置 {uuid} 到地址 {unicast_addr}...")
        result = self.provisioner.auto_provision_node(uuid)
        
        if result.get("result") != "success":
            logger.error(f"綁定失敗: {result}")
            return {"success": False, "message": f"綁定失敗: {result.get('step')}"}
        
        actual_addr = result.get("unicast_addr")
        logger.info(f"綁定成功，unicast 地址: {actual_addr}")
        
        # 設定訂閱和推播
        logger.info(f"設定訂閱地址: {subscribe_uid}")
        sub_result = self.provisioner.subscribe_group(actual_addr, subscribe_uid)
        logger.info(f"訂閱結果: {sub_result}")
        
        logger.info(f"設定推播地址: {publish_uid}")
        pub_result = self.provisioner.publish_to_target(actual_addr, publish_uid)
        logger.info(f"推播設定結果: {pub_result}")
        
        # 記錄裝置資訊
        device_info = {
            "uuid": uuid,
            "mac_address": mac_address,
            "device_name": device_name,
            "unicast_addr": actual_addr,
            "subscribe_uid": subscribe_uid,
            "publish_uid": publish_uid,
            "binding_time": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 更新裝置記錄 (添加到列表或替換現有記錄)
        existing_device = self._find_device_by_uuid(uuid)
        if existing_device:
            # 移除舊記錄
            self.devices = [d for d in self.devices if d.get("uuid") != uuid]
        
        # 添加新記錄
        self.devices.append(device_info)
        
        # 儲存到檔案
        self._save_devices()
        
        # 更新 unicast 計數器
        self.current_unicast += 1
        
        return {
            "success": True, 
            "message": f"裝置 {device_name} 綁定成功，unicast 地址: {actual_addr}",
            "device": device_info
        }
    
    def close(self):
        """關閉連接"""
        if self.serial_at:
            self.serial_at.close()
            logger.info("已關閉串口連接")

def main():
    """主程式入口"""
    parser = argparse.ArgumentParser(description='RL62M02 Mesh 裝置管理工具')
    parser.add_argument('port', help='串口名稱，如 COM3')
    parser.add_argument('--baudrate', type=int, default=115200, help='串口鮑率')
    parser.add_argument('--device-file', default='mesh_devices_config.json', help='裝置記錄檔案路徑')
    parser.add_argument('--debug', action='store_true', help='啟用除錯模式')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 掃描裝置
    scan_parser = subparsers.add_parser('scan', help='掃描周圍的 RL Mesh 裝置')
    scan_parser.add_argument('--time', type=float, default=5.0, help='掃描時間，單位為秒')
    
    # 綁定裝置
    bind_parser = subparsers.add_parser('bind', help='綁定單一裝置')
    bind_parser.add_argument('--uuid', required=True, help='裝置 UUID')
    bind_parser.add_argument('--name', required=True, help='裝置名稱')
    bind_parser.add_argument('--subscribe', help='訂閱地址 (預設 0xC000)')
    bind_parser.add_argument('--publish', help='推播地址 (預設 0xC000)')
    
    # 解除綁定所有裝置
    unbind_parser = subparsers.add_parser('unbind-all', help='解除所有裝置的綁定')
    unbind_parser.add_argument('--clear-json', action='store_true', help='同時清空 JSON 裝置記錄檔（預設不清空）')
    
    # 自動綁定
    subparsers.add_parser('auto-bind', help='從 JSON 記錄檔自動綁定裝置')
    
    # 列出已綁定的裝置
    subparsers.add_parser('list', help='列出記錄檔中的裝置')
    
    # 新增：先解除所有裝置綁定，然後綁定單一裝置
    reset_bind_parser = subparsers.add_parser('reset-and-bind', help='先解除所有裝置綁定，然後綁定單一裝置')
    reset_bind_parser.add_argument('--uuid', required=True, help='裝置 UUID')
    reset_bind_parser.add_argument('--name', required=True, help='裝置名稱')
    reset_bind_parser.add_argument('--subscribe', help='訂閱地址 (預設 0xC000)')
    reset_bind_parser.add_argument('--publish', help='推播地址 (預設 0xC000)')
    
    # 新增：互動式掃描並綁定裝置
    scan_bind_parser = subparsers.add_parser('scan-and-bind', help='掃描可用裝置並進行綁定和設定')
    scan_bind_parser.add_argument('--time', type=float, default=5.0, help='掃描時間，單位為秒')
    scan_bind_parser.add_argument('--subscribe', help='訂閱地址 (預設 0xC000)')
    scan_bind_parser.add_argument('--publish', help='推播地址 (預設 0xC000)')
    
    args = parser.parse_args()
    
    # 設定日誌級別
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # 初始化裝置管理器
        manager = MeshDeviceManager(args.port, args.baudrate, args.device_file)
        
        if args.command == 'scan':
            # 掃描裝置
            manager.scan_devices(args.time)
            
        elif args.command == 'bind':
            # 綁定單一裝置
            result = manager.provision_device(
                args.uuid, 
                args.name,
                args.subscribe,
                args.publish
            )
            if result.get("success"):
                print(f"綁定成功: {result.get('message')}")
            else:
                print(f"綁定失敗: {result.get('message')}")
            
        elif args.command == 'unbind-all':
            # 解除所有裝置的綁定
            result = manager.unprovision_all_devices()
            print(f"解綁結果: {result.get('message')}")
            # 新增：根據參數決定是否清空 JSON 檔案
            if getattr(args, 'clear_json', False):
                manager.devices = []
                manager._save_devices()
                print("已清空 JSON 裝置記錄檔")
            
        elif args.command == 'auto-bind':
            # 自動綁定裝置
            result = manager.auto_provision_from_json()
            print(f"自動綁定結果: {result.get('message')}")
            
        elif args.command == 'list':
            # 列出已綁定的裝置
            if not manager.devices:
                print("記錄檔中沒有裝置")
            else:
                print(f"已記錄 {len(manager.devices)} 個裝置:")
                for i, device in enumerate(manager.devices):
                    print(f"{i+1}. {device.get('device_name', '未命名')}")
                    print(f"   UUID: {device.get('uuid', '未知')}")
                    print(f"   MAC地址: {device.get('mac_address', '未知')}")
                    print(f"   Unicast地址: {device.get('unicast_addr', '未知')}")
                    print(f"   訂閱地址: {device.get('subscribe_uid', '未知')}")
                    print(f"   推播地址: {device.get('publish_uid', '未知')}")
                    print(f"   綁定時間: {device.get('binding_time', '未記錄')}")
                    print("")
        
        elif args.command == 'reset-and-bind':
            # 先解除所有裝置綁定，然後綁定單一裝置
            result = manager.reset_and_bind(
                args.uuid,
                args.name,
                args.subscribe,
                args.publish
            )
            if result.get("success"):
                print(f"重置與綁定成功: {result.get('message')}")
            else:
                print(f"重置與綁定失敗: {result.get('message')}")

        elif args.command == 'scan-and-bind':
            # 互動式掃描和綁定
            result = manager.scan_and_bind(
                scan_time=args.time,
                subscribe_uid=args.subscribe,
                publish_uid=args.publish
            )
            if result.get("success"):
                print(f"掃描與綁定成功: {result.get('message')}")
            else:
                print(f"掃描與綁定失敗: {result.get('message')}")

        else:
            print("請指定操作命令，使用 --help 查看幫助")
            
    except Exception as e:
        logger.error(f"發生錯誤: {str(e)}")
    finally:
        if 'manager' in locals():
            time.sleep(1) # 等待一段時間以確保所有操作完成 (unbind/ bind 時需要，避免延遲)
            manager.close()  # 確保在關閉管理器之前不會有延遲

if __name__ == "__main__":
    main()