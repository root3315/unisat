/**
 * @file mppt.c
 * @brief MPPT Perturb & Observe algorithm
 *
 * Tracks maximum power point of solar panels by perturbing
 * the duty cycle and observing power change direction.
 */

#include "mppt.h"
#include <math.h>

static MPPT_Status_t mppt_status;
static float prev_power = 0.0f;
static float prev_voltage = 0.0f;
static int8_t perturb_direction = 1;

void MPPT_Init(void) {
    mppt_status.voltage = 0.0f;
    mppt_status.current = 0.0f;
    mppt_status.power = 0.0f;
    mppt_status.duty_cycle = 0.5f;
    mppt_status.efficiency = 0.0f;
    prev_power = 0.0f;
    prev_voltage = 0.0f;
    perturb_direction = 1;
}

void MPPT_Update(float solar_voltage, float solar_current) {
    mppt_status.voltage = solar_voltage;
    mppt_status.current = solar_current;
    mppt_status.power = solar_voltage * solar_current;

    float delta_power = mppt_status.power - prev_power;
    float delta_voltage = mppt_status.voltage - prev_voltage;

    /* Perturb & Observe algorithm */
    if (fabsf(delta_power) > 0.001f) {
        if (delta_power > 0.0f) {
            /* Power increased: continue in same direction */
            if (delta_voltage > 0.0f) {
                perturb_direction = 1;
            } else {
                perturb_direction = -1;
            }
        } else {
            /* Power decreased: reverse direction */
            if (delta_voltage > 0.0f) {
                perturb_direction = -1;
            } else {
                perturb_direction = 1;
            }
        }
    }

    /* Apply perturbation */
    mppt_status.duty_cycle += perturb_direction * MPPT_STEP_SIZE;

    /* Clamp duty cycle */
    if (mppt_status.duty_cycle > MPPT_MAX_DUTY) {
        mppt_status.duty_cycle = MPPT_MAX_DUTY;
    }
    if (mppt_status.duty_cycle < MPPT_MIN_DUTY) {
        mppt_status.duty_cycle = MPPT_MIN_DUTY;
    }

    /* Calculate efficiency (vs theoretical max) */
    float theoretical_max = solar_voltage * solar_current;
    if (theoretical_max > 0.01f) {
        mppt_status.efficiency = mppt_status.power / theoretical_max;
    }

    prev_power = mppt_status.power;
    prev_voltage = mppt_status.voltage;
}

MPPT_Status_t MPPT_GetStatus(void) {
    return mppt_status;
}

float MPPT_GetDutyCycle(void) {
    return mppt_status.duty_cycle;
}
