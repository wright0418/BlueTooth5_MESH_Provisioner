# RL Mesh 設備控制模組使用指南

`RLMeshDeviceController` 類別提供了一個統一的介面，用於控制 RL Mesh 網路中的各種設備，例如 RGB LED 燈、智能插座、Smart-Box、Air-Box 環境監測器和電力計量設備。

## 目錄

- [RL Mesh 設備控制模組使用指南](#rl-mesh-設備控制模組使用指南)
  - [目錄](#目錄)
  - [設備類型](#設備類型)
  - [基本使用流程](#基本使用流程)
  - [初始化與設備註冊](#初始化與設備註冊)
    - [初始化控制器](#初始化控制器)
    - [註冊設備](#註冊設備)
    - [查詢已註冊設備](#查詢已註冊設備)
  - [設備控制方法](#設備控制方法)
    - [RGB LED 設備控制](#rgb-led-設備控制)
    - [智能插座控制](#智能插座控制)
    - [Smart-Box 設備控制](#smart-box-設備控制)
      - [讀取數據](#讀取數據)
      - [寫入數據](#寫入數據)
    - [Air-Box 環境監測設備](#air-box-環境監測設備)
    - [電錶數據讀取](#電錶數據讀取)
  - [使用範例](#使用範例)
  - [注意事項](#注意事項)

## 設備類型

`RLMeshDeviceController` 支援以下設備類型：

1. **RGB LED 燈** (`"RGB_LED"`): 可控制冷暖色溫和 RGB 顏色的智能燈具
2. **智能插座** (`"PLUG"`): 可遠程開關的智能插座
3. **Smart-Box 設備** (`"SMART_BOX"`): 通用智能設備盒子，支援 Modbus-RTU 協議
4. **Air-Box 空氣盒子** (`"AIR_BOX"`): 環境監測設備，可監測溫度、濕度、PM2.5 和 CO2
5. **電錶設備** (`"POWER_METER"`): 可監測電壓、電流和功率的電力計量設備

## 基本使用流程

使用 `RLMeshDeviceController` 控制設備的基本流程如下：

1. 初始化 `RLMeshDeviceController` 物件
2. 註冊需要控制的設備
3. 使用相應的方法控制或讀取設備數據

## 初始化與設備註冊

### 初始化控制器

首先需要導入必要的模組，並初始化 `RLMeshDeviceController` 物件：

```python
from rl62m02_provisioner import Provisioner
from RL_device_control import RLMeshDeviceController

# 創建 Provisioner 實例
provisioner = Provisioner(com_port="COM3", baud_rate=115200)  # 根據實際情況修改串口參數
provisioner.connect()

# 初始化 RLMeshDeviceController
device_controller = RLMeshDeviceController(provisioner)
```

### 註冊設備

在控制設備前，需要先註冊設備，建立 unicast address 與設備類型的映射關係：

```python
# 註冊一個 RGB LED 設備
device_controller.register_device(unicast_addr="0x0101", device_type="RGB_LED", device_name="客廳燈")

# 註冊一個智能插座
device_controller.register_device(unicast_addr="0x0102", device_type="PLUG", device_name="臥室插座")

# 註冊一個 Air-Box 空氣盒子
device_controller.register_device(unicast_addr="0x0103", device_type="AIR_BOX", device_name="客廳空氣檢測器")

# 註冊一個電錶設備
device_controller.register_device(unicast_addr="0x0104", device_type="POWER_METER", device_name="配電箱電錶")
```

### 查詢已註冊設備

可以使用 `get_registered_devices()` 方法查詢已經註冊的所有設備：

```python
devices = device_controller.get_registered_devices()
for addr, info in devices.items():
    print(f"設備地址: {addr}, 類型: {info['type']}, 名稱: {info['name']}")
```

## 設備控制方法

### RGB LED 設備控制

RGB LED 設備支援控制冷暖色溫以及 RGB 顏色：

```python
# 控制 RGB LED 設備
# 參數範圍：0-255
device_controller.control_rgb_led(
    unicast_addr="0x0101",  # 設備地址
    cold=100,               # 冷色温度 (0-255)
    warm=50,                # 暖色温度 (0-255)
    red=255,                # 紅色值 (0-255)
    green=0,                # 綠色值 (0-255)
    blue=0                  # 藍色值 (0-255)
)

# 調整為暖白光
device_controller.control_rgb_led("0x0101", 0, 255, 0, 0, 0)

# 調整為冷白光
device_controller.control_rgb_led("0x0101", 255, 0, 0, 0, 0)

# 調整為藍色燈光
device_controller.control_rgb_led("0x0101", 0, 0, 0, 0, 255)
```

### 智能插座控制

智能插座支援開關控制：

```python
# 打開插座
device_controller.control_plug("0x0102", True)

# 關閉插座
device_controller.control_plug("0x0102", False)
```

### Smart-Box 設備控制

Smart-Box 設備基於 Modbus-RTU 協議，支援多種數據讀寫操作：

#### 讀取數據

```python
# 讀取保持寄存器
from modbus import ModbusRTU

response = device_controller.read_smart_box_rtu(
    unicast_addr="0x0103",                     # 設備地址
    slave_address=1,                           # Modbus 從站地址
    function_code=ModbusRTU.READ_HOLDING_REGISTERS,  # 功能碼：讀保持寄存器
    start_address=0,                           # 起始地址
    quantity=10                                # 讀取數量
)

# 讀取輸入寄存器
response = device_controller.read_smart_box_rtu(
    unicast_addr="0x0103",
    slave_address=1,
    function_code=ModbusRTU.READ_INPUT_REGISTERS,
    start_address=0,
    quantity=10
)

# 讀取線圈
response = device_controller.read_smart_box_rtu(
    unicast_addr="0x0103",
    slave_address=1,
    function_code=ModbusRTU.READ_COILS,
    start_address=0,
    quantity=10
)
```

#### 寫入數據

```python
# 寫入單個寄存器
device_controller.write_smart_box_register(
    unicast_addr="0x0103",
    slave_address=1,
    register_address=0,
    register_value=100
)

# 寫入多個寄存器
device_controller.write_smart_box_registers(
    unicast_addr="0x0103",
    slave_address=1,
    start_address=0,
    register_values=[100, 200, 300]
)

# 寫入單個線圈
device_controller.write_smart_box_coil(
    unicast_addr="0x0103",
    slave_address=1,
    coil_address=0,
    coil_value=True
)
```

### Air-Box 環境監測設備

Air-Box 設備可以讀取環境數據，包括溫度、濕度、PM2.5和CO2：

```python
# 讀取 Air-Box 環境數據
air_data = device_controller.read_air_box_data(
    unicast_addr="0x0103",
    slave_address=1
)

# 解析環境數據
temperature = air_data["temperature"]  # 溫度，單位：攝氏度
humidity = air_data["humidity"]        # 濕度，單位：%
pm25 = air_data["pm25"]                # PM2.5，單位：μg/m³
co2 = air_data["co2"]                  # CO2，單位：ppm

print(f"溫度：{temperature}°C")
print(f"濕度：{humidity}%")
print(f"PM2.5：{pm25} μg/m³")
print(f"CO2：{co2} ppm")
```

### 電錶數據讀取

電錶設備可以讀取電壓、電流和功率：

```python
# 讀取電錶數據
power_data = device_controller.read_power_meter_data(
    unicast_addr="0x0104",
    slave_address=1
)

# 解析電力數據
voltage = power_data["voltage"]  # 電壓，單位：V
current = power_data["current"]  # 電流，單位：A
power = power_data["power"]      # 功率，單位：W

print(f"電壓：{voltage}V")
print(f"電流：{current}A")
print(f"功率：{power}W")
```

## 使用範例

以下是一個完整的使用範例，演示如何初始化、註冊和控制多種設備：

```python
import logging
import time
from rl62m02_provisioner import Provisioner
from RL_device_control import RLMeshDeviceController

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 初始化 Provisioner
provisioner = Provisioner(com_port="COM3", baud_rate=115200)
provisioner.connect()

# 初始化設備控制器
device_controller = RLMeshDeviceController(provisioner)

# 註冊設備
device_controller.register_device("0x0101", "RGB_LED", "客廳燈")
device_controller.register_device("0x0102", "PLUG", "臥室插座")
device_controller.register_device("0x0103", "AIR_BOX", "客廳空氣檢測器")
device_controller.register_device("0x0104", "POWER_METER", "配電箱電錶")

try:
    # 控制 RGB LED 燈
    print("將客廳燈調為暖黃色...")
    device_controller.control_rgb_led("0x0101", 0, 200, 255, 100, 0)
    time.sleep(1)
    
    # 控制智能插座
    print("打開臥室插座...")
    device_controller.control_plug("0x0102", True)
    time.sleep(1)
    
    # 讀取環境數據
    print("讀取環境數據...")
    air_data = device_controller.read_air_box_data("0x0103", 1)
    print(f"溫度：{air_data['temperature']}°C")
    print(f"濕度：{air_data['humidity']}%")
    print(f"PM2.5：{air_data['pm25']} μg/m³")
    print(f"CO2：{air_data['co2']} ppm")
    time.sleep(1)
    
    # 讀取電錶數據
    print("讀取電力數據...")
    power_data = device_controller.read_power_meter_data("0x0104", 1)
    print(f"電壓：{power_data['voltage']}V")
    print(f"電流：{power_data['current']}A")
    print(f"功率：{power_data['power']}W")
    
except Exception as e:
    logging.error(f"發生錯誤: {e}")
finally:
    # 關閉連接
    provisioner.disconnect()
```

---

## 注意事項

1. 使用前須確保 RL62M02 Provisioner 已正確初始化並連接。
2. 所有設備在使用前必須先註冊，否則控制方法將返回錯誤。
3. 對於 Smart-Box、Air-Box 和電錶等基於 Modbus-RTU 的設備，需要知道正確的從站地址、功能碼和寄存器地址。
4. 處理 RTU 回應數據時，應檢查返回的 `initial_response` 和 `mdtg_response` 兩個部分。