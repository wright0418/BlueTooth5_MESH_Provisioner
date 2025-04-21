import threading
import time
import logging
from .serial_at import SerialAT

class Provisioner:
    """
    Provisioner 類負責 RL Mesh 設備的配置和管理，
    提供設備掃描、綁定、通訊等操作。
    """
    
    DEFAULT_TIMEOUT = 2.0
    PROV_TIMEOUT = 8.0
    AKA_TIMEOUT = 5.0
    MAKB_TIMEOUT = 5.0
    NR_TIMEOUT = 3.0
    MODEL_ID = '0x4005D'
    APP_KEY_IDX = 0
    NET_KEY_IDX = 0
    
    def __init__(self, serial_at: SerialAT):
        """
        初始化 Provisioner 實例
        
        Args:
            serial_at (SerialAT): SerialAT 實例，用於與設備通訊
        """
        self.serial_at = serial_at
        self.last_response = None
        self.responses = []
        self.serial_at.on_receive = self._on_receive
        self._response_event = threading.Event()

    def _on_receive(self, line: str):
        """接收消息的回調函數"""
        self.responses.append(line)
        self.last_response = line
        self._response_event.set()

    def _send_and_wait(self, cmd: str, timeout: float = None):
        """
        發送命令並等待響應
        
        Args:
            cmd (str): 要發送的 AT 命令
            timeout (float): 超時時間，單位為秒
            
        Returns:
            str: 響應消息，如果超時則返回 None
        """
        if timeout is None:
            timeout = self.DEFAULT_TIMEOUT
        self._response_event.clear()
        self.serial_at.send(cmd)
        if self._response_event.wait(timeout):
            return self.last_response
        return None

    def get_version(self):
        """
        獲取設備版本
        
        Returns:
            str: 版本信息
        """
        resp = self._send_and_wait('AT+VER')
        if resp and resp.startswith('VER-MSG'):
            return resp
        return None

    def set_name(self, name: str):
        """
        設置設備名稱
        
        Args:
            name (str): 設備名稱
            
        Returns:
            str: 響應消息
        """
        resp = self._send_and_wait(f'AT+NAME {name}')
        return resp

    def reboot(self):
        """
        重啟設備
        
        Returns:
            str: 響應消息
        """
        resp = self._send_and_wait('AT+REBOOT')
        return resp

    def get_role(self):
        """
        獲取設備角色
        
        Returns:
            str: 角色信息
        """
        resp = self._send_and_wait('AT+MRG')
        return resp

    def scan_nodes(self, enable: bool = True, scan_time: float = 3.0):
        """
        掃描周圍 RL Mesh 設備
        
        Args:
            enable (bool): 是否啟用掃描
            scan_time (float): 掃描時間，單位為秒
            
        Returns:
            list: 掃描到的設備列表，每個設備為包含 mac address 與 uuid 的字典
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
        """
        配置設備
        
        Args:
            dev_uuid (str): 設備 UUID
            
        Returns:
            str: 響應消息
        """
        resp = self._send_and_wait(f'AT+PBADVCON {dev_uuid}')
        if resp and resp.startswith('PBADVCON-MSG SUCCESS'):
            prov_resp = self._send_and_wait('AT+PROV')
            return prov_resp
        return resp

    def get_node_list(self):
        """
        獲取已綁定的節點列表
        
        Returns:
            list: 節點列表
        """
        self.responses.clear()
        self.serial_at.send('AT+NL')
        time.sleep(1)
        return [r for r in self.responses if r.startswith('NL-MSG')]

    def set_appkey(self, dst: str, app_key_index: int, net_key_index: int):
        """
        設置 AppKey
        
        Args:
            dst (str): 目標設備地址
            app_key_index (int): AppKey 索引
            net_key_index (int): NetKey 索引
            
        Returns:
            str: 響應消息
        """
        resp = self._send_and_wait(f'AT+AKA {dst} {app_key_index} {net_key_index}')
        return resp

    def auto_provision_node(self, uuid: str):
        """
        自動配置並綁定節點
        
        Args:
            uuid (str): 設備 UUID
            
        Returns:
            dict: 綁定結果，包含結果狀態和 unicast address
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
        """
        訂閱群組
        
        Args:
            unicast_addr (str): 設備地址
            group_addr (str): 群組地址
            element_index (int): 元素索引，默認為 0
            model_id (str): 模型 ID，如果為 None 則使用默認模型 ID
            
        Returns:
            str: 響應消息
        """
        if model_id is None:
            model_id = self.MODEL_ID
        resp = self._send_and_wait(f'AT+MSAA {unicast_addr} {element_index} {model_id} {group_addr}', timeout=3.0)
        return resp

    def publish_to_target(self, unicast_addr: str, publish_addr: str, element_index: int = 0, model_id: str = None, app_key_idx: int = None):
        """
        設置發布目標
        
        Args:
            unicast_addr (str): 設備地址
            publish_addr (str): 發布地址
            element_index (int): 元素索引，默認為 0
            model_id (str): 模型 ID，如果為 None 則使用默認模型 ID
            app_key_idx (int): AppKey 索引，如果為 None 則使用默認索引
            
        Returns:
            str: 響應消息
        """
        if model_id is None:
            model_id = self.MODEL_ID
        if app_key_idx is None:
            app_key_idx = self.APP_KEY_IDX
        resp = self._send_and_wait(f'AT+MPAS {unicast_addr} {element_index} {model_id} {publish_addr} {app_key_idx}', timeout=3.0)
        return resp

    def send_datatrans(self, unicast_addr: str, data: str, element_index: int = 0, app_key_idx: int = 0, ack: int = 0):
        """
        設定 Vendor Model - Datatrans Model 的狀態 (AT+MDTS)
        
        Args:
            unicast_addr (str): 設備地址
            data (str): 1~20 bytes 的 16進位字串 (如 '0x112233')
            element_index (int): 元素索引，默認為 0
            app_key_idx (int): AppKey 索引，默認為 0
            ack (int): 是否需要回應，0=不回應, 1=需回應
            
        Returns:
            str: 響應消息
        """
        resp = self._send_and_wait(f'AT+MDTS {unicast_addr} {element_index} {app_key_idx} {ack} {data}', timeout=3.0)
        return resp

    def get_datatrans(self, unicast_addr: str, read_data_len: int, element_index: int = 0, app_key_idx: int = 0):
        """
        查詢 Vendor Model - Datatrans Model 的狀態 (AT+MDTG)
        
        Args:
            unicast_addr (str): 設備地址
            read_data_len (int): 讀取資料長度 (byte 數)
            element_index (int): 元素索引，默認為 0
            app_key_idx (int): AppKey 索引，默認為 0
            
        Returns:
            str: 響應消息
        """
        resp = self._send_and_wait(f'AT+MDTG {unicast_addr} {element_index} {app_key_idx} {read_data_len}', timeout=3.0)
        return resp

    def observe(self, print_all: bool = True):
        """
        進入觀察模式，持續接收所有周邊訊息
        
        Args:
            print_all (bool): 是否打印所有消息，默認為 True
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