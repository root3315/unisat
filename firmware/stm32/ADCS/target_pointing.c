/**
 * @file target_pointing.c
 * @brief PID quaternion-based pointing with wheel desaturation
 *
 * Uses quaternion error feedback with PID control to drive reaction
 * wheels. Includes magnetorquer-based momentum dumping when wheels
 * approach saturation speed.
 */

#include "target_pointing.h"
#include <math.h>
#include <string.h>

static float integral_err[3] = {0.0f, 0.0f, 0.0f};
static float target_error_deg = 180.0f;

void TargetPointing_Init(void) {
    memset(integral_err, 0, sizeof(integral_err));
    target_error_deg = 180.0f;
}

void TargetPointing_Update(const float quat[4], const float target_quat[4],
                            const float gyro[3], float wheel_cmd[3]) {
    /* Convert float arrays to Quaternion_t */
    Quaternion_t q_cur = {quat[0], quat[1], quat[2], quat[3]};
    Quaternion_t q_tgt = {target_quat[0], target_quat[1],
                          target_quat[2], target_quat[3]};

    /* Compute quaternion error */
    Quaternion_t q_err = Quat_Error(q_cur, q_tgt);

    /* Error vector (vector part of error quaternion) */
    float err[3] = {q_err.x, q_err.y, q_err.z};

    /* Sign convention: ensure shortest rotation path */
    float sign = (q_err.w >= 0.0f) ? 1.0f : -1.0f;
    err[0] *= sign;
    err[1] *= sign;
    err[2] *= sign;

    /* PID controller */
    float dt = 0.001f; /* 1 kHz control loop assumed */

    for (int i = 0; i < 3; i++) {
        /* Integrate error with anti-windup */
        integral_err[i] += err[i] * dt;
        if (integral_err[i] > 10.0f) integral_err[i] = 10.0f;
        if (integral_err[i] < -10.0f) integral_err[i] = -10.0f;

        /* PID output */
        wheel_cmd[i] = TARGET_KP * err[i]
                      + TARGET_KI * integral_err[i]
                      - TARGET_KD * gyro[i];

        /* Scale to RPM */
        wheel_cmd[i] *= 1000.0f;
        if (wheel_cmd[i] > 6000.0f) wheel_cmd[i] = 6000.0f;
        if (wheel_cmd[i] < -6000.0f) wheel_cmd[i] = -6000.0f;
    }

    /* Compute error magnitude in degrees */
    float err_mag = sqrtf(err[0]*err[0] + err[1]*err[1] + err[2]*err[2]);
    target_error_deg = 2.0f * asinf(fminf(err_mag, 1.0f)) * 180.0f /
                       3.14159265f;
}

float TargetPointing_GetError(void) {
    return target_error_deg;
}

/**
 * @brief Desaturation: dump wheel momentum using magnetorquers
 *
 * torquer_cmd = -k_desat * cross(B, h_wheel)
 * where h_wheel is wheel angular momentum (proportional to RPM)
 */
void TargetPointing_Desaturate(const float mag[3], const float wheel_rpm[3],
                                float torquer_cmd[3]) {
    /* Check if any wheel is near saturation */
    float max_rpm = 0.0f;
    for (int i = 0; i < 3; i++) {
        float abs_rpm = fabsf(wheel_rpm[i]);
        if (abs_rpm > max_rpm) max_rpm = abs_rpm;
    }

    if (max_rpm < DESAT_THRESHOLD_RPM) {
        torquer_cmd[0] = torquer_cmd[1] = torquer_cmd[2] = 0.0f;
        return;
    }

    /* Approximate angular momentum (proportional to RPM) */
    float h[3] = {wheel_rpm[0], wheel_rpm[1], wheel_rpm[2]};

    /* Cross product: M = -k * (B x h) */
    torquer_cmd[0] = -DESAT_GAIN * (mag[1]*h[2] - mag[2]*h[1]);
    torquer_cmd[1] = -DESAT_GAIN * (mag[2]*h[0] - mag[0]*h[2]);
    torquer_cmd[2] = -DESAT_GAIN * (mag[0]*h[1] - mag[1]*h[0]);

    /* Clamp to [-1, 1] duty cycle */
    for (int i = 0; i < 3; i++) {
        if (torquer_cmd[i] > 1.0f) torquer_cmd[i] = 1.0f;
        if (torquer_cmd[i] < -1.0f) torquer_cmd[i] = -1.0f;
    }
}
