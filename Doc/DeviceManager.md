# DeviceManager 類使用說明

## 概述

`DeviceManager` 是一個用於管理網狀網路設備的 Python 類，它提供了一套完整的工具來管理設備、設備群組以及設備之間的連動關係。此類使用 JSON 檔案作為儲存媒介，確保資料的持久性和可存取性。

主要功能：
- 設備的新增、查詢、修改和刪除
- 設備群組的創建和管理
- 設備間連動關係的建立和解除
- 資料的自動存儲和載入

## 初始化

### 建立 DeviceManager 實例

```python
from device_manager import DeviceManager

# 使用預設 JSON 檔案 (devices.json)
device_mgr = DeviceManager()

# 或指定自定義 JSON 檔案路徑
device_mgr = DeviceManager(json_file_path="my_devices.json")
```

初始化時，如果指定的 JSON 檔案已存在，則會自動載入；如果不存在，則會建立一個新的空檔案。

## 設備管理功能

### 新增設備

```python
# 新增一個設備，提供必須的 UUID、MAC 地址和 unicast 地址
device = device_mgr.add_device(
    uuid="12345678abcdef",
    mac_address="AABBCCDDEEFF",
    unicast_addr="0x0100"
)

# 新增設備時提供名稱和類型
device = device_mgr.add_device(
    uuid="12345678abcdef",
    mac_address="AABBCCDDEEFF",
    unicast_addr="0x0100",
    name="客廳燈",
    device_type="燈具"
)
```

### 查詢設備

```python
# 根據 unicast 地址查詢設備
device = device_mgr.get_device_by_unicast("0x0100")
if device:
    print(f"找到設備: {device['name']}")

# 根據 UUID 查詢設備
device = device_mgr.get_device_by_uuid("12345678abcdef")
if device:
    print(f"找到設備: {device['name']}")
```

### 移除設備

```python
# 移除單個設備
success = device_mgr.remove_device("0x0100")
if success:
    print("設備已成功移除")

# 移除所有設備
device_mgr.remove_all_devices()
```

### 獲取設備資訊

```python
# 獲取所有設備和群組的詳細資訊
info = device_mgr.get_device_info()
print(f"總設備數: {info['device_count']}")
print(f"總群組數: {info['group_count']}")

# 查看所有設備
for device in info['devices']:
    print(f"設備: {device['name']}, 位址: {device['unicast_addr']}")
```

## 群組管理功能

### 創建群組

```python
# 創建一個新群組
success = device_mgr.create_group("客廳")
if success:
    print("已創建群組: 客廳")
```

### 將設備添加到群組

```python
# 將設備添加到群組
success = device_mgr.add_device_to_group(unicast_addr="0x0100", group_name="客廳")
if success:
    print("設備已添加到群組: 客廳")
```

### 從群組中移除設備

```python
# 從指定群組移除設備
device_mgr.remove_device_from_group(unicast_addr="0x0100", group_name="客廳")

# 從任何群組中移除設備
device_mgr.remove_device_from_group(unicast_addr="0x0100")
```

### 獲取群組內設備

```python
# 獲取特定群組中的所有設備
devices = device_mgr.get_group_devices("客廳")
print(f"客廳群組有 {len(devices)} 個設備")
for unicast_addr in devices:
    device = device_mgr.get_device_by_unicast(unicast_addr)
    if device:
        print(f"設備: {device['name']}")
```

## 設備連動功能

### 建立設備連動關係

```python
# 建立從開關到燈的連動關係
success = device_mgr.link_devices(source_unicast="0x0100", target_unicast="0x0101")
if success:
    print("已建立設備連動關係")
```

此連動關係表示當來源設備 (source) 狀態改變時，目標設備 (target) 也應相應變化。

### 解除設備連動關係

```python
# 解除兩個設備間的連動關係
success = device_mgr.unlink_devices(source_unicast="0x0100", target_unicast="0x0101")
if success:
    print("已解除設備連動關係")
```

### 獲取連動設備列表

```python
# 獲取與特定設備連動的所有設備
linked_devices = device_mgr.get_linked_devices("0x0100")
print(f"與設備 0x0100 連動的設備數: {len(linked_devices)}")
for unicast_addr in linked_devices:
    device = device_mgr.get_device_by_unicast(unicast_addr)
    if device:
        print(f"連動設備: {device['name']}")
```

## 完整使用示例

```python
from device_manager import DeviceManager

# 初始化設備管理器
device_mgr = DeviceManager("mesh_devices.json")

# 新增設備
switch = device_mgr.add_device(
    uuid="switch001",
    mac_address="AABBCCDDEE01",
    unicast_addr="0x0100",
    name="主開關",
    device_type="開關"
)

light1 = device_mgr.add_device(
    uuid="light001",
    mac_address="AABBCCDDEE02",
    unicast_addr="0x0101",
    name="客廳主燈",
    device_type="燈具"
)

light2 = device_mgr.add_device(
    uuid="light002",
    mac_address="AABBCCDDEE03",
    unicast_addr="0x0102",
    name="客廳輔燈",
    device_type="燈具"
)

# 創建群組並添加設備
device_mgr.create_group("客廳燈光")
device_mgr.add_device_to_group("0x0101", "客廳燈光")
device_mgr.add_device_to_group("0x0102", "客廳燈光")

# 建立設備連動關係
device_mgr.link_devices("0x0100", "0x0101")  # 主開關連動客廳主燈
device_mgr.link_devices("0x0100", "0x0102")  # 主開關連動客廳輔燈

# 獲取資訊
info = device_mgr.get_device_info()
print(f"已註冊 {info['device_count']} 台設備，{info['group_count']} 個群組")

# 查看主開關的連動設備
linked = device_mgr.get_linked_devices("0x0100")
print(f"主開關連動的設備數: {len(linked)}")

# 查看客廳燈光群組中的設備
group_devices = device_mgr.get_group_devices("客廳燈光")
print(f"客廳燈光群組內有 {len(group_devices)} 台設備")
```

## 資料儲存格式

DeviceManager 使用的 JSON 檔案結構如下：

```json
{
  "devices": [
    {
      "uuid": "12345678abcdef",
      "mac_address": "AABBCCDDEEFF",
      "unicast_addr": "0x0100",
      "name": "設備名稱",
      "type": "設備類型",
      "group": "所屬群組名稱",
      "linked_devices": ["0x0101", "0x0102"]
    },
    // 更多設備...
  ],
  "groups": {
    "群組名稱1": ["0x0100", "0x0101"],
    "群組名稱2": ["0x0102", "0x0103"]
  }
}
```

## 注意事項

1. 每個設備只能屬於一個群組
2. 設備的連動關係是單向的，如需雙向連動，需分別設置
3. 移除設備時，相關的連動關係和群組成員身份會自動更新
4. 所有變更都會立即保存到 JSON 檔案中