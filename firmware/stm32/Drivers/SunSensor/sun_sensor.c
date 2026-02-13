/**
 * @file sun_sensor.c
 * @brief HAL driver implementation for 6-axis sun sensor array
 *
 * Reads 6 photodiode channels via the MCP3008 ADC, applies per-face
 * calibration, and computes a coarse sun vector in the satellite body frame.
 *
 * In SIMULATION_MODE the driver returns mock illumination data
 * corresponding to sunlight on the +X / +Z faces.
 *
 * @author UniSat CubeSat Team
 * @version 1.0.0
 */

#include "sun_sensor.h"
#include <math.h>
#include <string.h>

/* ───────────── Default Calibration Constants ───────────── */

/**
 * Default dark offset (ADC counts with no light).
 * Typical for SFH 2430 photodiode with 10k load resistor.
 */
#define DEFAULT_DARK_OFFSET     10

/**
 * Default gain to map [dark_offset .. 1023] to [0.0 .. 1.0].
 * gain = 1.0 / (1023 - dark_offset)
 */
#define DEFAULT_GAIN            (1.0f / (1023.0f - DEFAULT_DARK_OFFSET))

/** Minimum illumination threshold to consider sun detected */
#define SUN_DETECT_THRESHOLD    0.05f

/* ───────────── Channel Mapping ───────────── */

static const uint8_t face_channels[SUN_SENSOR_NUM_FACES] = {
    SUN_SENSOR_CH_PLUS_X,
    SUN_SENSOR_CH_MINUS_X,
    SUN_SENSOR_CH_PLUS_Y,
    SUN_SENSOR_CH_MINUS_Y,
    SUN_SENSOR_CH_PLUS_Z,
    SUN_SENSOR_CH_MINUS_Z
};

/* ───────────── Internal Helpers ───────────── */

/**
 * @brief Clamp a float to [0.0, 1.0].
 */
static float clampf(float val)
{
    if (val < 0.0f) return 0.0f;
    if (val > 1.0f) return 1.0f;
    return val;
}

/* ───────────── Public API ───────────── */

SunSensor_Status_t SunSensor_Init(SunSensor_Handle_t *dev)
{
    if (!dev) return SUN_SENSOR_ERR_NOT_INIT;

#ifndef SIMULATION_MODE
    if (!dev->adc || !dev->adc->initialized) {
        return SUN_SENSOR_ERR_ADC;
    }
#endif

    /* Apply default calibration to all faces */
    for (uint8_t i = 0; i < SUN_SENSOR_NUM_FACES; i++) {
        dev->calib[i].dark_offset = DEFAULT_DARK_OFFSET;
        dev->calib[i].gain        = DEFAULT_GAIN;
    }

    dev->initialized = true;
    return SUN_SENSOR_OK;
}

SunSensor_Status_t SunSensor_ReadAll(SunSensor_Handle_t *dev, float values[6])
{
    if (!dev || !dev->initialized || !values) {
        return SUN_SENSOR_ERR_NOT_INIT;
    }

#ifdef SIMULATION_MODE
    /*
     * Simulate sunlight hitting +X and +Z faces at ~45 degrees:
     *   +X = 0.72, -X = 0.02, +Y = 0.15, -Y = 0.10, +Z = 0.68, -Z = 0.03
     */
    static const float mock_illumination[SUN_SENSOR_NUM_FACES] = {
        0.72f, 0.02f, 0.15f, 0.10f, 0.68f, 0.03f
    };
    memcpy(values, mock_illumination, sizeof(mock_illumination));
    return SUN_SENSOR_OK;
#else
    for (uint8_t i = 0; i < SUN_SENSOR_NUM_FACES; i++) {
        uint16_t raw = 0;
        MCP3008_Status_t st = MCP3008_Read(dev->adc, face_channels[i], &raw);
        if (st != MCP3008_OK) {
            return SUN_SENSOR_ERR_ADC;
        }

        /* Apply calibration: illumination = (raw - dark_offset) * gain */
        float illumination;
        if (raw <= dev->calib[i].dark_offset) {
            illumination = 0.0f;
        } else {
            illumination = (float)(raw - dev->calib[i].dark_offset) * dev->calib[i].gain;
        }
        values[i] = clampf(illumination);
    }

    return SUN_SENSOR_OK;
#endif
}

SunSensor_Status_t SunSensor_GetSunVector(SunSensor_Handle_t *dev,
                                            SunSensor_Vector_t *vec)
{
    if (!dev || !dev->initialized || !vec) {
        return SUN_SENSOR_ERR_NOT_INIT;
    }

    vec->valid = false;
    vec->x = 0.0f;
    vec->y = 0.0f;
    vec->z = 0.0f;

    /* Read all faces */
    float illum[SUN_SENSOR_NUM_FACES];
    SunSensor_Status_t st = SunSensor_ReadAll(dev, illum);
    if (st != SUN_SENSOR_OK) return st;

    /*
     * Compute sun vector from differential illumination:
     *   Sx = I(+X) - I(-X)
     *   Sy = I(+Y) - I(-Y)
     *   Sz = I(+Z) - I(-Z)
     *
     * Then normalize to unit vector.
     */
    float sx = illum[0] - illum[1];  /* +X minus -X */
    float sy = illum[2] - illum[3];  /* +Y minus -Y */
    float sz = illum[4] - illum[5];  /* +Z minus -Z */

    float mag = sqrtf(sx * sx + sy * sy + sz * sz);

    if (mag < SUN_DETECT_THRESHOLD) {
        /* No significant illumination — satellite is in eclipse */
        vec->valid = false;
        return SUN_SENSOR_OK;
    }

    /* Normalize to unit vector */
    vec->x = sx / mag;
    vec->y = sy / mag;
    vec->z = sz / mag;
    vec->valid = true;

    return SUN_SENSOR_OK;
}

SunSensor_Status_t SunSensor_SetCalibration(SunSensor_Handle_t *dev,
                                              uint8_t face_index,
                                              uint16_t dark_offset,
                                              float gain)
{
    if (!dev) return SUN_SENSOR_ERR_NOT_INIT;
    if (face_index >= SUN_SENSOR_NUM_FACES) return SUN_SENSOR_ERR_CALIBRATION;
    if (gain <= 0.0f) return SUN_SENSOR_ERR_CALIBRATION;

    dev->calib[face_index].dark_offset = dark_offset;
    dev->calib[face_index].gain        = gain;

    return SUN_SENSOR_OK;
}

SunSensor_Status_t SunSensor_SelfTest(SunSensor_Handle_t *dev)
{
    if (!dev || !dev->initialized) return SUN_SENSOR_ERR_NOT_INIT;

    /* Read all faces and verify we get valid values */
    float values[SUN_SENSOR_NUM_FACES];
    SunSensor_Status_t st = SunSensor_ReadAll(dev, values);
    if (st != SUN_SENSOR_OK) return SUN_SENSOR_ERR_SELF_TEST;

    /* Verify all values are in valid range [0.0, 1.0] */
    for (uint8_t i = 0; i < SUN_SENSOR_NUM_FACES; i++) {
        if (values[i] < 0.0f || values[i] > 1.0f) {
            return SUN_SENSOR_ERR_SELF_TEST;
        }
    }

    /* Verify sun vector computation doesn't crash */
    SunSensor_Vector_t vec;
    st = SunSensor_GetSunVector(dev, &vec);
    if (st != SUN_SENSOR_OK) return SUN_SENSOR_ERR_SELF_TEST;

    /* If vector is valid, verify it's approximately unit length */
    if (vec.valid) {
        float mag = sqrtf(vec.x * vec.x + vec.y * vec.y + vec.z * vec.z);
        if (mag < 0.95f || mag > 1.05f) {
            return SUN_SENSOR_ERR_SELF_TEST;
        }
    }

    return SUN_SENSOR_OK;
}
