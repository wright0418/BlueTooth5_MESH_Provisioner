# RL_device_demo.py 使用說明

## 簡介
`RL_device_demo.py` 是一個用於控制 RL Mesh 設備的示範程式，提供多種設備的管理與控制功能，包括 RGB LED、插座、Smart-Box、Air-Box 和電錶等。

---

## 使用方式
執行此程式需要指定 COM 埠，並可選擇測試類型。
python 需要安裝 `pyserial` 模組來進行串口通訊。
請確保已安裝此模組，並且設備已正確連接到指定的 COM 埠。

### 基本指令
```bash
python RL_device_demo.py <COM埠> [測試類型]
```

### 參數說明
- `<COM埠>`: 指定設備連接的 COM 埠，例如 `COM3`。
- `[測試類型]`: 可選參數，指定測試的功能類型，預設為 `all`。
  - `all`: 執行所有功能。
  - `rgb`: 測試 RGB LED 控制功能。
  - `plug`: 測試插座控制功能。
  - `smart_box`: 測試 Smart-Box 功能。
  - `device_mgmt`: 進入設備管理功能選單。

---

## 功能介紹

### 1. 裝置管理功能
進入裝置管理選單，提供以下功能：
- 掃描與綁定新裝置
- 顯示所有裝置
- 顯示所有群組
- 設定裝置類型
- 測試控制裝置
- 解除綁定裝置

### 2. RGB LED 控制
提供多種燈光控制選項，包括：
- 設定為白光、紅色、綠色、藍色、紫色
- 關閉燈光
- 自訂顏色

### 3. 插座控制
控制插座的開啟與關閉。

### 4. Smart-Box 功能
支持 Modbus RTU 操作，包括：
- 讀取保持寄存器
- 讀取輸入寄存器
- 讀取線圈狀態
- 寫入單個寄存器
- 控制線圈

### 5. Air-Box 控制
讀取空氣盒子的環境數據，包括：
- 溫度
- 濕度
- PM2.5
- CO2

### 6. 電錶控制
讀取電錶的電力數據，包括：
- 電壓
- 電流
- 功率

---

## 注意事項
1. 確保設備已正確連接到指定的 COM 埠。
2. 執行程式前，請確認所需的依賴庫已安裝。
3. 若遇到錯誤，請檢查設備連接狀態或參數設定是否正確。

---

## 依賴項目
此程式依賴以下模組：
- `rl62m02_provisioner`
- `device_manager`
- `RL_device_control`
- `modbus`

請確保這些模組已正確安裝並可用。

---

## 範例
### 範例 1: 執行所有功能
```bash
python RL_device_demo.py COM3 all
```

### 範例 2: 測試 RGB LED 功能
```bash
python RL_device_demo.py COM3 rgb
```

### 範例 3: 進入設備管理功能
```bash
python RL_device_demo.py COM3 device_mgmt
```

---

## 聯絡方式
如有任何問題，請聯繫開發者或參考相關技術文檔。