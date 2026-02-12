/**
 * @file ccsds.c
 * @brief CCSDS Space Packet Protocol implementation
 */

#include "ccsds.h"
#include <string.h>

static uint16_t sequence_count = 0;

/** CRC-16/CCITT lookup table */
static const uint16_t crc16_table[256] = {
    0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50A5, 0x60C6, 0x70E7,
    0x8108, 0x9129, 0xA14A, 0xB16B, 0xC18C, 0xD1AD, 0xE1CE, 0xF1EF,
    0x1231, 0x0210, 0x3273, 0x2252, 0x52B5, 0x4294, 0x72F7, 0x62D6,
    0x9339, 0x8318, 0xB37B, 0xA35A, 0xD3BD, 0xC39C, 0xF3FF, 0xE3DE,
    0x2462, 0x3443, 0x0420, 0x1401, 0x64E6, 0x74C7, 0x44A4, 0x5485,
    0xA56A, 0xB54B, 0x8528, 0x9509, 0xE5EE, 0xF5CF, 0xC5AC, 0xD58D,
    0x3653, 0x2672, 0x1611, 0x0630, 0x76D7, 0x66F6, 0x5695, 0x46B4,
    0xB75B, 0xA77A, 0x9719, 0x8738, 0xF7DF, 0xE7FE, 0xD79D, 0xC7BC,
    0x4864, 0x5845, 0x6826, 0x7807, 0x08E0, 0x18C1, 0x28A2, 0x38A3,
    0xC94C, 0xD96D, 0xE90E, 0xF92F, 0x89C8, 0x99E9, 0xA98A, 0xB9AB,
    0x5A75, 0x4A54, 0x7A37, 0x6A16, 0x1AF1, 0x0AD0, 0x3AB3, 0x2A92,
    0xDB7D, 0xCB5C, 0xFB3F, 0xEB1E, 0x9BF9, 0x8BD8, 0xBBBB, 0xAB9A,
    0x6CA6, 0x7C87, 0x4CE4, 0x5CC5, 0x2C22, 0x3C03, 0x0C60, 0x1C41,
    0xEDAE, 0xFD8F, 0xCDEC, 0xDDCD, 0xAD2A, 0xBD0B, 0x8D68, 0x9D49,
    0x7E97, 0x6EB6, 0x5ED5, 0x4EF4, 0x3E13, 0x2E32, 0x1E51, 0x0E70,
    0xFF9F, 0xEFBE, 0xDFDD, 0xCFFC, 0xBF1B, 0xAF3A, 0x9F59, 0x8F78,
    0x9188, 0x81A9, 0xB1CA, 0xA1EB, 0xD10C, 0xC12D, 0xF14E, 0xE16F,
    0x1080, 0x00A1, 0x30C2, 0x20E3, 0x5004, 0x4025, 0x7046, 0x6067,
    0x83B9, 0x9398, 0xA3FB, 0xB3DA, 0xC33D, 0xD31C, 0xE37F, 0xF35E,
    0x02B1, 0x1290, 0x22F3, 0x32D2, 0x4235, 0x5214, 0x6277, 0x7256,
    0xB5EA, 0xA5CB, 0x95A8, 0x8589, 0xF56E, 0xE54F, 0xD52C, 0xC50D,
    0x34E2, 0x24C3, 0x14A0, 0x0480, 0x7467, 0x6446, 0x5425, 0x4404,
    0xA7DA, 0xB7FB, 0x8798, 0x97B9, 0xE75E, 0xF77F, 0xC71C, 0xD73D,
    0x26D2, 0x36F3, 0x0690, 0x16B1, 0x6656, 0x7677, 0x4614, 0x5635,
    0xD94D, 0xC96C, 0xF90F, 0xE92E, 0x99C9, 0x89E8, 0xB98B, 0xA9AA,
    0x5845, 0x4864, 0x7807, 0x6826, 0x18C1, 0x08E0, 0x3883, 0x28A2,
    0xCB7C, 0xDB5D, 0xEB3E, 0xFB1F, 0x8BF8, 0x9BD9, 0xABBA, 0xBB9B,
    0x4A74, 0x5A55, 0x6A36, 0x7A17, 0x0AF0, 0x1AD1, 0x2AB2, 0x3A93,
    0xEE2E, 0xFE0F, 0xCE6C, 0xDE4D, 0xAEAA, 0xBE8B, 0x8EE8, 0x9EC9,
    0x6F26, 0x7F07, 0x4F64, 0x5F45, 0x2FA2, 0x3F83, 0x0FE0, 0x1FC1,
    0xFC1F, 0xEC3E, 0xDC5D, 0xCC7C, 0xBC9B, 0xACBA, 0x9CD9, 0x8CF8,
    0x7D17, 0x6D36, 0x5D55, 0x4D74, 0x3D93, 0x2DB2, 0x1DD1, 0x0DF0
};

void CCSDS_Init(void) {
    sequence_count = 0;
}

uint16_t CCSDS_CalculateCRC16(const uint8_t *data, uint16_t length) {
    uint16_t crc = 0xFFFF;
    for (uint16_t i = 0; i < length; i++) {
        uint8_t index = (uint8_t)((crc >> 8) ^ data[i]);
        crc = (crc << 8) ^ crc16_table[index];
    }
    return crc;
}

uint16_t CCSDS_BuildPacket(CCSDS_Packet_t *packet, uint16_t apid,
                            CCSDS_PacketType_t type, uint8_t subsystem,
                            const uint8_t *data, uint16_t data_len) {
    if (data_len > CCSDS_MAX_DATA_SIZE) {
        data_len = CCSDS_MAX_DATA_SIZE;
    }

    /* Primary header: version(3) | type(1) | sec_hdr(1) | APID(11) */
    uint16_t first_word = (0 << 13) | ((type & 1) << 12) | (1 << 11) |
                          (apid & 0x7FF);
    packet->primary.version_type_apid = first_word;

    /* Sequence: flags(2) | count(14) */
    packet->primary.sequence = (3 << 14) | (sequence_count & 0x3FFF);
    sequence_count = (sequence_count + 1) & 0x3FFF;

    /* Data length = secondary header + data + CRC - 1 */
    uint16_t total_data = CCSDS_SECONDARY_HEADER_SIZE + data_len +
                          CCSDS_CRC_SIZE;
    packet->primary.data_length = total_data - 1;

    /* Secondary header */
#ifndef SIMULATION_MODE
    extern uint32_t HAL_GetTick(void);
    packet->secondary.timestamp = (uint64_t)HAL_GetTick();
#else
    packet->secondary.timestamp = 0;
#endif
    packet->secondary.subsystem_id = subsystem;
    packet->secondary.packet_subtype = 0;

    /* Copy data */
    if (data != NULL && data_len > 0) {
        memcpy(packet->data, data, data_len);
    }
    packet->data_length = data_len;

    return CCSDS_PRIMARY_HEADER_SIZE + total_data;
}

uint16_t CCSDS_Serialize(const CCSDS_Packet_t *packet, uint8_t *buffer,
                          uint16_t max_size) {
    uint16_t total_size = CCSDS_PRIMARY_HEADER_SIZE +
                          CCSDS_SECONDARY_HEADER_SIZE +
                          packet->data_length + CCSDS_CRC_SIZE;

    if (total_size > max_size) return 0;

    uint16_t offset = 0;

    /* Primary header (big-endian) */
    buffer[offset++] = (packet->primary.version_type_apid >> 8) & 0xFF;
    buffer[offset++] = packet->primary.version_type_apid & 0xFF;
    buffer[offset++] = (packet->primary.sequence >> 8) & 0xFF;
    buffer[offset++] = packet->primary.sequence & 0xFF;
    buffer[offset++] = (packet->primary.data_length >> 8) & 0xFF;
    buffer[offset++] = packet->primary.data_length & 0xFF;

    /* Secondary header */
    for (int i = 7; i >= 0; i--) {
        buffer[offset++] = (packet->secondary.timestamp >> (i * 8)) & 0xFF;
    }
    buffer[offset++] = packet->secondary.subsystem_id;
    buffer[offset++] = packet->secondary.packet_subtype;

    /* Data */
    memcpy(&buffer[offset], packet->data, packet->data_length);
    offset += packet->data_length;

    /* CRC-16 over everything before CRC */
    uint16_t crc = CCSDS_CalculateCRC16(buffer, offset);
    buffer[offset++] = (crc >> 8) & 0xFF;
    buffer[offset++] = crc & 0xFF;

    return offset;
}

bool CCSDS_Parse(const uint8_t *buffer, uint16_t length,
                  CCSDS_Packet_t *packet) {
    if (length < CCSDS_PRIMARY_HEADER_SIZE + CCSDS_CRC_SIZE) return false;

    /* Validate CRC */
    if (!CCSDS_ValidateCRC(buffer, length)) return false;

    /* Parse primary header */
    packet->primary.version_type_apid = (buffer[0] << 8) | buffer[1];
    packet->primary.sequence = (buffer[2] << 8) | buffer[3];
    packet->primary.data_length = (buffer[4] << 8) | buffer[5];

    uint16_t offset = CCSDS_PRIMARY_HEADER_SIZE;

    /* Parse secondary header */
    packet->secondary.timestamp = 0;
    for (int i = 0; i < 8; i++) {
        packet->secondary.timestamp = (packet->secondary.timestamp << 8) |
                                       buffer[offset++];
    }
    packet->secondary.subsystem_id = buffer[offset++];
    packet->secondary.packet_subtype = buffer[offset++];

    /* Extract data */
    packet->data_length = length - CCSDS_PRIMARY_HEADER_SIZE -
                          CCSDS_SECONDARY_HEADER_SIZE - CCSDS_CRC_SIZE;
    if (packet->data_length > CCSDS_MAX_DATA_SIZE) return false;

    memcpy(packet->data, &buffer[offset], packet->data_length);

    return true;
}

bool CCSDS_ValidateCRC(const uint8_t *buffer, uint16_t length) {
    if (length < CCSDS_CRC_SIZE) return false;

    uint16_t received_crc = (buffer[length - 2] << 8) | buffer[length - 1];
    uint16_t calculated_crc = CCSDS_CalculateCRC16(buffer, length - 2);

    return received_crc == calculated_crc;
}

uint16_t CCSDS_GetSequenceCount(void) {
    return sequence_count;
}

void CCSDS_ResetSequenceCount(void) {
    sequence_count = 0;
}
