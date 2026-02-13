/**
 * @file target_pointing.h
 * @brief Target/nadir pointing with PID controller and desaturation
 */

#ifndef TARGET_POINTING_H
#define TARGET_POINTING_H

#include "quaternion.h"

#define TARGET_KP  2.0f
#define TARGET_KI  0.01f
#define TARGET_KD  0.5f
#define TARGET_ACCURACY_DEG  1.0f
#define DESAT_THRESHOLD_RPM  5000.0f
#define DESAT_GAIN  0.001f

void TargetPointing_Init(void);
void TargetPointing_Update(const float quat[4], const float target_quat[4],
                            const float gyro[3], float wheel_cmd[3]);
float TargetPointing_GetError(void);
void TargetPointing_Desaturate(const float mag[3], const float wheel_rpm[3],
                                float torquer_cmd[3]);

#endif /* TARGET_POINTING_H */
