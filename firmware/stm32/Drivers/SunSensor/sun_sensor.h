/**
 * @file sun_sensor.h
 * @brief HAL driver for 6-axis sun sensor array (analog via MCP3008)
 *
 * The sun sensor subsystem uses 6 photodiodes mounted on the six faces
 * of the CubeSat.  Each photodiode is connected to one channel of an
 * MCP3008 10-bit ADC.  The raw readings are calibrated to produce
 * normalized illumination values (0.0 = dark, 1.0 = full sunlight).
 *
 * Face mapping (body-frame):
 *   CH0 = +X face
 *   CH1 = -X face
 *   CH2 = +Y face
 *   CH3 = -Y face
 *   CH4 = +Z face (nadir/zenith)
 *   CH5 = -Z face (nadir/zenith)
 *
 * @author UniSat CubeSat Team
 * @version 1.0.0
 */

#ifndef SUN_SENSOR_H
#define SUN_SENSOR_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>
#include "mcp3008.h"

/* ───────────── Configuration ───────────── */

#define SUN_SENSOR_NUM_FACES    6     /**< Number of photodiode faces */

/** ADC channel assignments for each face */
#define SUN_SENSOR_CH_PLUS_X    0     /**< +X face ADC channel */
#define SUN_SENSOR_CH_MINUS_X   1     /**< -X face ADC channel */
#define SUN_SENSOR_CH_PLUS_Y    2     /**< +Y face ADC channel */
#define SUN_SENSOR_CH_MINUS_Y   3     /**< -Y face ADC channel */
#define SUN_SENSOR_CH_PLUS_Z    4     /**< +Z face ADC channel */
#define SUN_SENSOR_CH_MINUS_Z   5     /**< -Z face ADC channel */

/* ───────────── Return Codes ───────────── */

typedef enum {
    SUN_SENSOR_OK = 0,               /**< Operation succeeded */
    SUN_SENSOR_ERR_ADC,              /**< ADC read error */
    SUN_SENSOR_ERR_NOT_INIT,         /**< Driver not initialized */
    SUN_SENSOR_ERR_CALIBRATION,      /**< Calibration data invalid */
    SUN_SENSOR_ERR_SELF_TEST         /**< Self-test failed */
} SunSensor_Status_t;

/* ───────────── Calibration Data ───────────── */

/**
 * @brief Per-face calibration parameters.
 *
 * Maps raw ADC value to normalized illumination:
 *   illumination = (raw - dark_offset) * gain
 * Clamped to [0.0, 1.0].
 */
typedef struct {
    uint16_t dark_offset;            /**< ADC value in complete darkness */
    float    gain;                   /**< Scaling factor to normalize to [0, 1] */
} SunSensor_FaceCalib_t;

/* ───────────── Handle ───────────── */

/**
 * @brief Driver instance handle.
 */
typedef struct {
    MCP3008_Handle_t       *adc;     /**< Pointer to initialized MCP3008 handle */
    SunSensor_FaceCalib_t   calib[SUN_SENSOR_NUM_FACES]; /**< Per-face calibration */
    bool                    initialized; /**< True after successful init */
} SunSensor_Handle_t;

/* ───────────── Sun Vector Result ───────────── */

/**
 * @brief Coarse sun vector in body frame (unit vector).
 */
typedef struct {
    float x;                         /**< Sun direction X component */
    float y;                         /**< Sun direction Y component */
    float z;                         /**< Sun direction Z component */
    bool  valid;                     /**< True if sun is detected */
} SunSensor_Vector_t;

/* ───────────── Public API ───────────── */

/**
 * @brief Initialize the sun sensor subsystem.
 *
 * Applies default calibration values and validates the ADC handle.
 *
 * @param[in,out] dev  Driver handle (adc must point to an initialized MCP3008).
 * @return SUN_SENSOR_OK on success.
 */
SunSensor_Status_t SunSensor_Init(SunSensor_Handle_t *dev);

/**
 * @brief Read all 6 faces and return normalized illumination values.
 *
 * Each value is in the range [0.0, 1.0] where 0.0 = dark and
 * 1.0 = maximum illumination.
 *
 * @param[in]  dev     Initialized driver handle.
 * @param[out] values  Array of 6 normalized illumination values
 *                     (indexed by SUN_SENSOR_CH_* constants).
 * @return SUN_SENSOR_OK on success.
 */
SunSensor_Status_t SunSensor_ReadAll(SunSensor_Handle_t *dev, float values[6]);

/**
 * @brief Compute a coarse sun vector from the 6-face readings.
 *
 * Uses differential illumination between opposing faces to estimate
 * the sun direction in the satellite body frame.
 *
 * @param[in]  dev  Initialized driver handle.
 * @param[out] vec  Computed sun vector (unit vector if valid).
 * @return SUN_SENSOR_OK on success.
 */
SunSensor_Status_t SunSensor_GetSunVector(SunSensor_Handle_t *dev,
                                            SunSensor_Vector_t *vec);

/**
 * @brief Set calibration parameters for a specific face.
 *
 * @param[in,out] dev          Driver handle.
 * @param[in]     face_index   Face index (0-5).
 * @param[in]     dark_offset  ADC reading in total darkness.
 * @param[in]     gain         Normalization gain.
 * @return SUN_SENSOR_OK on success.
 */
SunSensor_Status_t SunSensor_SetCalibration(SunSensor_Handle_t *dev,
                                              uint8_t face_index,
                                              uint16_t dark_offset,
                                              float gain);

/**
 * @brief Execute a basic self-test.
 *
 * Reads all faces and verifies the ADC returns valid data.
 *
 * @param[in] dev  Initialized driver handle.
 * @return SUN_SENSOR_OK if self-test passes.
 */
SunSensor_Status_t SunSensor_SelfTest(SunSensor_Handle_t *dev);

#ifdef __cplusplus
}
#endif

#endif /* SUN_SENSOR_H */
