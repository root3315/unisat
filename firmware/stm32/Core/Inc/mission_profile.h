/**
 * @file mission_profile.h
 * @brief Compile-time mission-profile selector — universal platform support.
 *
 * One STM32 firmware image is built per mission profile. The profile is
 * chosen through -DMISSION_PROFILE_<NAME>=1 on the compiler command line
 * (or by editing the default macro below). Everything else in the
 * firmware (driver inclusion, FDIR policy, telemetry rates) is gated by
 * the PROFILE_* feature flags this header exposes.
 *
 * Supported profiles:
 *   CANSAT_MINIMAL     — ≤350 g telemetry-only CanSat
 *   CANSAT_STANDARD    — ≤500 g CanSat (CDS Ø68 mm)
 *   CANSAT_ADVANCED    — ≤500 g CanSat with pyro + camera
 *   CUBESAT_1U         — 1U amateur-class, UHF beacon
 *   CUBESAT_1_5U       — 1.5U UHF + magnetorquer
 *   CUBESAT_2U         — 2U UHF + payload + coarse pointing
 *   CUBESAT_3U         — 3U LEO workhorse (reference)
 *   CUBESAT_6U         — 6U X-band, fine pointing
 *   CUBESAT_12U        — 12U research-class with propulsion
 *
 * Exactly one MISSION_PROFILE_<NAME> macro must evaluate truthy. If none
 * is defined on the command line, the default is CUBESAT_3U for
 * backwards compatibility with the previous single-profile build.
 *
 * The feature flags intentionally mirror the Python resolver in
 * flight-software/core/feature_flags.py so both sides of the system
 * come up consistent.
 */

#ifndef MISSION_PROFILE_H
#define MISSION_PROFILE_H

/* --- Default profile (3U LEO) ------------------------------------------ */

#if !defined(MISSION_PROFILE_CANSAT_MINIMAL) \
 && !defined(MISSION_PROFILE_CANSAT_STANDARD) \
 && !defined(MISSION_PROFILE_CANSAT_ADVANCED) \
 && !defined(MISSION_PROFILE_CUBESAT_1U) \
 && !defined(MISSION_PROFILE_CUBESAT_1_5U) \
 && !defined(MISSION_PROFILE_CUBESAT_2U) \
 && !defined(MISSION_PROFILE_CUBESAT_3U) \
 && !defined(MISSION_PROFILE_CUBESAT_6U) \
 && !defined(MISSION_PROFILE_CUBESAT_12U)
#define MISSION_PROFILE_CUBESAT_3U 1
#endif

/* --- Platform category -------------------------------------------------- */

#if defined(MISSION_PROFILE_CANSAT_MINIMAL) \
 || defined(MISSION_PROFILE_CANSAT_STANDARD) \
 || defined(MISSION_PROFILE_CANSAT_ADVANCED)
#define PROFILE_PLATFORM_CANSAT   1
#define PROFILE_PLATFORM_CUBESAT  0
#else
#define PROFILE_PLATFORM_CANSAT   0
#define PROFILE_PLATFORM_CUBESAT  1
#endif

/* --- Capability flags — orbital / attitude ----------------------------- */

#if PROFILE_PLATFORM_CUBESAT
#define PROFILE_FEATURE_ORBIT_PREDICTOR   1
#define PROFILE_FEATURE_SOLAR_PANELS      1
#define PROFILE_FEATURE_ECLIPSE_FDIR      1
#define PROFILE_FEATURE_MAGNETORQUERS     \
    (defined(MISSION_PROFILE_CUBESAT_1_5U) \
     || defined(MISSION_PROFILE_CUBESAT_2U) \
     || defined(MISSION_PROFILE_CUBESAT_3U) \
     || defined(MISSION_PROFILE_CUBESAT_6U) \
     || defined(MISSION_PROFILE_CUBESAT_12U))
#define PROFILE_FEATURE_REACTION_WHEELS   \
    (defined(MISSION_PROFILE_CUBESAT_3U) \
     || defined(MISSION_PROFILE_CUBESAT_6U) \
     || defined(MISSION_PROFILE_CUBESAT_12U))
#define PROFILE_FEATURE_STAR_TRACKER      \
    (defined(MISSION_PROFILE_CUBESAT_6U) \
     || defined(MISSION_PROFILE_CUBESAT_12U))
#define PROFILE_FEATURE_PROPULSION        defined(MISSION_PROFILE_CUBESAT_12U)
#else /* CanSat */
#define PROFILE_FEATURE_ORBIT_PREDICTOR   0
#define PROFILE_FEATURE_SOLAR_PANELS      0
#define PROFILE_FEATURE_ECLIPSE_FDIR      0
#define PROFILE_FEATURE_MAGNETORQUERS     0
#define PROFILE_FEATURE_REACTION_WHEELS   0
#define PROFILE_FEATURE_STAR_TRACKER      0
#define PROFILE_FEATURE_PROPULSION        0
#endif

/* --- Capability flags — descent / suborbital --------------------------- */

#define PROFILE_FEATURE_DESCENT_CONTROLLER PROFILE_PLATFORM_CANSAT
#define PROFILE_FEATURE_BAROMETER          PROFILE_PLATFORM_CANSAT

#if defined(MISSION_PROFILE_CANSAT_STANDARD) || \
    defined(MISSION_PROFILE_CANSAT_ADVANCED)
#define PROFILE_FEATURE_PARACHUTE_PYRO     1
#else
#define PROFILE_FEATURE_PARACHUTE_PYRO     0
#endif

/* --- Capability flags — radios ----------------------------------------- */

#define PROFILE_FEATURE_UHF_RADIO         1   /* every profile has UHF */

#if defined(MISSION_PROFILE_CUBESAT_3U) || \
    defined(MISSION_PROFILE_CUBESAT_6U) || \
    defined(MISSION_PROFILE_CUBESAT_12U)
#define PROFILE_FEATURE_S_BAND_RADIO      1
#else
#define PROFILE_FEATURE_S_BAND_RADIO      0
#endif

#if defined(MISSION_PROFILE_CUBESAT_6U) || \
    defined(MISSION_PROFILE_CUBESAT_12U)
#define PROFILE_FEATURE_X_BAND_RADIO      1
#else
#define PROFILE_FEATURE_X_BAND_RADIO      0
#endif

#if defined(MISSION_PROFILE_CUBESAT_12U)
#define PROFILE_FEATURE_KA_BAND_RADIO     1
#else
#define PROFILE_FEATURE_KA_BAND_RADIO     0
#endif

/* --- Capability flags — imaging / payload ------------------------------ */

#if defined(MISSION_PROFILE_CANSAT_ADVANCED) || \
    defined(MISSION_PROFILE_CUBESAT_1_5U) || \
    defined(MISSION_PROFILE_CUBESAT_2U) || \
    defined(MISSION_PROFILE_CUBESAT_3U) || \
    defined(MISSION_PROFILE_CUBESAT_6U) || \
    defined(MISSION_PROFILE_CUBESAT_12U)
#define PROFILE_FEATURE_CAMERA            1
#else
#define PROFILE_FEATURE_CAMERA            0
#endif

/* --- Capability flags — navigation ------------------------------------- */

#define PROFILE_FEATURE_IMU               1  /* everyone carries an IMU */

#if defined(MISSION_PROFILE_CANSAT_MINIMAL)
#define PROFILE_FEATURE_GNSS              0
#elif defined(MISSION_PROFILE_CUBESAT_1U)
#define PROFILE_FEATURE_GNSS              0
#else
#define PROFILE_FEATURE_GNSS              1
#endif

/* --- Telemetry defaults per profile ------------------------------------ */

#if defined(MISSION_PROFILE_CANSAT_MINIMAL)
#define PROFILE_TELEMETRY_HZ              4.0f
#elif defined(MISSION_PROFILE_CANSAT_STANDARD)
#define PROFILE_TELEMETRY_HZ              10.0f
#elif defined(MISSION_PROFILE_CANSAT_ADVANCED)
#define PROFILE_TELEMETRY_HZ              20.0f
#elif defined(MISSION_PROFILE_CUBESAT_1U)
#define PROFILE_TELEMETRY_HZ              0.2f
#elif defined(MISSION_PROFILE_CUBESAT_1_5U)
#define PROFILE_TELEMETRY_HZ              0.5f
#elif defined(MISSION_PROFILE_CUBESAT_2U)
#define PROFILE_TELEMETRY_HZ              0.5f
#elif defined(MISSION_PROFILE_CUBESAT_3U)
#define PROFILE_TELEMETRY_HZ              1.0f
#elif defined(MISSION_PROFILE_CUBESAT_6U)
#define PROFILE_TELEMETRY_HZ              2.0f
#elif defined(MISSION_PROFILE_CUBESAT_12U)
#define PROFILE_TELEMETRY_HZ              5.0f
#else
#define PROFILE_TELEMETRY_HZ              1.0f
#endif

/* --- FDIR timing per platform ----------------------------------------- */

#if PROFILE_PLATFORM_CANSAT
#define PROFILE_FDIR_COMM_TIMEOUT_S       300u     /* 5 min for short flights */
#define PROFILE_FDIR_BEACON_INTERVAL_S    5u
#else
#define PROFILE_FDIR_COMM_TIMEOUT_S       86400u   /* 24 h for LEO */
#define PROFILE_FDIR_BEACON_INTERVAL_S    30u
#endif

/* --- Profile string for diagnostics ----------------------------------- */

#if defined(MISSION_PROFILE_CANSAT_MINIMAL)
#define PROFILE_NAME "cansat_minimal"
#elif defined(MISSION_PROFILE_CANSAT_STANDARD)
#define PROFILE_NAME "cansat_standard"
#elif defined(MISSION_PROFILE_CANSAT_ADVANCED)
#define PROFILE_NAME "cansat_advanced"
#elif defined(MISSION_PROFILE_CUBESAT_1U)
#define PROFILE_NAME "cubesat_1u"
#elif defined(MISSION_PROFILE_CUBESAT_1_5U)
#define PROFILE_NAME "cubesat_1_5u"
#elif defined(MISSION_PROFILE_CUBESAT_2U)
#define PROFILE_NAME "cubesat_2u"
#elif defined(MISSION_PROFILE_CUBESAT_3U)
#define PROFILE_NAME "cubesat_3u"
#elif defined(MISSION_PROFILE_CUBESAT_6U)
#define PROFILE_NAME "cubesat_6u"
#elif defined(MISSION_PROFILE_CUBESAT_12U)
#define PROFILE_NAME "cubesat_12u"
#else
#define PROFILE_NAME "unknown"
#endif

#endif /* MISSION_PROFILE_H */
