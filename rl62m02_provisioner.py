import threading
import serial
import time
from typing import Callable, Optional
import logging
import inspect
from device_manager import DeviceManager  # 導入DeviceManager

# 設定 logging 格式，包含 module name 與 line number
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s][%(module)s:%(lineno)d] %(message)s'
)

class SerialAT:
    def __init__(self, port: str, baudrate: int = 115200, on_receive: Optional[Callable[[str], None]] = None):
        self.port = port
        self.baudrate = baudrate
        self.ser = serial.Serial(port, baudrate, timeout=1)
        self.on_receive = on_receive
        self._stop_event = threading.Event()
        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        time.sleep(2)
        self.ser.reset_input_buffer()
        self._recv_thread.start()
        self._response_queue = []  # 用於存儲收到的響應
        self._response_event = threading.Event()  # 用於通知有新響應

    def send(self, cmd: str):
        if not cmd.endswith('\r\n'):
            cmd += '\r\n'
        self.ser.write(cmd.encode('utf-8'))
        self.ser.flush()

    def _recv_loop(self):
        buffer = ''
        while not self._stop_event.is_set():
            try:
                if self.ser.in_waiting:
                    data = self.ser.read(self.ser.in_waiting)
                    if data:
                        buffer += data.decode('utf-8', errors='ignore')
                        while '\r\n' in buffer:
                            line, buffer = buffer.split('\r\n', 1)
                            logging.debug(f"RX: {line}")
                            # 將接收到的行添加到響應隊列
                            self._response_queue.append(line)
                            self._response_event.set()  # 通知有新響應
                            if self.on_receive:
                                self.on_receive(line)
                else:
                    time.sleep(0.1)
            except Exception as e:
                logging.debug(f"Exception: {e}")
                time.sleep(0.1)
    
    def wait_for_response(self, prefix: str, target_uid: str = None, timeout: float = 2.0):
        """
        等待指定前綴的響應，並可選擇性地檢查UID
        
        Args:
            prefix (str): 響應前綴
            target_uid (str, optional): 目標UID (unicast_addr)，如果提供則檢查UID是否匹配
            timeout (float): 超時時間，默認2秒
            
        Returns:
            str: 匹配的響應，如果超時則返回None
        """
        start_time = time.time()
        # 先檢查現有隊列
        for resp in list(self._response_queue):
            if resp.startswith(prefix):
                # 如果需要檢查UID
                if target_uid and prefix == "MDTG-MSG":
                    parts = resp.split()
                    # 確保有足夠的部分且UID匹配
                    if len(parts) >= 3 and parts[1] == target_uid:
                        self._response_queue.remove(resp)
                        return resp
                # 如果不需要檢查UID或者不是MDTG-MSG
                elif not target_uid:
                    self._response_queue.remove(resp)
                    return resp
        
        # 等待新響應
        while time.time() - start_time < timeout:
            if self._response_event.wait(0.1):  # 短暫等待以便檢查是否有新響應
                self._response_event.clear()
                # 檢查隊列中是否有匹配的響應
                for resp in list(self._response_queue):
                    if resp.startswith(prefix):
                        # 如果需要檢查UID
                        if target_uid and prefix == "MDTG-MSG":
                            parts = resp.split()
                            # 確保有足夠的部分且UID匹配
                            if len(parts) >= 3 and parts[1] == target_uid:
                                self._response_queue.remove(resp)
                                return resp
                        # 如果不需要檢查UID或者不是MDTG-MSG
                        elif not target_uid:
                            self._response_queue.remove(resp)
                            return resp
        
        return None  # 超時，沒有找到匹配的響應

    def close(self):
        self._stop_event.set()
        if self._recv_thread.is_alive():
            self._recv_thread.join(timeout=1.0)
        if self.ser.is_open:
            self.ser.close()

class Provisioner:
    DEFAULT_TIMEOUT = 2.0
    PROV_TIMEOUT = 8.0
    AKA_TIMEOUT = 5.0
    MAKB_TIMEOUT = 5.0
    NR_TIMEOUT = 3.0
    MODEL_ID = '0x4005D'
    APP_KEY_IDX = 0
    NET_KEY_IDX = 0
    
    def __init__(self, serial_at: SerialAT):
        self.serial_at = serial_at
        self.last_response = None
        self.responses = []
        self.serial_at.on_receive = self._on_receive
        self._response_event = threading.Event()

    def _on_receive(self, line: str):
        self.responses.append(line)
        self.last_response = line
        self._response_event.set()

    def _send_and_wait(self, cmd: str, timeout: float = None):
        if timeout is None:
            timeout = self.DEFAULT_TIMEOUT
        self._response_event.clear()
        self.serial_at.send(cmd)
        if self._response_event.wait(timeout):
            return self.last_response
        return None

    def get_version(self):
        resp = self._send_and_wait('AT+VER')
        if resp and resp.startswith('VER-MSG'):
            return resp
        return None

    def set_name(self, name: str):
        resp = self._send_and_wait(f'AT+NAME {name}')
        return resp

    def reboot(self):
        resp = self._send_and_wait('AT+REBOOT')
        return resp

    def get_role(self):
        resp = self._send_and_wait('AT+MRG')
        return resp

    def scan_nodes(self, enable: bool = True, scan_time: float = 3.0):
        """
        啟動掃描，回傳不重複的字典列表，每個字典包含 mac address 與 uuid。
        """
        if not enable:
            self._send_and_wait('AT+DIS 0')
            return []
        self.responses.clear()
        self._send_and_wait('AT+DIS 1')
        time.sleep(scan_time)
        self._send_and_wait('AT+DIS 0')
        mac_uuid_dict = {}
        for r in self.responses:
            if r.startswith('DIS-MSG '):
                parts = r.split()
                if len(parts) == 4:
                    mac = parts[1]
                    uuid = parts[3]
                    mac_uuid_dict[uuid] = mac  # 以 uuid 當 key 去重複
        return [{"mac address": mac, "uuid": uuid} for uuid, mac in mac_uuid_dict.items()]

    def provision(self, dev_uuid: str):
        resp = self._send_and_wait(f'AT+PBADVCON {dev_uuid}')
        if resp and resp.startswith('PBADVCON-MSG SUCCESS'):
            prov_resp = self._send_and_wait('AT+PROV')
            return prov_resp
        return resp

    def get_node_list(self):
        self.responses.clear()
        self.serial_at.send('AT+NL')
        time.sleep(1)
        return [r for r in self.responses if r.startswith('NL-MSG')]

    def set_appkey(self, dst: str, app_key_index: int, net_key_index: int):
        resp = self._send_and_wait(f'AT+AKA {dst} {app_key_index} {net_key_index}')
        return resp

    def auto_provision_node(self, uuid: str):
        """
        自動配置並綁定節點，傳入 uuid，完成 provision、AppKey 綁定與 Model AppKey 綁定。
        若任一步驟失敗或 timeout，會自動跳出，若已產生 unicast address 則自動刪除。
        回傳 unicast address 或錯誤訊息。
        """
        unicast_addr = None
        # 1. 開啟 PB-ADV 通道
        resp = self._send_and_wait(f'AT+PBADVCON {uuid}', timeout=self.AKA_TIMEOUT)
        if not resp or not resp.startswith('PBADVCON-MSG SUCCESS'):
            logging.warning(f'PBADVCON 失敗: {resp}')
            return {'result': 'fail', 'step': 'PBADVCON', 'msg': resp}
        # 2. 執行 Provisioning
        prov_resp = self._send_and_wait('AT+PROV', timeout=self.PROV_TIMEOUT)
        if not prov_resp or not prov_resp.startswith('PROV-MSG SUCCESS'):
            logging.warning(f'PROV 失敗: {prov_resp}')
            return {'result': 'fail', 'step': 'PROV', 'msg': prov_resp}
        # 取得 unicast address
        parts = prov_resp.split()
        if len(parts) < 3:
            logging.error(f'PROV 回應格式錯誤: {prov_resp}')
            return {'result': 'fail', 'step': 'PROV', 'msg': prov_resp}
        unicast_addr = parts[2]
        # 3. AppKey 綁定
        aka_resp = self._send_and_wait(f'AT+AKA {unicast_addr} {self.APP_KEY_IDX} {self.NET_KEY_IDX}', timeout=self.AKA_TIMEOUT)
        if not aka_resp or not aka_resp.startswith('AKA-MSG SUCCESS'):
            if unicast_addr:
                self._send_and_wait(f'AT+NR {unicast_addr}', timeout=self.NR_TIMEOUT)
            logging.warning(f'AKA 綁定失敗: {aka_resp}')
            return {'result': 'fail', 'step': 'AKA', 'msg': aka_resp, 'unicast_addr': unicast_addr, 'nr': 'sent'}
        # 4. Model AppKey 綁定
        makb_resp = self._send_and_wait(f'AT+MAKB {unicast_addr} {self.APP_KEY_IDX} {self.MODEL_ID} {self.NET_KEY_IDX}', timeout=self.MAKB_TIMEOUT)
        if not makb_resp or not makb_resp.startswith('MAKB-MSG SUCCESS'):
            if unicast_addr:
                self._send_and_wait(f'AT+NR {unicast_addr}', timeout=self.NR_TIMEOUT)
            logging.warning(f'MAKB 綁定失敗: {makb_resp}')
            return {'result': 'fail', 'step': 'MAKB', 'msg': makb_resp, 'unicast_addr': unicast_addr, 'nr': 'sent'}
        logging.info(f'自動綁定成功: {unicast_addr}')
        return {'result': 'success', 'unicast_addr': unicast_addr}

    def subscribe_group(self, unicast_addr: str, group_addr: str, element_index: int = 0, model_id: str = None):
        if model_id is None:
            model_id = self.MODEL_ID
        resp = self._send_and_wait(f'AT+MSAA {unicast_addr} {element_index} {model_id} {group_addr}', timeout=3.0)
        return resp

    def publish_to_target(self, unicast_addr: str, publish_addr: str, element_index: int = 0, model_id: str = None, app_key_idx: int = None):
        if model_id is None:
            model_id = self.MODEL_ID
        if app_key_idx is None:
            app_key_idx = self.APP_KEY_IDX
        resp = self._send_and_wait(f'AT+MPAS {unicast_addr} {element_index} {model_id} {publish_addr} {app_key_idx}', timeout=3.0)
        return resp

    def send_datatrans(self, unicast_addr: str, data: str, element_index: int = 0, app_key_idx: int = 0, ack: int = 0):
        """
        設定 Vendor Model - Datatrans Model 的狀態 (AT+MDTS)
        data: 1~20 bytes 的 16進位字串 (如 '0x112233')
        ack: 0=不回應, 1=需回應
        """
        resp = self._send_and_wait(f'AT+MDTS {unicast_addr} {element_index} {app_key_idx} {ack} {data}', timeout=3.0)
        return resp

    def get_datatrans(self, unicast_addr: str, read_data_len: int, element_index: int = 0, app_key_idx: int = 0):
        """
        查詢 Vendor Model - Datatrans Model 的狀態 (AT+MDTG)
        read_data_len: 讀取資料長度 (byte 數)
        """
        resp = self._send_and_wait(f'AT+MDTG {unicast_addr} {element_index} {app_key_idx} {read_data_len}', timeout=3.0)
        return resp

    def observe(self, print_all: bool = True):
        """
        進入觀察模式，持續接收所有周邊訊息，並解析 MDTS/MDTG 訊息。
        MDTG 會解析出來源 unicast_addr 及資料 bytes。
        """
        import re
        print("進入 Provisioner 觀察模式，持續接收所有周邊訊息... (Ctrl+C 返回主選單)")
        def observer_on_receive(line: str):
            if line.startswith('MDTS-MSG'):
                print(f"[MDTS] {line}")
            elif line.startswith('MDTG-MSG'):
                # 解析 MDTG-MSG 0x0100 0 1122334455
                m = re.match(r'MDTG-MSG (0x[0-9A-Fa-f]+) (\d+) ([0-9A-Fa-f]+)', line)
                if m:
                    unicast_addr = m.group(1)
                    element_idx = int(m.group(2))
                    hex_data = m.group(3)
                    data_bytes = bytes.fromhex(hex_data)
                    print(f"[MDTG] 來自 {unicast_addr}，資料: {data_bytes}")
                else:
                    print(f"[MDTG] {line}")
            elif print_all:
                print(f"[INFO] {line}")
        old_on_receive = self.serial_at.on_receive
        self.serial_at.on_receive = observer_on_receive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n離開觀察模式，返回主選單")
        finally:
            self.serial_at.on_receive = old_on_receive

def auto_bind_node(prov: Provisioner, device_manager: Optional[DeviceManager] = None):
    scan_result = prov.scan_nodes(scan_time=5)
    print('掃描結果:', scan_result)
    if scan_result:
        target = scan_result[0]
        print(f"開始自動綁定 UUID: {target['uuid']}")
        result = prov.auto_provision_node(target['uuid'])
        print('自動綁定結果:', result)
        
        # 如果綁定成功且提供了設備管理器，則添加設備到管理器
        if device_manager and result.get('result') == 'success':
            unicast_addr = result.get('unicast_addr')
            name = input('請輸入設備名稱 (或直接Enter使用預設名稱): ').strip()
            name = name or f"Device-{unicast_addr}"
            
            # 讓使用者輸入設備類型
            device_type = input('請輸入設備類型 (如 開關、燈具、感應器等，或直接Enter使用預設類型): ').strip()
            device_type = device_type or "未指定"
            
            device_manager.add_device(target['uuid'], target['mac address'], unicast_addr, name, device_type)
            print(f"設備 {name} (類型: {device_type}) 已添加到設備管理器")
    else:
        print('未掃描到可綁定裝置')

def unbind_node(prov: Provisioner, device_manager: Optional[DeviceManager] = None):
    node_list = prov.get_node_list()
    if not node_list:
        print('目前無已綁定節點')
        return
    print('目前節點清單:')
    for idx, node in enumerate(node_list):
        parts = node.split()
        if len(parts) >= 3:
            unicast_addr = parts[2]
            # 嘗試從設備管理器獲取名稱
            name = "未命名設備"
            if device_manager:
                device = device_manager.get_device_by_unicast(unicast_addr)
                if device:
                    name = device['name']
            print(f"{idx}: unicast_addr={unicast_addr}, 名稱={name}")
    sel = input('請輸入要解綁的節點編號: ').strip()
    try:
        sel_idx = int(sel)
        if 0 <= sel_idx < len(node_list):
            parts = node_list[sel_idx].split()
            unicast_addr = parts[2]
            resp = prov._send_and_wait(f'AT+NR {unicast_addr}', timeout=3.0)
            print(f'解綁結果: {resp}')
            
            # 如果解綁成功且提供了設備管理器，則從管理器中移除設備
            if device_manager and resp and resp.startswith('NR-MSG SUCCESS'):
                if device_manager.remove_device(unicast_addr):
                    print(f"設備 {unicast_addr} 已從設備管理器中移除")
        else:
            print('輸入編號超出範圍')
    except Exception as e:
        print(f'輸入錯誤: {e}')

def subscribe_group_menu(prov: Provisioner):
    node_list = prov.get_node_list()
    if not node_list:
        print('目前無已綁定節點')
        return
    print('目前節點清單:')
    for idx, node in enumerate(node_list):
        parts = node.split()
        if len(parts) >= 3:
            print(f"{idx}: unicast_addr={parts[2]}")
    sel = input('請輸入要訂閱群組的節點編號: ').strip()
    group_addr = input('請輸入 Group Address (如 0xc000): ').strip()
    try:
        sel_idx = int(sel)
        if 0 <= sel_idx < len(node_list):
            parts = node_list[sel_idx].split()
            unicast_addr = parts[2]
            resp = prov.subscribe_group(unicast_addr, group_addr)
            print(f'訂閱群組結果: {resp}')
        else:
            print('輸入編號超出範圍')
    except Exception as e:
        print(f'輸入錯誤: {e}')

def publish_menu(prov: Provisioner):
    node_list = prov.get_node_list()
    if not node_list:
        print('目前無已綁定節點')
        return
    print('目前節點清單:')
    for idx, node in enumerate(node_list):
        parts = node.split()
        if len(parts) >= 3:
            print(f"{idx}: unicast_addr={parts[2]}")
    sel = input('請輸入要設定推播的節點編號: ').strip()
    publish_addr = input('請輸入 Publish Address (如 0xc000 或 0x101): ').strip()
    try:
        sel_idx = int(sel)
        if 0 <= sel_idx < len(node_list):
            parts = node_list[sel_idx].split()
            unicast_addr = parts[2]
            resp = prov.publish_to_target(unicast_addr, publish_addr)
            print(f'設定推播結果: {resp}')
        else:
            print('輸入編號超出範圍')
    except Exception as e:
        print(f'輸入錯誤: {e}')

def datatrans_set_menu(prov: Provisioner):
    node_list = prov.get_node_list()
    if not node_list:
        print('目前無已綁定節點')
        return
    print('目前節點清單:')
    for idx, node in enumerate(node_list):
        parts = node.split()
        if len(parts) >= 3:
            print(f"{idx}: unicast_addr={parts[2]}")
    sel = input('請輸入要設定 Datatrans 的節點編號: ').strip()
    data = input('請輸入要發送的 16進位資料 (如 0x112233): ').strip()
    ack = input('是否需要ACK? (0=否, 1=是): ').strip()
    try:
        sel_idx = int(sel)
        ack_val = int(ack)
        if 0 <= sel_idx < len(node_list):
            parts = node_list[sel_idx].split()
            unicast_addr = parts[2]
            resp = prov.send_datatrans(unicast_addr, data, ack=ack_val)
            print(f'Datatrans 設定結果: {resp}')
        else:
            print('輸入編號超出範圍')
    except Exception as e:
        print(f'輸入錯誤: {e}')

def datatrans_get_menu(prov: Provisioner):
    node_list = prov.get_node_list()
    if not node_list:
        print('目前無已綁定節點')
        return
    print('目前節點清單:')
    for idx, node in enumerate(node_list):
        parts = node.split()
        if len(parts) >= 3:
            print(f"{idx}: unicast_addr={parts[2]}")
    sel = input('請輸入要查詢 Datatrans 的節點編號: ').strip()
    read_len = input('請輸入要讀取的資料長度 (byte): ').strip()
    try:
        sel_idx = int(sel)
        read_len_val = int(read_len)
        if 0 <= sel_idx < len(node_list):
            parts = node_list[sel_idx].split()
            unicast_addr = parts[2]
            resp = prov.get_datatrans(unicast_addr, read_len_val)
            print(f'Datatrans 查詢結果: {resp}')
        else:
            print('輸入編號超出範圍')
    except Exception as e:
        print(f'輸入錯誤: {e}')

def manage_devices(prov: Provisioner, device_manager: DeviceManager):
    while True:
        print("\n==== 設備管理選單 ====")
        print("1. 顯示所有設備")
        print("2. 顯示所有群組")
        print("3. 創建新群組")
        print("4. 添加設備到群組")
        print("5. 從群組移除設備")
        print("6. 建立設備連動關係")
        print("7. 解除設備連動關係")
        print("8. 全部解除綁定")
        print("0. 返回主選單")
        
        choice = input("請輸入選項: ").strip()
        
        if choice == '0':
            break
        elif choice == '1':
            display_all_devices(device_manager)
        elif choice == '2':
            display_all_groups(device_manager)
        elif choice == '3':
            create_new_group(device_manager)
        elif choice == '4':
            add_device_to_group_menu(device_manager)
        elif choice == '5':
            remove_device_from_group_menu(device_manager)
        elif choice == '6':
            link_devices_menu(device_manager)
        elif choice == '7':
            unlink_devices_menu(device_manager)
        elif choice == '8':
            unbind_all_devices(prov, device_manager)
        else:
            print('無效選項，請重新輸入')

def display_all_devices(device_manager: DeviceManager):
    info = device_manager.get_device_info()
    
    if not info['devices']:
        print("目前沒有設備")
        return
    
    print(f"\n設備總數: {info['device_count']}")
    for device in info['devices']:
        print(f"- {device['name']} (地址: {device['unicast_addr']}, UUID: {device['uuid']})")
        print(f"  MAC地址: {device['mac_address']}")
        print(f"  所屬群組: {device['group'] or '無'}")
        
        linked_devices = device.get('linked_devices', [])
        if linked_devices:
            linked_names = []
            for linked_addr in linked_devices:
                linked_device = device_manager.get_device_by_unicast(linked_addr)
                if linked_device:
                    linked_names.append(f"{linked_device['name']} ({linked_addr})")
            print(f"  連動設備: {', '.join(linked_names)}")
        else:
            print("  連動設備: 無")
        print("")

def display_all_groups(device_manager: DeviceManager):
    info = device_manager.get_device_info()
    
    if not info['groups']:
        print("目前沒有群組")
        return
    
    print(f"\n群組總數: {info['group_count']}")
    for group_name, device_addrs in info['groups'].items():
        print(f"- 群組: {group_name}")
        if device_addrs:
            for addr in device_addrs:
                device = device_manager.get_device_by_unicast(addr)
                if device:
                    print(f"  - {device['name']} ({addr})")
        else:
            print("  (群組為空)")
        print("")

def create_new_group(device_manager: DeviceManager):
    group_name = input("請輸入新群組名稱: ").strip()
    if not group_name:
        print("群組名稱不能為空")
        return
    
    if device_manager.create_group(group_name):
        print(f"成功創建群組: {group_name}")
    else:
        print(f"創建群組失敗，可能是群組已存在")

def add_device_to_group_menu(device_manager: DeviceManager):
    info = device_manager.get_device_info()
    
    if not info['devices']:
        print("目前沒有設備")
        return
    
    if not info['groups']:
        print("目前沒有群組，請先創建群組")
        return
    
    print("\n可用設備:")
    for idx, device in enumerate(info['devices']):
        print(f"{idx}: {device['name']} ({device['unicast_addr']})")
    
    print("\n可用群組:")
    groups = list(info['groups'].keys())
    for idx, group_name in enumerate(groups):
        print(f"{idx}: {group_name}")
    
    try:
        device_idx = int(input("\n請選擇設備編號: ").strip())
        group_idx = int(input("請選擇群組編號: ").strip())
        
        if 0 <= device_idx < len(info['devices']) and 0 <= group_idx < len(groups):
            unicast_addr = info['devices'][device_idx]['unicast_addr']
            group_name = groups[group_idx]
            
            if device_manager.add_device_to_group(unicast_addr, group_name):
                print(f"設備 {info['devices'][device_idx]['name']} 已添加到群組 {group_name}")
            else:
                print("操作失敗")
        else:
            print("選擇超出範圍")
    except ValueError:
        print("請輸入有效的數字")

def remove_device_from_group_menu(device_manager: DeviceManager):
    info = device_manager.get_device_info()
    
    if not info['groups']:
        print("目前沒有群組")
        return
    
    print("\n群組及其成員:")
    has_members = False
    for group_name, device_addrs in info['groups'].items():
        if device_addrs:
            has_members = True
            print(f"- 群組: {group_name}")
            for idx, addr in enumerate(device_addrs):
                device = device_manager.get_device_by_unicast(addr)
                if device:
                    print(f"  {idx}: {device['name']} ({addr})")
    
    if not has_members:
        print("所有群組都是空的")
        return
    
    group_name = input("\n請輸入要從中移除設備的群組名稱: ").strip()
    if group_name not in info['groups']:
        print(f"找不到群組: {group_name}")
        return
    
    if not info['groups'][group_name]:
        print(f"群組 {group_name} 是空的")
        return
    
    device_idx = input(f"請輸入要從群組 {group_name} 中移除的設備編號: ").strip()
    try:
        idx = int(device_idx)
        if 0 <= idx < len(info['groups'][group_name]):
            unicast_addr = info['groups'][group_name][idx]
            if device_manager.remove_device_from_group(unicast_addr, group_name):
                device = device_manager.get_device_by_unicast(unicast_addr)
                print(f"設備 {device['name'] if device else unicast_addr} 已從群組 {group_name} 移除")
            else:
                print("操作失敗")
        else:
            print("選擇超出範圍")
    except ValueError:
        print("請輸入有效的數字")

def link_devices_menu(device_manager: DeviceManager):
    info = device_manager.get_device_info()
    
    if not info['devices'] or len(info['devices']) < 2:
        print("設備數量不足，需要至少兩個設備才能建立連動關係")
        return
    
    print("\n可用設備:")
    for idx, device in enumerate(info['devices']):
        print(f"{idx}: {device['name']} ({device['unicast_addr']})")
    
    try:
        source_idx = int(input("\n請選擇來源設備編號: ").strip())
        target_idx = int(input("請選擇目標設備編號: ").strip())
        
        if source_idx != target_idx and 0 <= source_idx < len(info['devices']) and 0 <= target_idx < len(info['devices']):
            source_addr = info['devices'][source_idx]['unicast_addr']
            target_addr = info['devices'][target_idx]['unicast_addr']
            
            if device_manager.link_devices(source_addr, target_addr):
                print(f"已建立 {info['devices'][source_idx]['name']} 與 {info['devices'][target_idx]['name']} 的連動關係")
            else:
                print("操作失敗")
        else:
            if source_idx == target_idx:
                print("來源和目標不能是同一設備")
            else:
                print("選擇超出範圍")
    except ValueError:
        print("請輸入有效的數字")

def unlink_devices_menu(device_manager: DeviceManager):
    info = device_manager.get_device_info()
    
    linked_devices_exist = False
    print("\n具有連動關係的設備:")
    for idx, device in enumerate(info['devices']):
        if device['linked_devices']:
            linked_devices_exist = True
            print(f"{idx}: {device['name']} ({device['unicast_addr']}) 連動到:")
            for linked_addr in device['linked_devices']:
                linked_device = device_manager.get_device_by_unicast(linked_addr)
                if linked_device:
                    print(f"   - {linked_device['name']} ({linked_addr})")
    
    if not linked_devices_exist:
        print("目前沒有設備具有連動關係")
        return
    
    try:
        source_idx = int(input("\n請選擇來源設備編號: ").strip())
        if 0 <= source_idx < len(info['devices']):
            source_device = info['devices'][source_idx]
            source_addr = source_device['unicast_addr']
            
            if not source_device['linked_devices']:
                print(f"設備 {source_device['name']} 沒有連動關係")
                return
            
            print(f"\n{source_device['name']} 的連動目標:")
            for idx, target_addr in enumerate(source_device['linked_devices']):
                target_device = device_manager.get_device_by_unicast(target_addr)
                print(f"{idx}: {target_device['name'] if target_device else target_addr}")
            
            target_idx = int(input("\n請選擇要解除連動的目標設備編號: ").strip())
            if 0 <= target_idx < len(source_device['linked_devices']):
                target_addr = source_device['linked_devices'][target_idx]
                if device_manager.unlink_devices(source_addr, target_addr):
                    target_device = device_manager.get_device_by_unicast(target_addr)
                    print(f"已解除 {source_device['name']} 與 {target_device['name'] if target_device else target_addr} 的連動關係")
                else:
                    print("操作失敗")
            else:
                print("選擇超出範圍")
        else:
            print("選擇超出範圍")
    except ValueError:
        print("請輸入有效的數字")

def unbind_all_devices(prov: Provisioner, device_manager: DeviceManager):
    confirm = input("確定要解除所有設備的綁定？此操作無法撤銷 (y/n): ").strip().lower()
    if confirm != 'y':
        print("操作已取消")
        return
    
    node_list = prov.get_node_list()
    if not node_list:
        print('目前無已綁定節點')
        return
    
    success_count = 0
    fail_count = 0
    
    for node in node_list:
        parts = node.split()
        if len(parts) >= 3:
            unicast_addr = parts[2]
            resp = prov._send_and_wait(f'AT+NR {unicast_addr}', timeout=3.0)
            if resp and resp.startswith('NR-MSG SUCCESS'):
                success_count += 1
                print(f"成功解綁設備 {unicast_addr}")
            else:
                fail_count += 1
                print(f"解綁設備 {unicast_addr} 失敗")
    
    print(f"解綁完成，成功: {success_count}，失敗: {fail_count}")
    
    if success_count > 0:
        # 清空設備管理器
        device_manager.remove_all_devices()
        print("已清空設備管理器")

if __name__ == "__main__":

    def main_menu():
        
        try:
            ser = SerialAT("COM4", 115200)
            prov = Provisioner(ser)
            
            # 初始化設備管理器
            device_manager = DeviceManager("mesh_devices.json")
            
            menu_map = {
                '1': lambda p: auto_bind_node(p, device_manager),
                '2': lambda p: unbind_node(p, device_manager),
                '3': subscribe_group_menu,
                '4': publish_menu,
                '5': datatrans_set_menu,
                '6': datatrans_get_menu,
                '7': lambda p: p.observe(),
                '8': lambda p: manage_devices(p, device_manager),
            }
            while True:
                print("\n==== RL62M02 Provision 測試選單 ====")
                print("1. 自動綁定新節點")
                print("2. 解綁(NR)節點")
                print("3. 訂閱群組 (MSAA)")
                print("4. 設定推播 (MPAS)")
                print("5. 設定 Datatrans Model 狀態 (MDTS)")
                print("6. 查詢 Datatrans Model 狀態 (MDTG)")
                print("7. 進入觀察模式 (持續接收並分析 MDTS/MDTG 訊息)")
                print("8. 設備管理")
                print("0. 離開")
                choice = input("請輸入選項: ").strip()
                if choice == '0':
                    break
                func = menu_map.get(choice)
                if func:
                    func(prov)
                else:
                    print('無效選項，請重新輸入')
        except Exception as e:
            print(f"Error: {e}")
        finally:
            if 'ser' in locals():
                ser.close()


    main_menu()