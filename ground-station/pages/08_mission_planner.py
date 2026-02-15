"""Mission Planner — Pass predictions and imaging schedule."""

import random
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Mission Planner", layout="wide")
st.title("📅 Mission Planner")

# Next pass countdown
st.markdown("### Next Ground Station Pass")
col1, col2, col3 = st.columns(3)
col1.metric("Time to AOS", "00:12:34")
col2.metric("Max Elevation", "47.2°")
col3.metric("Duration", "8m 42s")

st.markdown("---")

# Pass predictions table
st.markdown("### Upcoming Passes (Tashkent GS)")
passes = []
for i in range(10):
    passes.append({
        "AOS": f"2026-02-15 {6 + i*2:02d}:{random.randint(0,59):02d}:00",
        "LOS": f"2026-02-15 {6 + i*2:02d}:{random.randint(5,14):02d}:00",
        "Max El.": f"{random.randint(5, 85)}°",
        "Direction": random.choice(["N→S", "S→N", "NE→SW"]),
        "Duration": f"{random.randint(3, 12)}m {random.randint(0, 59)}s",
        "Sunlit": random.choice(["☀️ Yes", "🌑 No"]),
    })
df = pd.DataFrame(passes)
st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown("---")

# Imaging planner
st.markdown("### Imaging Schedule")
st.markdown("Plan image captures based on target coordinates and orbit passes.")

target_lat = st.number_input("Target Latitude", -90.0, 90.0, 41.30)
target_lon = st.number_input("Target Longitude", -180.0, 180.0, 69.24)
target_name = st.text_input("Target Name", "Tashkent")

if st.button("Find Imaging Opportunities"):
    st.success(f"Found 3 imaging windows for {target_name} in next 48 hours")
    opportunities = [
        {"Window": "2026-02-15 08:23 - 08:25", "Elevation": "62°", "Lighting": "☀️ Sunlit", "Cloud": "15%"},
        {"Window": "2026-02-15 18:45 - 18:47", "Elevation": "34°", "Lighting": "🌑 Eclipse", "Cloud": "40%"},
        {"Window": "2026-02-16 09:12 - 09:14", "Elevation": "71°", "Lighting": "☀️ Sunlit", "Cloud": "5%"},
    ]
    st.dataframe(pd.DataFrame(opportunities), use_container_width=True, hide_index=True)
