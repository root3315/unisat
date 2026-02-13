/**
 * @file mppt.h
 * @brief Maximum Power Point Tracking (Perturb & Observe)
 */

#ifndef MPPT_H
#define MPPT_H

#include <stdint.h>

#define MPPT_STEP_SIZE    0.02f
#define MPPT_MIN_DUTY     0.1f
#define MPPT_MAX_DUTY     0.95f
#define MPPT_UPDATE_MS    100

typedef struct {
    float voltage;
    float current;
    float power;
    float duty_cycle;
    float efficiency;
} MPPT_Status_t;

void MPPT_Init(void);
void MPPT_Update(float solar_voltage, float solar_current);
MPPT_Status_t MPPT_GetStatus(void);
float MPPT_GetDutyCycle(void);

#endif /* MPPT_H */
