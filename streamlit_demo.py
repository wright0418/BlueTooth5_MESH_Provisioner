import streamlit as st
import time
import sys
import logging
import pandas as pd
from rl62m02.serial_at import SerialAT
from rl62m02.provisioner import Provisioner
from device_manager import DeviceManager
from RL_device_control import RLMeshDeviceController
from modbus import ModbusRTU

# --- Configuration & Initialization ---
DEVICE_FILE = "mesh_devices.json"
LOG_FILE = "rl_demo_web.log"

# Setup logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()])

# Function to initialize components and store in session state
def initialize_components(com_port):
    if 'initialized' not in st.session_state or st.session_state.get('com_port') != com_port:
        try:
            st.session_state.ser = SerialAT(com_port, 115200)
            st.session_state.prov = Provisioner(st.session_state.ser)
            st.session_state.device_manager = DeviceManager(DEVICE_FILE)
            st.session_state.controller = RLMeshDeviceController(st.session_state.prov)

            # Load existing devices into controller
            devices = st.session_state.device_manager.get_device_info()['devices']
            for dev in devices:
                dev_type_str = dev.get('type', 'UNKNOWN').upper() # Ensure uppercase for matching
                controller_type = getattr(RLMeshDeviceController, f"DEVICE_TYPE_{dev_type_str}", None)
                if controller_type and dev.get('unicast_addr'):
                    try:
                        st.session_state.controller.register_device(dev['unicast_addr'], controller_type, dev.get('name', 'Unknown'))
                        logging.info(f"Registered existing device {dev.get('name')} ({dev.get('unicast_addr')}) with type {dev_type_str}")
                    except Exception as reg_err:
                         logging.error(f"Error registering device {dev.get('name')}: {reg_err}")


            st.session_state.initialized = True
            st.session_state.com_port = com_port
            logging.info(f"Successfully initialized components on {com_port}")
            st.success(f"成功連接到 {com_port} 並完成初始化")
            # Rerun to update UI state after initialization
            st.rerun()

        except Exception as e:
            st.error(f"初始化失敗: {e}")
            logging.error(f"Initialization failed: {e}")
            # Clean up potentially partially initialized state
            if 'ser' in st.session_state and st.session_state.ser:
                st.session_state.ser.close()
            for key in ['ser', 'prov', 'device_manager', 'controller', 'initialized', 'com_port']:
                if key in st.session_state:
                    del st.session_state[key]
            st.stop() # Stop execution if initialization fails

# --- Helper Functions ---
def get_device_options():
    """Returns a list of device options for selectboxes."""
    if 'device_manager' not in st.session_state:
        return []
    devices = st.session_state.device_manager.get_device_info().get('devices', [])
    options = {f"{dev.get('name', '未命名')} ({dev.get('unicast_addr', '未知')})": dev.get('unicast_addr') for dev in devices}
    return options

def get_group_options():
     """Returns a list of group names."""
     if 'device_manager' not in st.session_state:
         return []
     groups = st.session_state.device_manager.get_device_info().get('groups', {})
     return list(groups.keys())

# --- UI Sections ---
def display_scan_provision():
    st.subheader("掃描與綁定新裝置")
    scan_duration = st.slider("掃描時間 (秒)", 1, 10, 5)

    if st.button("開始掃描"):
        prov = st.session_state.prov
        with st.spinner(f"掃描網狀網路裝置 ({scan_duration}秒)..."):
            try:
                scan_result = prov.scan_nodes(scan_time=scan_duration)
                st.session_state.scan_result = scan_result
                if not scan_result:
                    st.info("未掃描到任何裝置")
                else:
                    st.success(f"掃描到 {len(scan_result)} 個裝置")
            except Exception as e:
                st.error(f"掃描失敗: {e}")
                logging.error(f"Scan failed: {e}")
                st.session_state.scan_result = None

    if 'scan_result' in st.session_state and st.session_state.scan_result:
        st.markdown("---")
        st.write("掃描結果:")
        df = pd.DataFrame(st.session_state.scan_result)
        st.dataframe(df)

        options = {f"{idx+1}. MAC: {dev['mac address']}, UUID: {dev['uuid']}": idx for idx, dev in enumerate(st.session_state.scan_result)}
        selected_option = st.selectbox("選擇要綁定的裝置:", options.keys(), index=None, placeholder="請選擇...")

        if selected_option:
            selected_idx = options[selected_option]
            target = st.session_state.scan_result[selected_idx]

            st.write(f"準備綁定 UUID: {target['uuid']}")

            # Device Type Selection
            device_type_options = {
                "RGB LED": (RLMeshDeviceController.DEVICE_TYPE_RGB_LED, "RGB_LED"),
                "插座": (RLMeshDeviceController.DEVICE_TYPE_PLUG, "PLUG"),
                "Smart-Box": (RLMeshDeviceController.DEVICE_TYPE_SMART_BOX, "SMART_BOX"),
                "Air-Box": (RLMeshDeviceController.DEVICE_TYPE_AIR_BOX, "AIR_BOX"),
                "電錶 (Power Meter)": (RLMeshDeviceController.DEVICE_TYPE_POWER_METER, "POWER_METER"),
            }
            selected_type_name = st.selectbox("選擇設備類型:", device_type_options.keys())

            # Device Name Input
            default_name = f"{device_type_options[selected_type_name][1]}-{target['mac address'][-5:]}" # Use last 5 chars of MAC
            device_name = st.text_input("輸入設備名稱:", value=default_name)

            if st.button("開始綁定"):
                prov = st.session_state.prov
                controller = st.session_state.controller
                device_manager = st.session_state.device_manager
                device_type_const, device_type_str = device_type_options[selected_type_name]

                with st.spinner(f"正在綁定 UUID: {target['uuid']}..."):
                    try:
                        result = prov.auto_provision_node(target['uuid'])
                        st.json(result) # Display raw result

                        if result.get('result') == 'success':
                            unicast_addr = result.get('unicast_addr')
                            if not unicast_addr:
                                st.error("綁定成功，但未獲取到 Unicast 地址")
                                return

                            # Add device to manager and controller
                            device_manager.add_device(target['uuid'], target['mac address'], unicast_addr, device_name, device_type_str)
                            controller.register_device(unicast_addr, device_type_const, device_name)

                            st.success(f"設備 '{device_name}' (地址: {unicast_addr}) 已成功綁定並添加，類型: {device_type_str}")
                            logging.info(f"Device '{device_name}' ({unicast_addr}) provisioned and added as {device_type_str}")

                            # Clear scan results after successful provisioning
                            del st.session_state.scan_result
                            st.rerun() # Refresh UI

                        else:
                            st.error(f"綁定失敗: {result.get('reason', '未知錯誤')}")
                            logging.error(f"Provisioning failed for UUID {target['uuid']}: {result}")

                    except Exception as e:
                        st.error(f"綁定過程中發生錯誤: {e}")
                        logging.error(f"Error during provisioning for UUID {target['uuid']}: {e}")

def display_device_list():
    st.subheader("設備列表")
    dm = st.session_state.device_manager
    info = dm.get_device_info()

    if not info['devices']:
        st.info("目前沒有已綁定的設備")
        return

    st.write(f"設備總數: {info['device_count']}")

    # Prepare data for DataFrame
    data = []
    for device in info['devices']:
        data.append({
            '名稱': device.get('name', '未命名'),
            '地址': device.get('unicast_addr', '未知'),
            '類型': device.get('type', '未指定'),
            '群組': device.get('group', '無'),
            'MAC地址': device.get('mac_address', '未知'),
            'UUID': device.get('uuid', '未知'),
            '添加時間': device.get('added_time', '未記錄')
        })

    df = pd.DataFrame(data)
    st.dataframe(df)

    if st.button("重新整理設備列表"):
        st.rerun()

def display_group_list():
    st.subheader("群組列表")
    dm = st.session_state.device_manager
    info = dm.get_device_info()

    if not info['groups']:
        st.info("目前沒有群組")
    else:
        st.write(f"群組總數: {info['group_count']}")
        for group_name, device_addrs in info['groups'].items():
            with st.expander(f"群組: {group_name} ({len(device_addrs)}個設備)"):
                if device_addrs:
                    for addr in device_addrs:
                        device = dm.get_device_by_unicast(addr)
                        if device:
                            st.write(f"- {device.get('name', '未命名')} ({addr})")
                        else:
                            st.write(f"- 未知設備 ({addr})")
                else:
                    st.write("(群組為空)")

    st.markdown("---")
    st.subheader("管理群組")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**創建新群組**")
        new_group_name = st.text_input("新群組名稱:", key="new_group_name")
        if st.button("創建群組"):
            if new_group_name:
                if dm.create_group(new_group_name):
                    st.success(f"群組 '{new_group_name}' 已創建")
                    logging.info(f"Group '{new_group_name}' created.")
                    st.rerun()
                else:
                    st.warning(f"群組 '{new_group_name}' 已存在或創建失敗")
            else:
                st.warning("群組名稱不能為空")

    with col2:
        st.write("**添加設備到群組**")
        device_options = get_device_options()
        selected_device_display = st.selectbox("選擇設備:", device_options.keys(), index=None, key="group_add_device", placeholder="選擇要添加的設備...")

        group_options = get_group_options()
        selected_group = st.selectbox("選擇目標群組:", group_options, index=None, key="group_add_group", placeholder="選擇要加入的群組...")

        if st.button("添加到群組"):
            if selected_device_display and selected_group:
                unicast_addr = device_options[selected_device_display]
                if dm.add_device_to_group(unicast_addr, selected_group):
                    st.success(f"設備 {selected_device_display} 已添加到群組 {selected_group}")
                    logging.info(f"Device {unicast_addr} added to group {selected_group}")
                    st.rerun()
                else:
                    st.error("添加到群組失敗 (可能已在群組中)")
            else:
                st.warning("請選擇設備和群組")

    # TODO: Add functionality to remove device from group and delete group

def display_set_type():
    st.subheader("設定裝置類型")
    dm = st.session_state.device_manager
    controller = st.session_state.controller
    device_options = get_device_options()

    if not device_options:
        st.info("沒有可用設備")
        return

    selected_device_display = st.selectbox("選擇要設定的設備:", device_options.keys(), index=None, placeholder="請選擇...")

    if selected_device_display:
        unicast_addr = device_options[selected_device_display]
        current_device = dm.get_device_by_unicast(unicast_addr)
        st.write(f"當前類型: {current_device.get('type', '未指定')}")

        device_type_options = {
            "RGB LED": (RLMeshDeviceController.DEVICE_TYPE_RGB_LED, "RGB_LED"),
            "插座": (RLMeshDeviceController.DEVICE_TYPE_PLUG, "PLUG"),
            "Smart-Box": (RLMeshDeviceController.DEVICE_TYPE_SMART_BOX, "SMART_BOX"),
            "Air-Box": (RLMeshDeviceController.DEVICE_TYPE_AIR_BOX, "AIR_BOX"),
            "電錶 (Power Meter)": (RLMeshDeviceController.DEVICE_TYPE_POWER_METER, "POWER_METER"),
        }
        selected_type_name = st.selectbox("選擇新的設備類型:", device_type_options.keys())

        if st.button("確認更改類型"):
            device_type_const, device_type_str = device_type_options[selected_type_name]
            device_name = current_device.get('name', 'Unknown')
            try:
                # Update in DeviceManager first
                if dm.update_device_type(unicast_addr, device_type_str):
                     # Update in Controller
                    controller.register_device(unicast_addr, device_type_const, device_name) # Re-register effectively updates
                    st.success(f"設備 {device_name} ({unicast_addr}) 類型已更新為 {device_type_str}")
                    logging.info(f"Device type for {unicast_addr} updated to {device_type_str}")
                    st.rerun()
                else:
                    st.error("在設備管理器中更新類型失敗")

            except Exception as e:
                st.error(f"設定類型時發生錯誤: {e}")
                logging.error(f"Error setting device type for {unicast_addr}: {e}")

def display_control_device():
    st.subheader("控制裝置")
    dm = st.session_state.device_manager
    controller = st.session_state.controller
    device_options = get_device_options()

    if not device_options:
        st.info("沒有可用設備可控制")
        return

    selected_device_display = st.selectbox("選擇要控制的設備:", device_options.keys(), index=None, placeholder="請選擇...")

    if selected_device_display:
        unicast_addr = device_options[selected_device_display]
        device_info = dm.get_device_by_unicast(unicast_addr)
        device_name = device_info.get('name', '未命名')
        device_type_str = device_info.get('type', 'UNKNOWN').upper()

        st.markdown(f"--- \n ### 控制: {device_name} ({unicast_addr}) - 類型: {device_type_str}")

        # Map type string to controller constant
        controller_type = getattr(RLMeshDeviceController, f"DEVICE_TYPE_{device_type_str}", None)

        if not controller_type:
             st.warning(f"無法識別的設備類型 '{device_type_str}'。請先在 '設定類型' 選單中設定正確的類型。")
             return

        # Ensure device is registered in controller (might happen if added manually to JSON)
        if unicast_addr not in controller.device_map:
             try:
                 controller.register_device(unicast_addr, controller_type, device_name)
                 logging.info(f"Auto-registered device {unicast_addr} in controller.")
             except Exception as e:
                 st.error(f"嘗試在控制器中註冊設備時出錯: {e}")
                 return


        # --- Device Specific Controls ---
        try:
            if controller_type == RLMeshDeviceController.DEVICE_TYPE_RGB_LED:
                control_rgb_led_ui(controller, unicast_addr)
            elif controller_type == RLMeshDeviceController.DEVICE_TYPE_PLUG:
                control_plug_ui(controller, unicast_addr)
            elif controller_type == RLMeshDeviceController.DEVICE_TYPE_SMART_BOX:
                control_smart_box_ui(controller, unicast_addr)
            elif controller_type == RLMeshDeviceController.DEVICE_TYPE_AIR_BOX:
                control_air_box_ui(controller, unicast_addr)
            elif controller_type == RLMeshDeviceController.DEVICE_TYPE_POWER_METER:
                control_power_meter_ui(controller, unicast_addr)
            else:
                st.warning(f"此設備類型 ({device_type_str}) 的控制介面尚未實現。")
        except Exception as e:
            st.error(f"控制設備時發生錯誤: {e}")
            logging.error(f"Error controlling device {unicast_addr}: {e}")


def control_rgb_led_ui(controller, unicast_addr):
    st.write("**RGB LED 控制**")
    cols = st.columns(6)
    with cols[0]:
        if st.button("白光"):
            controller.control_rgb_led(unicast_addr, 255, 255, 0, 0, 0)
            st.toast("已設為白光")
    with cols[1]:
        if st.button("紅色"):
            controller.control_rgb_led(unicast_addr, 0, 0, 255, 0, 0)
            st.toast("已設為紅色")
    with cols[2]:
        if st.button("綠色"):
            controller.control_rgb_led(unicast_addr, 0, 0, 0, 255, 0)
            st.toast("已設為綠色")
    with cols[3]:
        if st.button("藍色"):
            controller.control_rgb_led(unicast_addr, 0, 0, 0, 0, 255)
            st.toast("已設為藍色")
    with cols[4]:
        if st.button("紫色"):
            controller.control_rgb_led(unicast_addr, 0, 0, 255, 0, 255)
            st.toast("已設為紫色")
    with cols[5]:
        if st.button("關燈"):
            controller.control_rgb_led(unicast_addr, 0, 0, 0, 0, 0)
            st.toast("已關燈")

    st.write("自訂顏色:")
    c_cols = st.columns(5)
    cold = c_cols[0].number_input("冷光", 0, 255, 0)
    warm = c_cols[1].number_input("暖光", 0, 255, 0)
    red = c_cols[2].number_input("紅", 0, 255, 0)
    green = c_cols[3].number_input("綠", 0, 255, 0)
    blue = c_cols[4].number_input("藍", 0, 255, 0)
    if st.button("設定自訂顏色"):
        controller.control_rgb_led(unicast_addr, cold, warm, red, green, blue)
        st.toast("已設定自訂顏色")

def control_plug_ui(controller, unicast_addr):
    st.write("**插座控制**")
    cols = st.columns(2)
    with cols[0]:
        if st.button("開啟插座"):
            controller.control_plug(unicast_addr, True)
            st.toast("插座已開啟")
    with cols[1]:
        if st.button("關閉插座"):
            controller.control_plug(unicast_addr, False)
            st.toast("插座已關閉")

def control_smart_box_ui(controller, unicast_addr):
    st.write("**Smart-Box Modbus RTU 控制**")
    slave_addr = st.number_input("從站地址 (Slave ID)", 1, 247, 1)

    tab1, tab2, tab3 = st.tabs(["讀取數據", "寫入寄存器", "寫入線圈"])

    with tab1:
        st.write("讀取功能")
        read_func_options = {
            "讀取保持寄存器 (0x03)": ModbusRTU.READ_HOLDING_REGISTERS,
            "讀取輸入寄存器 (0x04)": ModbusRTU.READ_INPUT_REGISTERS,
            "讀取線圈狀態 (0x01)": ModbusRTU.READ_COILS,
        }
        selected_read_func_name = st.selectbox("選擇讀取功能碼:", read_func_options.keys())
        start_addr = st.number_input("起始地址", 0, 65535, 0)
        quantity = st.number_input("讀取數量", 1, 125, 1)

        if st.button("讀取"):
            func_code = read_func_options[selected_read_func_name]
            with st.spinner("正在讀取..."):
                resp = controller.read_smart_box_rtu(unicast_addr, slave_addr, func_code, start_addr, quantity)
                st.write("響應:")
                st.json(resp) # Display full response

    with tab2:
        st.write("寫入單個寄存器 (0x06)")
        reg_addr = st.number_input("寄存器地址", 0, 65535, 0, key="write_reg_addr")
        value = st.number_input("寫入值", 0, 65535, 0, key="write_reg_val")
        if st.button("寫入寄存器"):
             with st.spinner("正在寫入..."):
                resp = controller.write_smart_box_register(unicast_addr, slave_addr, reg_addr, value)
                st.write("響應:")
                st.json(resp)

    with tab3:
        st.write("寫入單個線圈 (0x05)")
        coil_addr = st.number_input("線圈地址", 0, 65535, 0, key="write_coil_addr")
        state = st.radio("線圈狀態:", ("ON", "OFF"), key="write_coil_state", horizontal=True)
        coil_value = (state == 'ON')
        if st.button("寫入線圈"):
             with st.spinner("正在寫入..."):
                resp = controller.write_smart_box_coil(unicast_addr, slave_addr, coil_addr, coil_value)
                st.write("響應:")
                st.json(resp)


def control_air_box_ui(controller, unicast_addr):
    st.write("**Air-Box 空氣盒子控制**")
    slave_addr = st.number_input("從站地址 (Slave ID)", 1, 247, 1, key="airbox_slave")

    if st.button("讀取當前環境數據"):
        with st.spinner("正在讀取 Air-Box 數據..."):
            try:
                result = controller.read_air_box_data(unicast_addr, slave_addr)
                st.metric("溫度", f"{result.get('temperature', 'N/A')} °C")
                st.metric("濕度", f"{result.get('humidity', 'N/A')} %")
                st.metric("PM2.5", f"{result.get('pm25', 'N/A')} μg/m³")
                st.metric("CO2", f"{result.get('co2', 'N/A')} ppm")
            except Exception as e:
                st.error(f"讀取 Air-Box 失敗: {e}")
                logging.error(f"Failed to read Air-Box {unicast_addr}/{slave_addr}: {e}")

    # Continuous monitoring could be complex with Streamlit's execution model.
    # A simple approach is repeated button clicks or auto-refresh (less ideal).
    st.info("連續監測模式建議在原始 CLI 版本中使用，或需要更複雜的 Streamlit 狀態管理。")


def control_power_meter_ui(controller, unicast_addr):
    st.write("**電錶控制**")
    slave_addr = st.number_input("從站地址 (Slave ID)", 1, 247, 1, key="powermeter_slave")

    if st.button("讀取當前電力數據"):
        with st.spinner("正在讀取電錶數據..."):
            try:
                result = controller.read_power_meter_data(unicast_addr, slave_addr)
                st.metric("電壓", f"{result.get('voltage', 'N/A')} V")
                st.metric("電流", f"{result.get('current', 'N/A')} A")
                st.metric("功率", f"{result.get('power', 'N/A')} W")
                # Add Energy if implemented in controller
                # st.metric("電能", f"{result.get('energy', 'N/A')} kWh")
            except Exception as e:
                st.error(f"讀取電錶失敗: {e}")
                logging.error(f"Failed to read Power Meter {unicast_addr}/{slave_addr}: {e}")

    st.info("連續監測模式建議在原始 CLI 版本中使用，或需要更複雜的 Streamlit 狀態管理。")


def display_unbind_device():
    st.subheader("解除綁定裝置")
    prov = st.session_state.prov
    dm = st.session_state.device_manager
    device_options = get_device_options()

    if not device_options:
        st.info("沒有可用設備可解除綁定")
        return

    selected_device_display = st.selectbox("選擇要解除綁定的設備:", device_options.keys(), index=None, placeholder="請選擇...")

    if selected_device_display:
        unicast_addr = device_options[selected_device_display]
        device_name = selected_device_display.split(' (')[0] # Extract name

        st.warning(f"您確定要解除綁定設備 **{device_name} ({unicast_addr})** 嗎？此操作無法復原。")
        if st.button("確認解除綁定", type="primary"):
            with st.spinner(f"正在解除綁定 {device_name}..."):
                try:
                    # Send unbind command
                    resp = prov._send_and_wait(f'AT+NR {unicast_addr}', timeout=5.0)
                    st.write(f"解除綁定響應: `{resp}`")

                    # Check response and remove from manager
                    if isinstance(resp, str) and resp.startswith('NR-MSG SUCCESS'):
                        if dm.remove_device(unicast_addr):
                            st.success(f"設備 {device_name} ({unicast_addr}) 已成功解除綁定並從設備管理器中移除")
                            logging.info(f"Device {unicast_addr} unbound and removed.")
                            # Remove from controller map if exists
                            if unicast_addr in st.session_state.controller.device_map:
                                del st.session_state.controller.device_map[unicast_addr]
                            st.rerun() # Refresh UI
                        else:
                            st.warning(f"設備 {device_name} ({unicast_addr}) 解除綁定成功，但從管理器移除失敗")
                            logging.warning(f"Device {unicast_addr} unbound but failed to remove from manager.")
                    else:
                        st.error(f"解除綁定設備 {device_name} ({unicast_addr}) 失敗: {resp}")
                        logging.error(f"Failed to unbind device {unicast_addr}: {resp}")

                except Exception as e:
                    st.error(f"解除綁定過程中發生未預期的錯誤: {e}")
                    logging.error(f"Error during unbinding for {unicast_addr}: {e}")

# --- Main App Logic ---
st.set_page_config(page_title="RL Mesh 控制台", layout="wide")
st.title("💡 RL Mesh 設備管理與控制")
st.caption("使用 Streamlit 的網頁介面")

# --- COM Port Input ---
# Use command line argument for COM port
if len(sys.argv) < 2:
    st.error("請在命令列提供 COM 埠: `streamlit run RL_device_demo_web.py -- <COM埠>` (例如: `streamlit run RL_device_demo_web.py -- COM3`)")
    st.stop()
com_port_arg = sys.argv[1]

# Initialize components if not already done or if COM port changed
if 'initialized' not in st.session_state or st.session_state.get('com_port') != com_port_arg:
     initialize_components(com_port_arg)

# Check if initialization was successful before proceeding
if not st.session_state.get('initialized', False):
    st.warning("系統未初始化，請檢查 COM Port 連接或錯誤訊息。")
    st.stop()


# --- Sidebar Navigation ---
st.sidebar.header("功能選單")
menu_options = ("設備列表", "群組管理", "掃描與綁定", "設定類型", "控制設備", "解除綁定")
# Use session state to keep track of the current page
if 'current_page' not in st.session_state:
    st.session_state.current_page = menu_options[0] # Default page

# Create buttons for navigation
for option in menu_options:
    if st.sidebar.button(option, key=f"btn_{option}", use_container_width=True):
        st.session_state.current_page = option
        st.rerun() # Rerun to display the selected page

st.sidebar.markdown("---")
st.sidebar.info(f"已連接到: {st.session_state.com_port}")
if st.sidebar.button("重新整理狀態"):
     st.rerun()


# --- Main Content Area ---
# Display the selected page based on session state
current_page = st.session_state.current_page

if current_page == "設備列表":
    display_device_list()
elif current_page == "群組管理":
    display_group_list()
elif current_page == "掃描與綁定":
    display_scan_provision()
elif current_page == "設定類型":
    display_set_type()
elif current_page == "控制設備":
    display_control_device()
elif current_page == "解除綁定":
    display_unbind_device()


# --- Footer / Cleanup (Optional) ---
# Streamlit manages the app lifecycle. Explicit serial closing here might be complex.
# Ensure SerialAT's __del__ handles closing if possible, or rely on script termination.
# Consider adding a manual "Disconnect" button if needed, which would call ser.close()
# and clear session state, requiring re-initialization.