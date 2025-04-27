# RL Mesh 設備控制系統

本系統提供了使用 Python 控制 Richlink RL62M02 Mesh 設備的功能，包括 RGB LED 燈、智能插座以及支援 Modbus RTU 的 Smart-Box 設備。系統還提供設備管理功能，可以透過JSON檔案記錄設備、管理群組和連動關係。

## 1. 系統架構

整個系統由以下主要模組組成：

1.  **SerialAT** - 處理串口通訊，負責與 RL62M02 裝置間的基本 AT 指令收發
2.  **Provisioner** - Mesh 網路配置器，處理設備配網、綁定與資料傳輸
3.  **RLMeshDeviceController** - 設備控制層，提供對不同類型設備的高階控制功能
4.  **ModbusRTU** - 提供 Modbus RTU 協議封包的生成和解析功能
5.  **MeshDeviceManager** (`rl62m02/device_manager.py`) - 設備管理層，提供設備資訊記錄、群組管理和連動關係管理，並將設備資訊儲存於 JSON 檔案。

### 系統架構圖

```
+--------------------------------------------------+    +--------------------+    +----------------+
| RLMeshDeviceController                           |<---| MeshDeviceManager  |--->| JSON 設備記錄   |
|                                                  |    | (device_manager.py)|    | (mesh_devices.json)|
| - RGB LED 控制                                   |    +--------------------+    +----------------+
| - 插座控制                                       |
| - Smart-Box RTU 控制                             |
| - Air-Box 環境監測 (溫度、濕度、PM2.5、CO2)      |
| - 電錶監測 (電壓、電流、功率)                    |
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
  - Air-Box 數據讀取
  - 電錶數據讀取

### ModbusRTU
- 提供 Modbus RTU 協議實現
- 支援各種功能碼的封包生成與解析
- 提供 CRC16 校驗功能

### MeshDeviceManager (`rl62m02/device_manager.py`)
- 依賴於 Provisioner 和 RLMeshDeviceController
- 提供設備資訊記錄功能 (讀取/寫入 JSON 檔案)
- 封裝設備掃描、綁定、解綁、訂閱、推播等操作
- 提供統一的設備控制介面 (`control_device`)
- 支援群組管理 (透過訂閱/推播)
- 支援設備連動關係管理 (需自行實現邏輯)

## 3. 支援的設備類型

系統目前支援以下設備類型 (由 `RLMeshDeviceController` 和 `MeshDeviceManager` 處理):

1.  **RGB LED 設備** (`RGB_LED`)
    - 功能：控制 CWRGB 五色通道亮度
    - Opcode: 0x0100 (由控制器內部處理)

2.  **插座設備** (`PLUG`)
    - 功能：控制開關狀態
    - Opcode: 0x0200 (由控制器內部處理)

3.  **Smart-Box 設備** (`SMART_BOX`)
    - 功能：透過 Modbus RTU 協議控制外部裝置
    - 控制器支援讀寫寄存器/線圈

4.  **Air-Box 設備** (`AIR_BOX`)
    - 功能：監測空氣質量數據 (溫度、濕度、PM2.5、CO2)
    - 控制器透過 Modbus RTU 讀取

5.  **電錶設備** (`POWER_METER`)
    - 功能：監測電壓、電流和功率數據
    - 控制器透過 Modbus RTU 讀取

## 4. 使用方法

### 4.1 安裝套件

```bash
# 從目錄安裝
cd rl62m02
pip install -e .

# 或者，如果已經打包
pip install rl62m02-0.1.0.tar.gz
```

### 4.3 使用 mesh_device_manager_demo.py 進階設備管理工具

`mesh_device_manager_demo.py` 是一個基於 `MeshDeviceManager` 類別的全功能設備管理示範程式，提供更完整的設備管理與控制功能。

```bash
python mesh_device_manager_demo.py <COM 埠>
```

啟動後，會顯示以下功能選單：

1.  掃描並綁定設備 - 掃描周邊可用的 Mesh 設備並提供綁定選項
2.  顯示所有設備 - 以表格方式顯示所有已綁定設備的詳細資訊
3.  設定設備名稱 - 修改已綁定設備的顯示名稱 (儲存在 JSON)
4.  設定訂閱 - 設定設備的訂閱通道 (儲存在 JSON 並發送 AT 命令)
5.  設定推播 - 設定設備的推播通道 (儲存在 JSON 並發送 AT 命令)
6.  控制設備 - 依據設備類型提供不同控制選項
7.  解除綁定設備 - 解除特定設備的綁定 (發送 AT 命令並從 JSON 移除)
0.  離開

**特色功能：**

- **友善的設備管理**：以表格形式顯示設備資訊，包含編號、名稱(devType)、MAC、類型(devName)、UID、位置、狀態、訂閱、推播。
- **設備類型自動化控制**：根據不同設備類型(RGB LED、插座、SMART_BOX、AIR_BOX 等)提供對應的控制選項。
- **RGB LED 控制**：提供多種顏色預設與自定義顏色設定。
- **插座控制**：支援開啟、關閉、狀態切換操作。
- **Smart-Box 控制**：支援讀取/寫入寄存器。
- **Air-Box 控制**：支援讀取數據。
- **設備狀態顯示**：顯示設備當前的開關狀態 (僅限部分設備類型)。
- **設備位置記錄**：可記錄設備的安裝位置。
- **JSON 設備記錄**：設備資訊儲存於 `mesh_devices.json` 檔案 (預設)。

**使用範例：**

1.  **掃描並綁定設備**：
    - 選擇選項 `1`
    - 輸入掃描時間
    - 從掃描結果中選擇要綁定的設備編號
    - 輸入設備名稱 (會存入 JSON 的 `devType`)
    - 選擇設備類型 (會存入 JSON 的 `devName`)
    - 輸入設備位置 (可選)
    - 依照提示設定訂閱與推播通道 (可選)

2.  **控制 RGB LED 設備**：
    - 選擇選項 `6`
    - 選擇 RGB LED 設備編號
    - 選擇顏色預設或自定義顏色
    - 自定義顏色時可分別設定冷光、暖光、紅、綠、藍五個通道值(0-255)

3.  **控制插座設備**：
    - 選擇選項 `6`
    - 選擇插座設備編號
    - 選擇操作(開啟、關閉、切換狀態)

4.  **讀取 Air-Box 數據**:
    - 選擇選項 `6`
    - 選擇 Air-Box 設備編號
    - 選擇操作 `1` (讀取數據)

本工具專為設備管理與測試設計，適合進行設備初始配置、功能驗證與系統整合測試使用。

---

### 4.4 進階函式庫手動操作 (非互動模式)

以下範例展示如何直接透過函式庫進行初始化與操作，屬於進階用法，建議已熟悉 Mesh AT 指令與專案結構後再使用。

```python
# 導入並初始化
from rl62m02 import create_provisioner
from rl62m02.controllers.mesh_controller import RLMeshDeviceController
from rl62m02 import MeshDeviceManager # 導入 MeshDeviceManager
import logging
import time

logging.basicConfig(level=logging.INFO)
logging.getLogger('rl62m02').setLevel(logging.DEBUG)

# create_provisioner 返回 (serial_at, provisioner, None)
serial_at, provisioner, _ = create_provisioner("COM3", 115200)

# 建立控制器和設備管理器
controller = RLMeshDeviceController(provisioner)
device_manager = MeshDeviceManager(provisioner, controller, device_json_path="mesh_devices.json")

# 載入已儲存的設備 (可選)
device_manager.load_devices()

# 示例：掃描設備
devices = provisioner.scan_nodes(scan_time=5)  # 使用 provisioner.scan_nodes
print(f"掃描到 {len(devices)} 個設備:")
print([d['uuid'] for d in devices])

# 示例：綁定設備 (使用 MeshDeviceManager，會儲存)
if devices:
    uuid_to_bind = devices[0]['uuid']
    print(f"嘗試綁定 UUID: {uuid_to_bind}")
    res = device_manager.provision_device(
        uuid=uuid_to_bind,
        device_name="MyLED", # 存入 devType
        device_type="RGB_LED", # 存入 devName
        position="Lab"
    )
    print(f"綁定結果: {res}")

    if res.get('result') == 'success':
        unicast_addr = res['unicast_addr']
        print(f"綁定成功，地址: {unicast_addr}")

        # 示例：設定訂閱與推播 (使用 MeshDeviceManager)
        print("設定訂閱...")
        sub_res = device_manager.set_subscription(unicast_addr, '0xC000')
        print(f"訂閱結果: {sub_res}")
        time.sleep(1)
        print("設定推播...")
        pub_res = device_manager.set_publication(unicast_addr, '0xC001')
        print(f"推播結果: {pub_res}")
        time.sleep(1)

        # 示例：控制設備 (使用 MeshDeviceManager)
        print("控制設備 (設為紅色)...")
        ctrl_res = device_manager.control_device(unicast_addr, "set_rgb", red=255)
        print(f"控制結果: {ctrl_res}")

# 關閉串口
serial_at.close()
print("串口已關閉")

```

## 5. 設備註冊與管理

### ~~5.1 功能控制器註冊~~ (控制器不再需要手動註冊)

`RLMeshDeviceController` 不再需要手動 `register_device`。控制方法會直接使用提供的 `unicast_addr`。

### 5.2 設備管理器 (`MeshDeviceManager`)

系統提供完整的設備管理功能，透過 `MeshDeviceManager` 類實現，並使用 JSON 檔案持久化儲存設備資訊。

```python
# 創建設備管理器實例，使用JSON檔案保存設備資訊
from rl62m02 import create_provisioner, MeshDeviceManager
from rl62m02.controllers.mesh_controller import RLMeshDeviceController

serial_at, provisioner, _ = create_provisioner("COM3", 115200)
controller = RLMeshDeviceController(provisioner)
# 如果 JSON 檔案不存在，會自動創建
device_manager = MeshDeviceManager(provisioner, controller, device_json_path="mesh_devices.json")

# 載入設備 (從 JSON 檔案)
device_manager.load_devices()

# 使用設備管理器掃描設備
scan_result = device_manager.scan_devices(scan_time=5.0)
for device in scan_result:
    print(f"UUID: {device['uuid']}, MAC: {device['mac address']}")

# 綁定設備 (自動儲存到 JSON)
result = device_manager.provision_device(
    uuid="<some_uuid>",
    device_name="客廳燈", # 存入 devType
    device_type="RGB_LED", # 存入 devName
    position="客廳"
)
unicast_addr = result.get('unicast_addr')

if unicast_addr:
    # 設定訂閱 (自動儲存)
    device_manager.set_subscription(unicast_addr, "0xC000")

    # 設定推播 (自動儲存)
    device_manager.set_publication(unicast_addr, "0xC001")

    # 設定設備名稱 (僅更新 JSON 中的 devType)
    device_manager.set_device_name(unicast_addr, "新的設備名稱")

    # 控制 RGB LED 設備
    device_manager.control_device(unicast_addr, "set_rgb", cold=0, warm=0, red=255, green=0, blue=0)

    # 控制插座設備 (假設地址為 "0x0002")
    # device_manager.control_device("0x0002", "turn_on")  # 開啟
    # device_manager.control_device("0x0002", "turn_off")  # 關閉
    # device_manager.control_device("0x0002", "toggle")    # 切換狀態

    # 獲取所有設備 (從管理器內存)
    devices = device_manager.get_all_devices()
    print(f"設備數量: {len(devices)}")

    # 格式化顯示所有設備
    print(device_manager.display_devices())

    # 解除綁定設備 (發送 NR 命令並從 JSON 移除)
    device_manager.unbind_device(unicast_addr)

# 關閉串口
serial_at.close()
```

## 6. 錯誤處理

`Provisioner` 的方法通常返回 AT 指令的原始回應或 None/False。`RLMeshDeviceController` 和 `MeshDeviceManager` 的方法通常返回包含 `result` ("success" 或 "failed") 和其他資訊的字典。建議檢查這些返回值。

```python
try:
    # 使用 Controller
    resp = controller.control_rgb_led(unicast_addr, 255, 255, 0, 0, 0)
    if not resp or not resp.startswith('MDTS-MSG SUCCESS'):
        print(f"Controller 控制失敗: {resp}")
    else:
        print("Controller 控制成功")

    # 使用 Manager
    result = device_manager.control_device(unicast_addr, "turn_off")
    if result.get("result") == "success":
        print("Manager 控制成功")
    else:
        print(f"Manager 控制失敗: {result.get('error')}")

except Exception as e:
    print(f"發生錯誤: {e}")
```

## 7. 進階用法

### 設備群組操作 (使用 Provisioner)

```python
# 假設 provisioner 和 unicast_addr 已定義
group_addr = "0xc000"

# 將設備訂閱到該群組 (AT+MSAA)
resp = provisioner.subscribe_group(unicast_addr, group_addr)
print(f"Subscribe Response: {resp}")

# 設定設備推播到群組 (AT+MPAS)
resp = provisioner.publish_to_target(unicast_addr, group_addr)
print(f"Publish Response: {resp}")
```

### 觀察模式 (使用 Provisioner)

```python
# 進入觀察模式，監聽所有周邊訊息 (Ctrl+C 退出)
try:
    print("進入觀察模式，監聽設備消息...")
    provisioner.observe()
except KeyboardInterrupt:
    print("退出觀察模式")
```

## 8. 命令協議格式

(這些是設備端的協議，由 `RLMeshDeviceController` 內部處理)

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

1.  請確保在使用前正確連接實體裝置到指定的 COM 埠。
2.  設備必須先成功配網 (`provisioner.auto_provision_node` 或 `device_manager.provision_device`) 才能進行控制。
3.  若出現通訊錯誤，請檢查設備連接狀態、網路狀態及日誌輸出。
4.  使用完畢後請確保關閉串口連接 (`serial_at.close()`)。
5.  使用 `MeshDeviceManager` 控制設備時，請確保 JSON 檔案中的設備類型 (`devName`) 與實際設備匹配。
6.  網絡通訊可能會有延遲，AT 指令的回應可能需要等待，部分操作 (如讀取數據) 的結果可能透過異步消息返回。

## 10. 完整示例

下面是一個使用 `MeshDeviceManager` 的完整示例，展示如何掃描、配置和控制 RL Mesh 設備：

```python
from rl62m02 import create_provisioner
from rl62m02.controllers.mesh_controller import RLMeshDeviceController
from rl62m02 import MeshDeviceManager
import time
import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger('rl62m02').setLevel(logging.DEBUG)

def main():
    # 1. 初始化通訊和配置
    print("初始化設備...")
    try:
        serial_at, provisioner, _ = create_provisioner("COM3", 115200)
        print("Provisioner 初始化成功")
    except Exception as e:
        print(f"初始化失敗: {e}")
        return

    # 創建控制器和設備管理器
    controller = RLMeshDeviceController(provisioner)
    device_manager = MeshDeviceManager(provisioner, controller, "mesh_devices.json")

    # 2. 掃描設備
    print("掃描設備中...")
    devices = provisioner.scan_nodes(scan_time=5.0)
    print(f"發現 {len(devices)} 個設備:")
    for i, device in enumerate(devices):
        print(f"{i+1}. UUID: {device['uuid']}, MAC地址: {device['mac address']}")

    if not devices:
        print("未找到設備，請確認設備已開啟並在範圍內")
        serial_at.close()
        return

    # 3. 選擇並配置設備
    target_device = devices[0]  # 選擇第一個設備
    print(f"開始配置設備 {target_device['uuid']}...")

    result = device_manager.provision_device(
        uuid=target_device['uuid'],
        device_name="測試設備", # 存入 devType
        device_type="RGB_LED",  # 假設是RGB LED設備, 存入 devName
        position="客廳"
    )

    if result.get('result') != 'success':
        print(f"設備配置失敗: {result}")
        serial_at.close()
        return

    unicast_addr = result.get('unicast_addr')
    print(f"設備配置成功，Unicast地址: {unicast_addr}")

    # 4. 控制設備 (使用 MeshDeviceManager)
    print("開始控制設備...")
    time.sleep(1) # 等待綁定後穩定

    # 設置為紅色
    print("設置為紅色...")
    ctrl_res = device_manager.control_device(unicast_addr, "set_rgb", cold=0, warm=0, red=255, green=0, blue=0)
    print(f"控制結果: {ctrl_res}")
    time.sleep(2)

    # 設置為綠色
    print("設置為綠色...")
    ctrl_res = device_manager.control_device(unicast_addr, "set_rgb", cold=0, warm=0, red=0, green=255, blue=0)
    print(f"控制結果: {ctrl_res}")
    time.sleep(2)

    # 設置為藍色
    print("設置為藍色...")
    ctrl_res = device_manager.control_device(unicast_addr, "set_rgb", cold=0, warm=0, red=0, green=0, blue=255)
    print(f"控制結果: {ctrl_res}")
    time.sleep(2)

    # 設置為白色
    print("設置為白色...")
    ctrl_res = device_manager.control_device(unicast_addr, "set_white", cold=255, warm=255)
    print(f"控制結果: {ctrl_res}")
    time.sleep(2)

    # 關閉
    print("關閉燈光...")
    ctrl_res = device_manager.control_device(unicast_addr, "turn_off")
    print(f"控制結果: {ctrl_res}")

    print("設備控制演示完成")

    # 關閉串口
    serial_at.close()
    print("串口已關閉")

if __name__ == "__main__":
    main()
```

## 11. 設備資料結構

`MeshDeviceManager` 使用的 JSON 檔案結構如下 (預設 `mesh_devices.json`):

```json
{
  "gwMac": "",
  "gwType": "mini_PC",
  "gwPosition": "主機位置",
  "devices": [
    {
      "devMac": "AA:BB:CC:DD:EE:01", // 設備 MAC 地址 (掃描时獲取)
      "devName": "RGB_LED",         // 設備類型 (如 RGB_LED, PLUG, SMART_BOX)
      "devType": "客廳燈",          // 設備自定義名稱
      "devPosition": "客廳",        // 設備位置 (可選)
      "devGroup": "",              // 設備群組 (目前未使用)
      "uid": "0x0001",             // 設備的 unicast 地址 (綁定後分配)
      "state": 1,                  // 設備狀態 (1=開啟, 0=關閉, 可能不適用所有設備)
      "subscribe": ["0xC000"],      // 訂閱的群組地址列表
      "publish": "0xC001"          // 推播的目標地址
    }
    // ... more devices
  ]
}
```

> **重要**: 為了歷史兼容性原因，在 `MeshDeviceManager` 處理的 JSON 資料結構中，`devName` 欄位實際上存放的是**設備類型** (如 "RGB_LED", "PLUG")，而 `devType` 欄位存放的是**設備自定義名稱** (如 "客廳燈")。這與欄位名稱的直覺意義相反，請在使用和解析 JSON 時特別注意。

## 12. 命令行工具

RL62M02 套件提供了命令行工具 (`rl62m02/cli.py`)，可以透過 `setuptools` 安裝後直接在終端中使用：

```bash
# 掃描設備 (持續掃描，Ctrl+C 停止)
rl62m02 scan COM3

# 掃描並選擇綁定設備 (互動式)
rl62m02 provision COM3 --scan

# 直接綁定指定 UUID 的設備
rl62m02 provision COM3 --uuid <設備UUID> --name "客廳燈" --type RGB_LED

# 控制設備 (以地址 0x0100 為例)
# 控制燈光 (C,W,R,G,B)
rl62m02 control COM3 --addr 0x0100 light --value 255,255,0,0,0
# 控制插座 (on/off/toggle)
rl62m02 control COM3 --addr 0x0101 plug --action on
# 讀取 AirBox 數據 (假設地址 0x0102, 從站 1)
rl62m02 control COM3 --addr 0x0102 airbox --action read --slave 1
# 讀取 SmartBox 保持寄存器 (地址 0x0103, 從站 1, 起始 0, 數量 5)
rl62m02 control COM3 --addr 0x0103 smartbox --action read_holding --slave 1 --start 0 --quantity 5

# 解除綁定設備 (互動式選擇)
rl62m02 unprovision COM3 --list

# 直接解除綁定指定地址的設備
rl62m02 unprovision COM3 --addr 0x0100

# 顯示已綁定設備列表 (從 JSON 讀取)
rl62m02 list COM3
```

更多命令和選項可以查看幫助：

```bash
rl62m02 --help
rl62m02 provision --help
rl62m02 control --help
# ... etc
```

---

更詳細的 AT 指令說明請參考 `Doc/RL62M02_Provision_ATCMD.md` 與 `Doc/RL62M02_Mesh_AT_CMD_Programming_Guide_v1.0.pdf` 文件。