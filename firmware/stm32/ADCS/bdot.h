/**
 * @file bdot.h
 * @brief B-dot detumbling algorithm
 *
 * M = -k * (dB/dt)
 * Exit criterion: angular rate < 2 deg/s
 */

#ifndef BDOT_H
#define BDOT_H

#include <stdbool.h>

#define BDOT_GAIN           1.0e-4f
#define BDOT_THRESHOLD_DPS  2.0f

void BDot_Init(void);
void BDot_Update(const float mag[3], float dt, float moment_out[3]);
bool BDot_IsDetumbled(void);
void BDot_Reset(void);

#endif /* BDOT_H */
