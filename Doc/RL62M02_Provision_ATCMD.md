# 查詢韌體版本

>> AT+VER\r\n
<< VER-MSG SUCCESS 1.0.0\r\n

# 設置藍芽名稱

指令:AT+NAME [param]\r\n
返回值 :NAME-MSG {SUCCESS/ERROR}

<< AT+NAME BLE_TEST\r\n
>> NAME-MSG SUCCESS\r\n

# 重啟藍芽模組

AT+REBOOT
REBOOT-MSG {SUCCESS/ERROR}

<< AT+REBOOT\r\n
>> REBOOT-MSG SUCCESS\r\n
>> SYS-MSG PROVISIONER READY\r\n

# 查詢藍芽 Mesh 模組角色

AT+MRG
MRG-MSG {SUCCESS/ERROR} {PROVISIONER/DEVICE}
<< AT+MRG\r\n
>> MRG-MSG SUCCESS PROVISIONER\r\n

# 清除 Mesh 網路配置

AT+NR [param]
NR-MSG {SUCCESS/ERROR} <unicast_addr>

<< AT+NR\r\n
>> NR-MSG SUCCESS 0x0000\r\n
>> SYS-MSG PROVISIONER READY\r\n
--------------------------------------------
<< AT+NR 0x100\r\n
>> NR-MSG SUCCESS 0x0000\r\n
>> SYS-MSG PROVISIONER READY\r\n

# 掃描 Mesh 節點設備

AT+DIS [param]
DIS-MSG {SUCCESS/ERROR}
如果發現設備，會持續打印下列訊息
DIS-MSG <mac_addr> <RSSI> <UUID>

[param]=1 : 開啟 Mesh 節點設備掃描
[param]=0 : 關閉 Mesh 節點設備掃描

<< AT+DIS 1\r\n
>> DIS-MSG SUCCESS\r\n
>> DIS-MSG 655600000152 -48 123E4567E89B12D3A456655600000152\r\n
>> DIS-MSG 655600000152 -48 123E4567E89B12D3A456655600000153\r\n
>> DIS-MSG 655600000152 -48 123E4567E89B12D3A456655600000151\r\n
<< AT+DIS 0\r\n

# 開啟 Mesh PB-ADV 通道

AT+PBADVCON [DEV_UUID]
PBADVCON-MSG {SUCCESS/ERROR}

<< AT+PBADVCON 123E4567E89B12D3A456655600000151\r\n
>> PBADVCON-MSG SUCCESS\r\n

# 開啟 Provisioning 功能

AT+PROV
PROV-MSG {SUCCESS/ERROR} <unicast_address>

<< AT+PBADVCON 123E4567E89B12D3A456655600000152\r\n
>> PBADVCON-MSG SUCCESS\r\n
<< AT+PROV\r\n
>> PROV-MSG SUCCESS 0x0100\r\n

# 查詢配置節點設備清單

AT+NL
NL-MSG <index> <unicast_addr> <element_num> <state_online>

<< AT+NL\r\n
>> NL-MSG 0 0x0100 1 1\r\n
>> NL-MSG 1 0x0101 1 0\r\n
>> NL-MSG 2 0x0102 1 1\r\n

# 設置節點的 AppKey

AT+AKA [dst] [app_key_index] [net_key_index]
AKA-MSG {SUCCESS/ERROR}

<< AT+AKA 0x100 0 0\r\n
>> AKA-MSG SUCCESS\r\n

# 設置節點綁定 Model 的 Appkey

AT+MAKB [dst] [element_index] [model_id] [app_key_index]
MAKB-MSG {SUCCESS/ERROR}

<< AT+MAKB 0x100 0 0x1000ffff 0\r\n
>> MAKB-MSG SUCCESS\r\n

# 設置新增節點 Model 訂閱的 Group 位址

AT+MSAA [dst] [element_index] [model_id] [Group_addr]
MSAA-MSG {SUCCESS/ERROR}

設置目標節點 Model 訂閱 Group 地址， 不同設備中相同 Model 可以訂閱相同
的 Group 地址，即可實現同時控制，且 Model 可設定多組 Group Address。
Group 地址範圍: 0xc000 ~ 0xffff

<< AT+MSAA 0x100 0 0x1000ffff 0xc000\r\n
>> MSAA-MSG SUCCESS\r\n

# 設置刪除節點 Model 訂閱的 Group 位址

AT+MSAD [dst] [element_index] [model_id] [Group_addr]
MSAD-MSG {SUCCESS/ERROR}

<< AT+MSAD 0x100 0 x1000ffff 0xc000\r\n
>> MSAD-MSG SUCCESS\r\n

# 設置節點 Model 的 Publish 位址

AT+MPAS [dst] [element_idx] [model_id] [publish_addr] [publish_app_key_idx]
MPAS-MSG {SUCCESS/ERROR}
設置目標節點的 Model publish address。
如果有設定 Publish address，當綁定的 Model 狀態改變的時候，會自動發送自
身狀態到 publish 的地址上。
Publish address 可以是不同節點之 unicast address，也可以是 Group address。
設置目標節點的 Model publish address。
如果有設定 Publish address，當綁定的 Model 狀態改變的時候，會自動發送自
身狀態到 publish 的地址上。
<< AT+MPAS 0x100 0 0x1000ffff 0x101 0\r\n
>> MPAS-MSG SUCCESS\r\n

# 刪除節點 Model 的 Publish 位址

AT+MPAD [dst] [element_idx] [model_id] [publish_app_key_idx]
MPAD-MSG {SUCCESS/ERROR}
<< AT+MPAD 0x100 0 0x1000ffff 0\r\n
>> MPAD-MSG SUCCESS\r\n

# 設置 Vendor Model - Datatrans Model 的狀態

AT+MDTS [dst] [element_index] [app_key_idx] [ack] [data(1~20bytes)]
MDTS-MSG {SUCCESS/ERROR}

當有設置 ACK 時，將會收到下列
MDTS-MSG <unicast_addr> <element_idx> <send_bytes>
當目標節點 Datatrans model 有被綁定之後，
即可透過此指令發送且設定目標節點的 datatrans model 狀態。

<< AT+MDTS 0x100 0 0 1 0x1122335566778899\r\n
>> MDTS-MSG SUCCESS\r\n
>> MDTS-MSG 0x0100 0 8\r\n

# 查詢 Vendor Model - Datatrans Model 的狀態

AT+MDTG [dst] [element_index] [app_key_idx] [read_data_len]
MDTG-MSG <unicast_addr> <element_idx> <read_data>
當目標節點 Datatrans model 有被綁定後，
即可透過此指令發送且讀取目標節點的 Datatrans model 狀態。

<< AT+MDTG 0x100 0 0 3\r\n
>> MDTG-MSG SUCCESS\r\n
>> MDTG-MSG 0x0100 0 112233\r\n
--------------------------------------------
<< AT+MDTS 0x100 0 0 0 0x1122335566778899\r\n
>> MDTS-MSG SUCCESS \r\n
<< AT+MDTG 0x100 0 0 5\r\n
>> MDTG-MSG SUCCESS \r\n
>> MDTG-MSG 0x0100 0 1122334455\r\n
