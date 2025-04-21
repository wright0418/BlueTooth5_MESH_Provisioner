"""
RL62M02 - RL Mesh 設備配置與控制套件

該套件提供了與 RL Mesh 設備通訊的功能，
包括設備掃描、配置、控制等操作。
"""

import os
import sys
import importlib.util
__version__ = "0.1.0"

from .serial_at import SerialAT
from .provisioner import Provisioner

# 檢查上層目錄中的 device_manager.py 是否存在
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
device_manager_path = os.path.join(parent_dir, "device_manager.py")
DeviceManager = None

if os.path.exists(device_manager_path):
    # 動態導入 device_manager.py
    sys.path.insert(0, parent_dir)
    import device_manager
    DeviceManager = device_manager.DeviceManager
    sys.path.pop(0)

# 提供便捷函數，讓使用者可以輕鬆地初始化系統
def create_provisioner(com_port, baudrate=115200, device_manager_file=None):
    """
    快速建立一個配置器實例
    
    Args:
        com_port (str): COM 埠，例如 "COM3"
        baudrate (int, optional): 鮑率。預設為 115200
        device_manager_file (str, optional): 設備管理檔案路徑，預設使用上層目錄的 mesh_devices.json
        
    Returns:
        tuple: (SerialAT, Provisioner, DeviceManager) 三個主要物件的實例，如果 DeviceManager 不可用則返回 None
    """
    ser = SerialAT(com_port, baudrate)
    prov = Provisioner(ser)
    
    device_manager_instance = None
    if DeviceManager is not None:
        # 如果未指定檔案路徑，使用預設路徑
        if device_manager_file is None:
            device_manager_file = os.path.join(parent_dir, "mesh_devices.json")
        device_manager_instance = DeviceManager(device_manager_file)
    
    return ser, prov, device_manager_instance

# 簡化函數，使得使用者只需調用一行代碼即可執行常見操作
def scan_devices(provisioner, scan_time=5.0):
    """掃描附近的 RL Mesh 設備"""
    return provisioner.scan_nodes(scan_time=scan_time)

def provision_device(provisioner, uuid, device_manager=None, device_name=None, device_type=None):
    """
    配置並綁定設備
    
    Args:
        provisioner: Provisioner 實例
        uuid: 要綁定設備的 UUID
        device_manager: DeviceManager 實例，可選
        device_name: 設備名稱，可選
        device_type: 設備類型，可選
        
    Returns:
        dict: 綁定結果
    """
    result = provisioner.auto_provision_node(uuid)
    
    # 如果有設備管理器和成功綁定，則添加設備
    if device_manager and result.get("result") == "success":
        unicast_addr = result.get("unicast_addr")
        if not device_name:
            device_name = f"Device-{unicast_addr}"
        if not device_type:
            device_type = "未指定"
            
        # 獲取掃描結果中的設備 MAC 地址
        devices = provisioner.scan_nodes(scan_time=1.0)
        mac_address = ""
        for device in devices:
            if device.get('uuid') == uuid:
                mac_address = device.get('mac address', "")
                break
                
        device_manager.add_device(uuid, mac_address, unicast_addr, device_name, device_type)
    
    return result