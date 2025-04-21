"""
MODBUS RTU 協議處理類別
包含產生 RTU 封包與解析 RTU 封包的功能
"""

class ModbusRTU:
    """
    MODBUS RTU 協議處理類別
    提供 MODBUS RTU 封包的生成與解析功能
    """
    
    # MODBUS 功能碼定義
    READ_COILS = 0x01
    READ_DISCRETE_INPUTS = 0x02
    READ_HOLDING_REGISTERS = 0x03
    READ_INPUT_REGISTERS = 0x04
    WRITE_SINGLE_COIL = 0x05
    WRITE_SINGLE_REGISTER = 0x06
    WRITE_MULTIPLE_COILS = 0x0F
    WRITE_MULTIPLE_REGISTERS = 0x10
    
    # MODBUS 異常碼定義
    EXCEPTION_ILLEGAL_FUNCTION = 0x01
    EXCEPTION_ILLEGAL_DATA_ADDRESS = 0x02
    EXCEPTION_ILLEGAL_DATA_VALUE = 0x03
    EXCEPTION_SLAVE_DEVICE_FAILURE = 0x04
    EXCEPTION_ACKNOWLEDGE = 0x05
    EXCEPTION_SLAVE_DEVICE_BUSY = 0x06
    EXCEPTION_MEMORY_PARITY_ERROR = 0x08
    EXCEPTION_GATEWAY_PATH_UNAVAILABLE = 0x0A
    EXCEPTION_GATEWAY_TARGET_FAILED = 0x0B
    
    def __init__(self):
        """初始化 ModbusRTU 類別"""
        # 初始化 CRC 表
        self._crc_table = self._generate_crc_table()
    
    def _generate_crc_table(self):
        """生成 CRC16 (MODBUS) 查表法所需的表"""
        crc_table = []
        for i in range(256):
            crc = i
            for j in range(8):
                if crc & 0x01:
                    crc = (crc >> 1) ^ 0xA001  # MODBUS CRC-16 多項式 0xA001
                else:
                    crc = crc >> 1
            crc_table.append(crc)
        return crc_table
    
    def _calculate_crc(self, data):
        """
        計算 MODBUS CRC-16 校驗碼
        
        Args:
            data (bytes): 需要計算 CRC 的數據
            
        Returns:
            bytes: 2 bytes CRC 校驗碼 (低位在前，高位在後)
        """
        crc = 0xFFFF
        for byte in data:
            crc = (crc >> 8) ^ self._crc_table[(crc ^ byte) & 0xFF]
        # 返回低位在前，高位在後的 CRC
        return bytes([crc & 0xFF, crc >> 8])
    
    def _verify_crc(self, data):
        """
        驗證 MODBUS RTU 數據的 CRC 校驗
        
        Args:
            data (bytes): 包含 CRC 的完整數據
            
        Returns:
            bool: CRC 校驗成功返回 True，否則返回 False
        """
        if len(data) < 2:
            return False
        message = data[:-2]
        received_crc = data[-2:]
        calculated_crc = self._calculate_crc(message)
        return received_crc == calculated_crc
    
    def create_rtu_packet(self, slave_address, function_code, data):
        """
        創建 MODBUS RTU 封包
        
        Args:
            slave_address (int): 從站地址 (1-247)
            function_code (int): 功能碼
            data (bytes): 數據部分
            
        Returns:
            bytes: 完整的 MODBUS RTU 封包
        """
        # 檢查參數有效性
        if not (0 <= slave_address <= 247):
            raise ValueError("從站地址必須在 0-247 範圍內")
        
        # 組合封包 (不含 CRC)
        packet = bytes([slave_address, function_code]) + data
        
        # 計算並添加 CRC
        crc = self._calculate_crc(packet)
        
        # 返回完整封包
        return packet + crc
    
    def parse_rtu_packet(self, packet):
        """
        解析 MODBUS RTU 封包
        
        Args:
            packet (bytes): 完整的 MODBUS RTU 封包
            
        Returns:
            dict: 包含解析結果的字典，如果 CRC 校驗失敗則返回 None
                {
                    'slave_address': int,
                    'function_code': int,
                    'data': bytes,
                    'is_exception': bool,
                    'exception_code': int (如果是異常回覆)
                }
        """
        # 檢查參數有效性
        if len(packet) < 4:  # 至少需要地址(1) + 功能碼(1) + CRC(2)
            return None
        
        # 驗證 CRC
        if not self._verify_crc(packet):
            return None
        
        # 解析封包
        slave_address = packet[0]
        function_code = packet[1]
        data = packet[2:-2]
        
        # 檢查是否為異常回覆
        is_exception = (function_code & 0x80) != 0
        exception_code = data[0] if is_exception else None
        
        return {
            'slave_address': slave_address,
            'function_code': function_code & 0x7F,  # 移除異常標誌位
            'data': data,
            'is_exception': is_exception,
            'exception_code': exception_code
        }
    
    # === 以下是特定功能碼的封包生成與解析方法 ===
    
    def read_holding_registers_request(self, slave_address, start_address, quantity):
        """
        生成讀取保持寄存器 (功能碼 0x03) 請求封包
        
        Args:
            slave_address (int): 從站地址
            start_address (int): 起始寄存器地址
            quantity (int): 要讀取的寄存器數量
            
        Returns:
            bytes: 完整的 MODBUS RTU 封包
        """
        if not (1 <= quantity <= 125):
            raise ValueError("寄存器數量必須在 1-125 範圍內")
        
        data = bytes([
            (start_address >> 8) & 0xFF,
            start_address & 0xFF,
            (quantity >> 8) & 0xFF,
            quantity & 0xFF
        ])
        
        return self.create_rtu_packet(slave_address, self.READ_HOLDING_REGISTERS, data)
    
    def read_holding_registers_response(self, packet):
        """
        解析讀取保持寄存器 (功能碼 0x03) 回覆封包
        
        Args:
            packet (bytes): 完整的 MODBUS RTU 回覆封包
            
        Returns:
            list: 包含讀取到的寄存器值的列表，如果解析失敗則返回 None
        """
        parsed = self.parse_rtu_packet(packet)
        if parsed is None or parsed['function_code'] != self.READ_HOLDING_REGISTERS or parsed['is_exception']:
            return None
        
        byte_count = parsed['data'][0]
        if len(parsed['data']) != byte_count + 1:
            return None
        
        # 解析寄存器值 (每個寄存器 2 bytes)
        registers = []
        for i in range(1, byte_count, 2):
            register_value = (parsed['data'][i] << 8) + parsed['data'][i+1]
            registers.append(register_value)
        
        return registers
    
    def write_single_register_request(self, slave_address, register_address, register_value):
        """
        生成寫入單個寄存器 (功能碼 0x06) 請求封包
        
        Args:
            slave_address (int): 從站地址
            register_address (int): 寄存器地址
            register_value (int): 寄存器值 (0-65535)
            
        Returns:
            bytes: 完整的 MODBUS RTU 封包
        """
        if not (0 <= register_value <= 0xFFFF):
            raise ValueError("寄存器值必須在 0-65535 範圍內")
        
        data = bytes([
            (register_address >> 8) & 0xFF,
            register_address & 0xFF,
            (register_value >> 8) & 0xFF,
            register_value & 0xFF
        ])
        
        return self.create_rtu_packet(slave_address, self.WRITE_SINGLE_REGISTER, data)
    
    def write_multiple_registers_request(self, slave_address, start_address, register_values):
        """
        生成寫入多個寄存器 (功能碼 0x10) 請求封包
        
        Args:
            slave_address (int): 從站地址
            start_address (int): 起始寄存器地址
            register_values (list): 寄存器值列表
            
        Returns:
            bytes: 完整的 MODBUS RTU 封包
        """
        if not (1 <= len(register_values) <= 123):
            raise ValueError("寄存器數量必須在 1-123 範圍內")
        
        quantity = len(register_values)
        byte_count = quantity * 2
        
        # 頭部: 起始地址 + 數量 + 字節數
        data = bytes([
            (start_address >> 8) & 0xFF,
            start_address & 0xFF,
            (quantity >> 8) & 0xFF,
            quantity & 0xFF,
            byte_count
        ])
        
        # 添加寄存器值
        for value in register_values:
            if not (0 <= value <= 0xFFFF):
                raise ValueError(f"寄存器值 {value} 超出範圍 (0-65535)")
            data += bytes([(value >> 8) & 0xFF, value & 0xFF])
        
        return self.create_rtu_packet(slave_address, self.WRITE_MULTIPLE_REGISTERS, data)
    
    def read_input_registers_request(self, slave_address, start_address, quantity):
        """
        生成讀取輸入寄存器 (功能碼 0x04) 請求封包
        
        Args:
            slave_address (int): 從站地址
            start_address (int): 起始寄存器地址
            quantity (int): 要讀取的寄存器數量
            
        Returns:
            bytes: 完整的 MODBUS RTU 封包
        """
        if not (1 <= quantity <= 125):
            raise ValueError("寄存器數量必須在 1-125 範圍內")
        
        data = bytes([
            (start_address >> 8) & 0xFF,
            start_address & 0xFF,
            (quantity >> 8) & 0xFF,
            quantity & 0xFF
        ])
        
        return self.create_rtu_packet(slave_address, self.READ_INPUT_REGISTERS, data)
    
    def read_coils_request(self, slave_address, start_address, quantity):
        """
        生成讀取線圈 (功能碼 0x01) 請求封包
        
        Args:
            slave_address (int): 從站地址
            start_address (int): 起始線圈地址
            quantity (int): 要讀取的線圈數量
            
        Returns:
            bytes: 完整的 MODBUS RTU 封包
        """
        if not (1 <= quantity <= 2000):
            raise ValueError("線圈數量必須在 1-2000 範圍內")
        
        data = bytes([
            (start_address >> 8) & 0xFF,
            start_address & 0xFF,
            (quantity >> 8) & 0xFF,
            quantity & 0xFF
        ])
        
        return self.create_rtu_packet(slave_address, self.READ_COILS, data)
    
    def read_coils_response(self, packet):
        """
        解析讀取線圈 (功能碼 0x01) 回覆封包
        
        Args:
            packet (bytes): 完整的 MODBUS RTU 回覆封包
            
        Returns:
            list: 包含讀取到的線圈狀態的列表 (True/False)，如果解析失敗則返回 None
        """
        parsed = self.parse_rtu_packet(packet)
        if parsed is None or parsed['function_code'] != self.READ_COILS or parsed['is_exception']:
            return None
        
        byte_count = parsed['data'][0]
        if len(parsed['data']) != byte_count + 1:
            return None
        
        coils = []
        for i in range(1, byte_count + 1):
            byte_value = parsed['data'][i]
            for bit in range(8):
                coil_state = (byte_value & (1 << bit)) != 0
                coils.append(coil_state)
        
        return coils
    
    def write_single_coil_request(self, slave_address, coil_address, coil_value):
        """
        生成寫入單個線圈 (功能碼 0x05) 請求封包
        
        Args:
            slave_address (int): 從站地址
            coil_address (int): 線圈地址
            coil_value (bool): 線圈值 (True/False)
            
        Returns:
            bytes: 完整的 MODBUS RTU 封包
        """
        value = 0xFF00 if coil_value else 0x0000
        
        data = bytes([
            (coil_address >> 8) & 0xFF,
            coil_address & 0xFF,
            (value >> 8) & 0xFF,
            value & 0xFF
        ])
        
        return self.create_rtu_packet(slave_address, self.WRITE_SINGLE_COIL, data)
    
    def get_exception_message(self, exception_code):
        """
        根據異常碼獲取異常信息
        
        Args:
            exception_code (int): 異常碼
            
        Returns:
            str: 異常信息描述
        """
        exception_messages = {
            self.EXCEPTION_ILLEGAL_FUNCTION: "不合法的功能碼",
            self.EXCEPTION_ILLEGAL_DATA_ADDRESS: "不合法的數據地址",
            self.EXCEPTION_ILLEGAL_DATA_VALUE: "不合法的數據值",
            self.EXCEPTION_SLAVE_DEVICE_FAILURE: "從站設備故障",
            self.EXCEPTION_ACKNOWLEDGE: "確認",
            self.EXCEPTION_SLAVE_DEVICE_BUSY: "從站設備忙",
            self.EXCEPTION_MEMORY_PARITY_ERROR: "記憶體奇偶校驗錯誤",
            self.EXCEPTION_GATEWAY_PATH_UNAVAILABLE: "閘道路徑不可用",
            self.EXCEPTION_GATEWAY_TARGET_FAILED: "閘道目標設備回應失敗"
        }
        
        return exception_messages.get(exception_code, f"未知異常碼 {exception_code}")