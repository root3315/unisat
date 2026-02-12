/**
 * @file ccsds.h
 * @brief CCSDS Space Packet Protocol implementation
 *
 * Implements CCSDS 133.0-B-2 compatible packet format
 * with primary header, secondary header, data, and CRC-16.
 */

#ifndef CCSDS_H
#define CCSDS_H

#include <stdint.h>
#include <stdbool.h>

/** CCSDS header sizes */
#define CCSDS_PRIMARY_HEADER_SIZE   6
#define CCSDS_SECONDARY_HEADER_SIZE 10
#define CCSDS_CRC_SIZE              2
#define CCSDS_MAX_DATA_SIZE         240
#define CCSDS_MAX_PACKET_SIZE       (CCSDS_PRIMARY_HEADER_SIZE + \
                                     CCSDS_SECONDARY_HEADER_SIZE + \
                                     CCSDS_MAX_DATA_SIZE + CCSDS_CRC_SIZE)

/** CCSDS APID assignments */
#define APID_OBC_HOUSEKEEPING   0x001
#define APID_EPS_TELEMETRY      0x002
#define APID_COMM_STATUS        0x003
#define APID_ADCS_ATTITUDE      0x004
#define APID_GNSS_POSITION      0x005
#define APID_CAMERA_STATUS      0x006
#define APID_PAYLOAD_DATA       0x007
#define APID_ERROR_REPORT       0x010
#define APID_BEACON             0x0FF
#define APID_COMMAND            0x100

/** CCSDS packet type */
typedef enum {
    CCSDS_TELEMETRY = 0,
    CCSDS_TELECOMMAND = 1
} CCSDS_PacketType_t;

/** CCSDS primary header (6 bytes) */
typedef struct __attribute__((packed)) {
    uint16_t version_type_apid;
    uint16_t sequence;
    uint16_t data_length;
} CCSDS_PrimaryHeader_t;

/** CCSDS secondary header (10 bytes) */
typedef struct __attribute__((packed)) {
    uint64_t timestamp;
    uint8_t subsystem_id;
    uint8_t packet_subtype;
} CCSDS_SecondaryHeader_t;

/** Complete CCSDS packet */
typedef struct {
    CCSDS_PrimaryHeader_t primary;
    CCSDS_SecondaryHeader_t secondary;
    uint8_t data[CCSDS_MAX_DATA_SIZE];
    uint16_t data_length;
    uint16_t crc;
} CCSDS_Packet_t;

void CCSDS_Init(void);
uint16_t CCSDS_BuildPacket(CCSDS_Packet_t *packet, uint16_t apid,
                            CCSDS_PacketType_t type, uint8_t subsystem,
                            const uint8_t *data, uint16_t data_len);
uint16_t CCSDS_Serialize(const CCSDS_Packet_t *packet, uint8_t *buffer,
                          uint16_t max_size);
bool CCSDS_Parse(const uint8_t *buffer, uint16_t length, CCSDS_Packet_t *packet);
bool CCSDS_ValidateCRC(const uint8_t *buffer, uint16_t length);
uint16_t CCSDS_CalculateCRC16(const uint8_t *data, uint16_t length);
uint16_t CCSDS_GetSequenceCount(void);
void CCSDS_ResetSequenceCount(void);

#endif /* CCSDS_H */
