/**
 * @file power_distribution.h
 * @brief Priority-based power distribution unit
 */

#ifndef POWER_DISTRIBUTION_H
#define POWER_DISTRIBUTION_H

#include <stdint.h>
#include <stdbool.h>

#define PDU_MAX_CHANNELS  8

typedef struct {
    bool enabled;
    float current_draw_a;
    float max_current_a;
    uint8_t priority;
    const char *name;
} PDU_Channel_t;

typedef struct {
    PDU_Channel_t channels[PDU_MAX_CHANNELS];
    float total_current;
    float total_power;
    uint8_t active_channels;
} PDU_Status_t;

void PDU_Init(void);
void PDU_EnableChannel(uint8_t channel);
void PDU_DisableChannel(uint8_t channel);
void PDU_SetPriority(uint8_t channel, uint8_t priority);
void PDU_LoadShed(float available_power_w);
PDU_Status_t PDU_GetStatus(void);
void PDU_Update(void);

#endif /* POWER_DISTRIBUTION_H */
