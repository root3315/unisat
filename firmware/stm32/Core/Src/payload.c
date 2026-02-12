/**
 * @file payload.c
 * @brief Payload interface implementation
 */

#include "payload.h"
#include "sbm20.h"
#include "config.h"
#include <string.h>

#ifndef SIMULATION_MODE
#include "stm32f4xx_hal.h"
#else
static uint32_t sim_tick = 0;
static uint32_t HAL_GetTick(void) { return sim_tick += 1000; }
#endif

static Payload_Status_t payload_status;
static PayloadType_t current_type;

/* Radiation monitor data buffer */
static struct {
    uint32_t cps_values[60];
    uint8_t index;
    float dose_rate_usv_h;
    float total_dose_usv;
} radiation_data;

void Payload_Init(PayloadType_t type) {
    memset(&payload_status, 0, sizeof(payload_status));
    current_type = type;
    payload_status.type = type;
    payload_status.active = false;
    payload_status.health = 100;

    switch (type) {
        case PAYLOAD_RADIATION_MONITOR:
            memset(&radiation_data, 0, sizeof(radiation_data));
            SBM20_Init();
            break;
        default:
            break;
    }
}

Payload_Status_t Payload_GetStatus(void) {
    return payload_status;
}

bool Payload_Activate(void) {
    payload_status.active = true;
    return true;
}

void Payload_Deactivate(void) {
    payload_status.active = false;
}

uint16_t Payload_ReadData(uint8_t *buffer, uint16_t max_size) {
    if (!payload_status.active || max_size < 16) return 0;

    uint16_t offset = 0;

    switch (current_type) {
        case PAYLOAD_RADIATION_MONITOR: {
            /* Pack radiation data */
            uint32_t cps = SBM20_GetCPS();
            memcpy(&buffer[offset], &cps, 4); offset += 4;
            memcpy(&buffer[offset], &radiation_data.dose_rate_usv_h, 4);
            offset += 4;
            memcpy(&buffer[offset], &radiation_data.total_dose_usv, 4);
            offset += 4;
            memcpy(&buffer[offset], &payload_status.samples_collected, 4);
            offset += 4;
            break;
        }
        default:
            break;
    }

    return offset;
}

void Payload_ProcessCommand(const uint8_t *cmd, uint16_t length) {
    if (length == 0) return;

    switch (cmd[0]) {
        case 0x01: /* Activate */
            Payload_Activate();
            break;
        case 0x02: /* Deactivate */
            Payload_Deactivate();
            break;
        case 0x03: /* Reset */
            Payload_Init(current_type);
            Payload_Activate();
            break;
        default:
            break;
    }
}

void Payload_Update(void) {
    if (!payload_status.active) return;

    switch (current_type) {
        case PAYLOAD_RADIATION_MONITOR: {
            uint32_t cps = SBM20_GetCPS();

            radiation_data.cps_values[radiation_data.index] = cps;
            radiation_data.index = (radiation_data.index + 1) % 60;

            /* SBM-20: ~0.0057 uSv/h per CPM */
            float cpm = (float)cps * 60.0f;
            radiation_data.dose_rate_usv_h = cpm * 0.0057f;

            /* Accumulate total dose */
            radiation_data.total_dose_usv +=
                radiation_data.dose_rate_usv_h / 3600.0f;

            payload_status.samples_collected++;
            payload_status.last_sample_time = HAL_GetTick();
            break;
        }
        default:
            break;
    }
}
