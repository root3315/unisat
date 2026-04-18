"""UniSat Mission Configurator — Multi-platform web-based mission builder.

Supports CubeSat, CanSat, rocket, HAB, drone, and custom platforms.
Generates mission_config.json with the appropriate mission_type, phases,
and subsystem configuration for the selected platform and competition.
"""

import json
import streamlit as st

st.set_page_config(page_title="UniSat Configurator", layout="wide")
st.title("UniSat Mission Configurator")

# ---- Platform & Mission Type Selection ----

PLATFORM_OPTIONS = {
    "CubeSat": {
        "mission_types": ["cubesat_leo", "cubesat_sso", "cubesat_tech_demo"],
        # All CubeSat sizes supported as of v1.3.0 — including 1.5U.
        "form_factors": [
            "cubesat_1u", "cubesat_1_5u", "cubesat_2u",
            "cubesat_3u", "cubesat_6u", "cubesat_12u",
        ],
        "description": "Orbital CubeSat missions (LEO, SSO, ISS)",
    },
    "CanSat": {
        "mission_types": ["cansat_standard", "cansat_advanced"],
        "form_factors": ["cansat_minimal", "cansat_standard", "cansat_advanced"],
        "description": "CanSat competitions (ESERO, AAS, national)",
    },
    "Suborbital Rocket": {
        "mission_types": ["rocket_sounding", "rocket_competition"],
        "form_factors": ["rocket_payload"],
        "description": "Rocketry competitions (SA Cup, IREC, Team America)",
    },
    "High Altitude Balloon": {
        "mission_types": ["hab_standard", "hab_long_duration"],
        "form_factors": ["hab_payload"],
        "description": "HAB flights and competitions",
    },
    "Drone / UAV": {
        "mission_types": ["drone_survey", "drone_inspection"],
        "form_factors": ["drone_small"],
        "description": "UAV survey, inspection, and competition missions",
    },
    "Rover": {
        "mission_types": ["rover_survey"],
        "form_factors": ["rover_small"],
        "description": "Small ground rovers and exploration platforms",
    },
    "Custom": {
        "mission_types": ["custom"],
        "form_factors": ["custom"],
        "description": "User-defined platform and mission phases",
    },
}

st.markdown("### Platform Selection")
platform_name = st.selectbox(
    "Platform",
    list(PLATFORM_OPTIONS.keys()),
    index=0,
)
platform = PLATFORM_OPTIONS[platform_name]
st.caption(platform["description"])

col_mt, col_ff = st.columns(2)
mission_type = col_mt.selectbox("Mission Type", platform["mission_types"])
form_factor = col_ff.selectbox("Form Factor", platform["form_factors"])

# ---- Platform-specific configuration ----

st.markdown("---")

mission_name = st.text_input("Mission Name", "UniSat-1")

if platform_name == "CubeSat":
    st.markdown("### Orbit Configuration")
    c1, c2, c3 = st.columns(3)
    orbit_type = c1.selectbox("Orbit Type", ["LEO", "SSO", "ISS", "Custom"])
    altitude = c2.number_input("Altitude (km)", 200, 2000, 550)
    inclination = c3.number_input("Inclination (deg)", 0.0, 180.0, 97.6)
    show_orbit = True
else:
    show_orbit = False
    orbit_type = "N/A"
    altitude = 0
    inclination = 0.0

# ---- Subsystems (platform-aware) ----

st.markdown("### Subsystems")

PLATFORM_SUBSYSTEMS = {
    "CubeSat": {
        "obc": ("OBC (STM32F4)", True, True),
        "eps": ("EPS (Solar + Battery)", True, False),
        "comm_uhf": ("COMM UHF", True, False),
        "comm_sband": ("COMM S-band", True, False),
        "adcs": ("ADCS (Magnetorquers + Wheels)", True, False),
        "gnss": ("GNSS (u-blox)", True, False),
        "camera": ("Camera (8MP)", True, False),
        "payload": ("Payload Module", True, False),
    },
    "CanSat": {
        "obc": ("OBC (STM32F4)", True, True),
        "imu": ("IMU (Accelerometer + Gyro)", True, False),
        "barometer": ("Barometric Altimeter", True, False),
        "gnss": ("GNSS (u-blox)", True, False),
        "comm_uhf": ("COMM Radio (433/915 MHz)", True, False),
        "descent_controller": ("Descent Controller", True, False),
        "camera": ("Camera", False, False),
        "payload": ("Custom Payload", True, False),
    },
    "Suborbital Rocket": {
        "obc": ("OBC (STM32F4)", True, True),
        "imu": ("IMU (High-G)", True, False),
        "barometer": ("Barometric Altimeter", True, False),
        "gnss": ("GNSS (u-blox)", True, False),
        "comm_uhf": ("COMM Radio (915 MHz)", True, False),
        "camera": ("Camera", False, False),
        "payload": ("Experiment Payload", True, False),
    },
    "High Altitude Balloon": {
        "obc": ("OBC (STM32F4)", True, True),
        "barometer": ("Barometric Altimeter", True, False),
        "gnss": ("GNSS (u-blox)", True, False),
        "comm_uhf": ("COMM UHF / RTTY", True, False),
        "camera": ("Camera (Wide-angle)", True, False),
        "imu": ("IMU", False, False),
        "payload": ("Environmental Sensors", True, False),
    },
    "Drone / UAV": {
        "obc": ("OBC (STM32F4)", True, True),
        "imu": ("IMU (Flight Controller)", True, False),
        "barometer": ("Barometric Altimeter", True, False),
        "gnss": ("GNSS (u-blox)", True, False),
        "comm_uhf": ("COMM (2.4 GHz MAVLink)", True, False),
        "camera": ("Camera (Multispectral)", True, False),
        "payload": ("Survey Payload", True, False),
    },
    "Custom": {
        "obc": ("OBC (STM32F4)", True, True),
        "imu": ("IMU", False, False),
        "barometer": ("Barometric Altimeter", False, False),
        "eps": ("EPS (Solar + Battery)", False, False),
        "comm_uhf": ("COMM Radio", False, False),
        "adcs": ("ADCS", False, False),
        "gnss": ("GNSS", False, False),
        "camera": ("Camera", False, False),
        "descent_controller": ("Descent Controller", False, False),
        "payload": ("Payload Module", False, False),
    },
}

subsystem_defs = PLATFORM_SUBSYSTEMS.get(platform_name, PLATFORM_SUBSYSTEMS["Custom"])
enabled = {}
col1, col2 = st.columns(2)
items = list(subsystem_defs.items())
half = (len(items) + 1) // 2
for i, (key, (label, default_val, disabled)) in enumerate(items):
    col = col1 if i < half else col2
    enabled[key] = col.checkbox(label, value=default_val, disabled=disabled, key=f"sub_{key}")

# ---- Competition-specific settings ----

competition_config = {}
if platform_name == "CanSat":
    st.markdown("### CanSat Competition Settings")
    c1, c2, c3 = st.columns(3)
    competition_config["descent_rate_min"] = c1.number_input("Min descent rate (m/s)", 1.0, 20.0, 6.0)
    competition_config["descent_rate_max"] = c2.number_input("Max descent rate (m/s)", 1.0, 30.0, 11.0)
    competition_config["max_landing_velocity"] = c3.number_input("Max landing velocity (m/s)", 1.0, 30.0, 12.0)
    competition_config["deploy_altitude_m"] = st.number_input("Deploy altitude (m AGL)", 100, 2000, 500)

elif platform_name == "Suborbital Rocket":
    st.markdown("### Rocket Competition Settings")
    c1, c2 = st.columns(2)
    competition_config["target_altitude_m"] = c1.number_input("Target altitude (m)", 100, 30000, 3048)
    competition_config["dual_deploy"] = c2.checkbox("Dual deploy (drogue + main)", value=True)

elif platform_name == "High Altitude Balloon":
    st.markdown("### HAB Flight Settings")
    c1, c2 = st.columns(2)
    competition_config["target_altitude_m"] = c1.number_input("Target altitude (m)", 10000, 40000, 30000)
    competition_config["expected_ascent_rate"] = c2.number_input("Expected ascent rate (m/s)", 1.0, 10.0, 5.0)

elif platform_name == "Drone / UAV":
    st.markdown("### Drone Mission Settings")
    c1, c2, c3 = st.columns(3)
    competition_config["max_altitude_m"] = c1.number_input("Max altitude (m)", 10, 500, 120)
    competition_config["max_flight_time_min"] = c2.number_input("Max flight time (min)", 5, 120, 30)
    competition_config["geofence_radius_m"] = c3.number_input("Geofence radius (m)", 50, 5000, 500)

# ---- Budget Validation ----

st.markdown("---")
st.markdown("### Budget Validation")

from validators.mass_validator import validate_mass  # noqa: E402
from validators.volume_validator import validate_volume  # noqa: E402

mass_result = validate_mass(form_factor, enabled)
vol_result = validate_volume(form_factor, enabled)

c1, c2, c3 = st.columns(3)
c1.metric(
    "Mass",
    f"{mass_result.total_kg:.2f} kg",
    f"{'OK' if mass_result.valid else 'OVER'} (limit: {mass_result.limit_kg} kg)",
)
c2.metric(
    "Volume",
    f"{vol_result.total_cm3:.0f} cm3",
    f"{vol_result.utilization_pct:.0f}% used ({vol_result.available_cm3:.0f} cm3 avail)",
)
c3.metric("Platform", platform_name, f"Type: {mission_type}")

# ---- Config Generation ----

st.markdown("---")
if st.button("Generate mission_config.json", type="primary"):
    config: dict = {
        "mission": {
            "name": mission_name,
            "version": "1.0.0",
            "description": f"{platform_name} mission",
            "mission_type": mission_type,
            "platform": platform_name.lower().replace(" / ", "_").replace(" ", "_"),
            "operator": "Team Name",
            "telemetry_hz": {
                "CubeSat": 1.0, "CanSat": 10.0, "Suborbital Rocket": 20.0,
                "High Altitude Balloon": 0.5, "Drone / UAV": 10.0, "Custom": 1.0,
            }.get(platform_name, 1.0),
        },
        "satellite": {
            "form_factor": form_factor,
            "mass_kg": mass_result.total_kg,
        },
        "subsystems": {},
    }

    if show_orbit:
        config["orbit"] = {
            "type": orbit_type,
            "altitude_km": altitude,
            "inclination_deg": inclination,
        }

    for key, is_enabled in enabled.items():
        config["subsystems"][key] = {"enabled": is_enabled}

    if competition_config:
        config["mission"]["competition"] = competition_config

    st.json(config)
    st.download_button(
        "Download",
        json.dumps(config, indent=2),
        "mission_config.json",
        "application/json",
    )
