# RL62M02 藍牙 Mesh AT 指令程式設計指南

## 簡介
本文件提供 RL62M02 藍牙 Mesh 模組的 AT 指令集，用於配置和控制藍牙 Mesh 網絡。
文件中使用以下符號表示：
- `<<` 表示發送到模組的指令
- `>>` 表示從模組接收的回應

## 目錄
- [RL62M02 藍牙 Mesh AT 指令程式設計指南](#rl62m02-藍牙-mesh-at-指令程式設計指南)
  - [簡介](#簡介)
  - [目錄](#目錄)
  - [基本指令](#基本指令)
    - [查詢韌體版本](#查詢韌體版本)
    - [設置藍芽名稱](#設置藍芽名稱)
    - [重啟藍芽模組](#重啟藍芽模組)
    - [查詢藍芽 Mesh 模組角色](#查詢藍芽-mesh-模組角色)
  - [網絡配置指令](#網絡配置指令)
    - [清除 Mesh 網路配置](#清除-mesh-網路配置)
    - [掃描 Mesh 節點設備](#掃描-mesh-節點設備)
    - [開啟 Mesh PB-ADV 通道](#開啟-mesh-pb-adv-通道)
    - [開啟 Provisioning 功能](#開啟-provisioning-功能)
    - [查詢配置節點設備清單](#查詢配置節點設備清單)
  - [節點配置指令](#節點配置指令)
    - [設置節點的 AppKey](#設置節點的-appkey)
    - [設置節點綁定 Model 的 Appkey](#設置節點綁定-model-的-appkey)
    - [設置新增節點 Model 訂閱的 Group 位址](#設置新增節點-model-訂閱的-group-位址)
    - [設置刪除節點 Model 訂閱的 Group 位址](#設置刪除節點-model-訂閱的-group-位址)
    - [設置節點 Model 的 Publish 位址](#設置節點-model-的-publish-位址)
    - [刪除節點 Model 的 Publish 位址](#刪除節點-model-的-publish-位址)
  - [資料傳輸指令](#資料傳輸指令)
    - [設置 Vendor Model - Datatrans Model 的狀態](#設置-vendor-model---datatrans-model-的狀態)
    - [查詢 Vendor Model - Datatrans Model 的狀態](#查詢-vendor-model---datatrans-model-的狀態)

## 基本指令

### 查詢韌體版本

**指令格式：**
```
AT+VER
```

**返回值格式：**
```
VER-MSG {SUCCESS/ERROR} <version>
```

**範例：**
```
<< AT+VER
>> VER-MSG SUCCESS 1.0.0
```

### 設置藍芽名稱

**指令格式：**
```
AT+NAME [param]
```

**參數說明：**
- `[param]`：要設定的藍牙裝置名稱

**返回值格式：**
```
NAME-MSG {SUCCESS/ERROR}
```

**範例：**
```
<< AT+NAME BLE_TEST
>> NAME-MSG SUCCESS
```

### 重啟藍芽模組

**指令格式：**
```
AT+REBOOT
```

**返回值格式：**
```
REBOOT-MSG {SUCCESS/ERROR}
```

**範例：**
```
<< AT+REBOOT
>> REBOOT-MSG SUCCESS
>> SYS-MSG PROVISIONER READY
```

### 查詢藍芽 Mesh 模組角色

**指令格式：**
```
AT+MRG
```

**返回值格式：**
```
MRG-MSG {SUCCESS/ERROR} {PROVISIONER/DEVICE}
```

**範例：**
```
<< AT+MRG
>> MRG-MSG SUCCESS PROVISIONER
```

## 網絡配置指令

### 清除 Mesh 網路配置

**指令格式：**
```
AT+NR [param]
```

**參數說明：**
- `[param]`：可選參數，指定起始位址

**返回值格式：**
```
NR-MSG {SUCCESS/ERROR} <unicast_addr>
```

**範例：**
```
<< AT+NR
>> NR-MSG SUCCESS 0x0000
>> SYS-MSG PROVISIONER READY
```

```
<< AT+NR 0x100
>> NR-MSG SUCCESS 0x0000
>> SYS-MSG PROVISIONER READY
```

### 掃描 Mesh 節點設備

**指令格式：**
```
AT+DIS [param]
```

**參數說明：**
- `[param]`：1 表示開啟 Mesh 節點設備掃描，0 表示關閉掃描

**返回值格式：**
```
DIS-MSG {SUCCESS/ERROR}
DIS-MSG <mac_addr> <RSSI> <UUID>    // 發現設備時
```

**範例：**
```
<< AT+DIS 1
>> DIS-MSG SUCCESS
>> DIS-MSG 655600000152 -48 123E4567E89B12D3A456655600000152
>> DIS-MSG 655600000152 -48 123E4567E89B12D3A456655600000153
>> DIS-MSG 655600000152 -48 123E4567E89B12D3A456655600000151
<< AT+DIS 0
```

### 開啟 Mesh PB-ADV 通道

**指令格式：**
```
AT+PBADVCON [DEV_UUID]
```

**參數說明：**
- `[DEV_UUID]`：設備的 UUID

**返回值格式：**
```
PBADVCON-MSG {SUCCESS/ERROR}
```

**範例：**
```
<< AT+PBADVCON 123E4567E89B12D3A456655600000151
>> PBADVCON-MSG SUCCESS
```

### 開啟 Provisioning 功能

**指令格式：**
```
AT+PROV
```

**返回值格式：**
```
PROV-MSG {SUCCESS/ERROR} <unicast_address>
```

**範例：**
```
<< AT+PBADVCON 123E4567E89B12D3A456655600000152
>> PBADVCON-MSG SUCCESS
<< AT+PROV
>> PROV-MSG SUCCESS 0x0100
```

### 查詢配置節點設備清單

**指令格式：**
```
AT+NL
```

**返回值格式：**
```
NL-MSG <index> <unicast_addr> <element_num> <state_online>
```

**參數說明：**
- `<index>`：節點索引
- `<unicast_addr>`：節點的單播地址
- `<element_num>`：元素數量
- `<state_online>`：在線狀態，1 表示在線，0 表示離線

**範例：**
```
<< AT+NL
>> NL-MSG 0 0x0100 1 1
>> NL-MSG 1 0x0101 1 0
>> NL-MSG 2 0x0102 1 1
```

## 節點配置指令

### 設置節點的 AppKey

**指令格式：**
```
AT+AKA [dst] [app_key_index] [net_key_index]
```

**參數說明：**
- `[dst]`：目標節點地址
- `[app_key_index]`：應用密鑰索引
- `[net_key_index]`：網絡密鑰索引

**返回值格式：**
```
AKA-MSG {SUCCESS/ERROR}
```

**範例：**
```
<< AT+AKA 0x100 0 0
>> AKA-MSG SUCCESS
```

### 設置節點綁定 Model 的 Appkey

**指令格式：**
```
AT+MAKB [dst] [element_index] [model_id] [app_key_index]
```

**參數說明：**
- `[dst]`：目標節點地址
- `[element_index]`：元素索引
- `[model_id]`：模型 ID
- `[app_key_index]`：應用密鑰索引

**返回值格式：**
```
MAKB-MSG {SUCCESS/ERROR}
```

**範例：**
```
<< AT+MAKB 0x100 0 0x1000ffff 0
>> MAKB-MSG SUCCESS
```

### 設置新增節點 Model 訂閱的 Group 位址

**指令格式：**
```
AT+MSAA [dst] [element_index] [model_id] [Group_addr]
```

**參數說明：**
- `[dst]`：目標節點地址
- `[element_index]`：元素索引
- `[model_id]`：模型 ID
- `[Group_addr]`：群組地址

**備註：**
設置目標節點 Model 訂閱 Group 地址，不同設備中相同 Model 可以訂閱相同的 Group 地址，即可實現同時控制，且 Model 可設定多組 Group Address。
Group 地址範圍: 0xc000 ~ 0xffff

**返回值格式：**
```
MSAA-MSG {SUCCESS/ERROR}
```

**範例：**
```
<< AT+MSAA 0x100 0 0x1000ffff 0xc000
>> MSAA-MSG SUCCESS
```

### 設置刪除節點 Model 訂閱的 Group 位址

**指令格式：**
```
AT+MSAD [dst] [element_index] [model_id] [Group_addr]
```

**參數說明：**
- `[dst]`：目標節點地址
- `[element_index]`：元素索引
- `[model_id]`：模型 ID
- `[Group_addr]`：群組地址

**返回值格式：**
```
MSAD-MSG {SUCCESS/ERROR}
```

**範例：**
```
<< AT+MSAD 0x100 0 0x1000ffff 0xc000
>> MSAD-MSG SUCCESS
```

### 設置節點 Model 的 Publish 位址

**指令格式：**
```
AT+MPAS [dst] [element_idx] [model_id] [publish_addr] [publish_app_key_idx]
```

**參數說明：**
- `[dst]`：目標節點地址
- `[element_idx]`：元素索引
- `[model_id]`：模型 ID
- `[publish_addr]`：發布地址
- `[publish_app_key_idx]`：發布使用的應用密鑰索引

**備註：**
設置目標節點的 Model publish address。如果有設定 Publish address，當綁定的 Model 狀態改變的時候，會自動發送自身狀態到 publish 的地址上。
Publish address 可以是不同節點之 unicast address，也可以是 Group address。

**返回值格式：**
```
MPAS-MSG {SUCCESS/ERROR}
```

**範例：**
```
<< AT+MPAS 0x100 0 0x1000ffff 0x101 0
>> MPAS-MSG SUCCESS
```

### 刪除節點 Model 的 Publish 位址

**指令格式：**
```
AT+MPAD [dst] [element_idx] [model_id] [publish_app_key_idx]
```

**參數說明：**
- `[dst]`：目標節點地址
- `[element_idx]`：元素索引
- `[model_id]`：模型 ID
- `[publish_app_key_idx]`：發布使用的應用密鑰索引

**返回值格式：**
```
MPAD-MSG {SUCCESS/ERROR}
```

**範例：**
```
<< AT+MPAD 0x100 0 0x1000ffff 0
>> MPAD-MSG SUCCESS
```

## 資料傳輸指令

### 設置 Vendor Model - Datatrans Model 的狀態

**指令格式：**
```
AT+MDTS [dst] [element_index] [app_key_idx] [ack] [data(1~20bytes)]
```

**參數說明：**
- `[dst]`：目標節點地址
- `[element_index]`：元素索引
- `[app_key_idx]`：應用密鑰索引
- `[ack]`：是否需要確認回應，1 表示需要，0 表示不需要
- `[data]`：要傳送的數據，1-20 字節

**備註：**
當目標節點 Datatrans model 有被綁定之後，即可透過此指令發送且設定目標節點的 datatrans model 狀態。

**返回值格式：**
```
MDTS-MSG {SUCCESS/ERROR}
MDTS-MSG <unicast_addr> <element_idx> <send_bytes>  // 當有設置 ACK 時收到
```

**範例：**
```
<< AT+MDTS 0x100 0 0 1 0x1122335566778899
>> MDTS-MSG SUCCESS
>> MDTS-MSG 0x0100 0 8
```

### 查詢 Vendor Model - Datatrans Model 的狀態

**指令格式：**
```
AT+MDTG [dst] [element_index] [app_key_idx] [read_data_len]
```

**參數說明：**
- `[dst]`：目標節點地址
- `[element_index]`：元素索引
- `[app_key_idx]`：應用密鑰索引
- `[read_data_len]`：要讀取的數據長度

**備註：**
當目標節點 Datatrans model 有被綁定後，即可透過此指令發送且讀取目標節點的 Datatrans model 狀態。

**返回值格式：**
```
MDTG-MSG {SUCCESS/ERROR}
MDTG-MSG <unicast_addr> <element_idx> <read_data>
```

**範例：**
```
<< AT+MDTG 0x100 0 0 3
>> MDTG-MSG SUCCESS
>> MDTG-MSG 0x0100 0 112233
```

```
<< AT+MDTS 0x100 0 0 0 0x1122335566778899
>> MDTS-MSG SUCCESS
<< AT+MDTG 0x100 0 0 5
>> MDTG-MSG SUCCESS
>> MDTG-MSG 0x0100 0 1122334455
