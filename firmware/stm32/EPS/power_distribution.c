/**
 * @file power_distribution.c
 * @brief Power distribution with priority-based load shedding
 *
 * When available power drops below total demand, channels are
 * disabled in reverse priority order (lowest priority first).
 */

#include "power_distribution.h"
#include <string.h>

static PDU_Status_t pdu_status;

/* Default channel configuration */
static const struct {
    const char *name;
    float max_current_a;
    uint8_t priority; /* Higher = more important */
} default_channels[PDU_MAX_CHANNELS] = {
    {"OBC",      0.15f, 10},
    {"COMM_UHF", 0.30f,  9},
    {"ADCS",     0.20f,  7},
    {"GNSS",     0.10f,  6},
    {"CAMERA",   0.50f,  3},
    {"PAYLOAD",  0.15f,  4},
    {"HEATER",   0.30f,  5},
    {"SBAND",    0.50f,  2}
};

void PDU_Init(void) {
    memset(&pdu_status, 0, sizeof(pdu_status));

    for (uint8_t i = 0; i < PDU_MAX_CHANNELS; i++) {
        pdu_status.channels[i].name = default_channels[i].name;
        pdu_status.channels[i].max_current_a = default_channels[i].max_current_a;
        pdu_status.channels[i].priority = default_channels[i].priority;
        pdu_status.channels[i].enabled = (i < 4); /* Enable essentials */
        pdu_status.channels[i].current_draw_a = 0.0f;
    }
}

void PDU_EnableChannel(uint8_t channel) {
    if (channel >= PDU_MAX_CHANNELS) return;
    pdu_status.channels[channel].enabled = true;
}

void PDU_DisableChannel(uint8_t channel) {
    if (channel >= PDU_MAX_CHANNELS) return;
    if (channel == 0) return; /* Never disable OBC */
    pdu_status.channels[channel].enabled = false;
}

void PDU_SetPriority(uint8_t channel, uint8_t priority) {
    if (channel >= PDU_MAX_CHANNELS) return;
    pdu_status.channels[channel].priority = priority;
}

/**
 * @brief Shed loads when power is insufficient
 *
 * Disables channels in ascending priority order until
 * total consumption is within available power budget.
 */
void PDU_LoadShed(float available_power_w) {
    float bus_voltage = 5.0f;
    float available_current = available_power_w / bus_voltage;

    /* Calculate total current demand */
    float total_demand = 0.0f;
    for (uint8_t i = 0; i < PDU_MAX_CHANNELS; i++) {
        if (pdu_status.channels[i].enabled) {
            total_demand += pdu_status.channels[i].max_current_a;
        }
    }

    if (total_demand <= available_current) return;

    /* Sort by priority and shed lowest first */
    for (uint8_t pass = 0; pass < PDU_MAX_CHANNELS && total_demand > available_current; pass++) {
        uint8_t lowest_idx = 0xFF;
        uint8_t lowest_pri = 0xFF;

        for (uint8_t i = 0; i < PDU_MAX_CHANNELS; i++) {
            if (pdu_status.channels[i].enabled &&
                pdu_status.channels[i].priority < lowest_pri &&
                i != 0) { /* Skip OBC */
                lowest_pri = pdu_status.channels[i].priority;
                lowest_idx = i;
            }
        }

        if (lowest_idx != 0xFF) {
            pdu_status.channels[lowest_idx].enabled = false;
            total_demand -= pdu_status.channels[lowest_idx].max_current_a;
        }
    }
}

PDU_Status_t PDU_GetStatus(void) {
    return pdu_status;
}

void PDU_Update(void) {
    pdu_status.total_current = 0.0f;
    pdu_status.active_channels = 0;

    for (uint8_t i = 0; i < PDU_MAX_CHANNELS; i++) {
        if (pdu_status.channels[i].enabled) {
            pdu_status.total_current += pdu_status.channels[i].current_draw_a;
            pdu_status.active_channels++;
        }
    }

    pdu_status.total_power = pdu_status.total_current * 5.0f;
}
