"""Command Center — Send authenticated telecommands."""

import hashlib
import hmac
import time
import streamlit as st

st.set_page_config(page_title="Command Center", layout="wide")
st.title("🎮 Command Center")

# Available commands
COMMANDS = {
    "SET_MODE": {"params": ["mode"], "desc": "Change satellite operating mode"},
    "CAPTURE_IMAGE": {"params": ["resolution", "bands"], "desc": "Take an image"},
    "SET_ADCS_MODE": {"params": ["adcs_mode"], "desc": "Change pointing mode"},
    "REBOOT_OBC": {"params": [], "desc": "Restart onboard computer"},
    "ENABLE_PAYLOAD": {"params": ["payload_type"], "desc": "Activate payload"},
    "DISABLE_PAYLOAD": {"params": [], "desc": "Deactivate payload"},
    "DOWNLOAD_DATA": {"params": ["start_time", "end_time"], "desc": "Request data downlink"},
    "UPDATE_TLE": {"params": ["tle_line1", "tle_line2"], "desc": "Update orbit elements"},
}

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### Send Command")
    cmd = st.selectbox("Command", list(COMMANDS.keys()))
    cmd_info = COMMANDS[cmd]
    st.caption(cmd_info["desc"])

    params = {}
    for param in cmd_info["params"]:
        params[param] = st.text_input(f"Parameter: {param}")

    # Auth
    secret_key = st.text_input("Auth Key", type="password", value="unisat-secret-2026")
    seq_num = int(time.time())

    if st.button("🚀 Send Command", type="primary"):
        # Build command payload
        payload = f"{cmd}:{seq_num}:{str(params)}"
        mac = hmac.new(secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]

        st.success(f"Command sent: **{cmd}**")
        st.code(f"Payload: {payload}\nHMAC: {mac}\nSequence: {seq_num}")

        # Add to history
        if "cmd_history" not in st.session_state:
            st.session_state.cmd_history = []
        st.session_state.cmd_history.insert(0, {
            "time": time.strftime("%H:%M:%S"),
            "command": cmd,
            "params": str(params),
            "status": "SENT",
            "hmac": mac[:8] + "...",
        })

with col2:
    st.markdown("### Command History")
    history = st.session_state.get("cmd_history", [])
    if not history:
        # Demo history
        history = [
            {"time": "17:45:12", "command": "CAPTURE_IMAGE", "params": "{}", "status": "ACK", "hmac": "a3f2b1c8..."},
            {"time": "17:40:00", "command": "SET_ADCS_MODE", "params": "{'adcs_mode': 'nadir'}", "status": "ACK", "hmac": "e7d4c2a1..."},
            {"time": "17:35:30", "command": "ENABLE_PAYLOAD", "params": "{'payload_type': 'radiation'}", "status": "ACK", "hmac": "b8e5f3d2..."},
        ]
    for entry in history[:10]:
        status_icon = "✅" if entry["status"] == "ACK" else "📤"
        st.markdown(f"`{entry['time']}` {status_icon} **{entry['command']}** — {entry['status']}")
