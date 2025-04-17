#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RL Mesh 設備示範程式
提供控制 RL Mesh 各種設備的功能演示
"""

import time
import sys
import logging
from rl62m02_provisioner import SerialAT, Provisioner
from device_manager import DeviceManager
from RL_device_control import RLMeshDeviceController
from modbus import ModbusRTU

def main():
    if len(sys.argv) < 2:
        print("使用方式: python RL_device_demo.py <COM埠> [測試類型]")
        print("測試類型: all, rgb, plug, smart_box, device_mgmt (預設: all)")
        return
    
    com_port = sys.argv[1]
    test_type = "all"
    if len(sys.argv) >= 3:
        test_type = sys.argv[2].lower()
    
    try:
        # 初始化 SerialAT 和 Provisioner
        print(f"初始化 SerialAT 在埠 {com_port}...")
        ser = SerialAT(com_port, 115200)
        prov = Provisioner(ser)
        
        # 初始化設備管理器
        device_manager = DeviceManager("mesh_devices.json")
        
        # 創建控制器
        controller = RLMeshDeviceController(prov)
        
        # 裝置管理功能
        if test_type in ["all", "device_mgmt"]:
            device_management_menu(prov, controller, device_manager)
            return
                       
    except Exception as e:
        print(f"錯誤: {e}")
    finally:
        if 'ser' in locals():
            ser.close()

def device_management_menu(prov: Provisioner, controller: RLMeshDeviceController, device_manager: DeviceManager):
    """裝置管理功能選單"""
    while True:
        print("\n===== 裝置管理選單 =====")
        print("1. 掃描與綁定新裝置")
        print("2. 顯示所有裝置")
        print("3. 顯示所有群組")
        print("4. 設定裝置類型")
        print("5. 測試控制裝置")
        print("6. 解除綁定裝置")
        print("0. 離開")
        
        choice = input("請輸入選項: ").strip()
        
        if choice == '0':
            break
        elif choice == '1':
            scan_and_provision(prov, controller, device_manager)
        elif choice == '2':
            display_devices(device_manager)
        elif choice == '3':
            display_groups(device_manager)
        elif choice == '4':
            set_device_type(controller, device_manager)
        elif choice == '5':
            control_device_menu(controller, device_manager)
        elif choice == '6':
            unbind_device(prov, device_manager)
        else:
            print("無效選擇，請重試")

def scan_and_provision(prov: Provisioner, controller: RLMeshDeviceController, device_manager: DeviceManager):
    """掃描並綁定新裝置"""
    print("開始掃描網狀網路裝置...")
    scan_result = prov.scan_nodes(scan_time=5)
    
    if not scan_result:
        print("未掃描到任何裝置")
        return
        
    print("\n掃描結果:")
    for idx, device in enumerate(scan_result):
        print(f"{idx+1}. MAC: {device['mac address']}, UUID: {device['uuid']}")
    
    choice = input("\n請選擇要綁定的裝置編號 (1-" + str(len(scan_result)) + "), 或按 Enter 取消: ").strip()
    if not choice:
        return
        
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(scan_result):
            target = scan_result[idx]
            print(f"開始自動綁定 UUID: {target['uuid']}")
            result = prov.auto_provision_node(target['uuid'])
            print('綁定結果:', result)
            
            if result.get('result') == 'success':
                unicast_addr = result.get('unicast_addr')
                
                # 提示設備類型選擇
                print("\n請選擇設備類型:")
                print(f"1. RGB LED")
                print(f"2. 插座")
                print(f"3. Smart-Box")
                print(f"4. Air-Box")
                print(f"5. 電錶 (Power Meter)")
                device_type_choice = input("請輸入設備類型編號 (1-5): ").strip()
                
                device_type = RLMeshDeviceController.DEVICE_TYPE_RGB_LED  # 預設
                device_type_str = "RGB_LED"  # 預設類型字符串
                if device_type_choice == '2':
                    device_type = RLMeshDeviceController.DEVICE_TYPE_PLUG
                    device_type_str = "PLUG"
                elif device_type_choice == '3':
                    device_type = RLMeshDeviceController.DEVICE_TYPE_SMART_BOX
                    device_type_str = "SMART_BOX"
                elif device_type_choice == '4':
                    device_type = RLMeshDeviceController.DEVICE_TYPE_AIR_BOX
                    device_type_str = "AIR_BOX"
                elif device_type_choice == '5':
                    device_type = RLMeshDeviceController.DEVICE_TYPE_POWER_METER
                    device_type_str = "POWER_METER"
                
                # 設備名稱
                name = input(f"請輸入設備名稱 (直接按Enter使用預設): ").strip()
                if not name:
                    name = f"{device_type}-{unicast_addr}"
                
                # 添加設備到管理器，記錄設備類型
                device_manager.add_device(target['uuid'], target['mac address'], unicast_addr, name, device_type_str)
                # 註冊設備到控制器
                controller.register_device(unicast_addr, device_type, name)
                
                print(f"設備 {name} 已成功綁定並添加到設備管理器，類型: {device_type_str}")
                
                # 詢問是否添加到群組
                add_to_group = input("是否將設備添加到群組? (y/n): ").strip().lower()
                if add_to_group == 'y':
                    add_device_to_group(device_manager, unicast_addr)
        else:
            print("選擇無效")
    except ValueError:
        print("請輸入有效的數字")

def display_devices(device_manager: DeviceManager):
    """顯示所有裝置"""
    info = device_manager.get_device_info()
    if not info['devices']:
        print("目前沒有設備")
        return

    print("\n===== 設備列表 =====")
    print(f"設備總數: {info['device_count']}")
    print("-" * 60)
    header = f"{'名稱':<15} {'地址':<10} {'類型':<12} {'群組':<10} {'狀態':<8}"
    print(header)
    print("-" * 60)

    for device in info['devices']:
        # 集中處理欄位預設值
        name = str(device.get('name') or '未命名')
        addr = str(device.get('unicast_addr') or '未知')
        device_type = str(device.get('type') or '未指定')
        device_group = str(device.get('group') or '無')
        status = "已連接"
        print(f"{name:<15} {addr:<10} {device_type:<12} {device_group:<10} {status:<8}")

    print("-" * 60)
    print("\n詳細設備資訊:")
    for i, device in enumerate(info['devices']):
        # 集中處理欄位預設值
        name = device.get('name') or '未命名'
        addr = device.get('unicast_addr') or '未知'
        device_type = device.get('type') or '未指定'
        uuid = device.get('uuid') or '未知'
        mac = device.get('mac_address') or '未知'
        group = device.get('group') or '無'
        added_time = device.get('added_time') or '未記錄'

        print(f"\n[{i+1}] {name} ({addr})")
        print(f"    類型: {device_type}")
        print(f"    UUID: {uuid}")
        print(f"    MAC地址: {mac}")
        print(f"    所屬群組: {group}")
        print(f"    添加時間: {added_time}")

    print("\n使用提示:")
    print("- 使用「設定裝置類型」選項可以變更裝置類型")
    print("- 使用「測試控制裝置」選項可以控制裝置")

def display_groups(device_manager: DeviceManager):
    """顯示所有群組"""
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

def add_device_to_group(device_manager: DeviceManager, unicast_addr: str = None):
    """添加設備到群組"""
    info = device_manager.get_device_info()
    
    # 如果沒有傳入特定設備地址，請用戶選擇
    if unicast_addr is None:
        if not info['devices']:
            print("沒有可用設備")
            return
            
        print("\n可用設備:")
        for idx, device in enumerate(info['devices']):
            print(f"{idx+1}. {device['name']} ({device['unicast_addr']})")
            
        choice = input("\n請選擇設備編號，或按 Enter 取消: ").strip()
        if not choice:
            return
            
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(info['devices']):
                unicast_addr = info['devices'][idx]['unicast_addr']
            else:
                print("選擇無效")
                return
        except ValueError:
            print("請輸入有效的數字")
            return
    
    # 檢查現有群組，或創建新群組
    if not info['groups']:
        create_new = input("目前沒有群組。是否創建新群組? (y/n): ").strip().lower()
        if create_new != 'y':
            return
            
        group_name = input("請輸入新群組名稱: ").strip()
        if not group_name:
            print("群組名稱不能為空")
            return
            
        device_manager.create_group(group_name)
    else:
        print("\n可用群組:")
        groups = list(info['groups'].keys())
        for idx, name in enumerate(groups):
            print(f"{idx+1}. {name}")
            
        create_new = input("\n請選擇群組編號，或輸入 'n' 創建新群組: ").strip().lower()
        
        if create_new == 'n':
            group_name = input("請輸入新群組名稱: ").strip()
            if not group_name:
                print("群組名稱不能為空")
                return
                
            device_manager.create_group(group_name)
        else:
            try:
                idx = int(create_new) - 1
                if 0 <= idx < len(groups):
                    group_name = groups[idx]
                else:
                    print("選擇無效")
                    return
            except ValueError:
                print("請輸入有效的數字")
                return
    
    # 添加設備到群組
    if device_manager.add_device_to_group(unicast_addr, group_name):
        device = device_manager.get_device_by_unicast(unicast_addr)
        print(f"設備 {device['name']} 已添加到群組 {group_name}")
    else:
        print("添加到群組失敗")

def set_device_type(controller: RLMeshDeviceController, device_manager: DeviceManager):
    """設定裝置類型"""
    info = device_manager.get_device_info()
    
    if not info['devices']:
        print("沒有可用設備")
        return
        
    print("\n可用設備:")
    for idx, device in enumerate(info['devices']):
        print(f"{idx+1}. {device['name']} ({device['unicast_addr']})")
        
    choice = input("\n請選擇設備編號，或按 Enter 取消: ").strip()
    if not choice:
        return
        
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(info['devices']):
            unicast_addr = info['devices'][idx]['unicast_addr']
            device_name = info['devices'][idx]['name']
            
            print("\n請選擇設備類型:")
            print(f"1. RGB LED")
            print(f"2. 插座")
            print(f"3. Smart-Box")
            print(f"4. Air-Box")
            print(f"5. 電錶 (Power Meter)")
            
            device_type_choice = input("請輸入設備類型編號 (1-5): ").strip()
            
            if device_type_choice == '1':
                device_type = RLMeshDeviceController.DEVICE_TYPE_RGB_LED
            elif device_type_choice == '2':
                device_type = RLMeshDeviceController.DEVICE_TYPE_PLUG
            elif device_type_choice == '3':
                device_type = RLMeshDeviceController.DEVICE_TYPE_SMART_BOX
            elif device_type_choice == '4':
                device_type = RLMeshDeviceController.DEVICE_TYPE_AIR_BOX
            elif device_type_choice == '5':
                device_type = RLMeshDeviceController.DEVICE_TYPE_POWER_METER
            else:
                print("選擇無效")
                return
            
            controller.register_device(unicast_addr, device_type, device_name)
            print(f"設備 {device_name} 類型已設定為 {device_type}")
        else:
            print("選擇無效")
    except ValueError:
        print("請輸入有效的數字")

def control_device_menu(controller: RLMeshDeviceController, device_manager: DeviceManager):
    """控制裝置選單"""
    info = device_manager.get_device_info()
    
    if not info['devices']:
        print("沒有可用設備")
        return
        
    print("\n可用設備:")
    for idx, device in enumerate(info['devices']):
        device_type = device.get('type', '未指定')
        print(f"{idx+1}. {device['name']} ({device['unicast_addr']}) - 類型: {device_type}")
        
    choice = input("\n請選擇設備編號，或按 Enter 取消: ").strip()
    if not choice:
        return
        
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(info['devices']):
            unicast_addr = info['devices'][idx]['unicast_addr']
            device_name = info['devices'][idx]['name']
            
            # 從 device_manager 獲取設備類型
            device_type = info['devices'][idx].get('type', '未指定')
            
            # 轉換為控制器使用的類型常量
            controller_type = None
            if device_type == 'RGB_LED':
                controller_type = RLMeshDeviceController.DEVICE_TYPE_RGB_LED
            elif device_type == 'PLUG':
                controller_type = RLMeshDeviceController.DEVICE_TYPE_PLUG
            elif device_type == 'SMART_BOX':
                controller_type = RLMeshDeviceController.DEVICE_TYPE_SMART_BOX
            elif device_type == 'AIR_BOX':
                controller_type = RLMeshDeviceController.DEVICE_TYPE_AIR_BOX
            elif device_type == 'POWER_METER':
                controller_type = RLMeshDeviceController.DEVICE_TYPE_POWER_METER
            
            # 檢查設備是否已在控制器中註冊
            registered_devices = controller.get_registered_devices()
            if unicast_addr not in registered_devices and controller_type:
                # 自動註冊設備類型
                print(f"自動註冊設備類型: {device_type}")
                controller.register_device(unicast_addr, controller_type, device_name)
            elif unicast_addr not in registered_devices:
                print(f"設備 {device_name} 的類型 '{device_type}' 無法識別")
                type_choice = input("是否立即設定設備類型? (y/n): ").strip().lower()
                if type_choice == 'y':
                    set_device_type(controller, device_manager)
                return
            
            # 獲取控制器中的設備類型
            device_type = controller.device_map[unicast_addr]['type']
            
            # 根據不同設備類型提供不同控制選項
            if device_type == RLMeshDeviceController.DEVICE_TYPE_RGB_LED:
                control_rgb_led_menu(controller, unicast_addr, device_name)
            elif device_type == RLMeshDeviceController.DEVICE_TYPE_PLUG:
                control_plug_menu(controller, unicast_addr, device_name)
            elif device_type == RLMeshDeviceController.DEVICE_TYPE_SMART_BOX:
                control_smart_box_menu(controller, unicast_addr, device_name)
            elif device_type == RLMeshDeviceController.DEVICE_TYPE_AIR_BOX:
                control_air_box_menu(controller, unicast_addr, device_name)
            elif device_type == RLMeshDeviceController.DEVICE_TYPE_POWER_METER:
                control_power_meter_menu(controller, unicast_addr, device_name)
            else:
                print(f"不支援的設備類型: {device_type}")
        else:
            print("選擇無效")
    except ValueError:
        print("請輸入有效的數字")

def control_rgb_led_menu(controller: RLMeshDeviceController, unicast_addr: str, device_name: str):
    """RGB LED 控制選單"""
    print(f"\n控制 RGB LED: {device_name} ({unicast_addr})")
    print("1. 設定為白光")
    print("2. 設定為紅色")
    print("3. 設定為綠色")
    print("4. 設定為藍色")
    print("5. 設定為紫色")
    print("6. 關閉燈光")
    print("7. 自訂顏色")
    print("0. 返回")
    
    choice = input("請選擇: ").strip()
    
    if choice == '0':
        return
    elif choice == '1':
        controller.control_rgb_led(unicast_addr, 255, 255, 0, 0, 0)
    elif choice == '2':
        controller.control_rgb_led(unicast_addr, 0, 0, 255, 0, 0)
    elif choice == '3':
        controller.control_rgb_led(unicast_addr, 0, 0, 0, 255, 0)
    elif choice == '4':
        controller.control_rgb_led(unicast_addr, 0, 0, 0, 0, 255)
    elif choice == '5':
        controller.control_rgb_led(unicast_addr, 0, 0, 255, 0, 255)
    elif choice == '6':
        controller.control_rgb_led(unicast_addr, 0, 0, 0, 0, 0)
    elif choice == '7':
        try:
            cold = int(input("請輸入冷光值 (0-255): ").strip())
            warm = int(input("請輸入暖光值 (0-255): ").strip())
            red = int(input("請輸入紅色值 (0-255): ").strip())
            green = int(input("請輸入綠色值 (0-255): ").strip())
            blue = int(input("請輸入藍色值 (0-255): ").strip())
            controller.control_rgb_led(unicast_addr, cold, warm, red, green, blue)
        except ValueError:
            print("請輸入有效的數字")
    else:
        print("選擇無效")

def control_plug_menu(controller: RLMeshDeviceController, unicast_addr: str, device_name: str):
    """插座控制選單"""
    print(f"\n控制插座: {device_name} ({unicast_addr})")
    print("1. 開啟")
    print("2. 關閉")
    print("0. 返回")
    
    choice = input("請選擇: ").strip()
    
    if choice == '0':
        return
    elif choice == '1':
        controller.control_plug(unicast_addr, True)
        print("插座已開啟")
    elif choice == '2':
        controller.control_plug(unicast_addr, False)
        print("插座已關閉")
    else:
        print("選擇無效")

def control_smart_box_menu(controller: RLMeshDeviceController, unicast_addr: str, device_name: str):
    """Smart-Box 控制選單"""
    print(f"\n控制 Smart-Box: {device_name} ({unicast_addr})")
    print("1. 讀取保持寄存器")
    print("2. 讀取輸入寄存器")
    print("3. 讀取線圈狀態")
    print("4. 寫入單個寄存器")
    print("5. 控制線圈")
    print("0. 返回")
    
    choice = input("請選擇: ").strip()
    
    if choice == '0':
        return
    elif choice == '1':
        try:
            slave_addr = int(input("請輸入從站地址: ").strip())
            start_addr = int(input("請輸入起始地址: ").strip())
            quantity = int(input("請輸入讀取數量: ").strip())
            resp = controller.read_smart_box_rtu(unicast_addr, slave_addr, ModbusRTU.READ_HOLDING_REGISTERS, start_addr, quantity)
            print(f"初始響應: {resp['initial_response']}")
            if resp['mdtg_response']:
                print(f"MDTG-MSG 響應: {resp['mdtg_response']}")
        except ValueError:
            print("請輸入有效的數字")
    elif choice == '2':
        try:
            slave_addr = int(input("請輸入從站地址: ").strip())
            start_addr = int(input("請輸入起始地址: ").strip())
            quantity = int(input("請輸入讀取數量: ").strip())
            resp = controller.read_smart_box_rtu(unicast_addr, slave_addr, ModbusRTU.READ_INPUT_REGISTERS, start_addr, quantity)
            print(f"初始響應: {resp['initial_response']}")
            if resp['mdtg_response']:
                print(f"MDTG-MSG 響應: {resp['mdtg_response']}")
        except ValueError:
            print("請輸入有效的數字")
    elif choice == '3':
        try:
            slave_addr = int(input("請輸入從站地址: ").strip())
            start_addr = int(input("請輸入起始地址: ").strip())
            quantity = int(input("請輸入讀取數量: ").strip())
            resp = controller.read_smart_box_rtu(unicast_addr, slave_addr, ModbusRTU.READ_COILS, start_addr, quantity)
            print(f"初始響應: {resp['initial_response']}")
            if resp['mdtg_response']:
                print(f"MDTG-MSG 響應: {resp['mdtg_response']}")
        except ValueError:
            print("請輸入有效的數字")
    elif choice == '4':
        try:
            slave_addr = int(input("請輸入從站地址: ").strip())
            reg_addr = int(input("請輸入寄存器地址: ").strip())
            value = int(input("請輸入寄存器值: ").strip())
            resp = controller.write_smart_box_register(unicast_addr, slave_addr, reg_addr, value)
            print(f"初始響應: {resp['initial_response']}")
            if resp['mdtg_response']:
                print(f"MDTG-MSG 響應: {resp['mdtg_response']}")
        except ValueError:
            print("請輸入有效的數字")
    elif choice == '5':
        try:
            slave_addr = int(input("請輸入從站地址: ").strip())
            coil_addr = int(input("請輸入線圈地址: ").strip())
            state = input("請輸入線圈狀態 (on/off): ").strip().lower()
            coil_value = (state == 'on')
            resp = controller.write_smart_box_coil(unicast_addr, slave_addr, coil_addr, coil_value)
            print(f"初始響應: {resp['initial_response']}")
            if resp['mdtg_response']:
                print(f"MDTG-MSG 響應: {resp['mdtg_response']}")
        except ValueError:
            print("請輸入有效的數字")
    else:
        print("選擇無效")

def control_air_box_menu(controller: RLMeshDeviceController, unicast_addr: str, device_name: str):
    """Air-Box 空氣盒子控制選單"""
    while True:
        print(f"\n===== Air-Box 空氣盒子控制選單: {device_name} ({unicast_addr}) =====")
        print("1. 讀取環境數據 (溫度、濕度、PM2.5、CO2)")
        print("2. 連續監測模式 (每3秒讀取一次，按Ctrl+C停止)")
        print("0. 返回上級選單")
        
        choice = input("請輸入選項: ").strip()
        
        if choice == '0':
            break
        elif choice == '1':
            try:
                slave_addr = int(input("請輸入從站地址: ").strip())
                result = controller.read_air_box_data(unicast_addr, slave_addr)
                
                print("\n===== 環境數據結果 =====")
                if result["temperature"] is not None:
                    print(f"溫度: {result['temperature']}°C")
                else:
                    print("溫度: 讀取失敗")
                    
                if result["humidity"] is not None:
                    print(f"濕度: {result['humidity']}%")
                else:
                    print("濕度: 讀取失敗")
                    
                if result["pm25"] is not None:
                    print(f"PM2.5: {result['pm25']} μg/m³")
                else:
                    print("PM2.5: 讀取失敗")
                    
                if result["co2"] is not None:
                    print(f"CO2: {result['co2']} ppm")
                else:
                    print("CO2: 讀取失敗")
                    

            except ValueError:
                print("請輸入有效的數字")
            except Exception as e:
                print(f"發生錯誤: {e}")
                
        elif choice == '2':
            try:
                slave_addr = int(input("請輸入從站地址: ").strip())
                print("\n啟動連續監測模式，按 Ctrl+C 停止...\n")
                try:
                    while True:
                        result = controller.read_air_box_data(unicast_addr, slave_addr)
                        
                        # 清空當前行並顯示最新數據
                        print("\r", end="")
                        data_str = f"溫度: {result['temperature']:5.1f}°C | "
                        data_str += f"濕度: {result['humidity']:5.1f}% | "
                        data_str += f"PM2.5: {result['pm25']:3d} μg/m³ | "
                        data_str += f"CO2: {result['co2']:4d} ppm"
                        print(data_str, end="")
                        
                        time.sleep(3)  # 每3秒讀取一次
                except KeyboardInterrupt:
                    print("\n\n已停止連續監測")
            except ValueError:
                print("請輸入有效的數字")
            except Exception as e:
                print(f"發生錯誤: {e}")
        else:
            print("無效選擇，請重試")

def control_power_meter_menu(controller: RLMeshDeviceController, unicast_addr: str, device_name: str):
    """電錶控制選單"""
    while True:
        print(f"\n===== 電錶控制選單: {device_name} ({unicast_addr}) =====")
        print("1. 讀取電力數據 (電壓、電流、功率、電能)")
        print("2. 連續監測模式 (每3秒讀取一次，按Ctrl+C停止)")
        print("0. 返回上級選單")
        
        choice = input("請輸入選項: ").strip()
        
        if choice == '0':
            break
        elif choice == '1':
            try:
                slave_addr = int(input("請輸入從站地址: ").strip())
                result = controller.read_power_meter_data(unicast_addr, slave_addr)
                
                print("\n===== 電力數據結果 =====")
                if result["voltage"] is not None:
                    print(f"電壓: {result['voltage']} V")
                else:
                    print("電壓: 讀取失敗")
                    
                if result["current"] is not None:
                    print(f"電流: {result['current']} A")
                else:
                    print("電流: 讀取失敗")
                    
                if result["power"] is not None:
                    print(f"功率: {result['power']} W")
                else:
                    print("功率: 讀取失敗")
                    
                   
            except ValueError:
                print("請輸入有效的數字")
            except Exception as e:
                print(f"發生錯誤: {e}")
        elif choice == '2':
            try:
                slave_addr = int(input("請輸入從站地址: ").strip())
                print("\n啟動連續監測模式，按 Ctrl+C 停止...\n")
                try:
                    while True:
                        result = controller.read_power_meter_data(unicast_addr, slave_addr)
                        
                        # 清空當前行並顯示最新數據
                        print("\r", end="")
                        data_str = f"電壓: {result['voltage']:6.1f} V | "
                        data_str += f"電流: {result['current']:5.3f} A | "
                        data_str += f"功率: {result['power']:5.1f} W | "
                        print(data_str, end="")
                        
                        time.sleep(3)  # 每3秒讀取一次
                except KeyboardInterrupt:
                    print("\n\n已停止連續監測")
            except ValueError:
                print("請輸入有效的數字")
            except Exception as e:
                print(f"發生錯誤: {e}")
        else:
            print("無效選擇，請重試")

def unbind_device(prov: Provisioner, device_manager: DeviceManager):
    """解除綁定裝置"""
    info = device_manager.get_device_info()
    devices = info.get('devices', []) # 使用 .get 提供預設值

    if not devices:
        print("沒有可用設備")
        return

    print("\n可用設備:")
    for idx, device in enumerate(devices):
        # 使用 .get 處理可能的缺失鍵值
        name = device.get('name', '未命名')
        addr = device.get('unicast_addr', '未知')
        print(f"{idx+1}. {name} ({addr})")

    choice = input("\n請選擇要解除綁定的設備編號，或按 Enter 取消: ").strip()
    if not choice:
        return

    try:
        idx = int(choice) - 1
        if not (0 <= idx < len(devices)): # 簡化索引範圍檢查
            print("選擇無效")
            return

        # 直接從列表中取得裝置資訊
        selected_device = devices[idx]
        unicast_addr = selected_device.get('unicast_addr')
        device_name = selected_device.get('name', '未命名')

        # 檢查是否成功取得地址
        if not unicast_addr:
            print("錯誤：無法取得所選裝置的地址。")
            return

        confirm = input(f"確定要解除綁定設備 {device_name} ({unicast_addr})? (y/n): ").strip().lower()
        if confirm != 'y':
            print("操作已取消")
            return

        # 發送解除綁定命令並處理回應
        resp = prov._send_and_wait(f'AT+NR {unicast_addr}', timeout=5.0) # 增加超時時間以防萬一
        print(f"解除綁定結果: {resp}")

        # 更穩健的回應檢查
        if isinstance(resp, str) and resp.startswith('NR-MSG SUCCESS'):
            if device_manager.remove_device(unicast_addr):
                 print(f"設備 {device_name} ({unicast_addr}) 已成功解除綁定並從設備管理器中移除")
            else:
                 print(f"警告：設備 {device_name} ({unicast_addr}) 解除綁定成功，但從管理器移除失敗")
        elif isinstance(resp, str):
             print(f"解除綁定設備 {device_name} ({unicast_addr}) 失敗: {resp}")
        else:
             print(f"解除綁定設備 {device_name} ({unicast_addr}) 時收到無效回應")

    except ValueError:
        print("請輸入有效的數字")
    except Exception as e: # 捕捉其他潛在錯誤
        print(f"解除綁定過程中發生未預期的錯誤: {e}")


if __name__ == "__main__":
    main()
