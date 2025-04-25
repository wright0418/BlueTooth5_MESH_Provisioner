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
+--------------------------------------------------+    +----------------+
| RLMeshDeviceController                           |<-->| DeviceManager  |
|                                                  |    +----------------+
| - RGB LED 控制                                   |            |
| - 插座控制                                       |            v
| - Smart-Box RTU 控制                             |    +----------------+
| - Air-Box 環境監測 (溫度、濕度、PM2.5、CO2)      |    | JSON 設備記錄   |
| - 電錶監測 (電壓、電流、功率)                    |    +----------------+
+--------------------------------------------------+
           |                |
           |                v
           |          +----------+
           +--------->| ModbusRTU|
           |          +----------+
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

### 4.1 安裝套件

```bash
# 從目錄安裝
cd rl62m02
pip install -e .

# 或者，如果已經打包
pip install rl62m02-0.1.0.tar.gz
```

### 4.2 使用 RL_devices_demo.py 互動式設備管理工具

推薦使用專為本專案提供的 `RL_devices_demo.py` 腳本來掃描、綁定、管理與控制設備，免去手動撰寫程式碼。

```bash
python RL_devices_demo.py <COM 埠>
```

啟動後，會顯示以下功能選單：

1. 掃描並綁定新設備
2. 顯示所有已綁定設備
3. 設定設備名稱
4. 設定訂閱
5. 設定推播
6. 測試控制設備
7. 解除綁定設備
0. 離開

- 選單操作時依提示輸入對應編號及參數
- 操作日誌同時輸出到終端與 `mesh_device.log` 檔案
- 設備清單與設定儲存在 `new1_device.json`

### 4.3 使用 mesh_device_manager_demo.py 進階設備管理工具

`mesh_device_manager_demo.py` 是一個基於 `MeshDeviceManager` 類別的全功能設備管理示範程式，提供更完整的設備管理與控制功能。

```bash
python mesh_device_manager_demo.py <COM 埠>
```

啟動後，會顯示以下功能選單：

1. 掃描設備 - 掃描周邊可用的 Mesh 設備並提供綁定選項
2. 顯示所有設備 - 以表格方式顯示所有已綁定設備的詳細資訊
3. 設定設備名稱 - 修改已綁定設備的顯示名稱
4. 設定訂閱 - 設定設備的訂閱通道
5. 設定推播 - 設定設備的推播通道
6. 控制設備 - 依據設備類型提供不同控制選項
7. 解除綁定設備 - 解除特定設備的綁定
0. 離開

**特色功能：**

- **更友善的設備管理**：以表格形式顯示設備資訊，包含名稱、類型、UID、MAC地址、位置與狀態
- **設備類型自動化控制**：根據不同設備類型(RGB LED、插座等)提供對應的控制選項
- **RGB LED 控制**：提供多種顏色預設與自定義顏色設定
- **插座控制**：支援開啟、關閉、狀態切換操作
- **設備狀態顯示**：顯示設備當前的開關狀態
- **設備位置記錄**：可記錄設備的安裝位置
- **JSON 設備記錄**：設備資訊儲存於 `My_device.json` 檔案

**使用範例：**

1. **掃描並綁定設備**：
   - 選擇選項 `1` 掃描周圍設備
   - 輸入掃描時間(例如 5 秒)
   - 從掃描結果中選擇要綁定的設備編號
   - 選擇設備類型(RGB LED、插座、Smart-Box 等)
   - 輸入設備名稱與位置
   - 依照提示設定訂閱與推播通道

2. **控制 RGB LED 設備**：
   - 選擇選項 `6` 控制設備
   - 選擇 RGB LED 設備編號
   - 選擇顏色預設(白光、紅色、綠色、藍色、紫色)或自定義顏色
   - 自定義顏色時可分別設定冷光、暖光、紅、綠、藍五個通道值(0-255)

3. **控制插座設備**：
   - 選擇選項 `6` 控制設備
   - 選擇插座設備編號
   - 選擇操作(開啟、關閉、切換狀態)

本工具專為設備管理與測試設計，適合進行設備初始配置、功能驗證與系統整合測試使用。

---

### 4.4 進階函式庫手動操作 (非互動模式)

以下範例展示如何直接透過函式庫進行初始化與操作，屬於進階用法，建議已熟悉 Mesh AT 指令與專案結構後再使用。

```python
# 導入並初始化
from rl62m02 import create_provisioner
from rl62m02.controllers.mesh_controller import RLMeshDeviceController
import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger('rl62m02').setLevel(logging.DEBUG)
# create_provisioner 僅回傳 (serial_at, provisioner, _)，不再直接管理 DeviceManager
serial_at, provisioner, _ = create_provisioner("COM3", 115200)

# 建立控制器
controller = RLMeshDeviceController(provisioner)

# 示例：掃描設備
devices = provisioner.scan_devices(scan_time=5)
print([d['uuid'] for d in devices])

# 示例：綁定設備
res = provisioner.provision_device(devices[0]['uuid'])
print(res)

# 示例：訂閱與推播
provisioner.subscribe_group(res['unicast_addr'], '0xC000')
provisioner.publish_to_target(res['unicast_addr'], '0xC001')
```

<!-- 其餘章節編號向後調整 -->

## 5. 設備註冊與管理

### 5.1 功能控制器註冊

RLMeshDeviceController 提供了設備註冊與管理功能：

```python
# 註冊設備
controller.register_device(unicast_addr, "RGB_LED", "客廳RGB燈")

# 獲取已註冊的所有設備
devices = controller.get_registered_devices()
print(devices)
```

設備註冊可確保使用正確的協議格式與功能，並可添加易於識別的名稱。

### 5.2 設備管理器

系統提供完整的設備管理功能，透過 DeviceManager 類實現：

```python
# 創建設備管理器實例，使用JSON檔案保存設備資訊
# 如果使用 create_provisioner，會自動創建 device_manager
# 否則可以手動創建
from rl62m02 import DeviceManager
device_manager = DeviceManager("mesh_devices.json")

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

## 7. 進階用法

### 設備群組操作

```python
# 設定群組地址
group_addr = "0xc000"

# 將設備訂閱到該群組
provisioner.subscribe_group(unicast_addr, group_addr)

# 設定設備推播到群組
provisioner.publish_to_target(unicast_addr, group_addr)
```

### 觀察模式

```python
# 進入觀察模式，監聽所有周邊訊息 (Ctrl+C 退出)
try:
    print("進入觀察模式，監聽設備消息...")
    provisioner.observe()
except KeyboardInterrupt:
    print("退出觀察模式")
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
4. 使用完畢後請確保關閉串口連接 (`serial_at.close()`)
5. 控制設備時請確保註冊的設備類型與實際設備類型匹配
6. 網絡通訊可能會有延遲，如果控制指令沒有立即得到響應，可能需要增加超時時間或重試機制

## 10. 完整示例

下面是一個完整的示例，展示如何掃描、配置和控制 RL Mesh 設備：

```python
from rl62m02 import create_provisioner, scan_devices, provision_device
from rl62m02.controllers.mesh_controller import RLMeshDeviceController
import time

def main():
    # 1. 初始化通訊和配置
    print("初始化設備...")
    serial_at, provisioner, device_manager = create_provisioner("COM3", 115200)
    
    # 2. 掃描設備
    print("掃描設備中...")
    devices = scan_devices(provisioner, scan_time=5.0)
    print(f"發現 {len(devices)} 個設備:")
    for i, device in enumerate(devices):
        print(f"{i+1}. UUID: {device['uuid']}, MAC地址: {device['mac address']}")
    
    if not devices:
        print("未找到設備，請確認設備已開啟並在範圍內")
        return
    
    # 3. 選擇並配置設備
    target_device = devices[0]  # 選擇第一個設備
    print(f"開始配置設備 {target_device['uuid']}...")
    
    result = provision_device(
        provisioner, 
        target_device['uuid'], 
        device_manager=device_manager,
        device_name="測試設備",
        device_type="RGB_LED"  # 假設是RGB LED設備
    )
    
    if result.get('result') != 'success':
        print(f"設備配置失敗: {result}")
        return
        
    unicast_addr = result.get('unicast_addr')
    print(f"設備配置成功，Unicast地址: {unicast_addr}")
    
    # 4. 控制設備
    print("初始化設備控制器...")
    device_controller = RLMeshDeviceController(provisioner)
    device_controller.register_device(unicast_addr, "RGB_LED", "測試燈")
    
    print("開始控制設備...")
    
    # 設置為紅色
    print("設置為紅色...")
    device_controller.control_rgb_led(unicast_addr, 0, 0, 255, 0, 0)
    time.sleep(2)
    
    # 設置為綠色
    print("設置為綠色...")
    device_controller.control_rgb_led(unicast_addr, 0, 0, 0, 255, 0)
    time.sleep(2)
    
    # 設置為藍色
    print("設置為藍色...")
    device_controller.control_rgb_led(unicast_addr, 0, 0, 0, 0, 255)
    time.sleep(2)
    
    # 設置為白色
    print("設置為白色...")
    device_controller.control_rgb_led(unicast_addr, 255, 255, 0, 0, 0)
    
    print("設備控制演示完成")

if __name__ == "__main__":
    main()
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

## 12. 命令行工具

RL62M02 套件提供了命令行工具，可以直接在終端中使用：

```bash
# 掃描設備
rl62m02 scan COM3

# 配置設備
rl62m02 provision COM3 --uuid <設備UUID> --name "客廳燈" --type RGB_LED

# 控制設備
rl62m02 control COM3 --addr 0x0100 light --value 255,255,0,0,0
```

更多命令和選項可以查看幫助：

```bash
rl62m02 --help
```

---

更詳細的 AT 指令說明請參考 `Doc/RL62M02_Provision_ATCMD.md` 與 `Doc/RL62M02_Mesh_AT_CMD_Programming_Guide_v1.0.pdf` 文件。