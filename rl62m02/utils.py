#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
公用程式函數
"""

def format_mac_address(mac_address: str) -> str:
    """將 MAC 地址格式化為冒號分隔的形式"""
    # 移除所有冒號，以防萬一有冒號的情況
    mac_without_colon = mac_address.replace(":", "")
    
    # 確保有足夠的字符（12個十六進位數字）
    if len(mac_without_colon) != 12:
        return mac_address  # 如果格式不正確，返回原始值
        
    # 每兩個字符插入一個冒號
    mac_parts = [mac_without_colon[i:i+2] for i in range(0, 12, 2)]
    return ":".join(mac_parts).upper()
