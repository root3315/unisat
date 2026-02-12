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
#include <string.h>

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

uint16_t Telemetry_PackBeacon(uint8_t *buffer, uint16_t max_size) {
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

uint16_t Telemetry_PackError(uint8_t *buffer, uint16_t max_size,
                              uint8_t error_code, const char *message) {
    uint8_t data[36];
    uint16_t offset = 0;

    data[offset++] = error_code;
    uint16_t msg_len = strlen(message);
    if (msg_len > 34) msg_len = 34;
    data[offset++] = (uint8_t)msg_len;
    memcpy(&data[offset], message, msg_len);
    offset += msg_len;

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
        case TLM_BEACON:           len = Telemetry_PackBeacon(buffer, sizeof(buffer)); break;
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
