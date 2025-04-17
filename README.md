# RL Mesh 設備控制系統

本系統提供了使用 Python 控制 Richlink RL62M02 Mesh 設備的功能，包括 RGB LED 燈、智能插座以及支援 Modbus RTU 的 Smart-Box 設備。系統還提供設備管理功能，可以透過JSON檔案記錄設備、管理群組和連動關係。

## 1. 系統架構

整個系統由四個主要模組組成：

1. **SerialAT** - 處理串口通訊，負責與 RL62M02 裝置間的基本 AT 指令收發
2. **Provisioner** - Mesh 網路配置器，處理設備配網、綁定與資料傳輸
3. **RLMeshDeviceController** - 設備控制層，提供對不同類型設備的高階控制功能
4. **ModbusRTU** - 提供 Modbus RTU 協議封包的生成和解析功能
5. **DeviceManager** - 設備管理層，提供設備資訊記錄、群組管理和連動關係管理

### 系統架構圖

```
+------------------------+    +-----------------+
| RLMeshDeviceController |<-->| DeviceManager  |
+------------------------+    +-----------------+
         |     |                      |
         |     v                      v
         |  +----------+      +---------------+
         +->| ModbusRTU|      | JSON 設備記錄 |
         |  +----------+      +---------------+
         v
    +-------------+
    | Provisioner |
    +-------------+
         |
         v
     +----------+
     | SerialAT |
     +----------+
         |
         v
 +-----------------+
 | 實體串口 (COM埠) |
 +-----------------+
```

## 2. 類別關係

### SerialAT
- 負責串口通訊基本操作
- 提供異步讀取與寫入功能
- 支援回撥函數處理接收到的資料

### Provisioner
- 依賴於 SerialAT 進行通訊
- 封裝 RL62M02 的 AT 指令集
- 提供設備掃描、配網、綁定等功能
- 實現資料傳輸功能 (MDTS/MDTG)

### RLMeshDeviceController
- 依賴於 Provisioner 和 ModbusRTU
- 提供對不同類型設備的控制功能：
  - RGB LED 控制
  - 插座開關控制
  - Smart-Box RTU 設備控制

### ModbusRTU
- 提供 Modbus RTU 協議實現
- 支援各種功能碼的封包生成與解析
- 提供 CRC16 校驗功能

### DeviceManager
- 提供設備資訊記錄功能
- 支援群組管理
- 支援設備連動關係管理

## 3. 支援的設備類型

系統目前支援以下設備類型：

1. **RGB LED 設備** (DEVICE_TYPE_RGB_LED)
   - 功能：控制 CWRGB 五色通道亮度
   - Opcode: 0x0100

2. **插座設備** (DEVICE_TYPE_PLUG)
   - 功能：控制開關狀態
   - Opcode: 0x0200

3. **Smart-Box 設備** (DEVICE_TYPE_SMART_BOX)
   - 功能：透過 Modbus RTU 協議控制外部裝置
   - 支援類型：
     - SET (0x00)
     - GET (0x01)
     - RTU (0x02)
     - SENSOR (0x03)

4. **Air-Box 設備** (DEVICE_TYPE_AIR_BOX)
   - 功能：監測空氣質量數據

5. **電錶設備** (DEVICE_TYPE_POWER_METER)
   - 功能：監測電壓、電流和功率數據

## 4. 使用方法

### 4.1 基本設置

```python
# 導入必要的模組
from rl62m02_provisioner import SerialAT, Provisioner
from RL_device_control import RLMeshDeviceController
import time

# 初始化串口通訊
com_port = "COM4"  # 根據實際 COM 埠修改
ser = SerialAT(com_port, 115200)

# 創建 Provisioner 實例
prov = Provisioner(ser)

# 創建設備控制器
controller = RLMeshDeviceController(prov)
```

### 4.2 設備掃描與配網

```python
# 掃描設備
scan_result = prov.scan_nodes(scan_time=5)
print("掃描結果:", scan_result)

# 自動配網綁定設備
if scan_result:
    target = scan_result[0]
    print(f"開始自動綁定 UUID: {target['uuid']}")
    result = prov.auto_provision_node(target['uuid'])
    print('自動綁定結果:', result)
    
    # 如果綁定成功，獲取 unicast_addr
    if result['result'] == 'success':
        unicast_addr = result['unicast_addr']
        print(f"設備已成功綁定，unicast_addr: {unicast_addr}")
```

### 4.3 RGB LED 設備控制

```python
# 假設 unicast_addr 已經通過配網獲取
unicast_addr = "0x0100"

# 註冊 RGB LED 設備
controller.register_device(unicast_addr, RLMeshDeviceController.DEVICE_TYPE_RGB_LED, "客廳RGB燈")

# 控制 RGB LED - 白光
controller.control_rgb_led(unicast_addr, 255, 255, 0, 0, 0)  # 冷光和暖光最大

# 控制 RGB LED - 紅色
controller.control_rgb_led(unicast_addr, 0, 0, 255, 0, 0)

# 控制 RGB LED - 藍色
controller.control_rgb_led(unicast_addr, 0, 0, 0, 0, 255)

# 混合色 - 紫色
controller.control_rgb_led(unicast_addr, 0, 0, 255, 0, 255)

# 關閉燈光
controller.control_rgb_led(unicast_addr, 0, 0, 0, 0, 0)
```

### 4.4 插座控制

```python
# 假設 unicast_addr 已經通過配網獲取
unicast_addr = "0x0200"

# 註冊插座設備
controller.register_device(unicast_addr, RLMeshDeviceController.DEVICE_TYPE_PLUG, "主臥插座")

# 開啟插座
controller.control_plug(unicast_addr, True)

# 關閉插座
controller.control_plug(unicast_addr, False)
```

### 4.5 Smart-Box 設備控制

```python
# 假設 unicast_addr 已經通過配網獲取
unicast_addr = "0x0300"

# 註冊 Smart-Box 設備
controller.register_device(unicast_addr, RLMeshDeviceController.DEVICE_TYPE_SMART_BOX, "智能溫控器")

# 讀取保持寄存器
controller.read_smart_box_rtu(unicast_addr, 1, ModbusRTU.READ_HOLDING_REGISTERS, 0, 10)

# 寫入單個寄存器
controller.write_smart_box_register(unicast_addr, 1, 100, 12345)

# 寫入多個寄存器
controller.write_smart_box_registers(unicast_addr, 1, 200, [1111, 2222, 3333])

# 控制線圈
controller.write_smart_box_coil(unicast_addr, 1, 0, True)
```

### 4.6 錯誤處理

所有的控制命令都會返回執行結果，建議在實際應用中加入適當的錯誤處理：

```python
try:
    resp = controller.control_rgb_led(unicast_addr, 255, 255, 0, 0, 0)
    if not resp or not resp.startswith('MDTS-MSG SUCCESS'):
        print(f"控制失敗: {resp}")
    else:
        print("控制成功")
except Exception as e:
    print(f"發生錯誤: {e}")
```

## 5. 設備註冊與管理

### 5.1 功能控制器註冊

RLMeshDeviceController 提供了設備註冊與管理功能：

```python
# 註冊設備
controller.register_device(unicast_addr, device_type, device_name)

# 獲取已註冊的所有設備
devices = controller.get_registered_devices()
print(devices)
```

設備註冊可確保使用正確的協議格式與功能，並可添加易於識別的名稱。

### 5.2 設備管理器

系統提供完整的設備管理功能，透過 DeviceManager 類實現：

```python
# 導入設備管理器
from device_manager import DeviceManager

# 創建設備管理器實例，使用JSON檔案保存設備資訊
device_manager = DeviceManager("devices.json")

# 添加設備
device_manager.add_device("uuid-001", "AA:BB:CC:DD:EE:01", "0x0001", "客廳燈")

# 創建群組
device_manager.create_group("客廳群組")

# 將設備添加到群組
device_manager.add_device_to_group("0x0001", "客廳群組")

# 建立設備連動關係 (當開關1操作時會連動控制燈1)
device_manager.link_devices("0x0002", "0x0001")  # 開關地址, 燈地址

# 解除設備連動關係
device_manager.unlink_devices("0x0002", "0x0001")

# 獲取設備資訊
info = device_manager.get_device_info()
print(f"設備數量: {info['device_count']}")
print(f"群組數量: {info['group_count']}")
```

### 5.3 設備管理整合

主程式中已經整合了設備管理功能，可通過選單選項 "8. 設備管理" 進行以下操作：

1. 顯示所有設備
2. 顯示所有群組
3. 創建新群組
4. 添加設備到群組
5. 從群組移除設備
6. 建立設備連動關係
7. 解除設備連動關係 
8. 全部解除綁定

綁定和解綁設備時會自動更新設備管理記錄。

## 6. 錯誤處理

所有的控制命令都會返回執行結果，建議在實際應用中加入適當的錯誤處理：

```python
try:
    resp = controller.control_rgb_led(unicast_addr, 255, 255, 0, 0, 0)
    if not resp or not resp.startswith('MDTS-MSG SUCCESS'):
        print(f"控制失敗: {resp}")
    else:
        print("控制成功")
except Exception as e:
    print(f"發生錯誤: {e}")
```

## 7. 互動式測試

系統提供了一系列測試功能，可用於驗證設備控制功能：

```python
from RL_device_control import test_rgb_led_control, test_plug_control, test_smart_box_control

# 測試 RGB LED 控制
test_rgb_led_control(controller, "0x0100")

# 測試插座控制
test_plug_control(controller, "0x0200")

# 測試 Smart-Box 控制
test_smart_box_control(controller, "0x0300")
```

## 8. 命令協議格式

### RGB LED 設備
- Opcode: 0x0100
- Payload length: 0x05
- Payload: CWRGB (各 1 byte，範圍 0~255)

### 插座設備
- Opcode: 0x0200
- Payload length: 0x01
- Payload: 0x01(開)/0x00(關)

### Smart-Box 設備
- Header: 0x8276
- Device Type: SET(0x00)/GET(0x01)/RTU(0x02)/SENSOR(0x03)
- Payload: Modbus RTU 封包

## 9. 注意事項

1. 請確保在使用前正確連接實體裝置到指定的 COM 埠
2. 設備必須先成功配網才能進行控制
3. 若出現通訊錯誤，請檢查設備連接狀態與網路狀態
4. 使用完畢後請確保關閉串口連接 (`ser.close()`)

## 10. 進階用法

### 設備群組操作

```python
# 設定群組地址
group_addr = "0xc000"

# 將設備訂閱到該群組
prov.subscribe_group(unicast_addr, group_addr)

# 設定設備推播到群組
prov.publish_to_target(unicast_addr, group_addr)
```

### 觀察模式

```python
# 進入觀察模式，監聽所有周邊訊息 (Ctrl+C 退出)
prov.observe()
```

## 11. 設備資料結構

DeviceManager 使用的 JSON 檔案結構如下：

```json
{
  "devices": [
    {
      "uuid": "uuid-001",
      "mac_address": "AA:BB:CC:DD:EE:01", 
      "unicast_addr": "0x0001",
      "name": "燈光設備-1",
      "group": "燈光群組",
      "linked_devices": ["0x0003"]
    }
  ],
  "groups": {
    "燈光群組": ["0x0001", "0x0002"],
    "開關群組": ["0x0003", "0x0004"]
  }
}
```

## 12. Python 程式碼結構與功能說明

本專案包含以下 Python 程式碼檔案，每個檔案的功能與結構如下：

### 12.1 `device_manager.py`
- **功能**：
  - 提供設備管理功能，包括設備資訊記錄、群組管理和設備連動關係管理。
  - 支援 JSON 檔案保存設備資訊。
- **主要類別與方法**：
  - `DeviceManager` 類：
    - `add_device(uuid, mac_address, unicast_addr, name)`：新增設備。
    - `create_group(group_name)`：創建設備群組。
    - `add_device_to_group(unicast_addr, group_name)`：將設備添加到群組。
    - `link_devices(source_addr, target_addr)`：建立設備連動關係。
    - `unlink_devices(source_addr, target_addr)`：解除設備連動關係。

### 12.2 `mesh_devices.json`
- **功能**：
  - 保存 Mesh 設備的靜態資訊，包括 UUID、MAC 地址、單播地址、名稱、群組和連動關係。

### 12.3 `modbus.py`
- **功能**：
  - 提供 Modbus RTU 協議的封包生成與解析功能。
  - 支援 CRC16 校驗。
- **主要類別與方法**：
  - `ModbusRTU` 類：
    - `generate_request(function_code, start_addr, quantity)`：生成 Modbus 請求封包。
    - `parse_response(response)`：解析 Modbus 回應封包。

### 12.4 `RL_device_control.py`
- **功能**：
  - 提供對 Mesh 設備的高階控制功能，包括 RGB LED、插座和 Smart-Box 設備。
- **主要類別與方法**：
  - `RLMeshDeviceController` 類：
    - `register_device(unicast_addr, device_type, name)`：註冊設備。
    - `control_rgb_led(unicast_addr, cw, ww, r, g, b)`：控制 RGB LED 設備。
    - `control_plug(unicast_addr, state)`：控制插座設備。
    - `read_smart_box_rtu(unicast_addr, slave_id, function_code, start_addr, quantity)`：讀取 Smart-Box 資料。

### 12.5 `RL_device_demo.py`
- **功能**：
  - 提供互動式測試功能，用於驗證設備控制功能。
- **主要函數**：
  - `test_rgb_led_control(controller, unicast_addr)`：測試 RGB LED 控制。
  - `test_plug_control(controller, unicast_addr)`：測試插座控制。
  - `test_smart_box_control(controller, unicast_addr)`：測試 Smart-Box 控制。

### 12.6 `rl62m02_provisioner.py`
- **功能**：
  - 提供 Mesh 網路配置功能，包括設備掃描、配網和綁定。
- **主要類別與方法**：
  - `SerialAT` 類：
    - `send_command(command)`：發送 AT 指令。
    - `read_response()`：讀取回應。
  - `Provisioner` 類：
    - `scan_nodes(scan_time)`：掃描設備。
    - `auto_provision_node(uuid)`：自動綁定設備。
    - `subscribe_group(unicast_addr, group_addr)`：訂閱群組。
    - `publish_to_target(unicast_addr, target_addr)`：設置推播目標。


### 12.7 `Doc/`
- **功能**：
  - 提供相關技術文件與使用說明。
  - 包含：
    - `RL_Mesh_Device.md`：Mesh 設備使用說明。
    - `RL62M02_Mesh_AT_CMD_Programming_Guide_v1.0.pdf`：AT 指令集編程指南。
    - `RL62M02_Provision_ATCMD.md`：Provision AT 指令說明。

---

更詳細的 AT 指令說明請參考 `RL62M02_Provision_ATCMD.md` 與 `RL62M02_Mesh_AT_CMD_Programming_Guide_v1.0.pdf` 文件。