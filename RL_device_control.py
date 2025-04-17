#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RL Mesh 設備控制模組
提供控制 RL Mesh 各種設備的功能，包括 RGB LED、插座和 Smart-Box 設備
"""

import time
import logging
from typing import Dict, List, Optional, Tuple, Union
from rl62m02_provisioner import Provisioner
from modbus import ModbusRTU

class RLMeshDeviceController:
    """
    RL Mesh 設備控制類別
    提供控制 RL Mesh 各種設備的功能，支援 RGB LED、插座和 Smart-Box 設備
    """
    
    # RL Mesh 設備類型定義
    DEVICE_TYPE_RGB_LED = "RGB_LED"
    DEVICE_TYPE_PLUG = "PLUG"
    DEVICE_TYPE_SMART_BOX = "SMART_BOX"
    DEVICE_TYPE_AIR_BOX = "AIR_BOX"  # 新增 Air-Box 設備類型
    DEVICE_TYPE_POWER_METER = "POWER_METER"  # 電錶設備類型
    
    # RL Mesh 設備指令碼定義
    OPCODE_RGB_LED = 0x0100
    OPCODE_PLUG = 0x0200
    
    # Smart-Box 設備類型定義
    SMART_BOX_TYPE_SET = 0x00
    SMART_BOX_TYPE_GET = 0x01
    SMART_BOX_TYPE_RTU = 0x02
    SMART_BOX_TYPE_SENSOR = 0x03
    
    # Smart-Box 設備頭部定義
    SMART_BOX_HEADER = 0x8276
    
    # 有效的裝置類型列表
    VALID_DEVICE_TYPES = [
        DEVICE_TYPE_RGB_LED,
        DEVICE_TYPE_PLUG,
        DEVICE_TYPE_SMART_BOX,
        DEVICE_TYPE_AIR_BOX,
        DEVICE_TYPE_POWER_METER
    ]
    
    def __init__(self, provisioner: Provisioner):
        """
        初始化 RLMeshDeviceController 類別
        
        Args:
            provisioner (Provisioner): RL62M02 Provisioner 實例，用於與設備通訊
        """
        self.provisioner = provisioner
        self.modbus = ModbusRTU()
        self.device_map = {}  # 用於儲存裝置 UUID 與類型的對應
        
    def register_device(self, unicast_addr: str, device_type: str, device_name: str = None):
        """
        註冊設備，建立 unicast_addr 與設備類型的對應關係
        
        Args:
            unicast_addr (str): 設備的 unicast address (如 "0x0100")
            device_type (str): 設備類型 (參考 VALID_DEVICE_TYPES)
            device_name (str, optional): 設備名稱，方便識別
            
        Returns:
            bool: 註冊成功返回 True，否則返回 False
        """
        if device_type not in self.VALID_DEVICE_TYPES:
            logging.error(f"註冊失敗：不支援的設備類型: {device_type}")
            return False
        
        # 使用 get 方法安全地取得設備名稱，若不存在則使用 unicast_addr
        resolved_name = device_name or unicast_addr
        self.device_map[unicast_addr] = {
            "type": device_type,
            "name": resolved_name
        }
        logging.info(f"已註冊設備: {unicast_addr} 類型: {device_type} 名稱: {resolved_name}")
        return True
    
    def get_registered_devices(self):
        """
        獲取已註冊的所有設備
        
        Returns:
            Dict: 包含已註冊設備的字典
        """
        return self.device_map
    
    def control_rgb_led(self, unicast_addr: str, cold: int, warm: int, red: int, green: int, blue: int):
        """
        控制 RGB LED 設備
        
        Args:
            unicast_addr (str): 設備的 unicast address
            cold (int): 冷光值 (0-255)
            warm (int): 暖光值 (0-255)
            red (int): 紅色值 (0-255)
            green (int): 綠色值 (0-255)
            blue (int): 藍色值 (0-255)
            
        Returns:
            str: 指令執行結果或錯誤訊息
        """
        # 檢查設備是否已註冊且類型正確
        device_info = self.device_map.get(unicast_addr)
        if not device_info or device_info["type"] != self.DEVICE_TYPE_RGB_LED:
            error_msg = f"錯誤：設備 {unicast_addr} 未註冊或不是 RGB LED 類型。"
            logging.error(error_msg)
            return error_msg
        
        # 檢查參數範圍
        for value, name in [(cold, "cold"), (warm, "warm"), (red, "red"), (green, "green"), (blue, "blue")]:
            if not (0 <= value <= 255):
                logging.warning(f"{name} 值必須在 0-255 範圍內，當前值: {value}")
                return f"錯誤: {name} 值必須在 0-255 範圍內"
        
        # 構建 RGB LED 命令
        header = "87"
        opcode = f"{self.OPCODE_RGB_LED:04x}"
        payload_len = "05"
        payload = f"{cold:02x}{warm:02x}{red:02x}{green:02x}{blue:02x}"
        cmd = f"{header}{opcode}{payload_len}{payload}"
        
        # 發送命令
        logging.debug(f"發送 RGB LED 命令: {cmd} 到 {unicast_addr}")
        resp = self.provisioner.send_datatrans(unicast_addr, cmd)
        return resp
    
    def control_plug(self, unicast_addr: str, state: bool):
        """
        控制插座設備
        
        Args:
            unicast_addr (str): 設備的 unicast address
            state (bool): True 代表開，False 代表關
            
        Returns:
            str: 指令執行結果或錯誤訊息
        """
        # 檢查設備是否已註冊且類型正確
        device_info = self.device_map.get(unicast_addr)
        if not device_info or device_info["type"] != self.DEVICE_TYPE_PLUG:
            error_msg = f"錯誤：設備 {unicast_addr} 未註冊或不是插座類型。"
            logging.error(error_msg)
            return error_msg
        
        # 構建插座命令
        header = "87"
        opcode = f"{self.OPCODE_PLUG:04x}"
        payload_len = "01"
        payload = "01" if state else "00"
        cmd = f"{header}{opcode}{payload_len}{payload}"
        
        # 發送命令
        logging.debug(f"發送插座命令: {cmd} 到 {unicast_addr}")
        resp = self.provisioner.send_datatrans(unicast_addr, cmd)
        return resp
    
    def control_smart_box_rtu(self, unicast_addr: str, modbus_packet: bytes):
        """
        控制 Smart-Box 設備使用 RTU 模式
        
        Args:
            unicast_addr (str): 設備的 unicast address
            modbus_packet (bytes): 完整的 Modbus RTU 數據包
            
        Returns:
            dict: 包含指令執行結果和 MDTG-MSG 回應的字典，或包含錯誤訊息的字典
        """
        # 檢查設備是否已註冊且類型正確
        device_info = self.device_map.get(unicast_addr)
        # 允許 AIR_BOX 和 POWER_METER 也使用此底層 RTU 函數
        allowed_types = [self.DEVICE_TYPE_SMART_BOX, self.DEVICE_TYPE_AIR_BOX, self.DEVICE_TYPE_POWER_METER]
        if not device_info or device_info["type"] not in allowed_types:
            error_msg = f"錯誤：設備 {unicast_addr} 未註冊或不是支援 RTU 的類型 (SMART_BOX, AIR_BOX, POWER_METER)。"
            logging.error(error_msg)
            return {"initial_response": "ERROR", "mdtg_response": error_msg}

        # 構建 Smart-Box RTU 命令
        header = f"{self.SMART_BOX_HEADER:04x}"
        device_type = f"{self.SMART_BOX_TYPE_RTU:02x}"
        payload = ''.join([f"{b:02x}" for b in modbus_packet])
        cmd = f"{header}{device_type}{payload}"
        
        # 發送命令
        logging.debug(f"發送 Smart-Box RTU 命令: {cmd} 到 {unicast_addr}")
        initial_resp = self.provisioner.send_datatrans(unicast_addr, cmd)
        
        # 等待 MDTG-MSG 回應，檢查 UID 是否與請求的設備地址相符
        # 超時時間設定為3秒，因為RTU回應可能需要一些時間
        mdtg_resp = self.provisioner.serial_at.wait_for_response("MDTG-MSG", target_uid=unicast_addr, timeout=3.0)
        
        # 返回結構化結果
        result = {
            "initial_response": initial_resp,
            "mdtg_response": mdtg_resp
        }
        
        return result
    
    def read_smart_box_rtu(self, unicast_addr: str, slave_address: int, function_code: int, 
                          start_address: int, quantity: int):
        """
        讀取 Smart-Box RTU 設備的數據
        
        Args:
            unicast_addr (str): 設備的 unicast address
            slave_address (int): Modbus 從站地址
            function_code (int): Modbus 功能碼
            start_address (int): 起始地址
            quantity (int): 讀取數量
            
        Returns:
            str: 指令執行結果
        """
        # 根據功能碼構建適當的 Modbus 請求封包
        modbus_packet = None
        if function_code == ModbusRTU.READ_HOLDING_REGISTERS:
            modbus_packet = self.modbus.read_holding_registers_request(slave_address, start_address, quantity)
        elif function_code == ModbusRTU.READ_INPUT_REGISTERS:
            modbus_packet = self.modbus.read_input_registers_request(slave_address, start_address, quantity)
        elif function_code == ModbusRTU.READ_COILS:
            modbus_packet = self.modbus.read_coils_request(slave_address, start_address, quantity)
        else:
            logging.warning(f"不支援的功能碼: {function_code}")
            return "錯誤: 不支援的功能碼"
        
        # 發送 RTU 命令
        return self.control_smart_box_rtu(unicast_addr, modbus_packet)
    
    def write_smart_box_register(self, unicast_addr: str, slave_address: int, register_address: int, register_value: int):
        """
        寫入 Smart-Box RTU 設備的單個寄存器
        
        Args:
            unicast_addr (str): 設備的 unicast address
            slave_address (int): Modbus 從站地址
            register_address (int): 寄存器地址
            register_value (int): 寄存器值
            
        Returns:
            str: 指令執行結果
        """
        modbus_packet = self.modbus.write_single_register_request(slave_address, register_address, register_value)
        return self.control_smart_box_rtu(unicast_addr, modbus_packet)
    
    def write_smart_box_registers(self, unicast_addr: str, slave_address: int, start_address: int, register_values: List[int]):
        """
        寫入 Smart-Box RTU 設備的多個寄存器
        
        Args:
            unicast_addr (str): 設備的 unicast address
            slave_address (int): Modbus 從站地址
            start_address (int): 起始寄存器地址
            register_values (List[int]): 寄存器值列表
            
        Returns:
            str: 指令執行結果
        """
        modbus_packet = self.modbus.write_multiple_registers_request(slave_address, start_address, register_values)
        return self.control_smart_box_rtu(unicast_addr, modbus_packet)
    
    def write_smart_box_coil(self, unicast_addr: str, slave_address: int, coil_address: int, coil_value: bool):
        """
        寫入 Smart-Box RTU 設備的單個線圈
        
        Args:
            unicast_addr (str): 設備的 unicast address
            slave_address (int): Modbus 從站地址
            coil_address (int): 線圈地址
            coil_value (bool): 線圈值
            
        Returns:
            str: 指令執行結果
        """
        modbus_packet = self.modbus.write_single_coil_request(slave_address, coil_address, coil_value)
        return self.control_smart_box_rtu(unicast_addr, modbus_packet)
    
    def read_air_box_data(self, unicast_addr: str, slave_address: int):
        """
        讀取 Air-Box 空氣盒子的環境數據
        
        Args:
            unicast_addr (str): 設備的 unicast address
            slave_address (int): Modbus 從站地址
            
        Returns:
            dict: 包含溫度、濕度、PM2.5 和 CO2 的環境資料
        """
        # 檢查設備是否已註冊為 AIR_BOX 類型
        if unicast_addr in self.device_map and self.device_map[unicast_addr]["type"] != self.DEVICE_TYPE_AIR_BOX:
            logging.warning(f"設備 {unicast_addr} 不是 Air-Box 空氣盒子類型")
        
        # 固定起始位置 0x0000，讀取長度為 3
        start_address = 0x0000
        quantity = 6
        
        # 使用 RTU 讀取保持寄存器
        response = self.read_smart_box_rtu(unicast_addr, slave_address, ModbusRTU.READ_INPUT_REGISTERS, 
                                          start_address, quantity)
        
        result = {
            "temperature": None,
            "humidity": None,
            "co2": None,
            "pm25": None,
            "raw_data": response
        }
        
        # 解析 MDTG-MSG 回應
        if response and 'mdtg_response' in response and response['mdtg_response']:
            mdtg_msg = response['mdtg_response']
            
            # 從 MDTG-MSG 解析出數據部分
            # 格式例如: 0x0101 0 82 76 02 01 04 0C 00F9 02C1 000B 0000 0000 01EC FEAA
            
            if mdtg_msg and "MDTG-MSG" in mdtg_msg:
                parts = mdtg_msg.split()
                if len(parts) >= 4:
                    data_hex = parts[3]
                    
                    # 檢查數據是否有效
                    if len(data_hex) >= 24 and data_hex.startswith('8276'):
                        # 溫度 (例: 0101 => 0x0101/10 = 25.7°C)
                        temp_hex = data_hex[12:16]
  
                        temp_value = int(temp_hex, 16) / 10.0
                        result["temperature"] = temp_value
                        
                        humid_hex = data_hex[16:20]
                        humid_value = int(humid_hex, 16) / 10.0
                        result["humidity"] = humid_value

                        pm25_hex = data_hex[20:24]
                        pm25_value = int(pm25_hex, 16)
                        result["pm25"] = pm25_value

                        co2_hex = data_hex[32:36]
                        co2_value = int(co2_hex, 16)
                        result["co2"] = co2_value
                                                
                        logging.info(f"成功解析 Air-Box 數據: {result}")
                    else:
                        logging.warning(f"無效的數據格式: {data_hex}")
                else:
                    logging.warning(f"無效的 MDTG-MSG 格式: {mdtg_msg}")
                    
        return result
        
    def read_power_meter_data(self, unicast_addr: str, slave_address: int):
        """
        讀取電錶的電力數據
        
        Args:
            unicast_addr (str): 設備的 unicast address
            slave_address (int): Modbus 從站地址
            
        Returns:
            dict: 包含電壓、電流、功率、電能的電力資料
        """
        # 檢查設備是否已註冊為 POWER_METER 類型
        if unicast_addr in self.device_map and self.device_map[unicast_addr]["type"] != self.DEVICE_TYPE_POWER_METER:
            logging.warning(f"設備 {unicast_addr} 不是電錶類型")
        
        # 固定起始位置 0x000E，讀取長度為 4
        start_address = 0x000E
        quantity = 4
        
        # 使用 RTU 讀取輸入寄存器
        response = self.read_smart_box_rtu(unicast_addr, slave_address, ModbusRTU.READ_HOLDING_REGISTERS, 
                                          start_address, quantity)
        
        result = {
            "voltage": None,
            "current": None,
            "power": None,
            "raw_data": response
        }
        
        # 解析 MDTG-MSG 回應
        if response and 'mdtg_response' in response and response['mdtg_response']:
            mdtg_msg = response['mdtg_response']
            
            # 從 MDTG-MSG 解析出數據部分
            if mdtg_msg and "MDTG-MSG" in mdtg_msg:
                parts = mdtg_msg.split()
                if len(parts) >= 4:
                    data_hex = parts[3]
                    
                    # 檢查數據是否有效
                    if len(data_hex) >= 28 and data_hex.startswith('8276'):
                        # 電壓 (V) - 假設寄存器位置和格式
                        voltage_hex = data_hex[12:16]
                        voltage_value = int(voltage_hex, 16) / 10.0  # 除以10得到真實值
                        result["voltage"] = voltage_value
                        
                        # 電流 (A)
                        current_hex = data_hex[16:20]
                        current_value = int(current_hex, 16) / 1000.0  # 除以100得到真實值
                        result["current"] = current_value
                        
                        # 功率 (W)
                        power_hex = data_hex[24:28]
                        power_value = int(power_hex, 16) /10.0
                        result["power"] = power_value
                                           
                        logging.info(f"成功解析電錶數據: {result}")
                    else:
                        logging.warning(f"無效的數據格式: {data_hex}")
                else:
                    logging.warning(f"無效的 MDTG-MSG 格式: {mdtg_msg}")
        
        return result