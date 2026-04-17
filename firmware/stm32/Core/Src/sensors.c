/**
 * @file sensors.c
 * @brief Unified sensor reading with retry logic.
 *
 * Owns one handle per physical sensor and exposes the simpler
 * float-returning API used by ADCS/environment telemetry code.
 * Under SIMULATION_MODE each driver short-circuits to a benign
 * constant response (see individual driver .c files).
 */

#include "sensors.h"
#include "config.h"
#include <string.h>
#include "lis3mdl.h"
#include "bme280.h"
#include "tmp117.h"
#include "mpu9250.h"
#include "sbm20.h"
#include "mcp3008.h"
#include "sun_sensor.h"

/* ───────────── Driver handles ───────────── */

static LIS3MDL_Handle_t     mag_dev;
static MPU9250_Handle_t     imu_dev;
static BME280_Handle_t      env_dev;
static TMP117_Handle_t      temp_dev;
static MCP3008_Handle_t     adc_dev;
static SunSensor_Handle_t   sun_dev;
static SBM20_Handle_t       geiger_dev;

void Sensors_Init(void) {
    memset(&mag_dev,    0, sizeof(mag_dev));
    memset(&imu_dev,    0, sizeof(imu_dev));
    memset(&env_dev,    0, sizeof(env_dev));
    memset(&temp_dev,   0, sizeof(temp_dev));
    memset(&adc_dev,    0, sizeof(adc_dev));
    memset(&sun_dev,    0, sizeof(sun_dev));
    memset(&geiger_dev, 0, sizeof(geiger_dev));

    if (config.adcs.enabled) {
        (void)LIS3MDL_Init(&mag_dev);
        (void)MPU9250_Init(&imu_dev);
        (void)SunSensor_Init(&sun_dev);
    }
    (void)BME280_Init(&env_dev);
    (void)TMP117_Init(&temp_dev);
    if (config.payload.enabled) {
        (void)SBM20_Init(&geiger_dev);
    }
    (void)MCP3008_Init(&adc_dev);
}

SensorStatus_t Sensors_ReadMagnetometer(float *x, float *y, float *z) {
    if (!config.adcs.enabled) return SENSOR_DISABLED;

    for (uint8_t retry = 0; retry < IO_MAX_RETRIES; retry++) {
        if (LIS3MDL_ReadMag(&mag_dev, x, y, z) == LIS3MDL_OK) {
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
        bool gyro_ok  = (MPU9250_ReadGyro(&imu_dev, gx, gy, gz) == MPU9250_OK);
        bool accel_ok = (MPU9250_ReadAccel(&imu_dev, ax, ay, az) == MPU9250_OK);
        if (gyro_ok && accel_ok) return SENSOR_OK;
    }
    *gx = *gy = *gz = 0.0f;
    *ax = *ay = *az = 0.0f;
    return SENSOR_TIMEOUT;
}

SensorStatus_t Sensors_ReadEnvironment(float *temp, float *press, float *hum) {
    for (uint8_t retry = 0; retry < IO_MAX_RETRIES; retry++) {
        if (BME280_Read(&env_dev, temp, press, hum) == BME280_OK) {
            return SENSOR_OK;
        }
    }
    *temp = *press = *hum = 0.0f;
    return SENSOR_TIMEOUT;
}

SensorStatus_t Sensors_ReadPrecisionTemp(float *temp) {
    for (uint8_t retry = 0; retry < IO_MAX_RETRIES; retry++) {
        if (TMP117_Read(&temp_dev, temp) == TMP117_OK) {
            return SENSOR_OK;
        }
    }
    *temp = 0.0f;
    return SENSOR_TIMEOUT;
}

SensorStatus_t Sensors_ReadSunSensors(uint16_t values[6]) {
    if (!config.adcs.enabled) return SENSOR_DISABLED;

    for (uint8_t i = 0; i < 6; i++) {
        uint16_t v = 0;
        if (MCP3008_Read(&adc_dev, i, &v) != MCP3008_OK) {
            values[i] = 0;
        } else {
            values[i] = v;
        }
    }
    return SENSOR_OK;
}

SensorStatus_t Sensors_ReadRadiation(uint32_t *cps) {
    if (!config.payload.enabled) return SENSOR_DISABLED;
    uint32_t c = 0;
    if (SBM20_GetCPS(&geiger_dev, &c) != SBM20_OK) {
        *cps = 0;
        return SENSOR_TIMEOUT;
    }
    *cps = c;
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
