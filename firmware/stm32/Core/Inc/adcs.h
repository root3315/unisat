/**
 * @file adcs.h
 * @brief Attitude Determination and Control System interface
 */

#ifndef ADCS_H
#define ADCS_H

#include <stdint.h>
#include <stdbool.h>

/** ADCS operating modes */
typedef enum {
    ADCS_MODE_IDLE = 0,
    ADCS_MODE_DETUMBLING,
    ADCS_MODE_SUN_POINTING,
    ADCS_MODE_NADIR_POINTING,
    ADCS_MODE_TARGET_POINTING
} ADCS_Mode_t;

/** ADCS status */
typedef struct {
    ADCS_Mode_t mode;
    float quaternion[4];
    float angular_rate[3];
    float pointing_error_deg;
    bool magnetorquers_active;
    bool reaction_wheels_active;
    float wheel_speed_rpm[3];
} ADCS_Status_t;

/** Target coordinates for target pointing mode */
typedef struct {
    double latitude;
    double longitude;
    double altitude;
} ADCS_Target_t;

void ADCS_Init(void);
ADCS_Status_t ADCS_GetStatus(void);
void ADCS_SetMode(ADCS_Mode_t mode);
ADCS_Mode_t ADCS_GetMode(void);
void ADCS_SetTarget(ADCS_Target_t target);
void ADCS_Update(const float mag[3], const float gyro[3],
                 const float accel[3], const uint16_t sun[6]);
float ADCS_GetPointingError(void);
void ADCS_SetMagnetorquerDutyCycle(uint8_t axis, float duty);
void ADCS_SetWheelSpeed(uint8_t axis, float speed_rpm);
void ADCS_Desaturate(void);

#endif /* ADCS_H */
