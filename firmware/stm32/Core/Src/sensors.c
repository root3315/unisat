/**
 * @file sensors.c
 * @brief Unified sensor reading with retry logic
 */

#include "sensors.h"
#include "config.h"
#include "lis3mdl.h"
#include "bme280.h"
#include "tmp117.h"
#include "mpu9250.h"
#include "sbm20.h"
#include "mcp3008.h"
#include "sun_sensor.h"

void Sensors_Init(void) {
    if (config.adcs.enabled) {
        LIS3MDL_Init();
        MPU9250_Init();
        SunSensor_Init();
    }
    BME280_Init();
    TMP117_Init();
    if (config.payload.enabled) {
        SBM20_Init();
    }
    MCP3008_Init();
}

SensorStatus_t Sensors_ReadMagnetometer(float *x, float *y, float *z) {
    if (!config.adcs.enabled) return SENSOR_DISABLED;

    for (uint8_t retry = 0; retry < IO_MAX_RETRIES; retry++) {
        if (LIS3MDL_ReadMag(x, y, z)) {
            return SENSOR_OK;
        }
    }
    *x = *y = *z = 0.0f;
    return SENSOR_TIMEOUT;
}

SensorStatus_t Sensors_ReadIMU(float *gx, float *gy, float *gz,
                                float *ax, float *ay, float *az) {
    if (!config.adcs.enabled) return SENSOR_DISABLED;

    for (uint8_t retry = 0; retry < IO_MAX_RETRIES; retry++) {
        bool gyro_ok = MPU9250_ReadGyro(gx, gy, gz);
        bool accel_ok = MPU9250_ReadAccel(ax, ay, az);
        if (gyro_ok && accel_ok) return SENSOR_OK;
    }
    *gx = *gy = *gz = 0.0f;
    *ax = *ay = *az = 0.0f;
    return SENSOR_TIMEOUT;
}

SensorStatus_t Sensors_ReadEnvironment(float *temp, float *press,
                                        float *hum) {
    for (uint8_t retry = 0; retry < IO_MAX_RETRIES; retry++) {
        if (BME280_Read(temp, press, hum)) {
            return SENSOR_OK;
        }
    }
    *temp = *press = *hum = 0.0f;
    return SENSOR_TIMEOUT;
}

SensorStatus_t Sensors_ReadPrecisionTemp(float *temp) {
    for (uint8_t retry = 0; retry < IO_MAX_RETRIES; retry++) {
        if (TMP117_Read(temp)) {
            return SENSOR_OK;
        }
    }
    *temp = 0.0f;
    return SENSOR_TIMEOUT;
}

SensorStatus_t Sensors_ReadSunSensors(uint16_t values[6]) {
    if (!config.adcs.enabled) return SENSOR_DISABLED;

    for (uint8_t i = 0; i < 6; i++) {
        values[i] = MCP3008_Read(i);
    }
    return SENSOR_OK;
}

SensorStatus_t Sensors_ReadRadiation(uint32_t *cps) {
    if (!config.payload.enabled) return SENSOR_DISABLED;
    *cps = SBM20_GetCPS();
    return SENSOR_OK;
}

bool Sensors_SelfTest(void) {
    bool all_ok = true;
    float dummy_f;
    uint16_t dummy_u16[6];
    uint32_t dummy_u32;

    if (config.adcs.enabled) {
        float x, y, z;
        if (Sensors_ReadMagnetometer(&x, &y, &z) != SENSOR_OK) all_ok = false;
        if (Sensors_ReadIMU(&x, &y, &z, &x, &y, &z) != SENSOR_OK) all_ok = false;
        if (Sensors_ReadSunSensors(dummy_u16) != SENSOR_OK) all_ok = false;
    }

    if (Sensors_ReadEnvironment(&dummy_f, &dummy_f, &dummy_f) != SENSOR_OK) {
        all_ok = false;
    }
    if (Sensors_ReadPrecisionTemp(&dummy_f) != SENSOR_OK) all_ok = false;

    if (config.payload.enabled) {
        if (Sensors_ReadRadiation(&dummy_u32) != SENSOR_OK) all_ok = false;
    }

    return all_ok;
}
