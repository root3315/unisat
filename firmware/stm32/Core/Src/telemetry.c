/**
 * @file telemetry.c
 * @brief Telemetry collection and CCSDS packet formation
 */

#include "telemetry.h"
#include "obc.h"
#include "eps.h"
#include "adcs.h"
#include "gnss.h"
#include "comm.h"
#include "payload.h"
#include "config.h"
#include "board_temp.h"
#include <string.h>
#include <math.h>

static uint32_t packet_count = 0;

void Telemetry_Init(void) {
    packet_count = 0;
}

uint16_t Telemetry_PackOBC(uint8_t *buffer, uint16_t max_size) {
    OBC_Status_t status = OBC_GetStatus();
    uint8_t data[24];
    uint16_t offset = 0;

    memcpy(&data[offset], &status.uptime_seconds, 4); offset += 4;
    memcpy(&data[offset], &status.reset_count, 4); offset += 4;
    memcpy(&data[offset], &status.cpu_temperature, 4); offset += 4;
    memcpy(&data[offset], &status.free_heap, 4); offset += 4;
    data[offset++] = status.current_state;
    memcpy(&data[offset], &status.error_count, 2); offset += 2;

    CCSDS_Packet_t packet;
    CCSDS_BuildPacket(&packet, APID_OBC_HOUSEKEEPING, CCSDS_TELEMETRY,
                       0, data, offset);
    return CCSDS_Serialize(&packet, buffer, max_size);
}

uint16_t Telemetry_PackEPS(uint8_t *buffer, uint16_t max_size) {
    EPS_Status_t status = EPS_GetStatus();
    uint8_t data[36];
    uint16_t offset = 0;

    memcpy(&data[offset], &status.battery_voltage, 4); offset += 4;
    memcpy(&data[offset], &status.battery_current, 4); offset += 4;
    memcpy(&data[offset], &status.battery_soc, 4); offset += 4;
    memcpy(&data[offset], &status.solar_voltage, 4); offset += 4;
    memcpy(&data[offset], &status.solar_current, 4); offset += 4;
    memcpy(&data[offset], &status.solar_power, 4); offset += 4;
    memcpy(&data[offset], &status.bus_voltage, 4); offset += 4;
    memcpy(&data[offset], &status.total_consumption, 4); offset += 4;

    CCSDS_Packet_t packet;
    CCSDS_BuildPacket(&packet, APID_EPS_TELEMETRY, CCSDS_TELEMETRY,
                       1, data, offset);
    return CCSDS_Serialize(&packet, buffer, max_size);
}

uint16_t Telemetry_PackADCS(uint8_t *buffer, uint16_t max_size) {
    ADCS_Status_t status = ADCS_GetStatus();
    uint8_t data[40];
    uint16_t offset = 0;

    data[offset++] = (uint8_t)status.mode;
    memcpy(&data[offset], status.quaternion, 16); offset += 16;
    memcpy(&data[offset], status.angular_rate, 12); offset += 12;
    memcpy(&data[offset], &status.pointing_error_deg, 4); offset += 4;
    data[offset++] = status.magnetorquers_active ? 1 : 0;
    data[offset++] = status.reaction_wheels_active ? 1 : 0;

    CCSDS_Packet_t packet;
    CCSDS_BuildPacket(&packet, APID_ADCS_ATTITUDE, CCSDS_TELEMETRY,
                       3, data, offset);
    return CCSDS_Serialize(&packet, buffer, max_size);
}

uint16_t Telemetry_PackGNSS(uint8_t *buffer, uint16_t max_size) {
    GNSS_Data_t gnss = GNSS_GetFullData();
    uint8_t data[44];
    uint16_t offset = 0;

    memcpy(&data[offset], &gnss.latitude, 8); offset += 8;
    memcpy(&data[offset], &gnss.longitude, 8); offset += 8;
    memcpy(&data[offset], &gnss.altitude, 8); offset += 8;
    memcpy(&data[offset], &gnss.velocity_x, 4); offset += 4;
    memcpy(&data[offset], &gnss.velocity_y, 4); offset += 4;
    memcpy(&data[offset], &gnss.velocity_z, 4); offset += 4;
    data[offset++] = gnss.satellites;
    data[offset++] = (uint8_t)gnss.fix_type;

    CCSDS_Packet_t packet;
    CCSDS_BuildPacket(&packet, APID_GNSS_POSITION, CCSDS_TELEMETRY,
                       4, data, offset);
    return CCSDS_Serialize(&packet, buffer, max_size);
}

uint16_t Telemetry_PackPayload(uint8_t *buffer, uint16_t max_size) {
    uint8_t payload_data[PAYLOAD_DATA_MAX_SIZE];
    uint16_t data_len = Payload_ReadData(payload_data, PAYLOAD_DATA_MAX_SIZE);

    CCSDS_Packet_t packet;
    CCSDS_BuildPacket(&packet, APID_PAYLOAD_DATA, CCSDS_TELEMETRY,
                       6, payload_data, data_len);
    return CCSDS_Serialize(&packet, buffer, max_size);
}

uint16_t Telemetry_PackBeaconCcsds(uint8_t *buffer, uint16_t max_size) {
    uint8_t data[16];
    uint16_t offset = 0;

    OBC_Status_t obc = OBC_GetStatus();
    EPS_Status_t eps = EPS_GetStatus();

    data[offset++] = obc.current_state;
    memcpy(&data[offset], &obc.uptime_seconds, 4); offset += 4;
    memcpy(&data[offset], &eps.battery_voltage, 4); offset += 4;
    memcpy(&data[offset], &eps.battery_soc, 4); offset += 4;
    data[offset++] = GNSS_GetSatelliteCount();
    data[offset++] = (uint8_t)ADCS_GetMode();

    CCSDS_Packet_t packet;
    CCSDS_BuildPacket(&packet, APID_BEACON, CCSDS_TELEMETRY,
                       0xFF, data, offset);
    return CCSDS_Serialize(&packet, buffer, max_size);
}

uint16_t Telemetry_PackBeacon(uint8_t *buffer, uint16_t max_size) {
    static uint16_t seq = 0;

    if (max_size < 48) return 0;

    OBC_Status_t obc  = OBC_GetStatus();
    EPS_Status_t eps  = EPS_GetStatus();
    ADCS_Status_t adcs = ADCS_GetStatus();
    GNSS_Data_t gnss  = GNSS_GetFullData();

    /* Encode EPS scalars to integer units */
    uint16_t vbat_mv  = (uint16_t)(eps.battery_voltage * 1000.0f);
    int16_t  ibat_ma  = (int16_t)(eps.battery_current * 1000.0f);
    uint8_t  soc      = (uint8_t)eps.battery_soc;
    uint16_t psol_mw  = (uint16_t)(eps.solar_power * 1000.0f);

    /* OBC temperatures in 0.1 °C units.
     *   tcpu   — die-temperature from the internal ADC channel.
     *   tboard — PCB-level temperature read from the TMP117 via the
     *            BoardTemp facade (Phase 4). Returns 0 when the
     *            sensor hasn't yet produced a valid reading, which
     *            happens only in the first 1 s after boot before
     *            SensorTask has polled the bus. */
    int16_t tcpu    = (int16_t)(obc.cpu_temperature * 10.0f);
    int16_t tboard  = BoardTemp_GetScaled0p1();

    /* ADCS angular-rate magnitude: rad/s → 0.01 deg/s */
    float wx = adcs.angular_rate[0];
    float wy = adcs.angular_rate[1];
    float wz = adcs.angular_rate[2];
    float omega_deg_s = sqrtf(wx*wx + wy*wy + wz*wz) * 57.2957795f;
    uint16_t omega = (uint16_t)(omega_deg_s * 100.0f);

    /* GNSS position scaled to integer units */
    int32_t  lat_1e7 = (int32_t)(gnss.latitude  * 1e7);
    int32_t  lon_1e7 = (int32_t)(gnss.longitude * 1e7);
    uint16_t alt_m   = (uint16_t)gnss.altitude;

    uint8_t fix  = (uint8_t)gnss.fix_type;
    uint8_t errs = (uint8_t)(obc.error_count & 0xFF);

    /* Write 48-byte layout per communication_protocol.md §7.2 */
    uint16_t off = 0;

    /* Bytes 0-3: uptime (u32, sec) */
    memcpy(&buffer[off], &obc.uptime_seconds, 4); off += 4;

    /* Byte 4: mode (u8, enum) */
    buffer[off++] = (uint8_t)adcs.mode;

    /* Bytes 5-6: Vbat (u16, mV) */
    memcpy(&buffer[off], &vbat_mv, 2); off += 2;

    /* Bytes 7-8: Ibat (i16, mA) */
    memcpy(&buffer[off], &ibat_ma, 2); off += 2;

    /* Byte 9: SOC (u8, %) */
    buffer[off++] = soc;

    /* Bytes 10-11: Psol (u16, mW) */
    memcpy(&buffer[off], &psol_mw, 2); off += 2;

    /* Bytes 12-13: Tcpu (i16, 0.1 °C) */
    memcpy(&buffer[off], &tcpu, 2); off += 2;

    /* Bytes 14-15: Tboard (i16, 0.1 °C) */
    memcpy(&buffer[off], &tboard, 2); off += 2;

    /* Bytes 16-19: Qw (f32) */
    memcpy(&buffer[off], &adcs.quaternion[0], 4); off += 4;

    /* Bytes 20-23: Qx (f32) */
    memcpy(&buffer[off], &adcs.quaternion[1], 4); off += 4;

    /* Bytes 24-27: Qy (f32) */
    memcpy(&buffer[off], &adcs.quaternion[2], 4); off += 4;

    /* Bytes 28-31: Qz (f32) */
    memcpy(&buffer[off], &adcs.quaternion[3], 4); off += 4;

    /* Bytes 32-33: Omega (u16, 0.01 deg/s) */
    memcpy(&buffer[off], &omega, 2); off += 2;

    /* Bytes 34-37: Lat (i32, 1e-7 deg) */
    memcpy(&buffer[off], &lat_1e7, 4); off += 4;

    /* Bytes 38-41: Lon (i32, 1e-7 deg) */
    memcpy(&buffer[off], &lon_1e7, 4); off += 4;

    /* Bytes 42-43: Alt (u16, m) */
    memcpy(&buffer[off], &alt_m, 2); off += 2;

    /* Byte 44: Fix (u8, enum) */
    buffer[off++] = fix;

    /* Byte 45: Errs (u8, count) */
    buffer[off++] = errs;

    /* Bytes 46-47: SeqCnt (u16, count) */
    memcpy(&buffer[off], &seq, 2); off += 2;

    seq++;
    return off; /* must be 48 */
}

uint16_t Telemetry_PackError(uint8_t *buffer, uint16_t max_size,
                              uint8_t error_code, const char *message) {
    uint8_t data[36];
    uint16_t offset = 0;

    data[offset++] = error_code;
    size_t raw_len = strlen(message);
    if (raw_len > 34U) { raw_len = 34U; }
    uint16_t msg_len = (uint16_t)raw_len;
    data[offset++] = (uint8_t)msg_len;
    memcpy(&data[offset], message, msg_len);
    offset = (uint16_t)(offset + msg_len);

    CCSDS_Packet_t packet;
    CCSDS_BuildPacket(&packet, APID_ERROR_REPORT, CCSDS_TELEMETRY,
                       0x10, data, offset);
    return CCSDS_Serialize(&packet, buffer, max_size);
}

bool Telemetry_SendPacket(TelemetryType_t type) {
    uint8_t buffer[CCSDS_MAX_PACKET_SIZE];
    uint16_t len = 0;

    switch (type) {
        case TLM_OBC_HOUSEKEEPING: len = Telemetry_PackOBC(buffer, sizeof(buffer)); break;
        case TLM_EPS:              len = Telemetry_PackEPS(buffer, sizeof(buffer)); break;
        case TLM_ADCS:             len = Telemetry_PackADCS(buffer, sizeof(buffer)); break;
        case TLM_GNSS:             len = Telemetry_PackGNSS(buffer, sizeof(buffer)); break;
        case TLM_PAYLOAD:          len = Telemetry_PackPayload(buffer, sizeof(buffer)); break;
        case TLM_BEACON:           len = Telemetry_PackBeaconCcsds(buffer, sizeof(buffer)); break;
        default: return false;
    }

    if (len == 0) return false;

    bool ok = COMM_Send(COMM_CHANNEL_UHF, buffer, len);
    if (ok) packet_count++;
    return ok;
}

void Telemetry_SendAllHousekeeping(void) {
    Telemetry_SendPacket(TLM_OBC_HOUSEKEEPING);
    Telemetry_SendPacket(TLM_EPS);
    if (config.adcs.enabled) Telemetry_SendPacket(TLM_ADCS);
    if (config.gnss.enabled) Telemetry_SendPacket(TLM_GNSS);
    if (config.payload.enabled) Telemetry_SendPacket(TLM_PAYLOAD);
}

uint32_t Telemetry_GetPacketCount(void) {
    return packet_count;
}
