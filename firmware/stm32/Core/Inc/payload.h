/**
 * @file payload.h
 * @brief Payload interface for swappable modules
 */

#ifndef PAYLOAD_H
#define PAYLOAD_H

#include <stdint.h>
#include <stdbool.h>

#define PAYLOAD_DATA_MAX_SIZE  128

/** Payload types */
typedef enum {
    PAYLOAD_RADIATION_MONITOR = 0,
    PAYLOAD_EARTH_OBSERVATION,
    PAYLOAD_IOT_RELAY,
    PAYLOAD_MAGNETOMETER_SURVEY,
    PAYLOAD_SPECTROMETER,
    PAYLOAD_CUSTOM
} PayloadType_t;

/** Payload status */
typedef struct {
    PayloadType_t type;
    bool active;
    uint32_t samples_collected;
    uint32_t last_sample_time;
    uint8_t health;
} Payload_Status_t;

void Payload_Init(PayloadType_t type);
Payload_Status_t Payload_GetStatus(void);
bool Payload_Activate(void);
void Payload_Deactivate(void);
uint16_t Payload_ReadData(uint8_t *buffer, uint16_t max_size);
void Payload_ProcessCommand(const uint8_t *cmd, uint16_t length);
void Payload_Update(void);

#endif /* PAYLOAD_H */
