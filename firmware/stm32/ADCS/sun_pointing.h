/**
 * @file sun_pointing.h
 * @brief Sun pointing algorithm using PD controller
 */

#ifndef SUN_POINTING_H
#define SUN_POINTING_H

#include <stdint.h>

#define SUN_POINTING_KP  0.5f
#define SUN_POINTING_KD  0.1f
#define SUN_POINTING_ACCURACY_DEG  5.0f

void SunPointing_Init(void);
void SunPointing_Update(const uint16_t sun[6], const float gyro[3],
                         float wheel_cmd[3]);
float SunPointing_GetError(void);

#endif /* SUN_POINTING_H */
