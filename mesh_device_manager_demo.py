#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RL Mesh 設備管理器使用範例
示範 MeshDeviceManager 類別的主要功能
"""

import sys
import logging
import rl62m02
from rl62m02 import MeshDeviceManager

# 設定日誌格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def main():
    if len(sys.argv) < 2:
        print("使用方式: python mesh_device_manager_example.py <COM埠>")
        return

    com_port = sys.argv[1]
    
    try:
        # 初始化 RL62M02 系統
        print(f"初始化 RL62M02 在埠 {com_port}...")
        try:
            serial_at, provisioner, _ = rl62m02.create_provisioner(com_port)
            print("RL62M02 初始化成功")
        except ValueError as role_err:
            # 處理角色檢查失敗的情況
            print(f"錯誤: Provisioner 初始化失敗 - {role_err}")
            print("請確認設備已正確配置為 PROVISIONER 角色")
            return
        except Exception as init_err:
            # 處理其他初始化錯誤
            print(f"錯誤: 設備初始化失敗 - {init_err}")
            print("請檢查設備連接狀態和 COM 埠配置")
            return
        
        # 建立裝置管理器，使用 new1_device.json 作為設備資料存檔
        device_manager = MeshDeviceManager(
            provisioner=provisioner,
            device_json_path="My_device.json"
        )
        
        print("裝置管理器初始化成功")
        
        # 主選單
        while True:
            print("\n===== RL Mesh 設備管理器示範 =====")
            print("1. 掃描設備")
            print("2. 顯示所有設備")
            print("3. 設定設備名稱")
            print("4. 設定訂閱")
            print("5. 設定推播")
            print("6. 控制設備")
            print("7. 解除綁定設備")
            print("0. 離開")
            
            choice = input("請選擇操作: ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                scan_devices(device_manager)
            elif choice == '2':
                display_all_devices(device_manager)
            elif choice == '3':
                set_device_name(device_manager)
            elif choice == '4':
                set_subscription(device_manager)
            elif choice == '5':
                set_publication(device_manager)
            elif choice == '6':
                control_device(device_manager)
            elif choice == '7':
                unbind_device(device_manager)
            else:
                print("無效選擇，請重試")
    
    except Exception as e:
        print(f"發生錯誤: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'serial_at' in locals() and hasattr(serial_at, 'ser') and serial_at.ser.is_open:
            print("關閉序列埠...")
            serial_at.close()
        print("程式已結束")

def scan_devices(device_manager):
    """掃描附近設備並提供綁定選項"""
    scan_time = input("請輸入掃描時間(秒，默認5秒): ").strip()
    try:
        scan_time = float(scan_time) if scan_time else 5.0
        devices = device_manager.scan_devices(scan_time)
        
        if devices:
            print(f"\n發現 {len(devices)} 個設備:")
            for idx, device in enumerate(devices):
                print(f"{idx+1}. UUID: {device['uuid']}, MAC: {device['mac address']}")
            
            # 詢問是否要綁定設備
            choice = input("\n要綁定設備嗎? 請輸入設備編號進行綁定，或按 Enter 返回: ").strip()
            if choice:
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(devices):
                        provision_device(device_manager, devices, idx)
                    else:
                        print("選擇無效")
                except ValueError:
                    print("請輸入有效的數字")
        else:
            print("未發現任何設備，請確認設備已開啟")
    except ValueError:
        print("請輸入有效的數字")

def provision_device(device_manager, devices=None, selected_idx=None):
    """綁定設備"""
    # 如果沒有提供設備列表，先進行掃描
    if devices is None:
        print("掃描設備中...")
        devices = device_manager.scan_devices(5.0)
        
        if not devices:
            print("未發現可綁定的設備")
            return
        
        print(f"\n發現 {len(devices)} 個設備:")
        for idx, device in enumerate(devices):
            print(f"{idx+1}. UUID: {device['uuid']}, MAC: {device['mac address']}")
        
        choice = input("\n請選擇要綁定的設備編號，或按 Enter 取消: ").strip()
        if not choice:
            return
        
        try:
            selected_idx = int(choice) - 1
            if not (0 <= selected_idx < len(devices)):
                print("選擇無效")
                return
        except ValueError:
            print("請輸入有效的數字")
            return
    
    try:
        # 使用選定的設備
        target = devices[selected_idx]
        
        # 收集設備信息
        print("\n請選擇設備類型:")
        print("1. RGB LED")
        print("2. 插座 (Plug)")
        print("3. Smart-Box")
        print("4. Air-Box")
        print("5. 電錶 (Power Meter)")
        print("6. 其他 (自定義)")
        
        type_choice = input("請選擇設備類型 (1-6): ").strip()
        
        device_type = "RGB_LED"
        if type_choice == '2':
            device_type = "PLUG"
        elif type_choice == '3':
            device_type = "SMART_BOX"
        elif type_choice == '4':
            device_type = "AIR_BOX"
        elif type_choice == '5':
            device_type = "POWER_METER"
        elif type_choice == '6':
            device_type = input("請輸入自定義設備類型: ").strip()
        
        device_name = input("請輸入設備名稱: ").strip()
        position = input("請輸入設備位置 (可選): ").strip()
        
        # 執行綁定
        result = device_manager.provision_device(
            uuid=target['uuid'],
            device_name=device_name,
            device_type=device_type,
            position=position
        )
        
        if result["result"] == "success":
            print(f"設備綁定成功! UID: {result['unicast_addr']}")
            
            # 詢問是否設定訂閱和推播
            if input("是否設定訂閱? (y/n): ").strip().lower() == 'y':
                group_addr = input("請輸入訂閱通道地址 (例如: 0xC000): ").strip()
                device_manager.set_subscription(result['unicast_addr'], group_addr)
            
            if input("是否設定推播? (y/n): ").strip().lower() == 'y':
                pub_addr = input("請輸入推播通道地址 (例如: 0xC001): ").strip()
                device_manager.set_publication(result['unicast_addr'], pub_addr)
        else:
            print(f"綁定失敗: {result.get('error', '未知錯誤')}")
    except Exception as e:
        print(f"綁定過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()

def set_device_name(device_manager):
    """設定設備名稱"""
    devices = device_manager.get_all_devices()
    if not devices:
        print("沒有已綁定的設備")
        return
        
    print("\n可用設備:")
    for idx, device in enumerate(devices):
        name = device.get('devType') or '未命名'      # 從 devType 讀取名稱
        uid = device.get('uid', '未知')
        device_type = device.get('devName') or '未指定'  # 從 devName 讀取類型
        print(f"{idx+1}. {name} (類型: {device_type}, UID: {uid})")
    
    choice = input("\n請選擇要設定名稱的設備編號，或按 Enter 取消: ").strip()
    if not choice:
        return
        
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(devices):
            old_name = devices[idx].get('devType') or '未命名'
            print(f"當前名稱: {old_name}")
            
            new_name = input("請輸入新名稱: ").strip()
            if new_name:
                result = device_manager.set_device_name(idx, new_name)
                if result["result"] == "success":
                    print(f"設備名稱已更新為: {new_name}")
                else:
                    print(f"更新失敗: {result.get('error', '未知錯誤')}")
            else:
                print("名稱未更改")
        else:
            print("選擇無效")
    except ValueError:
        print("請輸入有效的數字")

def set_subscription(device_manager):
    """設定設備訂閱"""
    devices = device_manager.get_all_devices()
    if not devices:
        print("沒有已綁定的設備")
        return
        
    print("\n可用設備:")
    for idx, device in enumerate(devices):
        name = device.get('devType') or '未命名'      # 從 devType 讀取名稱
        uid = device.get('uid', '未知')
        device_type = device.get('devName') or '未指定'  # 從 devName 讀取類型
        print(f"{idx+1}. {name} (類型: {device_type}, UID: {uid})")
    
    choice = input("\n請選擇要設定訂閱的設備編號，或按 Enter 取消: ").strip()
    if not choice:
        return
        
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(devices):
            group_addr = input("請輸入訂閱通道地址 (例如: 0xC000): ").strip()
            if group_addr:
                result = device_manager.set_subscription(idx, group_addr)
                if result["result"] == "success":
                    print(f"訂閱設定成功，當前訂閱列表: {result['subscribe_list']}")
                else:
                    print(f"設定失敗: {result.get('error', '未知錯誤')}")
        else:
            print("選擇無效")
    except ValueError:
        print("請輸入有效的數字")
    except Exception as e:
        print(f"設定訂閱時發生錯誤: {e}")

def set_publication(device_manager):
    """設定設備推播"""
    devices = device_manager.get_all_devices()
    if not devices:
        print("沒有已綁定的設備")
        return
        
    print("\n可用設備:")
    for idx, device in enumerate(devices):
        name = device.get('devType') or '未命名'      # 從 devType 讀取名稱
        uid = device.get('uid', '未知')
        device_type = device.get('devName') or '未指定'  # 從 devName 讀取類型
        print(f"{idx+1}. {name} (類型: {device_type}, UID: {uid})")
    
    choice = input("\n請選擇要設定推播的設備編號，或按 Enter 取消: ").strip()
    if not choice:
        return
        
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(devices):
            pub_addr = input("請輸入推播通道地址 (例如: 0xC001): ").strip()
            if pub_addr:
                result = device_manager.set_publication(idx, pub_addr)
                if result["result"] == "success":
                    print(f"推播設定成功，當前推播通道: {result['publish']}")
                else:
                    print(f"設定失敗: {result.get('error', '未知錯誤')}")
        else:
            print("選擇無效")
    except ValueError:
        print("請輸入有效的數字")
    except Exception as e:
        print(f"設定推播時發生錯誤: {e}")

def control_device(device_manager):
    """控制設備"""
    devices = device_manager.get_all_devices()
    if not devices:
        print("沒有已綁定的設備")
        return
        
    print("\n可用設備:")
    for idx, device in enumerate(devices):
        name = device.get('devType') or '未命名'      # 從 devType 讀取名稱
        uid = device.get('uid', '未知')
        device_type = device.get('devName') or '未指定'  # 從 devName 讀取類型
        state = "開啟" if device.get('state') == 1 else "關閉" if device.get('state') == 0 else "未知"
        print(f"{idx+1}. {name} (類型: {device_type}, UID: {uid}, 狀態: {state})")
    
    choice = input("\n請選擇要控制的設備編號，或按 Enter 取消: ").strip()
    if not choice:
        return
        
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(devices):
            device = devices[idx]
            device_type = device.get('devName') or '未指定'  # 從 devName 讀取類型
            unicast_addr = device.get('uid', '')
            
            # 根據設備類型提供不同的控制選項
            if device_type == "RGB_LED":
                print("\n可用操作:")
                print("1. 設定為白光")
                print("2. 設定為紅色")
                print("3. 設定為綠色")
                print("4. 設定為藍色")
                print("5. 設定為紫色")
                print("6. 關閉燈光")
                print("7. 自定義顏色")
                print("0. 取消")
                
                action = input("請選擇操作: ").strip()
                
                if action == "0":
                    return
                elif action == "1":
                    # 使用控制器直接操作設備
                    try:
                        print(f"發送白光指令到設備 {unicast_addr}...")
                        result = device_manager.control_device(idx, "set_white", cold=255, warm=255)
                        print(f"設備響應: {result.get('message', '無響應')}")
                    except Exception as e:
                        print(f"發送指令時出錯: {e}")
                elif action == "2":
                    print(f"發送紅光指令到設備 {unicast_addr}...")
                    result = device_manager.control_device(idx, "set_rgb", red=255)
                    print(f"設備響應: {result.get('message', '無響應')}")
                elif action == "3":
                    print(f"發送綠光指令到設備 {unicast_addr}...")
                    result = device_manager.control_device(idx, "set_rgb", green=255)
                    print(f"設備響應: {result.get('message', '無響應')}")
                elif action == "4":
                    print(f"發送藍光指令到設備 {unicast_addr}...")
                    result = device_manager.control_device(idx, "set_rgb", blue=255)
                    print(f"設備響應: {result.get('message', '無響應')}")
                elif action == "5":
                    print(f"發送紫光指令到設備 {unicast_addr}...")
                    result = device_manager.control_device(idx, "set_rgb", red=255, blue=255)
                    print(f"設備響應: {result.get('message', '無響應')}")
                elif action == "6":
                    print(f"發送關閉指令到設備 {unicast_addr}...")
                    result = device_manager.control_device(idx, "turn_off")
                    print(f"設備響應: {result.get('message', '無響應')}")
                elif action == "7":
                    try:
                        cold = int(input("請輸入冷光值 (0-255): ").strip())
                        warm = int(input("請輸入暖光值 (0-255): ").strip())
                        red = int(input("請輸入紅色值 (0-255): ").strip())
                        green = int(input("請輸入綠色值 (0-255): ").strip())
                        blue = int(input("請輸入藍色值 (0-255): ").strip())
                        
                        print(f"發送自定義顏色指令到設備 {unicast_addr}...")
                        result = device_manager.control_device(idx, "set_rgb", 
                                                               cold=cold, warm=warm, 
                                                               red=red, green=green, blue=blue)
                        print(f"設備響應: {result.get('message', '無響應')}")
                    except ValueError:
                        print("請輸入有效的數字")
                        return
                else:
                    print("無效操作")
                    return
                
                if result["result"] == "success":
                    print("設備控制成功")
                    # 更新設備狀態顯示
                    new_state = "開啟" if action != "6" else "關閉"
                    print(f"設備當前狀態: {new_state}")
                else:
                    print(f"控制失敗: {result.get('error', '未知錯誤')}")
                    
            elif device_type == "PLUG":
                print("\n可用操作:")
                print("1. 開啟")
                print("2. 關閉")
                print("3. 切換狀態")
                print("0. 取消")
                
                action = input("請選擇操作: ").strip()
                
                if action == "0":
                    return
                elif action == "1":
                    print(f"發送開啟指令到插座設備 {unicast_addr}...")
                    result = device_manager.control_device(idx, "turn_on")
                    print(f"設備響應: {result.get('message', '無響應')}")
                elif action == "2":
                    print(f"發送關閉指令到插座設備 {unicast_addr}...")
                    result = device_manager.control_device(idx, "turn_off")
                    print(f"設備響應: {result.get('message', '無響應')}")
                elif action == "3":
                    current_state = device.get('state', 0)
                    state_desc = "關閉" if current_state == 1 else "開啟"
                    print(f"發送切換狀態指令到插座設備 {unicast_addr}（當前:{current_state}，將切換為{state_desc}）...")
                    result = device_manager.control_device(idx, "toggle")
                    print(f"設備響應: {result.get('message', '無響應')}")
                else:
                    print("無效操作")
                    return
                
                if result["result"] == "success":
                    print("設備控制成功")
                    # 更新設備狀態顯示
                    new_state = ""
                    if action == "1":
                        new_state = "開啟"
                    elif action == "2":
                        new_state = "關閉"
                    elif action == "3":
                        new_state = "關閉" if device.get('state', 0) == 1 else "開啟"
                    
                    if new_state:
                        print(f"設備當前狀態: {new_state}")
                else:
                    print(f"控制失敗: {result.get('error', '未知錯誤')}")
                    
            elif device_type == "SMART_BOX":
                print("\n智能盒子設備操作:")
                print("1. 讀取數據")
                print("2. 寫入數據")
                print("0. 取消")
                
                action = input("請選擇操作: ").strip()
                
                if action == "0":
                    return
                elif action == "1":
                    try:
                        slave_addr = int(input("請輸入從站地址 (通常為 1-247): ").strip())
                        function_code = int(input("請輸入功能碼 (3=保持寄存器, 4=輸入寄存器): ").strip())
                        start_addr = int(input("請輸入起始地址 (例如: 0): ").strip())
                        quantity = int(input("請輸入讀取數量 (例如: 10): ").strip())
                        
                        print(f"讀取從站 {slave_addr} 的數據中...")
                        # 使用裝置控制器直接讀取
                        result = device_manager.controller.read_smart_box_rtu(
                            unicast_addr, slave_addr, function_code, start_addr, quantity
                        )
                        
                        print("讀取結果:")
                        print(f"初始響應: {result.get('initial_response', '無響應')}")
                        print(f"數據響應: {result.get('mdtg_response', '無數據')}")
                    except ValueError:
                        print("請輸入有效的數字")
                        return
                elif action == "2":
                    try:
                        slave_addr = int(input("請輸入從站地址 (通常為 1-247): ").strip())
                        reg_addr = int(input("請輸入寄存器地址: ").strip())
                        reg_value = int(input("請輸入寄存器值: ").strip())
                        
                        print(f"寫入從站 {slave_addr} 的數據中...")
                        # 使用裝置控制器直接寫入
                        result = device_manager.controller.write_smart_box_register(
                            unicast_addr, slave_addr, reg_addr, reg_value
                        )
                        
                        print("寫入結果:")
                        print(f"初始響應: {result.get('initial_response', '無響應')}")
                        print(f"數據響應: {result.get('mdtg_response', '無數據')}")
                    except ValueError:
                        print("請輸入有效的數字")
                        return
                else:
                    print("無效操作")
                    return
                    
            elif device_type == "AIR_BOX":
                print("\n空氣盒子設備操作:")
                print("1. 讀取環境數據")
                print("0. 取消")
                
                action = input("請選擇操作: ").strip()
                
                if action == "0":
                    return
                elif action == "1":
                    try:
                        slave_addr = int(input("請輸入從站地址 (通常為 1): ").strip())
                        
                        print(f"讀取空氣盒子環境數據中...")
                        # 使用裝置控制器直接讀取
                        result = device_manager.controller.read_air_box_data(unicast_addr, slave_addr)
                        
                        print("\n環境數據結果:")
                        if result['temperature'] is not None:
                            print(f"溫度: {result['temperature']}°C")
                        if result['humidity'] is not None:
                            print(f"濕度: {result['humidity']}%")
                        if result['pm25'] is not None:
                            print(f"PM2.5: {result['pm25']} μg/m³")
                        if result['co2'] is not None:
                            print(f"CO2: {result['co2']} ppm")
                        
                        print("\n原始數據:")
                        print(f"MDTG響應: {result.get('raw_data', {}).get('mdtg_response', '無數據')}")
                    except ValueError:
                        print("請輸入有效的數字")
                        return
                else:
                    print("無效操作")
                    return
                    
            elif device_type == "POWER_METER":
                print("\n電錶設備操作:")
                print("1. 讀取電力數據")
                print("0. 取消")
                
                action = input("請選擇操作: ").strip()
                
                if action == "0":
                    return
                elif action == "1":
                    try:
                        slave_addr = int(input("請輸入從站地址 (通常為 1): ").strip())
                        
                        print(f"讀取電錶數據中...")
                        # 使用裝置控制器直接讀取
                        result = device_manager.controller.read_power_meter_data(unicast_addr, slave_addr)
                        
                        print("\n電力數據結果:")
                        if result['voltage'] is not None:
                            print(f"電壓: {result['voltage']} V")
                        if result['current'] is not None:
                            print(f"電流: {result['current']} A")
                        if result['power'] is not None:
                            print(f"功率: {result['power']} W")
                        
                        print("\n原始數據:")
                        print(f"MDTG響應: {result.get('raw_data', {}).get('mdtg_response', '無數據')}")
                    except ValueError:
                        print("請輸入有效的數字")
                        return
                else:
                    print("無效操作")
                    return
            else:
                print(f"目前不支援 {device_type} 類型設備的控制")
        else:
            print("選擇無效")
    except ValueError:
        print("請輸入有效的數字")
    except Exception as e:
        print(f"控制設備時發生錯誤: {e}")
        import traceback
        traceback.print_exc()

def unbind_device(device_manager):
    """解除綁定設備"""
    devices = device_manager.get_all_devices()
    if not devices:
        print("沒有已綁定的設備")
        return
        
    print("\n可用設備:")
    for idx, device in enumerate(devices):
        name = device.get('devType') or '未命名'      # 從 devType 讀取名稱
        uid = device.get('uid', '未知')
        mac = device.get('devMac', '未知')
        print(f"{idx+1}. {name} (UID: {uid}, MAC: {mac})")
    
    choice = input("\n請選擇要解除綁定的設備編號，或按 Enter 取消: ").strip()
    if not choice:
        return
        
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(devices):
            device = devices[idx]
            name = device.get('devType') or '未命名'
            uid = device.get('uid', '未知')
            
            confirm = input(f"確定要解除綁定設備 {name} ({uid})? (y/n): ").lower().strip()
            if confirm != 'y':
                print("操作已取消")
                return
                
            force = False
            result = device_manager.unbind_device(idx, force_remove=force)
            
            if result["result"] == "success":
                print(f"設備 {name} ({uid}) 已成功解除綁定")
            elif result["result"] == "failed" and input("解除綁定可能失敗，是否強制從數據文件中刪除該設備? (y/n): ").lower().strip() == 'y':
                # 強制移除
                force_result = device_manager.unbind_device(idx, force_remove=True)
                if force_result["result"] in ["success", "forced_removal"]:
                    print(f"設備已從設備數據檔案中強制移除")
                else:
                    print(f"強制移除失敗: {force_result.get('error', '未知錯誤')}")
            else:
                print(f"解除綁定失敗: {result.get('error', '未知錯誤')}")
        else:
            print("選擇無效")
    except ValueError:
        print("請輸入有效的數字")
    except Exception as e:
        print(f"解除綁定時發生錯誤: {e}")

def display_all_devices(device_manager):
    """顯示所有已綁定設備，帶有表頭"""
    devices = device_manager.get_all_devices()
    if not devices:
        print("沒有已綁定的設備")
        return
    
    # 定義表頭和分隔線
    header = f"{'編號':<6}{'名稱':<15}{'類型':<15}{'UID':<10}{'MAC 地址':<18}{'位置':<15}{'狀態':<6}"
    separator = "-" * 85
    
    print("\n所有綁定設備:")
    print(separator)
    print(header)
    print(separator)
    
    for idx, device in enumerate(devices):
        name = device.get('devType') or '未命名'      # 從 devType 讀取名稱
        uid = device.get('uid', '未知')
        device_type = device.get('devName') or '未指定'  # 從 devName 讀取類型
        mac = device.get('devMac', '未知')
        position = device.get('position', '未指定')
        state = "開啟" if device.get('state') == 1 else "關閉" if device.get('state') == 0 else "未知"
        
        print(f"{idx+1:<6}{name:<15}{device_type:<15}{uid:<10}{mac:<18}{position:<15}{state:<6}")
    
    print(separator)
    

if __name__ == "__main__":
    main()