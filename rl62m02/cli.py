#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RL62M02 命令行工具
提供命令行介面操作 RL Mesh 設備的功能
"""

import argparse
import logging
import time
import sys
import os

# 檢查是直接執行還是作為模組導入
if __name__ == "__main__":
    # 將父目錄添加到路徑中，以便能夠導入 rl62m02 模組
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

def setup_logger():
    """設置日誌紀錄器"""
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s][%(module)s:%(lineno)d] %(message)s'
    )

def scan_devices(args):
    """掃描設備命令處理"""
    try:
        ser = SerialAT(args.port, args.baudrate)
        prov = Provisioner(ser)
        
        print(f"掃描 {args.time} 秒...")
        devices = prov.scan_nodes(scan_time=args.time)
        print(f"找到 {len(devices)} 個設備:")
        for i, device in enumerate(devices):
            print(f"{i+1}. MAC: {device['mac address']}, UUID: {device['uuid']}")
    finally:
        if 'ser' in locals():
            ser.close()

def provision_device(args):
    """綁定設備命令處理"""
    try:
        ser = SerialAT(args.port, args.baudrate)
        prov = Provisioner(ser)
        device_manager = DeviceManager(args.device_file)
        
        if args.scan:
            print(f"掃描設備中...")
            devices = prov.scan_nodes(scan_time=3.0)
            if not devices:
                print("未找到任何設備")
                return
            
            print(f"找到 {len(devices)} 個設備:")
            for i, device in enumerate(devices):
                print(f"{i+1}. MAC: {device['mac address']}, UUID: {device['uuid']}")
            
            try:
                idx = int(input("請輸入要綁定的設備編號: ").strip()) - 1
                if not (0 <= idx < len(devices)):
                    print("無效的設備編號")
                    return
                uuid = devices[idx]['uuid']
                mac_address = devices[idx]['mac address']
            except (ValueError, IndexError):
                print("輸入錯誤")
                return
        else:
            # 直接使用提供的 UUID
            uuid = args.uuid
            mac_address = "未知"  # 沒有掃描就無法獲得 MAC
        
        # 設置設備名稱
        name = args.name if args.name else f"Device_{uuid[-4:]}"
        device_type = args.type if args.type else "未指定"
        
        print(f"開始綁定 UUID: {uuid}...")
        result = prov.auto_provision_node(uuid)
        print(f"綁定結果: {result}")
        
        if result.get('result') == 'success':
            unicast_addr = result.get('unicast_addr')
            device_manager.add_device(uuid, mac_address, unicast_addr, name, device_type)
            print(f"設備 {name} 已添加到設備管理器")
            
            if args.group:
                device_manager.add_device_to_group(unicast_addr, args.group)
                print(f"已將設備添加到群組 {args.group}")
    finally:
        if 'ser' in locals():
            ser.close()

def unprovision_device(args):
    """解綁設備命令處理"""
    try:
        ser = SerialAT(args.port, args.baudrate)
        prov = Provisioner(ser)
        device_manager = DeviceManager(args.device_file)
        
        if args.list:
            devices = device_manager.get_device_info()['devices']
            print(f"已綁定設備列表:")
            for i, device in enumerate(devices):
                print(f"{i+1}. {device.get('name', '未命名')} (地址: {device.get('unicast_addr', '未知')})")
            
            try:
                idx = int(input("請輸入要解綁的設備編號: ").strip()) - 1
                if not (0 <= idx < len(devices)):
                    print("無效的設備編號")
                    return
                unicast_addr = devices[idx]['unicast_addr']
            except (ValueError, IndexError):
                print("輸入錯誤")
                return
        else:
            # 直接使用提供的地址
            unicast_addr = args.addr
        
        print(f"正在解綁設備 {unicast_addr}...")
        resp = prov._send_and_wait(f'AT+NR {unicast_addr}', timeout=3.0)
        print(f"解綁結果: {resp}")
        
        if resp and resp.startswith('NR-MSG SUCCESS'):
            device_manager.remove_device(unicast_addr)
            print(f"設備 {unicast_addr} 已從設備管理器中移除")
    finally:
        if 'ser' in locals():
            ser.close()

def list_devices(args):
    """列出已綁定設備命令處理"""
    device_manager = DeviceManager(args.device_file)
    info = device_manager.get_device_info()
    
    print(f"設備總數: {info['device_count']}")
    if not info['devices']:
        print("沒有已綁定的設備")
        return
    
    for i, device in enumerate(info['devices']):
        print(f"{i+1}. {device.get('name', '未命名')}")
        print(f"   UUID: {device.get('uuid', '未知')}")
        print(f"   MAC地址: {device.get('mac_address', '未知')}")
        print(f"   Unicast地址: {device.get('unicast_addr', '未知')}")
        print(f"   類型: {device.get('type', '未指定')}")
        print(f"   所屬群組: {device.get('group', '無')}")
        print(f"   添加時間: {device.get('added_time', '未記錄')}")
        print("")
    
    if args.groups:
        print(f"\n群組總數: {info['group_count']}")
        for group_name, device_addrs in info['groups'].items():
            print(f"- 群組: {group_name}")
            if device_addrs:
                for addr in device_addrs:
                    device = device_manager.get_device_by_unicast(addr)
                    if device:
                        print(f"  - {device['name']} ({addr})")
                    else:
                        print(f"  - 未知設備 ({addr})")
            else:
                print("  (群組為空)")
            print("")

def control_device(args):
    """控制設備命令處理"""
    try:
        ser = SerialAT(args.port, args.baudrate)
        prov = Provisioner(ser)
        device_manager = DeviceManager(args.device_file)
        controller = RLMeshDeviceController(prov)
        
        # 載入設備到控制器
        devices = device_manager.get_device_info()['devices']
        for device in devices:
            device_type_str = device.get('type', 'UNKNOWN').upper()
            controller_type = None
            
            # 映射設備類型字符串到控制器常量
            if device_type_str == 'RGB_LED':
                controller_type = controller.DEVICE_TYPE_RGB_LED
            elif device_type_str == 'PLUG':
                controller_type = controller.DEVICE_TYPE_PLUG
            elif device_type_str == 'SMART_BOX':
                controller_type = controller.DEVICE_TYPE_SMART_BOX
            elif device_type_str == 'AIR_BOX':
                controller_type = controller.DEVICE_TYPE_AIR_BOX
            elif device_type_str == 'POWER_METER':
                controller_type = controller.DEVICE_TYPE_POWER_METER
            
            if controller_type and device.get('unicast_addr'):
                controller.register_device(device['unicast_addr'], controller_type, device.get('name', 'Unknown'))
        
        # 控制特定類型的設備
        if args.addr:
            unicast_addr = args.addr
        else:
            devices = device_manager.get_device_info()['devices']
            print(f"已綁定設備列表:")
            for i, device in enumerate(devices):
                print(f"{i+1}. {device.get('name', '未命名')} (地址: {device.get('unicast_addr', '未知')}, 類型: {device.get('type', '未指定')})")
            
            try:
                idx = int(input("請輸入要控制的設備編號: ").strip()) - 1
                if not (0 <= idx < len(devices)):
                    print("無效的設備編號")
                    return
                unicast_addr = devices[idx]['unicast_addr']
                device = devices[idx]
            except (ValueError, IndexError):
                print("輸入錯誤")
                return
        
        device = device_manager.get_device_by_unicast(unicast_addr)
        device_type_str = device.get('type', 'UNKNOWN').upper()
        
        # 根據設備類型執行相應的控制操作
        if device_type_str == 'RGB_LED':
            if args.command == 'on':
                # 打開燈 (白光)
                print(f"打開 RGB LED (白光)...")
                resp = controller.control_rgb_led(unicast_addr, 255, 255, 0, 0, 0)
            elif args.command == 'off':
                # 關閉燈
                print(f"關閉 RGB LED...")
                resp = controller.control_rgb_led(unicast_addr, 0, 0, 0, 0, 0)
            elif args.command == 'set':
                # 設置自訂顏色
                if not args.value:
                    print("請使用 --value 參數指定顏色，格式為: cold,warm,red,green,blue")
                    return
                
                try:
                    values = [int(x) for x in args.value.split(',')]
                    if len(values) != 5:
                        raise ValueError("需要 5 個值")
                    
                    cold, warm, red, green, blue = values
                    print(f"設置 RGB LED 顏色: cold={cold}, warm={warm}, red={red}, green={green}, blue={blue}")
                    resp = controller.control_rgb_led(unicast_addr, cold, warm, red, green, blue)
                except (ValueError, TypeError) as e:
                    print(f"無效的顏色格式: {e}")
                    print("格式應為 cold,warm,red,green,blue (數字用逗號分隔)")
                    return
            else:
                print("RGB LED 支援的命令: on, off, set")
                return
            
            print(f"控制結果: {resp}")
            
        elif device_type_str == 'PLUG':
            if args.command == 'on':
                # 打開插座
                print(f"打開插座...")
                resp = controller.control_plug(unicast_addr, True)
            elif args.command == 'off':
                # 關閉插座
                print(f"關閉插座...")
                resp = controller.control_plug(unicast_addr, False)
            else:
                print("插座支援的命令: on, off")
                return
            
            print(f"控制結果: {resp}")
            
        elif device_type_str in ['SMART_BOX', 'AIR_BOX', 'POWER_METER']:
            if not args.slave:
                slave_address = int(input("請輸入 Modbus 從站地址: ").strip())
            else:
                slave_address = args.slave
            
            if device_type_str == 'AIR_BOX':
                print(f"讀取空氣盒子數據...")
                result = controller.read_air_box_data(unicast_addr, slave_address)
                print(f"溫度: {result.get('temperature')} °C")
                print(f"濕度: {result.get('humidity')} %")
                print(f"PM2.5: {result.get('pm25')} μg/m³")
                print(f"CO2: {result.get('co2')} ppm")
                return
            
            if device_type_str == 'POWER_METER':
                print(f"讀取電錶數據...")
                result = controller.read_power_meter_data(unicast_addr, slave_address)
                print(f"電壓: {result.get('voltage')} V")
                print(f"電流: {result.get('current')} A")
                print(f"功率: {result.get('power')} W")
                return
            
            # Smart-Box 更通用的控制
            if args.command == 'read':
                # 讀取數據
                if not (args.value and args.reg_count):
                    print("請使用 --value 指定起始地址，--reg_count 指定讀取數量")
                    return
                
                start_address = int(args.value)
                count = int(args.reg_count)
                
                func_code_map = {
                    'holding': 0x03,
                    'input': 0x04,
                    'coil': 0x01
                }
                
                reg_type = args.reg_type if args.reg_type else 'holding'
                if reg_type not in func_code_map:
                    print(f"不支援的寄存器類型: {reg_type}")
                    print("支援的類型: holding, input, coil")
                    return
                
                func_code = func_code_map[reg_type]
                print(f"讀取 {reg_type} 寄存器，從 {start_address} 開始，數量 {count}...")
                resp = controller.read_smart_box_rtu(unicast_addr, slave_address, func_code, start_address, count)
                print(f"讀取結果: {resp}")
                
            elif args.command == 'write_reg':
                # 寫入寄存器
                if not (args.value and args.reg_value):
                    print("請使用 --value 指定寄存器地址，--reg_value 指定要寫入的值")
                    return
                
                reg_address = int(args.value)
                reg_value = int(args.reg_value)
                print(f"寫入寄存器 {reg_address} = {reg_value}...")
                resp = controller.write_smart_box_register(unicast_addr, slave_address, reg_address, reg_value)
                print(f"寫入結果: {resp}")
                
            elif args.command == 'write_coil':
                # 寫入線圈
                if not (args.value and args.reg_value is not None):
                    print("請使用 --value 指定線圈地址，--reg_value 指定要寫入的值 (0 或 1)")
                    return
                
                coil_address = int(args.value)
                coil_value = bool(int(args.reg_value))
                print(f"寫入線圈 {coil_address} = {coil_value}")
                resp = controller.write_smart_box_coil(unicast_addr, slave_address, coil_address, coil_value)
                print(f"寫入結果: {resp}")
                
            else:
                print("Smart-Box 支援的命令: read, write_reg, write_coil")
                return
        else:
            print(f"不支援的設備類型: {device_type_str}")
    finally:
        if 'ser' in locals():
            ser.close()

def parse_args():
    """解析命令行參數"""
    parser = argparse.ArgumentParser(description='RL62M02 Mesh 設備管理工具')
    parser.add_argument('--debug', action='store_true', help='啟用調試模式')
    parser.add_argument('--device-file', default='mesh_devices.json', help='設備管理文件路徑')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 掃描設備
    scan_parser = subparsers.add_parser('scan', help='掃描周圍的 RL Mesh 設備')
    scan_parser.add_argument('port', help='串口名稱，如 COM3')
    scan_parser.add_argument('--baudrate', type=int, default=115200, help='串口鮑率')
    scan_parser.add_argument('--time', type=float, default=5.0, help='掃描時間，單位為秒')
    scan_parser.set_defaults(func=scan_devices)
    
    # 綁定設備
    bind_parser = subparsers.add_parser('bind', help='綁定新 RL Mesh 設備')
    bind_parser.add_argument('port', help='串口名稱，如 COM3')
    bind_parser.add_argument('--baudrate', type=int, default=115200, help='串口鮑率')
    bind_group = bind_parser.add_mutually_exclusive_group(required=True)
    bind_group.add_argument('--scan', action='store_true', help='掃描並選擇設備綁定')
    bind_group.add_argument('--uuid', help='直接指定設備 UUID')
    bind_parser.add_argument('--name', help='設備名稱')
    bind_parser.add_argument('--type', help='設備類型')
    bind_parser.add_argument('--group', help='將設備添加到群組')
    bind_parser.set_defaults(func=provision_device)
    
    # 解綁設備
    unbind_parser = subparsers.add_parser('unbind', help='解綁 RL Mesh 設備')
    unbind_parser.add_argument('port', help='串口名稱，如 COM3')
    unbind_parser.add_argument('--baudrate', type=int, default=115200, help='串口鮑率')
    unbind_group = unbind_parser.add_mutually_exclusive_group(required=True)
    unbind_group.add_argument('--list', action='store_true', help='列出並選擇設備解綁')
    unbind_group.add_argument('--addr', help='直接指定設備地址')
    unbind_parser.set_defaults(func=unprovision_device)
    
    # 列出設備
    list_parser = subparsers.add_parser('list', help='列出已綁定的 RL Mesh 設備')
    list_parser.add_argument('--groups', action='store_true', help='同時顯示群組信息')
    list_parser.set_defaults(func=list_devices)
    
    # 控制設備
    control_parser = subparsers.add_parser('control', help='控制 RL Mesh 設備')
    control_parser.add_argument('port', help='串口名稱，如 COM3')
    control_parser.add_argument('--baudrate', type=int, default=115200, help='串口鮑率')
    control_parser.add_argument('--addr', help='設備地址')
    control_parser.add_argument('command', nargs='?', help='控制命令')
    control_parser.add_argument('--value', help='命令參數值')
    control_parser.add_argument('--slave', type=int, help='Modbus 從站地址')
    control_parser.add_argument('--reg_type', help='寄存器類型 (holding/input/coil)')
    control_parser.add_argument('--reg_count', type=int, help='讀取寄存器數量')
    control_parser.add_argument('--reg_value', type=int, help='寄存器/線圈值')
    control_parser.set_defaults(func=control_device)
    
    return parser.parse_args()

def main():
    """主函數入口"""
    args = parse_args()
    
    # 設置日誌級別
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    # 執行對應的命令處理函數
    if hasattr(args, 'func'):
        args.func(args)
    else:
        print("請指定操作命令，使用 --help 查看幫助")

if __name__ == "__main__":
    main()