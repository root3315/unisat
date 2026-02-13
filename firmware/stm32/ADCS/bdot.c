/**
 * @file bdot.c
 * @brief B-dot detumbling algorithm implementation
 *
 * Uses magnetometer derivative to command magnetorquers,
 * damping rotation after deployment.
 */

#include "bdot.h"
#include <math.h>
#include <string.h>

static float prev_mag[3] = {0.0f, 0.0f, 0.0f};
static float bdot[3] = {0.0f, 0.0f, 0.0f};
static float angular_rate_estimate = 999.0f;
static bool first_sample = true;

void BDot_Init(void) {
    memset(prev_mag, 0, sizeof(prev_mag));
    memset(bdot, 0, sizeof(bdot));
    angular_rate_estimate = 999.0f;
    first_sample = true;
}

void BDot_Update(const float mag[3], float dt, float moment_out[3]) {
    if (first_sample || dt <= 0.0f) {
        prev_mag[0] = mag[0];
        prev_mag[1] = mag[1];
        prev_mag[2] = mag[2];
        moment_out[0] = moment_out[1] = moment_out[2] = 0.0f;
        first_sample = false;
        return;
    }

    /* Compute dB/dt */
    bdot[0] = (mag[0] - prev_mag[0]) / dt;
    bdot[1] = (mag[1] - prev_mag[1]) / dt;
    bdot[2] = (mag[2] - prev_mag[2]) / dt;

    /* B-dot control law: M = -k * (dB/dt) */
    moment_out[0] = -BDOT_GAIN * bdot[0];
    moment_out[1] = -BDOT_GAIN * bdot[1];
    moment_out[2] = -BDOT_GAIN * bdot[2];

    /* Clamp output to [-1, 1] for duty cycle */
    for (int i = 0; i < 3; i++) {
        if (moment_out[i] > 1.0f) moment_out[i] = 1.0f;
        if (moment_out[i] < -1.0f) moment_out[i] = -1.0f;
    }

    /* Estimate angular rate from field derivative */
    float mag_norm = sqrtf(mag[0]*mag[0] + mag[1]*mag[1] + mag[2]*mag[2]);
    float bdot_norm = sqrtf(bdot[0]*bdot[0] + bdot[1]*bdot[1] +
                            bdot[2]*bdot[2]);

    if (mag_norm > 1e-6f) {
        /* omega ~ |dB/dt| / |B| (simplified) */
        float omega_rad = bdot_norm / mag_norm;
        angular_rate_estimate = omega_rad * 180.0f / 3.14159265f;
    }

    /* Low-pass filter on rate estimate */
    static float filtered_rate = 999.0f;
    filtered_rate = 0.9f * filtered_rate + 0.1f * angular_rate_estimate;
    angular_rate_estimate = filtered_rate;

    /* Store for next iteration */
    prev_mag[0] = mag[0];
    prev_mag[1] = mag[1];
    prev_mag[2] = mag[2];
}

bool BDot_IsDetumbled(void) {
    return angular_rate_estimate < BDOT_THRESHOLD_DPS;
}

void BDot_Reset(void) {
    BDot_Init();
}
