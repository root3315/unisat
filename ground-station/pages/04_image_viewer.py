"""Image Viewer — Earth observation gallery with geolocation."""

import random
import streamlit as st
import numpy as np

st.set_page_config(page_title="Image Viewer", layout="wide")
st.title("🖼️ Image Viewer")

# Demo image metadata
images = []
for i in range(12):
    images.append({
        "id": f"IMG_{8400 + i:04d}",
        "timestamp": f"2026-02-14 {10 + i}:{random.randint(0,59):02d}:00",
        "lat": round(random.uniform(-60, 60), 4),
        "lon": round(random.uniform(-180, 180), 4),
        "alt_km": 550.0,
        "gsd_m": 30,
        "size_kb": random.randint(200, 800),
        "bands": "R,G,B,NIR",
        "compressed": True,
        "svd_rank": 50,
    })

st.markdown(f"### {len(images)} images captured")

# Gallery grid
cols = st.columns(4)
for idx, img in enumerate(images):
    with cols[idx % 4]:
        # Generate colored placeholder
        color = [random.randint(30, 100), random.randint(80, 150), random.randint(30, 80)]
        arr = np.full((120, 160, 3), color, dtype=np.uint8)
        arr += np.random.randint(0, 30, arr.shape, dtype=np.uint8)
        st.image(arr, caption=img["id"], use_container_width=True)
        st.caption(f"📍 {img['lat']:.2f}, {img['lon']:.2f}")
        st.caption(f"📅 {img['timestamp']}")

# Selected image details
st.markdown("---")
st.markdown("### Image Details")
selected = st.selectbox("Select image", [img["id"] for img in images])
img_data = next(i for i in images if i["id"] == selected)

col1, col2 = st.columns(2)
with col1:
    st.json(img_data)
with col2:
    st.markdown(f"**Resolution:** {img_data['gsd_m']}m GSD")
    st.markdown(f"**Bands:** {img_data['bands']}")
    st.markdown(f"**SVD Rank:** k={img_data['svd_rank']}")
    st.markdown(f"**Size:** {img_data['size_kb']} KB")
