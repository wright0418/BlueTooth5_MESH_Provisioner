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
import json

# 統一導入方式，不再區分直接執行和作為模組導入
try:
    # 優先從包內導入
    from .serial_at import SerialAT
    from .provisioner import Provisioner
    from .device_manager import MeshDeviceManager
    from .controllers.mesh_controller import RLMeshDeviceController
except ImportError:
    # 作為腳本直接執行時的導入方式
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)
    
    from rl62m02.serial_at import SerialAT
    from rl62m02.provisioner import Provisioner
    from rl62m02.device_manager import MeshDeviceManager
    from rl62m02.controllers.mesh_controller import RLMeshDeviceController

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
        controller = RLMeshDeviceController(prov)
        device_manager = MeshDeviceManager(prov, controller, args.device_file)
        
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
        device_type = args.type if args.type else "RGB_LED"
        
        print(f"開始綁定 UUID: {uuid}...")
        result = device_manager.provision_device(uuid, name, device_type)
        print(f"綁定結果: {result}")
        
        if result.get('result') == 'success':
            unicast_addr = result.get('unicast_addr')
            print(f"設備 {name} 已成功綁定，地址: {unicast_addr}")
            
            if args.group:
                # 目前 MeshDeviceManager 沒有直接添加到群組的方法
                # 如果需要設置訂閱，可以使用 set_subscription 方法
                group_result = device_manager.set_subscription(unicast_addr, args.group)
                print(f"添加到群組 {args.group} 結果: {group_result}")
    finally:
        if 'ser' in locals():
            ser.close()

def unprovision_device(args):
    """解綁設備命令處理"""
    try:
        ser = SerialAT(args.port, args.baudrate)
        prov = Provisioner(ser)
        controller = RLMeshDeviceController(prov)
        device_manager = MeshDeviceManager(prov, controller, args.device_file)
        
        if args.list:
            devices = device_manager.get_all_devices()
            print(f"已綁定設備列表:")
            for i, device in enumerate(devices):
                print(f"{i+1}. {device.get('devType', '未命名')} (地址: {device.get('uid', '未知')})")
            
            try:
                idx = int(input("請輸入要解綁的設備編號: ").strip()) - 1
                if not (0 <= idx < len(devices)):
                    print("無效的設備編號")
                    return
                unicast_addr = devices[idx]['uid']
            except (ValueError, IndexError):
                print("輸入錯誤")
                return
        else:
            # 直接使用提供的地址
            unicast_addr = args.addr
        
        print(f"正在解綁設備 {unicast_addr}...")
        result = device_manager.unbind_device(unicast_addr)
        print(f"解綁結果: {result}")
    finally:
        if 'ser' in locals():
            ser.close()

def list_devices(args):
    """列出已綁定設備命令處理"""
    ser = SerialAT(args.port, args.baudrate)
    prov = Provisioner(ser)
    controller = RLMeshDeviceController(prov)
    device_manager = MeshDeviceManager(prov, controller, args.device_file)
    
    # 直接使用 display_devices 方法顯示格式化的設備列表
    devices_info = device_manager.display_devices()
    print(devices_info)
    
    # 顯示群組信息（訂閱關係）
    if args.groups:
        devices = device_manager.get_all_devices()
        subscriptions = {}
        
        # 收集所有訂閱關係
        for device in devices:
            uid = device.get('uid')
            device_name = device.get('devType', '未命名')
            subs = device.get('subscribe', [])
            
            for group in subs:
                if group not in subscriptions:
                    subscriptions[group] = []
                subscriptions[group].append((uid, device_name))
        
        # 顯示群組信息
        print("\n===== 群組信息 =====")
        if subscriptions:
            for group, devices in subscriptions.items():
                print(f"群組地址 {group}:")
                for uid, name in devices:
                    print(f"  - {name} ({uid})")
        else:
            print("沒有設定的群組")

def control_device(args):
    """控制設備命令處理"""
    try:
        ser = SerialAT(args.port, args.baudrate)
        prov = Provisioner(ser)
        controller = RLMeshDeviceController(prov)
        device_manager = MeshDeviceManager(prov, controller, args.device_file)
        
        # 選擇控制的設備
        if args.addr:
            unicast_addr = args.addr
            device = device_manager.get_device_by_uid(unicast_addr)
        else:
            devices = device_manager.get_all_devices()
            print(f"已綁定設備列表:")
            for i, device in enumerate(devices):
                print(f"{i+1}. {device.get('devType', '未命名')} (地址: {device.get('uid', '未知')}, 類型: {device.get('devName', '未指定')})")
            
            try:
                idx = int(input("請輸入要控制的設備編號: ").strip()) - 1
                if not (0 <= idx < len(devices)):
                    print("無效的設備編號")
                    return
                device = devices[idx]
                unicast_addr = device.get('uid')
            except (ValueError, IndexError):
                print("輸入錯誤")
                return
        
        if not device:
            print(f"找不到設備: {unicast_addr}")
            return
        
        # 獲取設備類型（在 devName 中）
        device_type_str = device.get('devName', 'UNKNOWN').upper()
        
        # 根據設備類型執行相應的控制操作
        if device_type_str == 'RGB_LED':
            if args.command == 'on':
                # 打開燈 (白光)
                print(f"打開 RGB LED (白光)...")
                result = device_manager.control_device(unicast_addr, 'turn_on')
            elif args.command == 'off':
                # 關閉燈
                print(f"關閉 RGB LED...")
                result = device_manager.control_device(unicast_addr, 'turn_off')
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
                    result = device_manager.control_device(
                        unicast_addr, 'set_rgb', 
                        cold=cold, warm=warm, red=red, green=green, blue=blue
                    )
                except (ValueError, TypeError) as e:
                    print(f"無效的顏色格式: {e}")
                    print("格式應為 cold,warm,red,green,blue (數字用逗號分隔)")
                    return
            else:
                print("RGB LED 支援的命令: on, off, set")
                return
            
            print(f"控制結果: {result}")
            
        elif device_type_str == 'PLUG':
            if args.command == 'on':
                # 打開插座
                print(f"打開插座...")
                result = device_manager.control_device(unicast_addr, 'turn_on')
            elif args.command == 'off':
                # 關閉插座
                print(f"關閉插座...")
                result = device_manager.control_device(unicast_addr, 'turn_off')
            elif args.command == 'toggle':
                # 切換插座狀態
                print(f"切換插座狀態...")
                result = device_manager.control_device(unicast_addr, 'toggle')
            else:
                print("插座支援的命令: on, off, toggle")
                return
            
            print(f"控制結果: {result}")
            
        # 其他設備類型的支持需要根據 MeshDeviceManager 的功能來實現
        else:
            print(f"目前不支援對設備類型 {device_type_str} 的控制")
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
    list_parser.add_argument('port', help='串口名稱，如 COM3')
    list_parser.add_argument('--baudrate', type=int, default=115200, help='串口鮑率')
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