/**
 * @file sun_pointing.c
 * @brief Sun pointing using 6 face-mounted sun sensors + PD controller
 *
 * Determines sun vector from 6 sensors (one per face), then uses a PD
 * controller to command reaction wheels for alignment.
 */

#include "sun_pointing.h"
#include <math.h>

static float sun_error_deg = 180.0f;

void SunPointing_Init(void) {
    sun_error_deg = 180.0f;
}

/**
 * @brief Determine sun vector in body frame from 6 face sensors
 *
 * Sensor mapping: 0=+X, 1=-X, 2=+Y, 3=-Y, 4=+Z, 5=-Z
 * Each sensor reads 0-4095 proportional to illumination.
 */
static void compute_sun_vector(const uint16_t sun[6], float vec[3]) {
    /* Differential measurement per axis */
    vec[0] = (float)sun[0] - (float)sun[1]; /* +X minus -X */
    vec[1] = (float)sun[2] - (float)sun[3]; /* +Y minus -Y */
    vec[2] = (float)sun[4] - (float)sun[5]; /* +Z minus -Z */

    /* Normalize */
    float norm = sqrtf(vec[0]*vec[0] + vec[1]*vec[1] + vec[2]*vec[2]);
    if (norm > 1.0f) {
        vec[0] /= norm;
        vec[1] /= norm;
        vec[2] /= norm;
    }
}

void SunPointing_Update(const uint16_t sun[6], const float gyro[3],
                         float wheel_cmd[3]) {
    float sun_vec[3];
    compute_sun_vector(sun, sun_vec);

    /* Target: align +Z body axis with sun vector */
    /* Error = cross product of current Z-axis [0,0,1] with sun vector */
    float error[3];
    error[0] =  sun_vec[1];  /* cross(Z, sun).x =  sun_y */
    error[1] = -sun_vec[0];  /* cross(Z, sun).y = -sun_x */
    error[2] =  0.0f;        /* No rotation about sun vector */

    /* PD controller */
    wheel_cmd[0] = SUN_POINTING_KP * error[0] - SUN_POINTING_KD * gyro[0];
    wheel_cmd[1] = SUN_POINTING_KP * error[1] - SUN_POINTING_KD * gyro[1];
    wheel_cmd[2] = SUN_POINTING_KP * error[2] - SUN_POINTING_KD * gyro[2];

    /* Scale to RPM (arbitrary mapping for simulation) */
    for (int i = 0; i < 3; i++) {
        wheel_cmd[i] *= 1000.0f;
        if (wheel_cmd[i] > 6000.0f) wheel_cmd[i] = 6000.0f;
        if (wheel_cmd[i] < -6000.0f) wheel_cmd[i] = -6000.0f;
    }

    /* Compute pointing error angle */
    /* cos(theta) = dot(Z_body, sun_vec) = sun_vec[2] */
    float cos_angle = sun_vec[2];
    if (cos_angle > 1.0f) cos_angle = 1.0f;
    if (cos_angle < -1.0f) cos_angle = -1.0f;
    sun_error_deg = acosf(cos_angle) * 180.0f / 3.14159265f;
}

float SunPointing_GetError(void) {
    return sun_error_deg;
}
