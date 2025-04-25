#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RL Mesh 設備管理器
提供設備資料管理、存取、控制等操作的統一介面
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Union, Tuple
import traceback

from .provisioner import Provisioner
from .controllers.mesh_controller import RLMeshDeviceController


class MeshDeviceManager:
    """Mesh 設備管理器，整合設備資訊管理、操作等功能"""
    
    DEFAULT_JSON_PATH = "mesh_devices.json"
    
    def __init__(self, provisioner: Provisioner, controller: Optional[RLMeshDeviceController] = None, 
                 device_json_path: str = DEFAULT_JSON_PATH) -> None:
        """初始化設備管理器
        
        Args:
            provisioner: Provisioner 實例，用於與 Mesh 網路通訊
            controller: RLMeshDeviceController 實例，用於控制設備
            device_json_path: 設備數據檔案路徑
        """
        self.provisioner = provisioner
        self.controller = controller or RLMeshDeviceController(provisioner)
        self.device_json_path = device_json_path
        # 初始化 logger 必須在使用之前
        self.logger = logging.getLogger(__name__)
        # 載入設備數據
        self.devices_data = self._load_device_data()
        
        # 確保 controller 中註冊了所有設備
        self._register_devices_to_controller()
    
    def _load_device_data(self) -> Dict[str, Any]:
        """載入或創建設備數據檔案"""
        try:
            if os.path.exists(self.device_json_path):
                with open(self.device_json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.logger.info(f"已從 {self.device_json_path} 載入設備數據")
                    return data
            else:
                # 創建新的數據結構
                data = {
                    "gwMac": "",
                    "gwType": "mini_PC",
                    "gwPosition": "主機位置",
                    "devices": []
                }
                self.logger.info(f"未找到設備數據檔案，創建新結構")
                return data
        except Exception as e:
            self.logger.error(f"載入設備數據時發生錯誤: {e}")
            return {
                "gwMac": "",
                "gwType": "mini_PC",
                "gwPosition": "主機位置",
                "devices": []
            }
    
    def save_device_data(self) -> bool:
        """保存設備數據到檔案"""
        try:
            with open(self.device_json_path, 'w', encoding='utf-8') as f:
                json.dump(self.devices_data, f, indent=4, ensure_ascii=False)
                self.logger.info(f"設備數據已保存到 {self.device_json_path}")
            return True
        except Exception as e:
            self.logger.error(f"保存設備數據時發生錯誤: {e}")
            return False
    
    def _register_devices_to_controller(self) -> None:
        """將已存在的設備註冊到控制器"""
        devices = self.devices_data.get("devices", [])
        for device in devices:
            try:
                uid = device.get('uid', '')
                name = device.get('devType') or device.get('devName') or '未命名'  # devType 存放名稱，devName 存放類型
                device_type_str = device.get('devName') or 'RGB_LED'  # devName 存放類型
                
                # 轉換設備類型
                type_mapping = {
                    "RGB_LED": RLMeshDeviceController.DEVICE_TYPE_RGB_LED,
                    "PLUG": RLMeshDeviceController.DEVICE_TYPE_PLUG,
                    "SMART_BOX": RLMeshDeviceController.DEVICE_TYPE_SMART_BOX,
                    "AIR_BOX": RLMeshDeviceController.DEVICE_TYPE_AIR_BOX,
                    "POWER_METER": RLMeshDeviceController.DEVICE_TYPE_POWER_METER
                }
                controller_type = type_mapping.get(device_type_str, RLMeshDeviceController.DEVICE_TYPE_RGB_LED)
                
                if uid:
                    self.controller.register_device(uid, controller_type, name)
                    self.logger.debug(f"已註冊設備: {name} ({uid}), 類型: {device_type_str}")
            except Exception as e:
                self.logger.error(f"註冊設備到控制器時發生錯誤: {e}")
    
    def format_mac_address(self, mac_address: str) -> str:
        """將 MAC 地址格式化為冒號分隔的形式"""
        # 移除所有冒號，以防萬一有冒號的情況
        mac_without_colon = mac_address.replace(":", "")
        
        # 確保有足夠的字符（12個十六進位數字）
        if len(mac_without_colon) != 12:
            return mac_address  # 如果格式不正確，返回原始值
            
        # 每兩個字符插入一個冒號
        mac_parts = [mac_without_colon[i:i+2] for i in range(0, 12, 2)]
        return ":".join(mac_parts).upper()
    
    def get_all_devices(self) -> List[Dict[str, Any]]:
        """獲取所有設備列表"""
        return self.devices_data.get("devices", [])
    
    def get_device_by_index(self, index: int) -> Optional[Dict[str, Any]]:
        """根據索引獲取設備
        
        Args:
            index: 設備索引（從0開始）
        
        Returns:
            設備信息字典或 None（如果索引無效）
        """
        devices = self.devices_data.get("devices", [])
        if 0 <= index < len(devices):
            return devices[index]
        return None
    
    def get_device_by_uid(self, uid: str) -> Optional[Dict[str, Any]]:
        """根據 UID 獲取設備
        
        Args:
            uid: 設備 UID
        
        Returns:
            設備信息字典或 None（如果未找到）
        """
        # 標準化 UID 格式
        if not uid.startswith('0x'):
            uid = '0x' + uid.lstrip('0x')
            
        devices = self.devices_data.get("devices", [])
        for device in devices:
            if device.get('uid') == uid:
                return device
        return None
    
    def get_device_by_mac(self, mac: str) -> Optional[Dict[str, Any]]:
        """根據 MAC 地址獲取設備
        
        Args:
            mac: MAC 地址
        
        Returns:
            設備信息字典或 None（如果未找到）
        """
        # 標準化 MAC 地址格式
        mac = self.format_mac_address(mac)
        
        devices = self.devices_data.get("devices", [])
        for device in devices:
            if device.get('devMac') == mac:
                return device
        return None
    
    def scan_devices(self, scan_time: float = 5.0) -> List[Dict[str, str]]:
        """掃描附近的網狀網路設備
        
        Args:
            scan_time: 掃描時間（秒）
        
        Returns:
            設備列表，每個設備包含 uuid 和 mac address
        """
        self.logger.info("開始掃描網狀網路裝置...")
        
        # 使用 Provisioner 的掃描函數
        try:
            # 修正：使用 scan_nodes 而不是 scan_devices
            scan_result = self.provisioner.scan_nodes(True, scan_time=scan_time)
            self.logger.info(f"掃描完成，發現 {len(scan_result)} 個設備")
            
            # 格式化 MAC 地址
            for device in scan_result:
                if 'mac address' in device:
                    device['mac address'] = self.format_mac_address(device['mac address'])
                    
            return scan_result
        except Exception as e:
            self.logger.error(f"掃描設備時發生錯誤: {e}")
            return []
    
    def provision_device(self, uuid: str, device_name: str = "", device_type: str = "RGB_LED", 
                         position: str = "") -> Dict[str, Any]:
        """綁定設備到網路
        
        Args:
            uuid: 設備 UUID
            device_name: 設備名稱
            device_type: 設備類型，如 'RGB_LED', 'PLUG' 等
            position: 設備位置
            
        Returns:
            包含操作結果和信息的字典
        """
        self.logger.info(f"開始綁定設備 UUID: {uuid}")
        
        try:
            # 使用 provisioner 進行綁定
            result = self.provisioner.auto_provision_node(uuid)
            
            if result and 'unicast_addr' in result:
                unicast_addr = result['unicast_addr']
                self.logger.info(f"綁定成功! 設備地址: {unicast_addr}")
                
                # 從掃描結果中查詢 MAC 地址
                mac_address = ""
                # 修正：使用 scan_nodes 而不是 scan_devices
                scan_result = self.provisioner.scan_nodes(True, scan_time=1)
                for device in scan_result:
                    if device.get('uuid') == uuid:
                        mac_address = self.format_mac_address(device.get('mac address', ''))
                        break
                
                # 如果未提供名稱，使用默認格式
                if not device_name:
                    device_name = f"Device_{mac_address[-5:].replace(':', '')}" if mac_address else f"Device_{uuid[-6:]}"
                
                # 註冊到控制器
                controller_type = self._get_controller_device_type(device_type)
                self.controller.register_device(unicast_addr, controller_type, device_name)
                
                # 將設備添加到 JSON 數據中
                # 注意這裡 devName 存放類型，devType 存放名稱
                new_device = {
                    "devMac": mac_address,
                    "devName": device_type,  # 存放類型
                    "devType": device_name,  # 存放名稱
                    "devPosition": position,
                    "devGroup": "",
                    "uid": unicast_addr,
                    "state": 1,
                    "subscribe": [],
                    "publish": ""
                }
                
                # 檢查是否已存在相同 MAC 的設備
                if mac_address:
                    existing_device = next((d for d in self.devices_data["devices"] 
                                           if d.get("devMac") == mac_address), None)
                    if existing_device:
                        # 更新現有設備
                        self.logger.info(f"更新現有設備 MAC: {mac_address}")
                        self.devices_data["devices"].remove(existing_device)
                
                self.devices_data["devices"].append(new_device)
                self.save_device_data()
                
                self.logger.info(f"設備 {device_name} 已成功綁定並添加到設備數據檔案")
                
                return {
                    "result": "success",
                    "unicast_addr": unicast_addr,
                    "device": new_device
                }
            else:
                self.logger.error(f"綁定失敗: {result}")
                return {
                    "result": "failed",
                    "error": str(result)
                }
        except Exception as e:
            self.logger.error(f"綁定過程中發生錯誤: {e}")
            traceback.print_exc()
            return {
                "result": "error",
                "error": str(e)
            }
    
    def _get_controller_device_type(self, device_type_str: str) -> int:
        """將設備類型字符串轉換為控制器使用的常量"""
        type_mapping = {
            "RGB_LED": RLMeshDeviceController.DEVICE_TYPE_RGB_LED,
            "PLUG": RLMeshDeviceController.DEVICE_TYPE_PLUG,
            "SMART_BOX": RLMeshDeviceController.DEVICE_TYPE_SMART_BOX,
            "AIR_BOX": RLMeshDeviceController.DEVICE_TYPE_AIR_BOX,
            "POWER_METER": RLMeshDeviceController.DEVICE_TYPE_POWER_METER
        }
        return type_mapping.get(device_type_str, RLMeshDeviceController.DEVICE_TYPE_RGB_LED)
    
    def set_device_name(self, device_id: Union[int, str], new_name: str) -> Dict[str, Any]:
        """設定設備名稱
        
        Args:
            device_id: 設備索引（從0開始）或 UID
            new_name: 新的設備名稱
            
        Returns:
            操作結果字典
        """
        try:
            # 根據 device_id 類型確定查找方式
            if isinstance(device_id, int):
                device = self.get_device_by_index(device_id)
            else:
                device = self.get_device_by_uid(device_id)
                
            if not device:
                self.logger.error(f"未找到設備 ID: {device_id}")
                return {"result": "failed", "error": "未找到設備"}
            
            old_name = device.get('devType') or '未命名'  # 從 devType 讀取舊名稱
            device['devType'] = new_name                 # 將新名稱寫入 devType
            self.save_device_data()
            
            self.logger.info(f"設備名稱已從 {old_name} 更新為 {new_name}")
            
            # 同時更新控制器中的設備名稱
            uid = device.get('uid', '')
            if uid in self.controller.get_registered_devices():
                device_info = self.controller.get_registered_devices()[uid]
                device_info['name'] = new_name
            
            return {"result": "success", "old_name": old_name, "new_name": new_name}
            
        except Exception as e:
            self.logger.error(f"設定設備名稱時發生錯誤: {e}")
            return {"result": "error", "error": str(e)}
    
    def set_subscription(self, device_id: Union[int, str], group_addr: str) -> Dict[str, Any]:
        """為設備設定訂閱
        
        Args:
            device_id: 設備索引（從0開始）或 UID
            group_addr: 組地址，例如 '0xC000'
            
        Returns:
            操作結果字典
        """
        try:
            # 根據 device_id 類型確定查找方式
            if isinstance(device_id, int):
                device = self.get_device_by_index(device_id)
            else:
                device = self.get_device_by_uid(device_id)
                
            if not device:
                self.logger.error(f"未找到設備 ID: {device_id}")
                return {"result": "failed", "error": "未找到設備"}
            
            unicast_addr = device.get('uid', '')
            device_name = device.get('devType') or '未命名'  # 從 devType 讀取名稱
            
            # 確保 unicast_addr 格式正確
            if not unicast_addr.startswith('0x'):
                unicast_addr = '0x' + unicast_addr
            
            self.logger.info(f"為設備 {device_name} ({unicast_addr}) 設定訂閱...")
            
            # 確保 group_addr 格式正確
            if not group_addr.startswith('0x'):
                group_addr = '0x' + group_addr
                
            # 設定訂閱
            result = self.provisioner.subscribe_group(unicast_addr, group_addr)
            
            if "MSAA" in result and "SUCCESS" in result:
                self.logger.info(f"訂閱設定成功: {result}")
                # 更新設備的訂閱資訊
                if "subscribe" not in device:
                    device["subscribe"] = []
                # 移除可能存在的舊的訂閱
                device["subscribe"] = [sub for sub in device["subscribe"] if sub != group_addr]
                # 添加新的訂閱
                device["subscribe"].append(group_addr)
                
                # 更新設備數據
                self.save_device_data()
                self.logger.info(f"已更新訂閱資訊，當前設備訂閱列表：{device['subscribe']}")
                
                return {
                    "result": "success", 
                    "message": result,
                    "subscribe_list": device['subscribe']
                }
            else:
                self.logger.error(f"訂閱設定失敗: {result}")
                return {"result": "failed", "error": result}
                
        except Exception as e:
            self.logger.error(f"訂閱設定過程中發生錯誤: {e}")
            traceback.print_exc()
            return {"result": "error", "error": str(e)}
    
    def set_publication(self, device_id: Union[int, str], pub_addr: str) -> Dict[str, Any]:
        """為設備設定推播
        
        Args:
            device_id: 設備索引（從0開始）或 UID
            pub_addr: 推播目標地址，例如 '0xC001'
            
        Returns:
            操作結果字典
        """
        try:
            # 根據 device_id 類型確定查找方式
            if isinstance(device_id, int):
                device = self.get_device_by_index(device_id)
            else:
                device = self.get_device_by_uid(device_id)
                
            if not device:
                self.logger.error(f"未找到設備 ID: {device_id}")
                return {"result": "failed", "error": "未找到設備"}
            
            unicast_addr = device.get('uid', '')
            device_name = device.get('devType') or '未命名'  # 從 devType 讀取名稱
            
            # 確保 unicast_addr 格式正確
            if not unicast_addr.startswith('0x'):
                unicast_addr = '0x' + unicast_addr
            
            self.logger.info(f"為設備 {device_name} ({unicast_addr}) 設定推播...")
            
            # 確保 pub_addr 格式正確
            if not pub_addr.startswith('0x'):
                pub_addr = '0x' + pub_addr
            
            # 設定推播
            result = self.provisioner.publish_to_target(unicast_addr, pub_addr)
            
            if "MPAS-MSG SUCCESS" in result:
                self.logger.info(f"推播設定成功: {result}")
                # 更新推播設定
                device["publish"] = pub_addr
                
                # 更新設備數據
                self.save_device_data()
                self.logger.info(f"已更新推播資訊，當前設備推播通道：{pub_addr}")
                
                return {
                    "result": "success", 
                    "message": result,
                    "publish": pub_addr
                }
            else:
                self.logger.error(f"推播設定失敗: {result}")
                return {"result": "failed", "error": result}
                
        except Exception as e:
            self.logger.error(f"推播設定過程中發生錯誤: {e}")
            traceback.print_exc()
            return {"result": "error", "error": str(e)}
    
    def unbind_device(self, device_id: Union[int, str], force_remove: bool = False) -> Dict[str, Any]:
        """解除綁定裝置
        
        Args:
            device_id: 設備索引（從0開始）或 UID
            force_remove: 是否強制從數據文件中刪除（即使解綁失敗）
            
        Returns:
            操作結果字典
        """
        try:
            # 根據 device_id 類型確定查找方式
            if isinstance(device_id, int):
                device = self.get_device_by_index(device_id)
            else:
                device = self.get_device_by_uid(device_id)
                
            if not device:
                self.logger.error(f"未找到設備 ID: {device_id}")
                return {"result": "failed", "error": "未找到設備"}
            
            uid = device.get('uid', '')
            # 確保 uid 有 0x 前綴
            if not uid.startswith('0x'):
                uid = '0x' + uid.lstrip('0x')  # 移除可能存在的 0x 再加上新的
                
            device_name = device.get('devName') or '未命名'
            
            if not uid:
                self.logger.error("選擇的設備沒有有效的 UID")
                return {"result": "failed", "error": "設備沒有有效的 UID"}
            
            self.logger.info(f"正在解除綁定設備 {device_name} ({uid})...")
            
            # 使用 Provisioner 的 node_reset 方法進行解除綁定
            resp = self.provisioner.node_reset(uid)
            self.logger.info(f"解除綁定響應: {resp}")
            
            # 根據回應判斷是否成功
            success = resp and "NR-MSG SUCCESS" in resp
            
            if success or force_remove:
                # 從設備數據中移除
                self.devices_data["devices"].remove(device)
                self.save_device_data()
                
                # 從控制器中移除註冊
                uid_without_prefix = uid
                if uid_without_prefix in self.controller.get_registered_devices():
                    del self.controller.get_registered_devices()[uid_without_prefix]
                
                self.logger.info(f"設備已從設備數據檔案中{'強制' if force_remove and not success else ''}移除")
                return {
                    "result": "success" if success else "forced_removal",
                    "message": f"設備 {device_name} ({uid}) 已{'強制' if force_remove and not success else ''}移除"
                }
            else:
                self.logger.error(f"解除綁定設備失敗: {resp}")
                return {"result": "failed", "error": resp}
                
        except Exception as e:
            self.logger.error(f"解除綁定過程中發生錯誤: {e}")
            traceback.print_exc()
            return {"result": "error", "error": str(e)}
    
    def control_device(self, device_id: Union[int, str], action: str, **params) -> Dict[str, Any]:
        """控制設備執行特定動作
        
        Args:
            device_id: 設備索引（從0開始）或 UID
            action: 動作名稱，例如 'set_rgb', 'toggle' 等
            **params: 動作需要的參數
            
        Returns:
            操作結果字典
        """
        try:
            # 根據 device_id 類型確定查找方式
            if isinstance(device_id, int):
                device = self.get_device_by_index(device_id)
            else:
                device = self.get_device_by_uid(device_id)
                
            if not device:
                self.logger.error(f"未找到設備 ID: {device_id}")
                return {"result": "failed", "error": "未找到設備"}
            
            unicast_addr = device.get('uid', '')
            device_type = device.get('devName') or 'RGB_LED'  # 從 devName 讀取類型
            
            # 根據設備類型和動作執行不同操作
            if device_type == "RGB_LED":
                if action == "set_rgb":
                    cold = params.get('cold', 0)
                    warm = params.get('warm', 0)
                    red = params.get('red', 0)
                    green = params.get('green', 0)
                    blue = params.get('blue', 0)
                    result = self.controller.control_rgb_led(unicast_addr, cold, warm, red, green, blue)
                    
                    # 更新設備狀態
                    if any([cold, warm, red, green, blue]):
                        device['state'] = 1  # 開啟
                    else:
                        device['state'] = 0  # 關閉
                    self.save_device_data()
                    
                    return {"result": "success", "message": result}
                
                elif action == "turn_on":
                    # 開啟燈光 (使用預設值，如暖光)
                    cold = params.get('cold', 0)
                    warm = params.get('warm', 255)  # 默認使用暖光
                    result = self.controller.control_rgb_led(unicast_addr, cold, warm, 0, 0, 0)
                    device['state'] = 1  # 開啟
                    self.save_device_data()
                    return {"result": "success", "message": result}
                    
                elif action == "set_white":
                    # 設為白光
                    cold = params.get('cold', 255)
                    warm = params.get('warm', )
                    result = self.controller.control_rgb_led(unicast_addr, cold, warm, 0, 0, 0)
                    device['state'] = 1  # 開啟
                    self.save_device_data()
                    return {"result": "success", "message": result}
                    
                elif action == "turn_off":
                    # 關閉燈光
                    result = self.controller.control_rgb_led(unicast_addr, 0, 0, 0, 0, 0)
                    device['state'] = 0  # 關閉
                    self.save_device_data()
                    return {"result": "success", "message": result}
                    
                else:
                    return {"result": "failed", "error": f"不支援的動作: {action}"}
                
            elif device_type == "PLUG":
                if action == "toggle":
                    # 切換開關狀態
                    current_state = device.get('state', 0)
                    new_state = not current_state
                    result = self.controller.control_plug(unicast_addr, new_state)
                    device['state'] = 1 if new_state else 0
                    self.save_device_data()
                    return {"result": "success", "message": result, "state": new_state}
                    
                elif action == "turn_on":
                    # 開啟插座
                    result = self.controller.control_plug(unicast_addr, True)
                    device['state'] = 1
                    self.save_device_data()
                    return {"result": "success", "message": result}
                    
                elif action == "turn_off":
                    # 關閉插座
                    result = self.controller.control_plug(unicast_addr, False)
                    device['state'] = 0
                    self.save_device_data()
                    return {"result": "success", "message": result}
                    
                else:
                    return {"result": "failed", "error": f"不支援的動作: {action}"}
                    
            # 可以根據需要擴展其他設備類型的控制功能
            else:
                return {"result": "failed", "error": f"不支援的設備類型: {device_type}"}
                
        except Exception as e:
            self.logger.error(f"控制設備時發生錯誤: {e}")
            traceback.print_exc()
            return {"result": "error", "error": str(e)}
    
    def display_devices(self) -> str:
        """格式化顯示所有設備信息
        
        Returns:
            格式化的設備列表字符串
        """
        devices = self.devices_data.get("devices", [])
        
        if not devices:
            return "目前沒有已綁定的設備"
        
        result = [f"\n===== 設備列表 =====", f"設備總數: {len(devices)}"]
        
        # 定義欄位
        headers = ["序號", "名稱", "MAC地址", "類型", "UID", "位置", "狀態", "訂閱通道", "推播通道"]
        
        # 處理每個設備
        for idx, device in enumerate(devices):
            name = device.get('devType') or '未命名'        # devType 存放名稱
            mac = device.get('devMac') or '未知'
            device_type = device.get('devName') or '未指定'  # devName 存放類型
            uid = device.get('uid', '未知')
            position = device.get('devPosition') or '未設定'
            state_code = device.get('state')
            state = "開啟" if state_code == 1 else "關閉" if state_code == 0 else "未知"
            
            # 處理訂閱和推播資訊
            subscribe_list = device.get('subscribe', [])
            if isinstance(subscribe_list, list):
                subscribe_str = ', '.join(subscribe_list) if subscribe_list else '未設定'
            else:
                subscribe_str = str(subscribe_list)
            publish_addr = device.get('publish', '未設定')
            
            # 格式化輸出
            device_info = [
                f"{idx+1}", name, mac, device_type, uid, position, state, subscribe_str, publish_addr
            ]
            
            result.append(" | ".join(device_info))
        
        return "\n".join(result)

    def get_device_ids(self) -> List[str]:
        """獲取所有設備的 ID 列表
        
        Returns:
            設備 ID 列表
        """
        return [device.get('uid', '') for device in self.devices_data.get("devices", [])]
        
    def get_device_names(self) -> List[str]:
        """獲取所有設備的名稱列表
        
        Returns:
            設備名稱列表
        """
        return [device.get('devType', '未命名') for device in self.devices_data.get("devices", [])]