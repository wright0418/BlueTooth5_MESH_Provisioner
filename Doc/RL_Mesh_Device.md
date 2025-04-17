# RL Mesh Device command format (不需要檢查 回傳訊息)
start header ,1 byte , 0x87
opcode ,2 bytes
payload length ,1 byte
payload , 1~16 bytes

 
## RGB LED Device
    opcode = 0x0100
    payload length = 0x05
    payload = CWRGB , 
    "C= 0~255 ,W = 0~255,R = 0~255 ,G = 0~255,B = 0~255"

## Plug Device
    opcode = 0x0200
    payload length = 0x01
    payload = ON/OFF , 
    "ON = 0x01 , OFF = 0x00"

## RL Mesh Device ATCMD @Provisioner 

    AT+MDTS <device uid> 0 <RL Mesh Device command format hex string>

# Smart-Box Device command format (需要接收 MDTG 由此 uid 回傳) 
    start header ,2 byte , 0x8276
    DEVICE TYPE ,1 byte ,  SET:0x00 , GET:0x01 , RTU:0x02 ,SENSOR:0x03
    payload , 0~17 byte , MODBUS RTU PACKET


# MODBUD RTU Packet
    DEVICE_ADDRESS , 1byte
    FUNC CODE , 1 byte 
    DATA , n byte ,data = (start addr , length)
    CRC16 , 2 byte , CRC16 = CRC16(DEVICE_ADDRESS + FUNC CODE + DATA)
    CRC16 (Lo) , 1 byte
    CRC16 (Hi) , 1 byte


# Smart-Box ATCMD @Provisioner 

    AT+MDTS <device uid> 0 <Smart-Box Device command format hex string>
    ex. Smart-box RTU 溫控器
        device uid = 0x0100 , rtu address = 0x01 , func code = 0x03 , 
        data  = (start addr = 0x0001 , length =0x0006 )
        crc16 = 0x9408

        AT+MDTS 0x0100 0 8276 0103000100069408

    ex. Smart-box RTU DIGITAL IN
        device uid = 0x0101 , rtu address = 0x02 , func code = 0x02 , 
        data  = (start addr = 0x0002 , length =0x0001 ) 
        crc16 = 0x59C8

        AT+MDTS 0x0101 0 8276 01030002000159C8

    ex . Smart-box Agent Model (non header 0x8276)
        device uid = 0x0102 , rtu address = 0x03 , func code = 0x03 , 
        data  = (start addr = 0x0003 , length =0x0001 ) 
        crc16 = 0x59C8

        AT+MDTS 0x0102 0 01030003000159C8
