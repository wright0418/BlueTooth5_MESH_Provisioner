import threading
import serial
import time
from typing import Callable, Optional
import logging

class SerialAT:
    """
    SerialAT 類為 RL Mesh 設備提供串口通信功能。
    負責與裝置進行串口通訊，包含自動接收與傳送 AT 指令的功能。
    """

    def __init__(self, port: str, baudrate: int = 115200, on_receive: Optional[Callable[[str], None]] = None):
        """
        初始化 SerialAT 實例
        
        Args:
            port (str): 串口名稱，例如 "COM3"
            baudrate (int): 鮑率，預設為 115200
            on_receive (callable): 收到訊息時的回調函數，可選
        """
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
        self._queue_lock = threading.Lock()  # 添加互斥鎖保護共享資源

    def send(self, cmd: str):
        """
        發送 AT 指令
        
        Args:
            cmd (str): 要發送的指令
        """
        if not cmd.endswith('\r\n'):
            cmd += '\r\n'
        self.ser.write(cmd.encode('utf-8'))
        self.ser.flush()

    def _recv_loop(self):
        """接收循環，在獨立的線程中運行"""
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
                            with self._queue_lock:  # 使用互斥鎖保護共享資源
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
        with self._queue_lock:
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
                with self._queue_lock:
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
        """關閉串口連接並停止接收線程"""
        self._stop_event.set()
        if self._recv_thread.is_alive():
            self._recv_thread.join(timeout=1.0)
        if self.ser.is_open:
            self.ser.close()