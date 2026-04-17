/**
 * @file test_stubs.c
 * @brief Subsystem stubs for isolated host tests.
 *
 * Provides minimal implementations of the OBC/EPS/ADCS/GNSS/Payload
 * interfaces so individual tests can link against telemetry.c + ccsds.c
 * without dragging in the full firmware (which has pre-existing host
 * build errors in gnss.c — out of scope for Track 1).
 */

#include "obc.h"
#include "eps.h"
#include "adcs.h"
#include "gnss.h"
#include "payload.h"
#include "comm.h"
#include "config.h"
#include <string.h>

/* ---- Global config (telemetry.c references `config.*.enabled`) ----- */

SystemConfig_t config = {
    .obc = { .enabled = true },
    .eps = { .enabled = true, .solar_panels = 6, .panel_efficiency = 0.295f,
             .battery_capacity_wh = 30.0f, .bus_voltage = 5.0f },
    .comm = { .enabled = true, .uhf_enabled = true, .sband_enabled = false },
    .adcs = { .enabled = true, .magnetorquers = 3, .reaction_wheels = 3,
              .sun_sensors = 6 },
    .gnss = { .enabled = true },
    .camera = { .enabled = false },
    .payload = { .enabled = false },
};

/* ---- COMM (only COMM_Send needed by Telemetry_SendPacket) ---------- */

bool COMM_Send(CommChannel_t ch, const uint8_t *data, uint16_t len) {
    (void)ch; (void)data; (void)len;
    return true;
}

/* ---- ADCS ---------------------------------------------------------- */

/* Default to identity quaternion so tests that don't explicitly call
 * ADCS_Init still observe a non-trivial attitude. The minimal Unity
 * framework in this repo does not invoke setUp/tearDown. */
static ADCS_Status_t s_adcs = {
    .mode = ADCS_MODE_IDLE,
    .quaternion = { 1.0f, 0.0f, 0.0f, 0.0f },
};

void ADCS_Init(void) {
    memset(&s_adcs, 0, sizeof(s_adcs));
    s_adcs.mode = ADCS_MODE_IDLE;
    s_adcs.quaternion[0] = 1.0f;
}
ADCS_Status_t ADCS_GetStatus(void) { return s_adcs; }
void ADCS_SetMode(ADCS_Mode_t mode) { s_adcs.mode = mode; }
ADCS_Mode_t ADCS_GetMode(void) { return s_adcs.mode; }
void ADCS_SetTarget(ADCS_Target_t t) { (void)t; }
void ADCS_Update(const float mag[3], const float gyro[3],
                 const float accel[3], const uint16_t sun[6]) {
    (void)mag; (void)gyro; (void)accel; (void)sun;
}
float ADCS_GetPointingError(void) { return s_adcs.pointing_error_deg; }
void ADCS_SetMagnetorquerDutyCycle(uint8_t axis, float duty) {
    (void)axis; (void)duty;
}
void ADCS_SetWheelSpeed(uint8_t axis, float rpm) { (void)axis; (void)rpm; }
void ADCS_Desaturate(void) {}

/* ---- OBC ----------------------------------------------------------- */

void OBC_Init(void) {}
OBC_Status_t OBC_GetStatus(void) {
    OBC_Status_t s = {0};
    s.uptime_seconds = 12345;
    s.reset_count = 1;
    s.cpu_temperature = 25.0f;
    s.free_heap = 32768;
    s.current_state = 0;
    s.error_count = 0;
    return s;
}
void OBC_UpdateUptime(void) {}
float OBC_ReadCpuTemperature(void) { return 25.0f; }
uint32_t OBC_GetFreeHeap(void) { return 32768; }
uint32_t OBC_GetResetCount(void) { return 1; }
void OBC_SoftwareReset(void) {}
void OBC_EnterLowPower(void) {}
void OBC_BackupWrite(uint32_t addr, uint32_t data) { (void)addr; (void)data; }
uint32_t OBC_BackupRead(uint32_t addr) { (void)addr; return 0; }

/* ---- EPS ----------------------------------------------------------- */

void EPS_Init(void) {}
EPS_Status_t EPS_GetStatus(void) {
    EPS_Status_t s = {0};
    s.battery_voltage = 3.7f;
    s.battery_current = 0.5f;
    s.battery_soc = 80.0f;
    s.solar_voltage = 4.2f;
    s.solar_current = 0.6f;
    s.solar_power = 2.5f;
    s.bus_voltage = 5.0f;
    s.total_consumption = 1.2f;
    return s;
}
float EPS_ReadBatteryVoltage(void) { return 3.7f; }
float EPS_ReadBatteryCurrent(void) { return 0.5f; }
float EPS_ReadSolarVoltage(void) { return 4.2f; }
float EPS_ReadSolarCurrent(void) { return 0.6f; }
float EPS_GetBatterySOC(void) { return 80.0f; }
void EPS_EnableSubsystem(PowerSubsystem_t s) { (void)s; }
void EPS_DisableSubsystem(PowerSubsystem_t s) { (void)s; }
bool EPS_IsSubsystemEnabled(PowerSubsystem_t s) { (void)s; return true; }
void EPS_EmergencyShutdown(void) {}
void EPS_Update(void) {}

/* ---- GNSS ---------------------------------------------------------- */

void GNSS_Init(void) {}
GNSS_Data_t GNSS_GetFullData(void) {
    GNSS_Data_t d = {0};
    d.latitude = 43.2351;
    d.longitude = 76.9091;
    d.altitude = 500.0;
    d.satellites = 8;
    d.fix_type = GNSS_FIX_3D;
    return d;
}
bool GNSS_GetPosition(double *lat, double *lon, double *alt, uint8_t *fix) {
    if (lat) *lat = 43.2351;
    if (lon) *lon = 76.9091;
    if (alt) *alt = 500.0;
    if (fix) *fix = GNSS_FIX_3D;
    return true;
}
bool GNSS_GetVelocity(float *vx, float *vy, float *vz) {
    if (vx) *vx = 0.0f;
    if (vy) *vy = 0.0f;
    if (vz) *vz = 0.0f;
    return true;
}
uint8_t GNSS_GetSatelliteCount(void) { return 8; }
bool GNSS_HasFix(void) { return true; }
void GNSS_ProcessNMEA(const char *s) { (void)s; }
void GNSS_Update(void) {}

/* ---- Payload ------------------------------------------------------- */

void Payload_Init(PayloadType_t t) { (void)t; }
Payload_Status_t Payload_GetStatus(void) {
    Payload_Status_t s = {0};
    return s;
}
bool Payload_Activate(void) { return true; }
void Payload_Deactivate(void) {}
uint16_t Payload_ReadData(uint8_t *buf, uint16_t max) {
    (void)buf; (void)max;
    return 0;
}
void Payload_ProcessCommand(const uint8_t *cmd, uint16_t n) {
    (void)cmd; (void)n;
}
void Payload_Update(void) {}
