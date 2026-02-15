"""Health Report — System diagnostics and anomaly detection."""

import random
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Health Report", layout="wide")
st.title("🏥 Health Report")

# Overall health score
score = 94
st.markdown(f"### System Health Score: **{score}/100**")
st.progress(score / 100)

st.markdown("---")

# Subsystem health table
st.markdown("### Subsystem Status")
subsystems = [
    {"Subsystem": "OBC", "Status": "🟢 Nominal", "CPU": "34.2°C", "Uptime": "14d 7h", "Errors": 0},
    {"Subsystem": "EPS", "Status": "🟢 Nominal", "Battery": "78.5%", "Solar": "4.2W", "Errors": 0},
    {"Subsystem": "COMM UHF", "Status": "🟢 Nominal", "RSSI": "-82 dBm", "Packets": "48,231", "Errors": 3},
    {"Subsystem": "ADCS", "Status": "🟡 Warning", "Mode": "Sun Point", "Error": "1.8°", "Errors": 12},
    {"Subsystem": "GNSS", "Status": "🟢 Nominal", "Fix": "3D", "Sats": "9", "Errors": 0},
    {"Subsystem": "Camera", "Status": "🟢 Nominal", "Images": "847", "Storage": "12.3 GB", "Errors": 1},
    {"Subsystem": "Payload", "Status": "🟢 Nominal", "Samples": "124,560", "Dose": "2.34 uSv", "Errors": 0},
]
st.dataframe(pd.DataFrame(subsystems), use_container_width=True, hide_index=True)

st.markdown("---")

# Anomalies
st.markdown("### Detected Anomalies")
anomalies = [
    {"Time": "2026-02-14 17:42:30", "Severity": "⚠️ Warning", "Subsystem": "ADCS",
     "Description": "Pointing error exceeded 2° threshold for 30 seconds"},
    {"Time": "2026-02-14 12:15:00", "Severity": "ℹ️ Info", "Subsystem": "COMM",
     "Description": "3 CRC errors in last 1000 packets (0.3% error rate)"},
    {"Time": "2026-02-13 22:00:00", "Severity": "ℹ️ Info", "Subsystem": "EPS",
     "Description": "Battery SOC dropped below 70% during eclipse"},
]
st.dataframe(pd.DataFrame(anomalies), use_container_width=True, hide_index=True)

st.markdown("---")

# Recommendations
st.markdown("### Recommendations")
st.markdown("""
1. **ADCS:** Consider running desaturation cycle — reaction wheel #2 at 4800 RPM
2. **COMM:** Monitor error rate — currently within acceptable limits
3. **EPS:** Next eclipse period in ~45 min — camera capture should complete before then
4. **Payload:** Radiation levels nominal — no EVA restrictions needed
""")

# Uptime stats
st.markdown("---")
st.markdown("### Uptime Statistics")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Uptime", "14d 7h 23m")
col2.metric("Safe Mode Events", "0")
col3.metric("Reboots", "2")
col4.metric("Comm Sessions", "412")
