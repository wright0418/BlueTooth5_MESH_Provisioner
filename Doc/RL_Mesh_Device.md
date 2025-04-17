# RL Mesh 設備通訊協議文檔

## 1. RL Mesh Device 命令格式 (不需要檢查回傳訊息)

| 欄位 | 大小 | 值 |
|------|------|-----|
| Start Header | 1 byte | 0x87 |
| Opcode | 2 bytes | 詳見各設備類型 |
| Payload Length | 1 byte | Payload 長度 |
| Payload | 1~16 bytes | 依設備類型而定 |

### 1.1 RGB LED Device

| 欄位 | 值 |
|------|-----|
| Opcode | 0x0100 |
| Payload Length | 0x05 |
| Payload | CWRGB |

**參數說明:**
- C = 0~255 (冷光)
- W = 0~255 (暖光)
- R = 0~255 (紅色)
- G = 0~255 (綠色)
- B = 0~255 (藍色)

### 1.2 Plug Device

| 欄位 | 值 |
|------|-----|
| Opcode | 0x0200 |
| Payload Length | 0x01 |
| Payload | ON/OFF |

**參數說明:**
- ON = 0x01
- OFF = 0x00

### 1.3 RL Mesh Device AT 命令格式 @Provisioner

```
AT+MDTS <device uid> 0 <RL Mesh Device command format hex string>
```

**參數說明:**
- `device uid`: 設備唯一識別碼
- `0`: 固定參數
- `hex string`: RL Mesh Device 命令的十六進制字串

## 2. Smart-Box Device 命令格式 (需要接收 MDTG 由此 uid 回傳)

| 欄位 | 大小 | 值 |
|------|------|-----|
| Start Header | 2 bytes | 0x8276 |
| Device Type | 1 byte | SET: 0x00, GET: 0x01, RTU: 0x02, SENSOR: 0x03 |
| Payload | 0~17 bytes | MODBUS RTU PACKET |

## 3. MODBUS RTU 封包格式

| 欄位 | 大小 | 說明 |
|------|------|------|
| DEVICE_ADDRESS | 1 byte | 設備地址 |
| FUNC CODE | 1 byte | 功能碼 |
| DATA | n bytes | data = (start addr, length) |
| CRC16 | 2 bytes | CRC16 = CRC16(DEVICE_ADDRESS + FUNC CODE + DATA) |
| CRC16 (Lo) | 1 byte | CRC16 低位元組 |
| CRC16 (Hi) | 1 byte | CRC16 高位元組 |

## 4. Smart-Box AT 命令格式 @Provisioner

```
AT+MDTS <device uid> 0 <Smart-Box Device command format hex string>
```

### 4.1 應用實例

#### 例1: Smart-box RTU 溫控器
```
device uid = 0x0100
rtu address = 0x01
func code = 0x03
data = (start addr = 0x0001, length = 0x0006)
crc16 = 0x9408

AT+MDTS 0x0100 0 8276 0103000100069408
```

#### 例2: Smart-box RTU DIGITAL IN
```
device uid = 0x0101
rtu address = 0x02
func code = 0x02
data = (start addr = 0x0002, length = 0x0001)
crc16 = 0x59C8

AT+MDTS 0x0101 0 8276 01030002000159C8
```

#### 例3: Smart-box Agent Model (無 header 0x8276)
```
device uid = 0x0102
rtu address = 0x03
func code = 0x03
data = (start addr = 0x0003, length = 0x0001)
crc16 = 0x59C8

AT+MDTS 0x0102 0 01030003000159C8
```

## 5. 通訊流程圖

```
Provisioner          RL Mesh Device
    |                      |
    |------- MDTS -------->|   發送命令
    |                      |
    |<------ MDTG ---------| (Smart-Box 需要回傳)
    |                      |
```

## 6. 常見問題與解決方案

- **問題**: 發送命令後沒有收到回應
  **解決方案**: 檢查設備 UID 是否正確，檢查網絡連接狀態

- **問題**: CRC16 計算結果不正確
  **解決方案**: 確保 CRC16 計算包含了完整的 DEVICE_ADDRESS + FUNC CODE + DATA
