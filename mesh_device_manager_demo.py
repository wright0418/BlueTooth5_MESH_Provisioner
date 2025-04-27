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
from rl62m02.utils import format_mac_address # Import the function

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
            print("\\n===== RL Mesh 設備管理器示範 =====")
            print("1. 掃描並綁定設備") # Changed option text
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
                handle_scan_and_provision(device_manager) # Changed function call
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

def handle_scan_and_provision(device_manager):
    """掃描附近設備，讓使用者選擇並進行綁定"""
    scan_time = input("請輸入掃描時間(秒，默認5秒): ").strip()
    try:
        scan_time = float(scan_time) if scan_time else 5.0
        print("掃描設備中...")
        # 使用 provisioner 的 scan_nodes 方法
        devices = device_manager.provisioner.scan_nodes(scan_time=scan_time)
        
        if not devices:
            print("未發現可綁定的設備")
            return
        
        print(f"\\n發現 {len(devices)} 個設備:")
        # 格式化 MAC 地址
        for idx, device in enumerate(devices):
            if 'mac address' in device:
                # Ensure MAC address is formatted if present
                device['mac address'] = format_mac_address(device['mac address']) # Use the imported function directly
            mac_display = device.get('mac address', 'N/A') # Handle missing MAC
            print(f"{idx+1}. UUID: {device['uuid']}, MAC: {mac_display}")
        
        choice = input("\\n請選擇要綁定的設備編號，或按 Enter 取消: ").strip()
        if not choice:
            return
        
        selected_idx = -1
        try:
            selected_idx = int(choice) - 1
            if not (0 <= selected_idx < len(devices)):
                print("選擇無效")
                return
        except ValueError:
            print("請輸入有效的數字")
            return

        # --- Provisioning Logic (moved from old provision_device) ---
        try:
            target = devices[selected_idx]
            target_uuid = target['uuid']
            target_mac = target.get('mac address') # Get MAC address from scan result
            
            # 收集設備信息
            print("\\n請選擇設備類型:")
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
                custom_type = input("請輸入自定義設備類型: ").strip()
                if custom_type:
                    device_type = custom_type
                else:
                    print("未輸入自定義類型，使用預設 RGB_LED")
            
            device_name = input("請輸入設備名稱: ").strip()
            if not device_name:
                print("設備名稱為必填項，操作取消。")
                return

            position = input("請輸入設備位置 (可選): ").strip()
            
            # 執行綁定 (Calling the core manager method)
            print(f"\\n開始綁定 UUID: {target_uuid}...")
            result = device_manager.provision_device(
                uuid=target_uuid,
                device_name=device_name,
                device_type=device_type,
                position=position,
                mac_address=target_mac # Pass the MAC address
            )
            
            if result.get("result") == "success": # Safely check result
                unicast_addr = result.get('unicast_addr') # Get the UID from the result
                if not unicast_addr:
                    print("綁定成功，但未獲取到設備 UID，無法進行後續設定。")
                    return 
                
                print(f"設備綁定成功! UID: {unicast_addr}")

                # 詢問是否設定訂閱和推播
                if input("是否設定訂閱? (y/n): ").strip().lower() == 'y':
                    group_addr = input("請輸入訂閱通道地址 (例如: 0xC000): ").strip()
                    if group_addr:
                        # Use the UID (unicast_addr) directly
                        sub_result = device_manager.set_subscription(unicast_addr, group_addr)
                        if sub_result.get("result") == "success":
                             print(f"訂閱設定成功，當前訂閱列表: {sub_result.get('subscribe_list', 'N/A')}")
                        else:
                             # Display more specific error
                             print(f"訂閱設定失敗: {sub_result.get('error', '未知錯誤')}")
                    else:
                        print("未輸入訂閱地址，跳過設定。")

                if input("是否設定推播? (y/n): ").strip().lower() == 'y':
                    pub_addr = input("請輸入推播通道地址 (例如: 0xC001): ").strip()
                    if pub_addr:
                        # Use the UID (unicast_addr) directly
                        pub_result = device_manager.set_publication(unicast_addr, pub_addr)
                        if pub_result.get("result") == "success":
                            print(f"推播設定成功，當前推播通道: {pub_result.get('publish', 'N/A')}")
                        else:
                            # Display more specific error
                            print(f"推播設定失敗: {pub_result.get('error', '未知錯誤')}")
                    else:
                        print("未輸入推播地址，跳過設定。")
            else:
                # Display more specific error from the manager
                print(f"綁定失敗: {result.get('error', '未知錯誤')}")
        except Exception as e:
            print(f"綁定過程中發生錯誤: {e}")
            import traceback
            traceback.print_exc()

    except ValueError:
        print("掃描時間請輸入有效的數字")
    except Exception as e:
        print(f"掃描或綁定過程中發生錯誤: {e}")
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
                    # Display more specific error
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
                    print(f"訂閱設定成功，當前訂閱列表: {result.get('subscribe_list', 'N/A')}") # Use .get for safety
                else:
                    # Display more specific error
                    print(f"設定失敗: {result.get('error', '未知錯誤')}")
            else:
                 print("未輸入訂閱地址，跳過設定。")
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
                    print(f"推播設定成功，當前推播通道: {result.get('publish', 'N/A')}") # Use .get for safety
                else:
                    # Display more specific error
                    print(f"設定失敗: {result.get('error', '未知錯誤')}")
            else:
                print("未輸入推播地址，跳過設定。")
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
                    # 使用 Manager 的 control_device 方法
                    try:
                        print(f"發送白光指令到設備 {unicast_addr}...")
                        # 使用 UID (unicast_addr) 而不是索引 idx
                        result = device_manager.control_device(unicast_addr, "set_white", cold=255, warm=255) 
                        print(f"設備響應: {result.get('message', '無響應')}")
                    except Exception as e:
                        print(f"發送指令時出錯: {e}")
                        result = {"result": "error", "error": str(e)} # Ensure result is defined
                elif action == "2":
                    print(f"發送紅光指令到設備 {unicast_addr}...")
                    result = device_manager.control_device(unicast_addr, "set_rgb", red=255)
                    print(f"設備響應: {result.get('message', '無響應')}")
                elif action == "3":
                    print(f"發送綠光指令到設備 {unicast_addr}...")
                    result = device_manager.control_device(unicast_addr, "set_rgb", green=255)
                    print(f"設備響應: {result.get('message', '無響應')}")
                elif action == "4":
                    print(f"發送藍光指令到設備 {unicast_addr}...")
                    result = device_manager.control_device(unicast_addr, "set_rgb", blue=255)
                    print(f"設備響應: {result.get('message', '無響應')}")
                elif action == "5":
                    print(f"發送紫光指令到設備 {unicast_addr}...")
                    result = device_manager.control_device(unicast_addr, "set_rgb", red=255, blue=255)
                    print(f"設備響應: {result.get('message', '無響應')}")
                elif action == "6":
                    print(f"發送關閉指令到設備 {unicast_addr}...")
                    result = device_manager.control_device(unicast_addr, "turn_off")
                    print(f"設備響應: {result.get('message', '無響應')}")
                elif action == "7":
                    try:
                        cold = int(input("請輸入冷光值 (0-255): ").strip())
                        warm = int(input("請輸入暖光值 (0-255): ").strip())
                        red = int(input("請輸入紅色值 (0-255): ").strip())
                        green = int(input("請輸入綠色值 (0-255): ").strip())
                        blue = int(input("請輸入藍色值 (0-255): ").strip())
                        
                        print(f"發送自定義顏色指令到設備 {unicast_addr}...")
                        result = device_manager.control_device(unicast_addr, "set_rgb", 
                                                               cold=cold, warm=warm, 
                                                               red=red, green=green, blue=blue)
                        print(f"設備響應: {result.get('message', '無響應')}")
                    except ValueError:
                        print("請輸入有效的數字")
                        result = {"result": "failed", "error": "輸入無效"} # Ensure result is defined
                    except Exception as e:
                        print(f"發送指令時出錯: {e}")
                        result = {"result": "error", "error": str(e)} # Ensure result is defined
                else:
                    print("無效操作")
                    result = {"result": "failed", "error": "無效操作"} # Ensure result is defined
                
                # Check result status and display message
                if result.get("result") == "success":
                    print("設備控制成功")
                    # Manager handles state update, no need to display manually
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
                    # Use UID directly
                    result = device_manager.control_device(unicast_addr, "turn_on")
                    print(f"設備響應: {result.get('message', '無響應')}")
                elif action == "2":
                    print(f"發送關閉指令到插座設備 {unicast_addr}...")
                    result = device_manager.control_device(unicast_addr, "turn_off")
                    print(f"設備響應: {result.get('message', '無響應')}")
                elif action == "3":
                    current_state = device.get('state', 0)
                    state_desc = "關閉" if current_state == 1 else "開啟"
                    print(f"發送切換狀態指令到插座設備 {unicast_addr}（當前:{current_state}，將切換為{state_desc}）...")
                    result = device_manager.control_device(unicast_addr, "toggle")
                    print(f"設備響應: {result.get('message', '無響應')}")
                else:
                    print("無效操作")
                    result = {"result": "failed", "error": "無效操作"} # Ensure result is defined
                
                # Check result status and display message
                if result.get("result") == "success":
                    print("設備控制成功")
                    # Manager handles state update, no need to display manually
                else:
                    print(f"控制失敗: {result.get('error', '未知錯誤')}")
                    
            elif device_type == "SMART_BOX":
                print("\n智能盒子設備操作:")
                print("1. 讀取數據 (RTU)")
                print("2. 寫入寄存器")
                print("0. 取消")
                
                action = input("請選擇操作: ").strip()
                
                if action == "0":
                    return
                elif action == "1": # Read RTU
                    try:
                        slave_addr = int(input("請輸入從站地址 (通常為 1-247): ").strip())
                        function_code = int(input("請輸入功能碼 (3=保持寄存器, 4=輸入寄存器): ").strip())
                        start_addr = int(input("請輸入起始地址 (例如: 0): ").strip())
                        quantity = int(input("請輸入讀取數量 (例如: 10): ").strip())
                        
                        print(f"讀取從站 {slave_addr} 的數據中...")
                        # Use manager's control_device
                        result = device_manager.control_device(
                            unicast_addr, "read_rtu", 
                            slave_addr=slave_addr, function_code=function_code, 
                            start_addr=start_addr, quantity=quantity
                        )
                        
                        if result.get("result") == "success":
                            print("讀取指令已發送，響應數據:")
                            print(result.get('data', {})) # Display the returned data
                        else:
                            print(f"讀取失敗: {result.get('error', '未知錯誤')}")
                            
                    except ValueError:
                        print("請輸入有效的數字")
                        return
                elif action == "2": # Write Register
                    try:
                        slave_addr = int(input("請輸入從站地址 (通常為 1-247): ").strip())
                        reg_addr = int(input("請輸入寄存器地址: ").strip())
                        reg_value = int(input("請輸入寄存器值: ").strip())
                        
                        print(f"寫入從站 {slave_addr} 的數據中...")
                        # Use manager's control_device
                        result = device_manager.control_device(
                            unicast_addr, "write_register",
                            slave_addr=slave_addr, reg_addr=reg_addr, reg_value=reg_value
                        )

                        if result.get("result") == "success":
                            print("寫入指令已發送，響應數據:")
                            print(result.get('data', {})) # Display the returned data
                        else:
                            print(f"寫入失敗: {result.get('error', '未知錯誤')}")

                    except ValueError:
                        print("請輸入有效的數字")
                        return
                else:
                    print("無效操作")
                    return
                    
            elif device_type == "AIR_BOX":
                print("\n空氣盒子設備操作:")
                print("1. 讀取數據")
                print("0. 取消")
                
                action = input("請選擇操作: ").strip()
                
                if action == "0":
                    return
                elif action == "1": # Read Data
                    try:
                        slave_addr = int(input("請輸入從站地址 (通常為 1): ").strip())
                        
                        print(f"讀取空氣盒子環境數據中...")
                        # Use manager's control_device
                        result = device_manager.control_device(unicast_addr, "read_data", slave_addr=slave_addr)
                        
                        if result.get("result") == "success":
                            data = result.get('data', {})
                            print("\n環境數據結果:")
                            if data.get('temperature') is not None:
                                print(f"溫度: {data['temperature']}°C")
                            if data.get('humidity') is not None:
                                print(f"濕度: {data['humidity']}%")
                            if data.get('pm25') is not None:
                                print(f"PM2.5: {data['pm25']} μg/m³")
                            if data.get('co2') is not None:
                                print(f"CO2: {data['co2']} ppm")
                            
                            print("\n原始數據:")
                            print(f"MDTG響應: {data.get('raw_data', {}).get('mdtg_response', '無數據')}")
                        else:
                            print(f"讀取失敗: {result.get('error', '未知錯誤')}")

                    except ValueError:
                        print("請輸入有效的數字")
                        return
                else:
                    print("無效操作")
                    return
                    
            elif device_type == "POWER_METER":
                print("\n電錶設備操作:")
                print("1. 讀取數據")
                print("0. 取消")
                
                action = input("請選擇操作: ").strip()
                
                if action == "0":
                    return
                elif action == "1": # Read Data
                    try:
                        slave_addr = int(input("請輸入從站地址 (通常為 1): ").strip())
                        
                        print(f"讀取電錶數據中...")
                        # Use manager's control_device
                        result = device_manager.control_device(unicast_addr, "read_data", slave_addr=slave_addr)
                        
                        if result.get("result") == "success":
                            data = result.get('data', {})
                            print("\n電力數據結果:")
                            if data.get('voltage') is not None:
                                print(f"電壓: {data['voltage']} V")
                            if data.get('current') is not None:
                                print(f"電流: {data['current']} A")
                            if data.get('power') is not None:
                                print(f"功率: {data['power']} W")
                            
                            print("\n原始數據:")
                            print(f"MDTG響應: {data.get('raw_data', {}).get('mdtg_response', '無數據')}")
                        else:
                             print(f"讀取失敗: {result.get('error', '未知錯誤')}")

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
    """顯示所有已綁定設備 (使用 Manager 的方法)"""
    # 直接調用 MeshDeviceManager 的 display_devices 方法
    print(device_manager.display_devices())

if __name__ == "__main__":
    main()
