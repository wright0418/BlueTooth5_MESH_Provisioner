from .serial_at import SerialAT
from .provisioner import Provisioner
from .controllers.mesh_controller import RLMeshDeviceController
from .device_manager import MeshDeviceManager

def create_provisioner(com_port, baud_rate=115200):
    """
    創建 Provisioner 和相關物件
    
    Args:
        com_port (str): COM 埠，例如 "COM3"
        baud_rate (int): 波特率，預設為 115200
        
    Returns:
        tuple: (SerialAT 實例, Provisioner 實例, None)
    """
    from .serial_at import SerialAT
    from .provisioner import Provisioner
    
    # 創建 SerialAT 物件
    serial_at = SerialAT(com_port, baud_rate)
    
    # 創建 Provisioner 物件
    prov = Provisioner(serial_at)
    
    # 返回物件元組，為了兼容性，第三個元素保持為 None
    return (serial_at, prov, None)

def provision_device(provisioner, uuid):
    """
    綁定設備到 Mesh 網路
    
    Args:
        provisioner (Provisioner): Provisioner 實例
        uuid (str): 設備 UUID
        
    Returns:
        dict: 包含綁定結果和訊息的字典
    """
    return provisioner.auto_provision_node(uuid)

__all__ = [
    'SerialAT',
    'Provisioner',
    'provision_device',
    'create_provisioner',
    'RLMeshDeviceController',
    'MeshDeviceManager',
]