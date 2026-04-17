/**
 * @file telemetry.h
 * @brief Telemetry collection and formatting
 */

#ifndef TELEMETRY_H
#define TELEMETRY_H

#include <stdint.h>
#include <stdbool.h>
#include "ccsds.h"

#define TELEMETRY_MAX_BUFFER_SIZE  512

/** Telemetry packet types */
typedef enum {
    TLM_OBC_HOUSEKEEPING = 0,
    TLM_EPS,
    TLM_COMM,
    TLM_ADCS,
    TLM_GNSS,
    TLM_CAMERA,
    TLM_PAYLOAD,
    TLM_ERROR,
    TLM_BEACON
} TelemetryType_t;

void Telemetry_Init(void);
uint16_t Telemetry_PackOBC(uint8_t *buffer, uint16_t max_size);
uint16_t Telemetry_PackEPS(uint8_t *buffer, uint16_t max_size);
uint16_t Telemetry_PackADCS(uint8_t *buffer, uint16_t max_size);
uint16_t Telemetry_PackGNSS(uint8_t *buffer, uint16_t max_size);
uint16_t Telemetry_PackPayload(uint8_t *buffer, uint16_t max_size);
uint16_t Telemetry_PackBeaconCcsds(uint8_t *buffer, uint16_t max_size);
uint16_t Telemetry_PackBeacon(uint8_t *buffer, uint16_t max_size);
uint16_t Telemetry_PackError(uint8_t *buffer, uint16_t max_size,
                              uint8_t error_code, const char *message);
bool Telemetry_SendPacket(TelemetryType_t type);
void Telemetry_SendAllHousekeeping(void);
uint32_t Telemetry_GetPacketCount(void);

#endif /* TELEMETRY_H */
