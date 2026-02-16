"""UniSat Mission Configurator — Web-based mission builder."""

import json
import streamlit as st

st.set_page_config(page_title="UniSat Configurator", layout="wide")
st.title("🔧 UniSat Mission Configurator")

# Form factor
form_factor = st.selectbox("Form Factor", ["1U", "2U", "3U", "6U"], index=2)
mass_limits = {"1U": 1.33, "2U": 2.66, "3U": 4.0, "6U": 12.0}
panel_counts = {"1U": 4, "2U": 4, "3U": 6, "6U": 8}

# Orbit
st.markdown("### Orbit Configuration")
c1, c2, c3 = st.columns(3)
orbit_type = c1.selectbox("Orbit Type", ["LEO", "SSO", "ISS", "Custom"])
altitude = c2.number_input("Altitude (km)", 200, 2000, 550)
inclination = c3.number_input("Inclination (°)", 0.0, 180.0, 97.6)

# Subsystems
st.markdown("### Subsystems")
col1, col2 = st.columns(2)
with col1:
    obc = st.checkbox("OBC (STM32F4)", value=True, disabled=True)
    eps = st.checkbox("EPS (Solar + Battery)", value=True)
    comm_uhf = st.checkbox("COMM UHF (437 MHz)", value=True)
    comm_sband = st.checkbox("COMM S-band (2.4 GHz)", value=True)
with col2:
    adcs = st.checkbox("ADCS (Magnetorquers + Wheels)", value=True)
    gnss = st.checkbox("GNSS (u-blox)", value=True)
    camera = st.checkbox("Camera (8MP)", value=True)
    payload = st.checkbox("Payload Module", value=True)

# Validation
st.markdown("---")
st.markdown("### Budget Validation")

mass_items = {"OBC": 0.15, "EPS": 0.8, "COMM": 0.2, "ADCS": 0.6,
              "GNSS": 0.05, "Camera": 0.3, "Payload": 0.2, "Structure": 0.5}
total_mass = sum(mass_items.values())
mass_limit = mass_limits[form_factor]

c1, c2, c3 = st.columns(3)
mass_ok = total_mass <= mass_limit
c1.metric("Total Mass", f"{total_mass:.2f} kg",
          f"{'OK' if mass_ok else 'OVER'} (limit: {mass_limit} kg)")

power_gen = panel_counts[form_factor] * 0.06 * 1361 * 0.295 * 0.5
power_use = 3.5
power_ok = power_gen > power_use
c2.metric("Power Balance", f"+{power_gen - power_use:.1f} W",
          f"Gen: {power_gen:.1f}W, Use: {power_use:.1f}W")

c3.metric("Form Factor", form_factor, f"{panel_counts[form_factor]} panels")

# Generate config
if st.button("Generate mission_config.json", type="primary"):
    config = {
        "mission": {"name": "UniSat-1", "version": "1.0.0"},
        "satellite": {"form_factor": form_factor, "mass_kg": total_mass},
        "orbit": {"type": orbit_type, "altitude_km": altitude,
                  "inclination_deg": inclination},
        "subsystems": {
            "obc": {"enabled": True}, "eps": {"enabled": eps},
            "comm": {"enabled": comm_uhf, "uhf": {"enabled": comm_uhf},
                     "s_band": {"enabled": comm_sband}},
            "adcs": {"enabled": adcs}, "gnss": {"enabled": gnss},
            "camera": {"enabled": camera}, "payload": {"enabled": payload},
        },
    }
    st.json(config)
    st.download_button("Download", json.dumps(config, indent=2),
                       "mission_config.json", "application/json")
