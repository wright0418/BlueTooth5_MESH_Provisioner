#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RL Mesh 設備示範程式 (使用 rl62m02 套件)
提供控制 RL Mesh 各種設備的功能演示
"""

import time
import sys,os
import logging
import rl62m02
from rl62m02.controllers.mesh_controller import RLMeshDeviceController
from rl62m02.modbus import ModbusRTU

# 注意：DeviceManager 現在透過 rl62m02.create_provisioner 取得

def main():
    if len(sys.argv) < 2:
        print("使用方式: python demo/RL_devices_demo.py <COM埠> [測試類型]")
        print("測試類型: all, rgb, plug, smart_box, device_mgmt (預設: all)")
        return

    com_port = sys.argv[1]
    test_type = "all"
    if len(sys.argv) >= 3:
        test_type = sys.argv[2].lower()

    ser = None # 初始化 ser 變數
    try:
        # 使用 rl62m02 套件的輔助函數初始化
        print(f"初始化 rl62m02 在埠 {com_port}...")
        # create_provisioner 會處理 SerialAT, Provisioner 和 DeviceManager 的初始化
        # 它會自動尋找上層目錄的 mesh_devices.json
        ser, prov, device_manager = rl62m02.create_provisioner(com_port)

        if device_manager is None:
            print("警告: 無法初始化 DeviceManager，請確保 mesh_devices.json 存在於正確位置。")
            # 根據需求，這裡可以選擇退出或繼續執行不依賴 device_manager 的功能
            # return

        # 創建控制器
        controller = RLMeshDeviceController(prov)

        # 如果 device_manager 成功初始化，載入現有設備並註冊到控制器
        if device_manager:
            print("從 device_manager 載入並註冊設備到控制器...")
            all_devices = device_manager.get_device_info().get('devices', [])
            for device in all_devices:
                addr = device.get('unicast_addr')
                dtype = device.get('type')
                name = device.get('name')
                if addr and dtype and name:
                    # 將 device_manager 中的類型字串轉換為控制器使用的常數
                    controller_type = None
                    if dtype == 'RGB_LED':
                        controller_type = RLMeshDeviceController.DEVICE_TYPE_RGB_LED
                    elif dtype == 'PLUG':
                        controller_type = RLMeshDeviceController.DEVICE_TYPE_PLUG
                    elif dtype == 'SMART_BOX':
                        controller_type = RLMeshDeviceController.DEVICE_TYPE_SMART_BOX
                    elif dtype == 'AIR_BOX':
                        controller_type = RLMeshDeviceController.DEVICE_TYPE_AIR_BOX
                    elif dtype == 'POWER_METER':
                        controller_type = RLMeshDeviceController.DEVICE_TYPE_POWER_METER

                    if controller_type:
                        controller.register_device(addr, controller_type, name)
                        print(f"  - 已註冊: {name} ({addr}), 類型: {dtype}")
                    else:
                        print(f"  - 警告: 設備 {name} ({addr}) 的類型 '{dtype}' 無法識別，未註冊到控制器。")
            print("設備註冊完成。")


        # 裝置管理功能
        if test_type in ["all", "device_mgmt"]:
            # 確保 device_manager 存在才傳遞
            device_management_menu(prov, controller, device_manager if device_manager else None)
            return # 執行完管理選單後退出

        # 其他測試類型 (如果需要的話)
        # ... (可以保留或移除原有的 rgb, plug, smart_box 測試)

    except Exception as e:
        print(f"發生錯誤: {e}")
        import traceback
        traceback.print_exc() # 打印詳細的錯誤追蹤
    finally:
        if ser and hasattr(ser, 'ser') and ser.ser.is_open: # 檢查 ser 是否已成功初始化且開啟
            print("關閉序列埠...")
            ser.close()

def device_management_menu(prov: rl62m02.Provisioner, controller: RLMeshDeviceController, device_manager):
    """裝置管理功能選單"""
    if device_manager is None:
        print("\n錯誤：Device Manager 未初始化，無法進行裝置管理。")
        return

    while True:
        print("\n===== 裝置管理選單 (使用 rl62m02 套件) =====")
        print("1. 掃描與綁定新裝置")
        print("2. 顯示所有裝置")
        print("3. 顯示所有群組")
        print("4. 設定裝置類型 (更新控制器中的註冊)")
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
            # 注意：此功能現在主要更新 Controller 的內部註冊
            # Device Manager 中的類型在綁定時設定
            set_device_type(controller, device_manager)
        elif choice == '5':
            control_device_menu(controller, device_manager)
        elif choice == '6':
            unbind_device(prov, device_manager)
        else:
            print("無效選擇，請重試")

def scan_and_provision(prov: rl62m02.Provisioner, controller: RLMeshDeviceController, device_manager):
    """掃描並綁定新裝置 (使用 rl62m02 輔助函數)"""
    print("開始掃描網狀網路裝置...")
    # 使用套件的掃描函數
    scan_result = rl62m02.scan_devices(prov, scan_time=5)

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
            target_uuid = target['uuid']
            target_mac = target['mac address']

            print(f"開始自動綁定 UUID: {target_uuid}")

            # 提示設備類型選擇
            print("\n請選擇設備類型:")
            print(f"1. RGB LED ({RLMeshDeviceController.DEVICE_TYPE_RGB_LED})")
            print(f"2. 插座 ({RLMeshDeviceController.DEVICE_TYPE_PLUG})")
            print(f"3. Smart-Box ({RLMeshDeviceController.DEVICE_TYPE_SMART_BOX})")
            print(f"4. Air-Box ({RLMeshDeviceController.DEVICE_TYPE_AIR_BOX})")
            print(f"5. 電錶 ({RLMeshDeviceController.DEVICE_TYPE_POWER_METER})")
            device_type_choice = input("請輸入設備類型編號 (1-5): ").strip()

            device_type_str = RLMeshDeviceController.DEVICE_TYPE_RGB_LED # 預設類型字串
            controller_type = RLMeshDeviceController.DEVICE_TYPE_RGB_LED # 控制器使用的類型
            if device_type_choice == '2':
                device_type_str = RLMeshDeviceController.DEVICE_TYPE_PLUG
                controller_type = RLMeshDeviceController.DEVICE_TYPE_PLUG
            elif device_type_choice == '3':
                device_type_str = RLMeshDeviceController.DEVICE_TYPE_SMART_BOX
                controller_type = RLMeshDeviceController.DEVICE_TYPE_SMART_BOX
            elif device_type_choice == '4':
                device_type_str = RLMeshDeviceController.DEVICE_TYPE_AIR_BOX
                controller_type = RLMeshDeviceController.DEVICE_TYPE_AIR_BOX
            elif device_type_choice == '5':
                device_type_str = RLMeshDeviceController.DEVICE_TYPE_POWER_METER
                controller_type = RLMeshDeviceController.DEVICE_TYPE_POWER_METER

            # 設備名稱
            name = input(f"請輸入設備名稱 (直接按Enter使用預設): ").strip()
            # 如果名稱為空，在 provision_device 內部會生成預設名稱

            # 使用套件的綁定函數，它會處理綁定和添加到 device_manager
            result = rl62m02.provision_device(prov, target_uuid, device_manager, name, device_type_str)
            print('綁定結果:', result)

            if result.get('result') == 'success':
                unicast_addr = result.get('unicast_addr')
                # provision_device 已經處理了 device_manager.add_device
                # 但我們仍需手動註冊到控制器
                # 使用從 result 中獲取的最終設備名稱 (可能是預設的)
                final_name = device_manager.get_device_by_unicast(unicast_addr).get('name', f"Device-{unicast_addr}")
                controller.register_device(unicast_addr, controller_type, final_name)

                print(f"設備 {final_name} ({unicast_addr}) 已成功綁定並添加到設備管理器，類型: {device_type_str}")
                print(f"設備 {final_name} ({unicast_addr}) 已註冊到控制器")


                # 詢問是否添加到群組
                add_to_group_choice = input("是否將設備添加到群組? (y/n): ").strip().lower()
                if add_to_group_choice == 'y':
                    add_device_to_group(device_manager, unicast_addr)
            else:
                 print(f"綁定失敗: {result.get('message', '未知錯誤')}")

        else:
            print("選擇無效")
    except ValueError:
        print("請輸入有效的數字")
    except Exception as e:
        print(f"綁定過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()


# --- display_devices, display_groups, add_device_to_group 保持不變 ---
# --- (因為它們只依賴 device_manager) ---
def display_devices(device_manager):
    """顯示所有裝置"""
    if not device_manager:
        print("Device Manager 未初始化。")
        return
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
        status = "已連接" # 假設狀態，實際狀態需查詢
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
    print("- 使用「設定裝置類型」選項可以更新控制器中的裝置類型註冊")
    print("- 使用「測試控制裝置」選項可以控制裝置")

def display_groups(device_manager):
    """顯示所有群組"""
    if not device_manager:
        print("Device Manager 未初始化。")
        return
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
                    print(f"  - {device.get('name', '未命名')} ({addr})")
                else:
                    print(f"  - (地址 {addr} 的設備資訊未找到)")
        else:
            print("  (群組為空)")
        print("")

def add_device_to_group(device_manager, unicast_addr: str = None):
    """添加設備到群組"""
    if not device_manager:
        print("Device Manager 未初始化。")
        return
    info = device_manager.get_device_info()

    # 如果沒有傳入特定設備地址，請用戶選擇
    if unicast_addr is None:
        if not info['devices']:
            print("沒有可用設備")
            return

        print("\n可用設備:")
        for idx, device in enumerate(info['devices']):
            print(f"{idx+1}. {device.get('name', '未命名')} ({device.get('unicast_addr', '未知')})")

        choice = input("\n請選擇設備編號，或按 Enter 取消: ").strip()
        if not choice:
            return

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(info['devices']):
                unicast_addr = info['devices'][idx].get('unicast_addr')
                if not unicast_addr:
                    print("錯誤：選擇的設備沒有地址。")
                    return
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
                print("請輸入有效的數字或 'n'")
                return

    # 添加設備到群組
    if device_manager.add_device_to_group(unicast_addr, group_name):
        device = device_manager.get_device_by_unicast(unicast_addr)
        print(f"設備 {device.get('name', '未命名')} 已添加到群組 {group_name}")
    else:
        print("添加到群組失敗 (可能設備已在群組中)")


def set_device_type(controller: RLMeshDeviceController, device_manager):
    """設定裝置類型 (主要更新 Controller 的註冊)"""
    if not device_manager:
        print("Device Manager 未初始化。")
        return
    info = device_manager.get_device_info()

    if not info['devices']:
        print("沒有可用設備")
        return

    print("\n可用設備 (來自 Device Manager):")
    for idx, device in enumerate(info['devices']):
         print(f"{idx+1}. {device.get('name', '未命名')} ({device.get('unicast_addr', '未知')}) - 當前類型 (DM): {device.get('type', '未指定')}")

    choice = input("\n請選擇要更新控制器註冊的設備編號，或按 Enter 取消: ").strip()
    if not choice:
        return

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(info['devices']):
            selected_device = info['devices'][idx]
            unicast_addr = selected_device.get('unicast_addr')
            device_name = selected_device.get('name', '未命名')

            if not unicast_addr:
                print("錯誤：選擇的設備沒有地址。")
                return

            print("\n請選擇新的設備類型 (用於控制器):")
            print(f"1. RGB LED ({RLMeshDeviceController.DEVICE_TYPE_RGB_LED})")
            print(f"2. 插座 ({RLMeshDeviceController.DEVICE_TYPE_PLUG})")
            print(f"3. Smart-Box ({RLMeshDeviceController.DEVICE_TYPE_SMART_BOX})")
            print(f"4. Air-Box ({RLMeshDeviceController.DEVICE_TYPE_AIR_BOX})")
            print(f"5. 電錶 ({RLMeshDeviceController.DEVICE_TYPE_POWER_METER})")

            device_type_choice = input("請輸入設備類型編號 (1-5): ").strip()

            controller_type = None
            if device_type_choice == '1':
                controller_type = RLMeshDeviceController.DEVICE_TYPE_RGB_LED
            elif device_type_choice == '2':
                controller_type = RLMeshDeviceController.DEVICE_TYPE_PLUG
            elif device_type_choice == '3':
                controller_type = RLMeshDeviceController.DEVICE_TYPE_SMART_BOX
            elif device_type_choice == '4':
                controller_type = RLMeshDeviceController.DEVICE_TYPE_AIR_BOX
            elif device_type_choice == '5':
                controller_type = RLMeshDeviceController.DEVICE_TYPE_POWER_METER
            else:
                print("選擇無效")
                return

            # 更新控制器中的註冊
            if controller.register_device(unicast_addr, controller_type, device_name):
                 print(f"控制器中設備 {device_name} ({unicast_addr}) 的類型已更新為 {controller_type}")
            else:
                 print(f"更新控制器中設備 {device_name} 的類型失敗。")
            # 注意：這不會修改 device_manager 中存儲的類型

        else:
            print("選擇無效")
    except ValueError:
        print("請輸入有效的數字")

def control_device_menu(controller: RLMeshDeviceController, device_manager):
    """控制裝置選單"""
    if not device_manager:
        print("Device Manager 未初始化。")
        return

    registered_devices = controller.get_registered_devices()
    if not registered_devices:
        print("控制器中沒有已註冊的設備可供控制。")
        print("請先綁定設備並確保它們已在啟動時或手動移除。")
        return

    print("\n可控制的設備 (來自控制器):")
    device_list = list(registered_devices.items()) # (unicast_addr, {'type': type, 'name': name})
    for idx, (addr, info) in enumerate(device_list):
        print(f"{idx+1}. {info['name']} ({addr}) - 類型: {info['type']}")

    choice = input("\n請選擇設備編號，或按 Enter 取消: ").strip()
    if not choice:
        return

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(device_list):
            unicast_addr, device_info = device_list[idx]
            device_name = device_info['name']
            device_type = device_info['type'] # 這裡直接使用控制器中的類型

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
                # 理論上不應該發生，因為是從 registered_devices 來的
                print(f"不支援的設備類型: {device_type}")
        else:
            print("選擇無效")
    except ValueError:
        print("請輸入有效的數字")

# --- control_rgb_led_menu, control_plug_menu, control_smart_box_menu ---
# --- control_air_box_menu, control_power_meter_menu 保持不變 ---
# --- (因為它們只依賴 controller) ---
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

    result = "操作取消或無效選擇"
    try:
        if choice == '0':
            return
        elif choice == '1':
            result = controller.control_rgb_led(unicast_addr, 255, 255, 0, 0, 0)
        elif choice == '2':
            result = controller.control_rgb_led(unicast_addr, 0, 0, 255, 0, 0)
        elif choice == '3':
            result = controller.control_rgb_led(unicast_addr, 0, 0, 0, 255, 0)
        elif choice == '4':
            result = controller.control_rgb_led(unicast_addr, 0, 0, 0, 0, 255)
        elif choice == '5':
            result = controller.control_rgb_led(unicast_addr, 0, 0, 255, 0, 255)
        elif choice == '6':
            result = controller.control_rgb_led(unicast_addr, 0, 0, 0, 0, 0)
        elif choice == '7':
            try:
                cold = int(input("請輸入冷光值 (0-255): ").strip())
                warm = int(input("請輸入暖光值 (0-255): ").strip())
                red = int(input("請輸入紅色值 (0-255): ").strip())
                green = int(input("請輸入綠色值 (0-255): ").strip())
                blue = int(input("請輸入藍色值 (0-255): ").strip())
                result = controller.control_rgb_led(unicast_addr, cold, warm, red, green, blue)
            except ValueError:
                print("請輸入有效的數字")
                result = "輸入無效"
        else:
            print("選擇無效")

        print(f"控制結果: {result}")

    except Exception as e:
        print(f"控制 RGB LED 時發生錯誤: {e}")


def control_plug_menu(controller: RLMeshDeviceController, unicast_addr: str, device_name: str):
    """插座控制選單"""
    print(f"\n控制插座: {device_name} ({unicast_addr})")
    print("1. 開啟")
    print("2. 關閉")
    print("0. 返回")

    choice = input("請選擇: ").strip()
    result = "操作取消或無效選擇"
    try:
        if choice == '0':
            return
        elif choice == '1':
            result = controller.control_plug(unicast_addr, True)
            print("插座已開啟")
        elif choice == '2':
            result = controller.control_plug(unicast_addr, False)
            print("插座已關閉")
        else:
            print("選擇無效")

        print(f"控制結果: {result}")

    except Exception as e:
        print(f"控制插座時發生錯誤: {e}")


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

    try:
        if choice == '0':
            return
        elif choice == '1':
            try:
                slave_addr = int(input("請輸入從站地址: ").strip())
                start_addr = int(input("請輸入起始地址: ").strip())
                quantity = int(input("請輸入讀取數量: ").strip())
                resp = controller.read_smart_box_rtu(unicast_addr, slave_addr, ModbusRTU.READ_HOLDING_REGISTERS, start_addr, quantity)
                print(f"初始響應: {resp.get('initial_response', 'N/A')}")
                print(f"MDTG-MSG 響應: {resp.get('mdtg_response', 'N/A')}")
            except ValueError:
                print("請輸入有效的數字")
        elif choice == '2':
            try:
                slave_addr = int(input("請輸入從站地址: ").strip())
                start_addr = int(input("請輸入起始地址: ").strip())
                quantity = int(input("請輸入讀取數量: ").strip())
                resp = controller.read_smart_box_rtu(unicast_addr, slave_addr, ModbusRTU.READ_INPUT_REGISTERS, start_addr, quantity)
                print(f"初始響應: {resp.get('initial_response', 'N/A')}")
                print(f"MDTG-MSG 響應: {resp.get('mdtg_response', 'N/A')}")
            except ValueError:
                print("請輸入有效的數字")
        elif choice == '3':
            try:
                slave_addr = int(input("請輸入從站地址: ").strip())
                start_addr = int(input("請輸入起始地址: ").strip())
                quantity = int(input("請輸入讀取數量: ").strip())
                resp = controller.read_smart_box_rtu(unicast_addr, slave_addr, ModbusRTU.READ_COILS, start_addr, quantity)
                print(f"初始響應: {resp.get('initial_response', 'N/A')}")
                print(f"MDTG-MSG 響應: {resp.get('mdtg_response', 'N/A')}")
            except ValueError:
                print("請輸入有效的數字")
        elif choice == '4':
            try:
                slave_addr = int(input("請輸入從站地址: ").strip())
                reg_addr = int(input("請輸入寄存器地址: ").strip())
                value = int(input("請輸入寄存器值: ").strip())
                resp = controller.write_smart_box_register(unicast_addr, slave_addr, reg_addr, value)
                print(f"初始響應: {resp.get('initial_response', 'N/A')}")
                print(f"MDTG-MSG 響應: {resp.get('mdtg_response', 'N/A')}")
            except ValueError:
                print("請輸入有效的數字")
        elif choice == '5':
            try:
                slave_addr = int(input("請輸入從站地址: ").strip())
                coil_addr = int(input("請輸入線圈地址: ").strip())
                state = input("請輸入線圈狀態 (on/off): ").strip().lower()
                coil_value = (state == 'on')
                resp = controller.write_smart_box_coil(unicast_addr, slave_addr, coil_addr, coil_value)
                print(f"初始響應: {resp.get('initial_response', 'N/A')}")
                print(f"MDTG-MSG 響應: {resp.get('mdtg_response', 'N/A')}")
            except ValueError:
                print("請輸入有效的數字")
        else:
            print("選擇無效")

    except Exception as e:
        print(f"控制 Smart Box 時發生錯誤: {e}")


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
                print(f"原始響應: {result.get('raw_data', 'N/A')}") # 顯示原始響應以供調試
                if result["temperature"] is not None:
                    print(f"溫度: {result['temperature']:.1f}°C")
                else:
                    print("溫度: 讀取失敗或解析失敗")

                if result["humidity"] is not None:
                    print(f"濕度: {result['humidity']:.1f}%")
                else:
                    print("濕度: 讀取失敗或解析失敗")

                if result["pm25"] is not None:
                    print(f"PM2.5: {result['pm25']} μg/m³")
                else:
                    print("PM2.5: 讀取失敗或解析失敗")

                if result["co2"] is not None:
                    print(f"CO2: {result['co2']} ppm")
                else:
                    print("CO2: 讀取失敗或解析失敗")


            except ValueError:
                print("請輸入有效的數字")
            except Exception as e:
                print(f"讀取 Air Box 數據時發生錯誤: {e}")
                import traceback
                traceback.print_exc()

        elif choice == '2':
            try:
                slave_addr = int(input("請輸入從站地址: ").strip())
                print("\n啟動連續監測模式，按 Ctrl+C 停止...\n")
                try:
                    while True:
                        result = controller.read_air_box_data(unicast_addr, slave_addr)

                        # 清空當前行並顯示最新數據
                        print("\r", end="") # 清除行
                        temp_str = f"{result['temperature']:.1f}°C" if result['temperature'] is not None else "N/A"
                        hum_str = f"{result['humidity']:.1f}%" if result['humidity'] is not None else "N/A"
                        pm25_str = f"{result['pm25']}" if result['pm25'] is not None else "N/A"
                        co2_str = f"{result['co2']}" if result['co2'] is not None else "N/A"

                        data_str = f"溫度: {temp_str:<8} | "
                        data_str += f"濕度: {hum_str:<7} | "
                        data_str += f"PM2.5: {pm25_str:<5} μg/m³ | "
                        data_str += f"CO2: {co2_str:<5} ppm"
                        print(data_str.ljust(80), end="") # 打印並用空格填充以覆蓋舊內容
                        sys.stdout.flush() # 確保立即顯示

                        time.sleep(3)  # 每3秒讀取一次
                except KeyboardInterrupt:
                    print("\n\n已停止連續監測")
            except ValueError:
                print("請輸入有效的數字")
            except Exception as e:
                print(f"\n連續監測時發生錯誤: {e}")
        else:
            print("無效選擇，請重試")

def control_power_meter_menu(controller: RLMeshDeviceController, unicast_addr: str, device_name: str):
    """電錶控制選單"""
    while True:
        print(f"\n===== 電錶控制選單: {device_name} ({unicast_addr}) =====")
        print("1. 讀取電力數據 (電壓、電流、功率)")
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
                print(f"原始響應: {result.get('raw_data', 'N/A')}") # 顯示原始響應以供調試
                if result["voltage"] is not None:
                    print(f"電壓: {result['voltage']:.1f} V")
                else:
                    print("電壓: 讀取失敗或解析失敗")

                if result["current"] is not None:
                    print(f"電流: {result['current']:.3f} A")
                else:
                    print("電流: 讀取失敗或解析失敗")

                if result["power"] is not None:
                    print(f"功率: {result['power']:.1f} W")
                else:
                    print("功率: 讀取失敗或解析失敗")


            except ValueError:
                print("請輸入有效的數字")
            except Exception as e:
                print(f"讀取電錶數據時發生錯誤: {e}")
                import traceback
                traceback.print_exc()
        elif choice == '2':
            try:
                slave_addr = int(input("請輸入從站地址: ").strip())
                print("\n啟動連續監測模式，按 Ctrl+C 停止...\n")
                try:
                    while True:
                        result = controller.read_power_meter_data(unicast_addr, slave_addr)

                        # 清空當前行並顯示最新數據
                        print("\r", end="") # 清除行
                        volt_str = f"{result['voltage']:.1f} V" if result['voltage'] is not None else "N/A"
                        curr_str = f"{result['current']:.3f} A" if result['current'] is not None else "N/A"
                        pow_str = f"{result['power']:.1f} W" if result['power'] is not None else "N/A"

                        data_str = f"電壓: {volt_str:<8} | "
                        data_str += f"電流: {curr_str:<9} | "
                        data_str += f"功率: {pow_str:<8}"
                        print(data_str.ljust(60), end="") # 打印並用空格填充
                        sys.stdout.flush() # 確保立即顯示

                        time.sleep(3)  # 每3秒讀取一次
                except KeyboardInterrupt:
                    print("\n\n已停止連續監測")
            except ValueError:
                print("請輸入有效的數字")
            except Exception as e:
                print(f"\n連續監測時發生錯誤: {e}")
        else:
            print("無效選擇，請重試")


def unbind_device(prov: rl62m02.Provisioner, device_manager):
    """解除綁定裝置"""
    if not device_manager:
        print("Device Manager 未初始化。")
        return
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

        # 使用 Provisioner 的 node_reset 方法 (假設存在且功能相同)
        # 注意：需要確認 provisioner.py 中是否有 node_reset 方法及其返回值
        # 如果沒有，可能需要繼續使用 _send_and_wait 或其他公共方法
        print(f"正在解除綁定 {device_name} ({unicast_addr})...")
        # 假設 node_reset 返回 True/False 或 包含成功/失敗信息的字典
        success = False
        message = "未知錯誤"
        try:
            # 嘗試使用公共方法 node_reset
            # 假設它返回一個字典，包含 'result' 和 'message'
            # 或者直接返回布林值
            resp = prov.node_reset(unicast_addr)
            print(f"解除綁定響應: {resp}")

            # 根據實際的返回值調整判斷邏輯
            if isinstance(resp, bool):
                success = resp
                message = "成功" if success else "失敗 (來自 node_reset)"
            elif isinstance(resp, dict):
                 # 假設字典格式類似 {'result': 'success'/'fail', 'message': '...'}
                 if resp.get('result') == 'success':
                     success = True
                     message = resp.get('message', '成功')
                 else:
                     success = False
                     message = resp.get('message', '失敗')
            elif isinstance(resp, str) and "SUCCESS" in resp: # 兼容舊的字串響應模式
                 success = True
                 message = resp
            else:
                 message = f"收到未知的響應類型: {type(resp)}"


        except AttributeError:
             print("警告: Provisioner 物件沒有 'node_reset' 方法，嘗試使用舊的 AT 命令。")
             # 回退到使用私有方法或直接發送 AT 命令
             at_cmd_resp = prov.serial_at.send_command(f'AT+NR {unicast_addr}', timeout=5.0)
             print(f"AT+NR 命令響應: {at_cmd_resp}")
             if isinstance(at_cmd_resp, str) and "NR-MSG SUCCESS" in at_cmd_resp:
                 success = True
                 message = at_cmd_resp
             else:
                 message = f"AT 命令失敗或超時: {at_cmd_resp}"
        except Exception as nr_err:
             message = f"調用 node_reset 時出錯: {nr_err}"


        if success:
            print(f"設備 {device_name} ({unicast_addr}) 解除綁定成功。")
            # 從設備管理器中移除
            if device_manager.remove_device(unicast_addr):
                 print(f"設備已從設備管理器中移除。")
            else:
                 print(f"警告：從管理器移除設備失敗。")
            # 注意：控制器中的註冊會保留，直到下次啟動或手動移除
            # 可以考慮在這裡也從控制器移除：
            # if unicast_addr in controller.device_map:
            #     del controller.device_map[unicast_addr]
            #     print("設備已從控制器註冊中移除。")
        else:
             print(f"解除綁定設備 {device_name} ({unicast_addr}) 失敗: {message}")


    except ValueError:
        print("請輸入有效的數字")
    except Exception as e: # 捕捉其他潛在錯誤
        print(f"解除綁定過程中發生未預期的錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":


    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)
    
    # 使用絕對導入
    from rl62m02.serial_at import SerialAT
    from rl62m02.provisioner import Provisioner
    import device_manager
    DeviceManager = device_manager.DeviceManager
    from rl62m02.controllers.mesh_controller import RLMeshDeviceController


    
else:
    # 作為模組導入時，使用相對導入
    from .serial_at import SerialAT
    from .provisioner import Provisioner
    try:
        from .device_manager import DeviceManager
    except ImportError:
        # 嘗試從上層目錄導入
        import sys
        import os
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, parent_dir)
        import device_manager
        DeviceManager = device_manager.DeviceManager
        sys.path.pop(0)
    from .controllers.mesh_controller import RLMeshDeviceController
    # 設定日誌級別，以便看到套件內部的調試信息（如果套件有配置日誌）
    # logging.basicConfig(level=logging.DEBUG)
    logging.basicConfig(level=logging.INFO) # 或 INFO，根據需要調整

main()