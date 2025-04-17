import json
import os
import logging
from typing import Dict, List, Optional, Any, Union

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s][%(module)s:%(lineno)d] %(message)s'
)

class DeviceManager:
    """
    設備管理類，使用JSON檔案紀錄並管理網狀網路設備的綁定和連動關係
    """
    def __init__(self, json_file_path: str = "devices.json"):
        """
        初始化設備管理器
        
        Args:
            json_file_path: JSON檔案路徑，預設為'devices.json'
        """
        self.json_file_path = json_file_path
        self.devices = []
        self.groups = {}
        
        # 如果檔案存在，則載入資料
        if os.path.exists(json_file_path):
            self.load_devices()
        else:
            # 建立初始結構並保存
            self.save_devices()
        
    def load_devices(self) -> None:
        """從JSON檔案載入設備資訊"""
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.devices = data.get('devices', [])
                self.groups = data.get('groups', {})
            logging.info(f"已從 {self.json_file_path} 載入 {len(self.devices)} 台設備")
        except Exception as e:
            logging.error(f"載入設備資訊時發生錯誤: {e}")
            self.devices = []
            self.groups = {}
    
    def save_devices(self) -> None:
        """將設備資訊保存到JSON檔案"""
        data = {
            'devices': self.devices,
            'groups': self.groups
        }
        try:
            with open(self.json_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logging.info(f"已保存 {len(self.devices)} 台設備到 {self.json_file_path}")
        except Exception as e:
            logging.error(f"保存設備資訊時發生錯誤: {e}")
    
    def add_device(self, uuid: str, mac_address: str, unicast_addr: str, name: Optional[str] = None, device_type: Optional[str] = None) -> Dict[str, Any]:
        """
        新增設備
        
        Args:
            uuid: 設備UUID
            mac_address: 設備MAC地址
            unicast_addr: 設備的unicast地址
            name: 設備名稱 (可選)
            device_type: 設備類型 (可選)
            
        Returns:
            新增的設備信息
        """
        # 檢查是否已經存在相同UUID或unicast地址的設備
        for device in self.devices:
            if device['uuid'] == uuid:
                logging.warning(f"UUID為 {uuid} 的設備已存在")
                return device
            if device['unicast_addr'] == unicast_addr:
                logging.warning(f"unicast地址為 {unicast_addr} 的設備已存在")
                return device
                
        # 創建新設備
        device = {
            'uuid': uuid,
            'mac_address': mac_address,
            'unicast_addr': unicast_addr,
            'name': name or f"Device-{unicast_addr}",
            'type': device_type or "未指定",
            'group': None,
            'linked_devices': []
        }
        
        self.devices.append(device)
        self.save_devices()
        logging.info(f"已新增設備: {name or unicast_addr}, 類型: {device_type or '未指定'}")
        return device
    
    def get_device_by_unicast(self, unicast_addr: str) -> Optional[Dict[str, Any]]:
        """
        透過unicast地址獲取設備
        
        Args:
            unicast_addr: 設備的unicast地址
            
        Returns:
            設備信息 或 None
        """
        for device in self.devices:
            if device['unicast_addr'] == unicast_addr:
                return device
        return None
    
    def get_device_by_uuid(self, uuid: str) -> Optional[Dict[str, Any]]:
        """
        透過UUID獲取設備
        
        Args:
            uuid: 設備UUID
            
        Returns:
            設備信息 或 None
        """
        for device in self.devices:
            if device['uuid'] == uuid:
                return device
        return None
    
    def remove_device(self, unicast_addr: str) -> bool:
        """
        移除單一設備
        
        Args:
            unicast_addr: 設備的unicast地址
            
        Returns:
            是否成功移除
        """
        initial_length = len(self.devices)
        
        # 移除設備
        self.devices = [d for d in self.devices if d['unicast_addr'] != unicast_addr]
        
        # 從所有設備的連動列表中移除此設備
        for device in self.devices:
            if unicast_addr in device['linked_devices']:
                device['linked_devices'].remove(unicast_addr)
        
        # 從所有群組中移除此設備
        for group_name, group_devices in self.groups.items():
            if unicast_addr in group_devices:
                self.groups[group_name].remove(unicast_addr)
        
        # 保存變更
        self.save_devices()
        
        success = len(self.devices) < initial_length
        if success:
            logging.info(f"設備 {unicast_addr} 已移除")
        else:
            logging.warning(f"未找到設備 {unicast_addr}")
        return success
    
    def remove_all_devices(self) -> None:
        """移除所有設備"""
        self.devices = []
        self.groups = {}
        self.save_devices()
        logging.info("所有設備已移除")
    
    def create_group(self, group_name: str) -> bool:
        """
        創建設備群組
        
        Args:
            group_name: 群組名稱
            
        Returns:
            是否成功創建
        """
        if group_name in self.groups:
            logging.warning(f"群組 '{group_name}' 已存在")
            return False
        
        self.groups[group_name] = []
        self.save_devices()
        logging.info(f"已創建群組 '{group_name}'")
        return True
    
    def add_device_to_group(self, unicast_addr: str, group_name: str) -> bool:
        """
        將設備添加到群組
        
        Args:
            unicast_addr: 設備的unicast地址
            group_name: 群組名稱
            
        Returns:
            是否成功添加
        """
        # 檢查設備和群組是否存在
        device = self.get_device_by_unicast(unicast_addr)
        if not device:
            logging.warning(f"設備 {unicast_addr} 不存在")
            return False
        
        if group_name not in self.groups:
            logging.warning(f"群組 '{group_name}' 不存在")
            return False
        
        # 先從其他群組中移除此設備
        for g_name in self.groups:
            if unicast_addr in self.groups[g_name]:
                self.groups[g_name].remove(unicast_addr)
        
        # 添加到指定群組
        if unicast_addr not in self.groups[group_name]:
            self.groups[group_name].append(unicast_addr)
        
        # 更新設備的群組信息
        device['group'] = group_name
        
        self.save_devices()
        logging.info(f"設備 {unicast_addr} 已添加到群組 '{group_name}'")
        return True
    
    def remove_device_from_group(self, unicast_addr: str, group_name: Optional[str] = None) -> bool:
        """
        從群組中移除設備
        
        Args:
            unicast_addr: 設備的unicast地址
            group_name: 群組名稱，若為None則從任何群組中移除
            
        Returns:
            是否成功移除
        """
        device = self.get_device_by_unicast(unicast_addr)
        if not device:
            logging.warning(f"設備 {unicast_addr} 不存在")
            return False
        
        removed = False
        
        if group_name:
            # 從指定群組中移除
            if group_name in self.groups and unicast_addr in self.groups[group_name]:
                self.groups[group_name].remove(unicast_addr)
                removed = True
        else:
            # 從任何群組中移除
            for g_name in self.groups:
                if unicast_addr in self.groups[g_name]:
                    self.groups[g_name].remove(unicast_addr)
                    removed = True
        
        if removed:
            # 更新設備的群組信息
            device['group'] = None
            self.save_devices()
            logging.info(f"設備 {unicast_addr} 已從群組中移除")
            return True
        else:
            logging.warning(f"設備 {unicast_addr} 不在指定群組中")
            return False
    
    def link_devices(self, source_unicast: str, target_unicast: str) -> bool:
        """
        建立設備間的連動關係
        
        Args:
            source_unicast: 來源設備的unicast地址
            target_unicast: 目標設備的unicast地址
            
        Returns:
            是否成功建立連動關係
        """
        source = self.get_device_by_unicast(source_unicast)
        target = self.get_device_by_unicast(target_unicast)
        
        if not source or not target:
            logging.warning(f"無法連動: 來源或目標設備不存在")
            return False
        
        if source_unicast == target_unicast:
            logging.warning(f"無法連動: 不能與自己連動")
            return False
        
        if target_unicast not in source['linked_devices']:
            source['linked_devices'].append(target_unicast)
            self.save_devices()
            logging.info(f"設備 {source_unicast} 已與 {target_unicast} 建立連動關係")
            return True
        else:
            logging.warning(f"設備 {source_unicast} 已與 {target_unicast} 建立連動關係")
            return False
    
    def unlink_devices(self, source_unicast: str, target_unicast: str) -> bool:
        """
        解除設備間的連動關係
        
        Args:
            source_unicast: 來源設備的unicast地址
            target_unicast: 目標設備的unicast地址
            
        Returns:
            是否成功解除連動關係
        """
        source = self.get_device_by_unicast(source_unicast)
        
        if not source:
            logging.warning(f"來源設備 {source_unicast} 不存在")
            return False
        
        if target_unicast in source['linked_devices']:
            source['linked_devices'].remove(target_unicast)
            self.save_devices()
            logging.info(f"已解除設備 {source_unicast} 與 {target_unicast} 的連動關係")
            return True
        else:
            logging.warning(f"設備 {source_unicast} 與 {target_unicast} 之間沒有連動關係")
            return False
    
    def get_linked_devices(self, unicast_addr: str) -> List[str]:
        """
        獲取與指定設備連動的所有設備
        
        Args:
            unicast_addr: 設備的unicast地址
            
        Returns:
            連動設備的unicast地址列表
        """
        device = self.get_device_by_unicast(unicast_addr)
        if not device:
            logging.warning(f"設備 {unicast_addr} 不存在")
            return []
        
        return device.get('linked_devices', [])
    
    def get_group_devices(self, group_name: str) -> List[str]:
        """
        獲取群組中的所有設備
        
        Args:
            group_name: 群組名稱
            
        Returns:
            群組中設備的unicast地址列表
        """
        if group_name not in self.groups:
            logging.warning(f"群組 '{group_name}' 不存在")
            return []
        
        return self.groups[group_name]
        
    def get_device_info(self) -> Dict[str, Any]:
        """
        獲取所有設備和群組信息
        
        Returns:
            包含所有設備和群組信息的字典
        """
        return {
            'devices': self.devices,
            'groups': self.groups,
            'device_count': len(self.devices),
            'group_count': len(self.groups)
        }