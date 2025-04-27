#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RL Mesh 自動/手動設備管理器
實現手動綁定、解除所有綁定、從檔案自動綁定等功能
"""

import sys
import logging
import json
import time
import rl62m02
import re # Import re for input validation
from rl62m02 import MeshDeviceManager
from rl62m02.utils import format_mac_address

# 設定日誌格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DEVICE_CONFIG_FILE = "My_device.json" # 預設設備資料存檔

def initialize_provisioner(com_port):
    """初始化 RL62M02 Provisioner"""
    print(f"初始化 RL62M02 在埠 {com_port}...")
    try:
        serial_at, provisioner, _ = rl62m02.create_provisioner(com_port)
        print("RL62M02 初始化成功")
        return serial_at, provisioner
    except ValueError as role_err:
        print(f"錯誤: Provisioner 初始化失敗 - {role_err}")
        print("請確認設備已正確配置為 PROVISIONER 角色")
        return None, None
    except Exception as init_err:
        print(f"錯誤: 設備初始化失敗 - {init_err}")
        print("請檢查設備連接狀態和 COM 埠配置")
        return None, None

def is_valid_group_address(address_str):
    """驗證輸入是否為有效的十六進位 Group Address (0xC000 - 0xFFFF)"""
    # 允許以 0x 開頭，後面跟 4 個十六進位數字
    if re.fullmatch(r'0x[0-9a-fA-F]{4}', address_str):
        try:
            addr_int = int(address_str, 16)
            # Group Addresses are typically in the range 0xC000 to 0xFFFF
            return 0xC000 <= addr_int <= 0xFFFF
        except ValueError:
            return False
    return False


def manual_bind_device(device_manager):
    """手動綁定單個設備"""
    print("\n===== 手動綁定設備 =====")
    print("正在掃描周邊設備...")
    try:
        scanned_devices = device_manager.provisioner.scan_nodes(scan_time=5.0)
        if not scanned_devices:
            print("未掃描到任何設備。請確認設備已開啟並處於可被發現狀態。")
            return

        print("\n掃描到的設備列表:")
        for i, device in enumerate(scanned_devices):
            print(f"{i+1}. UUID: {device['uuid']}, MAC: {device['mac address']}")

        while True:
            choice = input(f"請選擇要綁定的設備編號 (1-{len(scanned_devices)}): ").strip()
            try:
                choice_index = int(choice) - 1
                if 0 <= choice_index < len(scanned_devices):
                    selected_device = scanned_devices[choice_index]
                    uuid_str = selected_device['uuid']
                    mac_address = selected_device['mac address']
                    print(f"已選擇設備: UUID: {uuid_str}, MAC: {mac_address}")
                    break
                else:
                    print("無效的編號，請重新輸入。")
            except ValueError:
                print("無效的輸入，請輸入數字編號。")

    except Exception as e:
        print(f"掃描設備時發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return

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

    # 執行綁定
    print(f"\n開始綁定 UUID: {uuid_str}...")
    try:
        result = device_manager.provision_device(
            uuid=uuid_str,
            device_name=device_name,
            device_type=device_type,
            position=position,
            mac_address=mac_address # 將掃描到的 MAC 地址傳遞給 provision_device
        )

        if result["result"] == "success":
            print(f"設備綁定成功! UID: {result['unicast_addr']}")
            # 綁定成功後，provision_device 內部會自動儲存到 JSON

            # --- 設定訂閱和推撥通道 ---
            unicast_addr = result['unicast_addr']

            # 詢問訂閱通道
            while True:
                sub_addr_str = input(f"請輸入設備 UID {unicast_addr} 的訂閱通道 (例如 0xC000, 留空跳過): ").strip()
                if not sub_addr_str:
                    print("跳過訂閱設定。")
                    break
                if is_valid_group_address(sub_addr_str):
                    try:
                        sub_addr = int(sub_addr_str, 16)
                        print(f"正在設定設備 UID {unicast_addr} 的訂閱通道為 {sub_addr_str}...")
                        # 呼叫 Provisioner 的方法來設定訂閱
                        # 假設 rl62m02 庫有 subscribe_group 方法 (原 config_model_subscription_add)
                        # 這裡不指定 model_id，依賴庫的默認行為
                        # subscribe_group 返回的是 AT 命令的響應字串，需要檢查是否成功
                        # 假設成功響應以 'MSAA-MSG SUCCESS' 開頭
                        sub_result_str = device_manager.provisioner.subscribe_group(unicast_addr, sub_addr)
                        if sub_result_str and sub_result_str.startswith("MSAA-MSG SUCCESS"):
                            print(f"設備 UID {unicast_addr} 訂閱通道設定成功。")
                        else:
                            print(f"設備 UID {unicast_addr} 訂閱通道設定失敗: {sub_result_str if sub_result_str else '無回應或超時'}")
                        break # 成功或失敗後都跳出迴圈
                    except Exception as config_e:
                        print(f"設定訂閱通道時發生錯誤: {config_e}")
                        logger.error(f"設定訂閱通道時發生錯誤: {config_e}", exc_info=True)
                        break # 發生例外時跳出迴圈
                else:
                    print("無效的 Group Address 格式，請輸入有效的十六進位地址 (例如 0xC000)。")

            # 詢問推撥通道
            while True:
                pub_addr_str = input(f"請輸入設備 UID {unicast_addr} 的推撥通道 (例如 0xC001, 留空跳過): ").strip()
                if not pub_addr_str:
                    print("跳過推撥設定。")
                    break
                if is_valid_group_address(pub_addr_str):
                    try:
                        pub_addr = int(pub_addr_str, 16)
                        print(f"正在設定設備 UID {unicast_addr} 的推撥通道為 {pub_addr_str}...")
                        # 呼叫 Provisioner 的方法來設定推撥
                        # 呼叫 Provisioner 的方法來設定推撥 (使用 publish_to_target)
                        # 這裡不指定 model_id 或 element_index，依賴庫的默認行為
                        pub_result = device_manager.provisioner.publish_to_target(unicast_addr, pub_addr)
                        # publish_to_target 返回的是 AT 命令的響應字串，需要檢查是否成功
                        # 假設成功響應以 'MPAS-MSG SUCCESS' 開頭
                        if pub_result and pub_result.startswith("MPAS-MSG SUCCESS"):
                            print(f"設備 UID {unicast_addr} 推撥通道設定成功。")
                        else:
                            print(f"設備 UID {unicast_addr} 推撥通道設定失敗: {pub_result.get('error', '未知錯誤') if pub_result else '未知錯誤'}")
                        break # 成功或失敗後都跳出迴圈
                    except Exception as config_e:
                        print(f"設定推撥通道時發生錯誤: {config_e}")
                        logger.error(f"設定推撥通道時發生錯誤: {config_e}", exc_info=True)
                        break # 發生例外時跳出迴圈
                else:
                    print("無效的 Group Address 格式，請輸入有效的十六進位地址 (例如 0xC001)。")

        else:
            print(f"綁定失敗: {result.get('error', '未知錯誤')}")
    except Exception as e:
        print(f"綁定過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()

def unbind_all_devices(device_manager):
    """解除所有設備綁定"""
    print("\n===== 解除所有設備綁定 =====")
    devices = device_manager.get_all_devices()
    if not devices:
        print("沒有已綁定的設備需要解除。")
        return

    confirm = input(f"確定要解除綁定所有 {len(devices)} 個設備? (y/n): ").lower().strip()
    if confirm != 'y':
        print("操作已取消")
        return

    # 詢問使用者是否在每次解除綁定後儲存 JSON
    while True:
        save_choice = input("您希望在解除綁定每個裝置後立即儲存設備資料檔案嗎？ (y/n): ").lower().strip()
        if save_choice in ['y', 'n']:
            save_after_unbind = save_choice == 'y'
            break
        else:
            print("無效選擇，請輸入 'y' 或 'n'。")

    # 創建一個副本，因為解除綁定會修改原始列表
    devices_to_unbind = list(devices)

    for idx, device in enumerate(devices_to_unbind):
        name = device.get('devType') or '未命名'
        uid = device.get('uid', '未知')
        mac = device.get('devMac', '未知')
        print(f"正在解除綁定設備 {idx+1}/{len(devices_to_unbind)}: {name} (UID: {uid}, MAC: {mac})...")

        try:
            # 這裡需要找到當前設備在 device_manager 內部列表中的正確索引
            # 因為在解除綁定過程中列表會變動，直接使用迴圈的 idx 是不安全的
            # 更好的做法是根據 UID 或 UUID 來找到設備並解除綁定
            
            current_devices = device_manager.get_all_devices()
            target_device_in_manager = next((d for d in current_devices if d.get('uid') == uid), None)

            if target_device_in_manager:
                target_idx_in_manager = current_devices.index(target_device_in_manager)
                # 呼叫 unbind_device 時傳入 save_after_unbind 參數
                result = device_manager.unbind_device(target_idx_in_manager, force_remove=False, save_after_unbind=save_after_unbind)

                if result["result"] == "success":
                    print(f"設備 {name} ({uid}) 已成功解除綁定。")
                elif result["result"] == "forced_removal":
                     print(f"設備 {name} ({uid}) 解除綁定失敗，但已從數據檔案中強制移除。")
                else:
                    print(f"嘗試解除綁定設備 {name} ({uid}) 失敗: {result.get('error', '未知錯誤')}")
            else:
                 print(f"設備 {name} ({uid}) (UID: {uid}) 在當前管理器列表中未找到，跳過解除綁定。")

        except Exception as e:
            print(f"解除綁定設備 {name} ({uid}) 時發生錯誤: {e}")
            import traceback
            traceback.print_exc()

    # 處理清除 JSON 檔案的選項 (此選項獨立於上面的儲存選項)
    clear_json = input("是否清除設備資料檔案 (.json)? (y/n): ").lower().strip()
    if clear_json == 'y':
        print(f"正在清除設備資料檔案 {DEVICE_CONFIG_FILE}...")
        try:
            # 清空 MeshDeviceManager 內部列表並儲存空的 JSON
            device_manager.devices_data["devices"] = [] # 直接清空 devices 列表
            device_manager.save_device_data()
            print("設備資料檔案已清除。")
        except Exception as e:
            print(f"清除設備資料檔案時發生錯誤: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("設備資料檔案未清除。")


def auto_bind_from_json(device_manager):
    """從 JSON 檔案自動綁定設備"""
    print("\n===== 從 JSON 檔案自動綁定設備 =====")

    # 步驟 1: 清除 Provisioner 上的現有綁定並清空 Manager 列表
    print("正在清除 Provisioner 上的現有綁定並清空管理器列表...")
    try:
        # 這裡假設 Provisioner 物件有方法可以清除所有綁定
        # 參考 rl62m02 庫，provisioner.py 中可能需要添加一個 reset 或 clear_bindings 方法
        # 如果沒有直接的方法，可能需要通過 AT 命令實現
        # 暫時假設 Provisioner 有一個 reset_mesh 方法可以達到目的
        # 如果實際庫中沒有，這部分需要根據實際 API 調整
        if hasattr(device_manager.provisioner, 'reset_mesh'):
             reset_result = device_manager.provisioner.reset_mesh()
             print(f"Provisioner 重置結果: {reset_result}")
        else:
             print("Provisioner 物件沒有 reset_mesh 方法，跳過 Provisioner 重置。")
             print("請注意：這可能導致 UID 分配不是從 0x0100 開始。")


    except Exception as e:
        print(f"清除 Provisioner 或管理器時發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        print("自動綁定操作終止。")
        return

    # 步驟 2: 從 JSON 檔案載入設備列表
    device_data = {}
    try:
        with open(DEVICE_CONFIG_FILE, 'r', encoding='utf-8') as f:
            device_data = json.load(f)
        devices_to_bind = device_data.get("devices", []) # 從載入的字典中獲取 devices 列表
        print(f"從 {DEVICE_CONFIG_FILE} 載入 {len(devices_to_bind)} 個設備。")
    except FileNotFoundError:
        print(f"錯誤: 找不到設備資料檔案 {DEVICE_CONFIG_FILE}。")
        print("請先使用手動綁定功能建立檔案。")
        return
    except json.JSONDecodeError:
        print(f"錯誤: 無法解析設備資料檔案 {DEVICE_CONFIG_FILE}，請檢查檔案格式。")
        return
    except Exception as e:
        print(f"載入設備資料檔案時發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return

    # 步驟 3: 掃描周邊設備
    print("正在掃描周邊設備以獲取最新的 UUID...")
    try:
        scanned_devices = device_manager.provisioner.scan_nodes(scan_time=10.0)
        if not scanned_devices:
            print("警告: 未掃描到任何設備。無法進行自動綁定。")
            return
        print(f"掃描到 {len(scanned_devices)} 個設備。")
        # 將掃描結果轉換為 MAC 到 UUID 的字典，方便查找
        scanned_mac_to_uuid = {d['mac address']: d['uuid'] for d in scanned_devices}

    except Exception as e:
        print(f"掃描設備時發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        print("自動綁定操作終止。")
        return

    # 步驟 4: 遍歷列表並自動綁定
    successful_binds = 0
    failed_binds = []

    for idx, device_info in enumerate(devices_to_bind):
        device_name = device_info.get('devType') # 從 devType 讀取名稱
        device_type = device_info.get('devName') # 從 devName 讀取類型
        position = device_info.get('position')
        mac_address = device_info.get('devMac') # 從 devMac 讀取 MAC

    # 步驟 4: 遍歷列表並自動綁定
    successful_binds = 0
    failed_binds = []

    logger.debug(f"開始遍歷 {len(devices_to_bind)} 個設備進行自動綁定...")
    for idx, device_info in enumerate(devices_to_bind):
        logger.debug(f"處理設備 {idx+1}/{len(devices_to_bind)}: {device_info}")
        device_name = device_info.get('devType') # 從 devType 讀取名稱
        device_type = device_info.get('devName') # 從 devName 讀取類型
        position = device_info.get('position')
        mac_address = device_info.get('devMac') # 從 devMac 讀取 MAC

        if not device_name or not device_type or not mac_address:
            print(f"警告: 設備列表中的第 {idx+1} 個條目缺少必要的名稱、類型或 MAC 地址資訊，跳過。")
            logger.warning(f"設備列表中的第 {idx+1} 個條目缺少必要資訊，跳過: {device_info}")
            failed_binds.append({"device_info": device_info, "error": "缺少必要資訊 (名稱, 類型, 或 MAC 地址)"})
            continue

        # 根據 MAC 地址從掃描結果中查找 UUID
        uuid_str = scanned_mac_to_uuid.get(mac_address)
        logger.debug(f"查找 MAC 地址 {mac_address} 對應的 UUID: {uuid_str}")

        if not uuid_str:
            print(f"警告: 在掃描結果中找不到 MAC 地址為 {mac_address} 的設備，跳過綁定。")
            logger.warning(f"在掃描結果中找不到 MAC 地址為 {mac_address} 的設備，跳過綁定。")
            failed_binds.append({"device_info": device_info, "error": f"掃描結果中找不到 MAC 地址 {mac_address}"})
            continue

        print(f"\n正在自動綁定設備 {idx+1}/{len(devices_to_bind)}: {device_name} (MAC: {mac_address}, UUID: {uuid_str})...")
        logger.debug(f"嘗試綁定設備: UUID={uuid_str}, MAC={mac_address}, 名稱={device_name}, 類型={device_type}, 位置={position}")

        retries = 0
        bind_success = False
        last_error = "未知錯誤"

        while retries < 3:
            logger.debug(f"綁定嘗試 {retries+1}/3")
            try:
                # 執行綁定，使用從掃描結果中找到的 UUID
                result = device_manager.provision_device(
                    uuid=uuid_str,
                    device_name=device_name,
                    device_type=device_type,
                    position=position,
                    mac_address=mac_address # 繼續使用儲存的 MAC 地址
                )

                logger.debug(f"provision_device 結果: {result}")
                if result["result"] == "success":
                    print(f"設備 {device_name} (MAC: {mac_address}) 綁定成功! UID: {result['unicast_addr']}")
                    logger.info(f"設備 {device_name} (MAC: {mac_address}) 綁定成功! UID: {result['unicast_addr']}")
                    successful_binds += 1
                    bind_success = True
                    # 綁定成功後，provision_device 內部會自動儲存到 JSON
                    break # 成功則跳出重試迴圈
                else:
                    last_error = result.get('error', '未知錯誤')
                    print(f"綁定設備 {device_name} (MAC: {mac_address}) 失敗 (第 {retries+1} 次嘗試): {last_error}")
                    logger.warning(f"綁定設備 {device_name} (MAC: {mac_address}) 失敗 (第 {retries+1} 次嘗試): {last_error}")
                    retries += 1
                    time.sleep(1) # 等待一小段時間再重試

            except Exception as e:
                last_error = str(e)
                print(f"綁定設備 {device_name} (MAC: {mac_address}) 時發生錯誤 (第 {retries+1} 次嘗試): {last_error}")
                import traceback
                traceback.print_exc()
                logger.error(f"綁定設備 {device_name} (MAC: {mac_address}) 時發生錯誤 (第 {retries+1} 次嘗試): {e}", exc_info=True)
                retries += 1
                time.sleep(1) # 等待一小段時間再重試

        if not bind_success:
            print(f"設備 {device_name} (MAC: {mac_address}) 綁定失敗，重試 {retries} 次後仍失敗。")
            logger.error(f"設備 {device_name} (MAC: {mac_address}) 綁定失敗，重試 {retries} 次後仍失敗。最後錯誤: {last_error}")
            failed_binds.append({"device_info": device_info, "error": last_error})

    # 步驟 5: 總結結果
    print("\n===== 自動綁定結果總結 =====")
    logger.debug("自動綁定結果總結:")
    print(f"總共嘗試綁定 {len(devices_to_bind)} 個設備。")
    logger.debug(f"總共嘗試綁定 {len(devices_to_bind)} 個設備。")
    print(f"成功綁定: {successful_binds} 個。")
    logger.debug(f"成功綁定: {successful_binds} 個。")
    print(f"失敗綁定: {len(failed_binds)} 個。")
    logger.debug(f"失敗綁定: {len(failed_binds)} 個。")

    if failed_binds:
        print("\n失敗設備列表:")
        logger.debug("失敗設備列表:")
        for item in failed_binds:
            device_info = item["device_info"]
            error = item["error"]
            print(f"- MAC: {device_info.get('devMac', '未知')}, 名稱: {device_info.get('devType', '未知')}, 錯誤: {error}")
            logger.debug(f"- MAC: {device_info.get('devMac', '未知')}, 名稱: {device_info.get('devType', '未知')}, 錯誤: {error}")


def main():
    if len(sys.argv) < 2:
        print("使用方式: python Auto_mesh_device_manager.py <COM埠>")
        return

    com_port = sys.argv[1]

    serial_at, provisioner = initialize_provisioner(com_port)
    if not provisioner:
        return

    try:
        # 建立裝置管理器，使用指定的設備資料存檔
        device_manager = MeshDeviceManager(
            provisioner=provisioner,
            device_json_path=DEVICE_CONFIG_FILE
        )

        print("裝置管理器初始化成功")

        # 獲取 Provisioner 的 MAC 地址並更新 My_device.json
        try:
            print("正在查詢 Provisioner 的 MAC 地址...")
            gw_mac = provisioner.get_self_mac_address()
            if gw_mac:
                print(f"成功獲取 Provisioner MAC 地址: {gw_mac}")
                try:
                    with open(DEVICE_CONFIG_FILE, 'r+', encoding='utf-8') as f:
                        device_data = json.load(f)
                        if device_data.get("gwMac") != gw_mac:
                            device_data["gwMac"] = gw_mac
                            f.seek(0) # 回到檔案開頭
                            json.dump(device_data, f, indent=4, ensure_ascii=False)
                            f.truncate() # 清除可能殘留的舊內容
                            print(f"已將 Provisioner MAC 地址更新到 {DEVICE_CONFIG_FILE}")
                        else:
                            print(f"{DEVICE_CONFIG_FILE} 中的 gwMac 已是最新 ({gw_mac})，無需更新。")
                except FileNotFoundError:
                    print(f"警告: 找不到設備資料檔案 {DEVICE_CONFIG_FILE}，無法更新 gwMac。")
                except json.JSONDecodeError:
                    print(f"警告: 無法解析設備資料檔案 {DEVICE_CONFIG_FILE}，無法更新 gwMac。")
                except Exception as json_err:
                    print(f"更新 {DEVICE_CONFIG_FILE} 時發生錯誤: {json_err}")
            else:
                print("查詢 Provisioner MAC 地址失敗，無法更新 gwMac。")
        except Exception as mac_err:
            print(f"查詢 Provisioner MAC 地址時發生錯誤: {mac_err}")


        # 主選單
        while True:
            print(f"\n===== RL Mesh 自動/手動設備管理器 ({DEVICE_CONFIG_FILE}) =====")
            print("1. 手動綁定設備")
            print("2. 解除所有設備綁定")
            print("3. 從檔案自動綁定設備")
            print("4. 顯示所有已綁定設備") # 添加顯示功能
            print("0. 離開")

            choice = input("請選擇操作: ").strip()

            if choice == '0':
                break
            elif choice == '1':
                manual_bind_device(device_manager)
            elif choice == '2':
                unbind_all_devices(device_manager)
            elif choice == '3':
                auto_bind_from_json(device_manager)
            elif choice == '4': # 實現顯示功能
                 display_all_devices(device_manager)
            else:
                print("無效選擇，請重試")

    except Exception as e:
        print(f"發生錯誤: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if serial_at and hasattr(serial_at, 'ser') and serial_at.ser.is_open:
            print("關閉序列埠...")
            serial_at.close()
        print("程式已結束")

# 將 demo 腳本中的 display_all_devices 函數複製過來
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
    # 檢查是否有 --debug 參數
    debug_mode = '--debug' in sys.argv
    if debug_mode:
        # 如果有 --debug 參數，將根日誌記錄器的級別設置為 DEBUG
        logging.getLogger().setLevel(logging.DEBUG)
        print("Debug 模式已啟用。")
        # 移除 --debug 參數，以免影響其他參數處理
        sys.argv.remove('--debug')

    main()
