/**
 * @file adcs.c
 * @brief ADCS mode controller — dispatches to specific algorithms
 */

#include "adcs.h"
#include "config.h"
#include <string.h>
#include <math.h>

/* Forward declarations for ADCS algorithm modules */
extern void BDot_Update(const float mag[3], float dt, float moment_out[3]);
extern bool BDot_IsDetumbled(void);
extern void SunPointing_Update(const uint16_t sun[6], const float gyro[3],
                                float wheel_cmd[3]);
extern void TargetPointing_Update(const float quat[4], const float target_quat[4],
                                   const float gyro[3], float wheel_cmd[3]);

static ADCS_Status_t adcs_status;
static ADCS_Target_t current_target;
static float dt = 0.001f;

void ADCS_Init(void) {
    memset(&adcs_status, 0, sizeof(adcs_status));
    adcs_status.mode = ADCS_MODE_DETUMBLING;
    adcs_status.quaternion[0] = 1.0f; /* Identity quaternion */
    adcs_status.magnetorquers_active = false;
    adcs_status.reaction_wheels_active = false;
}

ADCS_Status_t ADCS_GetStatus(void) {
    return adcs_status;
}

void ADCS_SetMode(ADCS_Mode_t mode) {
    adcs_status.mode = mode;

    switch (mode) {
        case ADCS_MODE_DETUMBLING:
            adcs_status.magnetorquers_active = true;
            adcs_status.reaction_wheels_active = false;
            break;
        case ADCS_MODE_SUN_POINTING:
        case ADCS_MODE_NADIR_POINTING:
        case ADCS_MODE_TARGET_POINTING:
            adcs_status.magnetorquers_active = false;
            adcs_status.reaction_wheels_active = true;
            break;
        case ADCS_MODE_IDLE:
        default:
            adcs_status.magnetorquers_active = false;
            adcs_status.reaction_wheels_active = false;
            break;
    }
}

ADCS_Mode_t ADCS_GetMode(void) {
    return adcs_status.mode;
}

void ADCS_SetTarget(ADCS_Target_t target) {
    current_target = target;
}

void ADCS_Update(const float mag[3], const float gyro[3],
                 const float accel[3], const uint16_t sun[6]) {
    (void)accel;

    memcpy(adcs_status.angular_rate, gyro, sizeof(float) * 3);

    float cmd[3] = {0.0f, 0.0f, 0.0f};

    switch (adcs_status.mode) {
        case ADCS_MODE_DETUMBLING:
            BDot_Update(mag, dt, cmd);
            for (uint8_t i = 0; i < 3; i++) {
                ADCS_SetMagnetorquerDutyCycle(i, cmd[i]);
            }
            if (BDot_IsDetumbled()) {
                ADCS_SetMode(ADCS_MODE_SUN_POINTING);
            }
            break;

        case ADCS_MODE_SUN_POINTING:
            SunPointing_Update(sun, gyro, cmd);
            for (uint8_t i = 0; i < 3; i++) {
                ADCS_SetWheelSpeed(i, cmd[i]);
            }
            break;

        case ADCS_MODE_NADIR_POINTING:
        case ADCS_MODE_TARGET_POINTING: {
            float target_quat[4] = {1.0f, 0.0f, 0.0f, 0.0f};
            TargetPointing_Update(adcs_status.quaternion, target_quat,
                                   gyro, cmd);
            for (uint8_t i = 0; i < 3; i++) {
                ADCS_SetWheelSpeed(i, cmd[i]);
            }
            break;
        }

        case ADCS_MODE_IDLE:
        default:
            break;
    }

    /* Calculate pointing error */
    float omega_mag = sqrtf(gyro[0]*gyro[0] + gyro[1]*gyro[1] +
                            gyro[2]*gyro[2]);
    adcs_status.pointing_error_deg = omega_mag * 180.0f / 3.14159265f;
}

float ADCS_GetPointingError(void) {
    return adcs_status.pointing_error_deg;
}

void ADCS_SetMagnetorquerDutyCycle(uint8_t axis, float duty) {
    if (axis >= 3) return;
    /* Clamp duty cycle to [-1.0, 1.0] */
    if (duty > 1.0f) duty = 1.0f;
    if (duty < -1.0f) duty = -1.0f;

#ifndef SIMULATION_MODE
    /* Set PWM for magnetorquer coil */
    /* Implementation depends on timer/PWM configuration */
#endif
    (void)duty;
}

void ADCS_SetWheelSpeed(uint8_t axis, float speed_rpm) {
    if (axis >= 3) return;
    /* Clamp speed */
    if (speed_rpm > 6000.0f) speed_rpm = 6000.0f;
    if (speed_rpm < -6000.0f) speed_rpm = -6000.0f;

    adcs_status.wheel_speed_rpm[axis] = speed_rpm;

#ifndef SIMULATION_MODE
    /* Command reaction wheel motor driver */
#endif
}

void ADCS_Desaturate(void) {
    /* Use magnetorquers to dump angular momentum from reaction wheels */
    adcs_status.magnetorquers_active = true;
    /* Implementation in target_pointing module */
}
