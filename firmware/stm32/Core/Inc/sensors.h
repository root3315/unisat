/**
 * @file sensors.h
 * @brief Unified sensor interface
 */

#ifndef SENSORS_H
#define SENSORS_H

#include <stdint.h>
#include <stdbool.h>

/** Sensor health status */
typedef enum {
    SENSOR_OK = 0,
    SENSOR_TIMEOUT,
    SENSOR_CRC_ERROR,
    SENSOR_NOT_FOUND,
    SENSOR_DISABLED
} SensorStatus_t;

void Sensors_Init(void);
SensorStatus_t Sensors_ReadAll(void *sensor_data);
SensorStatus_t Sensors_ReadMagnetometer(float *x, float *y, float *z);
SensorStatus_t Sensors_ReadIMU(float *gx, float *gy, float *gz,
                                float *ax, float *ay, float *az);
SensorStatus_t Sensors_ReadEnvironment(float *temp, float *press, float *hum);
SensorStatus_t Sensors_ReadPrecisionTemp(float *temp);
SensorStatus_t Sensors_ReadSunSensors(uint16_t values[6]);
SensorStatus_t Sensors_ReadRadiation(uint32_t *cps);
bool Sensors_SelfTest(void);

#endif /* SENSORS_H */
