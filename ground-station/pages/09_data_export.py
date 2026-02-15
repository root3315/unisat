"""Data Export — Download telemetry in CSV, JSON, or CCSDS format."""

import json
import io
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Data Export", layout="wide")
st.title("📦 Data Export")

# Options
col1, col2, col3 = st.columns(3)
with col1:
    export_format = st.selectbox("Format", ["CSV", "JSON", "CCSDS Raw"])
with col2:
    start_date = st.date_input("Start Date", value=pd.Timestamp("2026-02-11"))
with col3:
    end_date = st.date_input("End Date", value=pd.Timestamp("2026-02-14"))

data_type = st.multiselect(
    "Data Types",
    ["OBC Housekeeping", "EPS Telemetry", "ADCS Attitude", "GNSS Position",
     "Payload Data", "Radiation"],
    default=["OBC Housekeeping", "EPS Telemetry"]
)

st.markdown("---")

# Generate sample data
n = 500
np.random.seed(42)
sample_data = pd.DataFrame({
    "timestamp": pd.date_range(start=str(start_date), periods=n, freq="5min"),
    "cpu_temp_c": 35 + np.random.normal(0, 3, n),
    "battery_v": 14.2 + np.random.normal(0, 0.3, n),
    "battery_soc_pct": 75 + np.cumsum(np.random.normal(0, 0.5, n)),
    "solar_power_w": np.maximum(0, 4 + np.random.normal(0, 2, n)),
    "radiation_cpm": np.random.poisson(120, n),
    "lat": np.random.uniform(-60, 60, n),
    "lon": np.random.uniform(-180, 180, n),
    "alt_km": 550 + np.random.normal(0, 0.5, n),
})

st.markdown(f"**{len(sample_data)} records** from {start_date} to {end_date}")
st.dataframe(sample_data.head(20), use_container_width=True, hide_index=True)

# Download
st.markdown("---")
if export_format == "CSV":
    csv_data = sample_data.to_csv(index=False)
    st.download_button("⬇️ Download CSV", csv_data, "unisat_telemetry.csv", "text/csv")
elif export_format == "JSON":
    json_data = sample_data.to_json(orient="records", indent=2, date_format="iso")
    st.download_button("⬇️ Download JSON", json_data, "unisat_telemetry.json", "application/json")
else:
    # CCSDS raw (simulated binary header + data)
    buffer = io.BytesIO()
    for _, row in sample_data.iterrows():
        header = bytes([0x08, 0x01, 0xC0, 0x00, 0x00, 0x20])  # CCSDS primary header
        data = row["battery_v"].to_bytes(4, "big", signed=False) if isinstance(row["battery_v"], int) else b"\x00" * 4
        buffer.write(header + b"\x00" * 10 + data)
    st.download_button("⬇️ Download CCSDS", buffer.getvalue(), "unisat_telemetry.ccsds", "application/octet-stream")
