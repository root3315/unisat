/**
 * @file lis3mdl.h
 * @brief HAL driver for LIS3MDL 3-axis magnetometer (I2C)
 *
 * Provides initialization, magnetic field reading, self-test, and
 * full-scale range configuration for the STMicroelectronics LIS3MDL.
 *
 * @note I2C address: 0x1C (SDO/SA1 = GND) or 0x1E (SDO/SA1 = VDD)
 * @note Datasheet: ST DocID026866
 *
 * @author UniSat CubeSat Team
 * @version 1.0.0
 */

#ifndef LIS3MDL_H
#define LIS3MDL_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>

/* ───────────── I2C Address ───────────── */

#define LIS3MDL_I2C_ADDR_LOW   0x1C  /**< SDO/SA1 connected to GND */
#define LIS3MDL_I2C_ADDR_HIGH  0x1E  /**< SDO/SA1 connected to VDD */
#define LIS3MDL_DEFAULT_ADDR   LIS3MDL_I2C_ADDR_LOW

/* ───────────── Register Map ───────────── */

#define LIS3MDL_REG_WHO_AM_I   0x0F  /**< Device identification (expected 0x3D) */
#define LIS3MDL_REG_CTRL_REG1  0x20  /**< Control register 1 (ODR, mode) */
#define LIS3MDL_REG_CTRL_REG2  0x21  /**< Control register 2 (full-scale) */
#define LIS3MDL_REG_CTRL_REG3  0x22  /**< Control register 3 (operating mode) */
#define LIS3MDL_REG_CTRL_REG4  0x23  /**< Control register 4 (Z-axis mode) */
#define LIS3MDL_REG_CTRL_REG5  0x24  /**< Control register 5 (block data update) */
#define LIS3MDL_REG_STATUS     0x27  /**< Status register */
#define LIS3MDL_REG_OUT_X_L    0x28  /**< X-axis output low byte */
#define LIS3MDL_REG_OUT_X_H    0x29  /**< X-axis output high byte */
#define LIS3MDL_REG_OUT_Y_L    0x2A  /**< Y-axis output low byte */
#define LIS3MDL_REG_OUT_Y_H    0x2B  /**< Y-axis output high byte */
#define LIS3MDL_REG_OUT_Z_L    0x2C  /**< Z-axis output low byte */
#define LIS3MDL_REG_OUT_Z_H    0x2D  /**< Z-axis output high byte */
#define LIS3MDL_REG_TEMP_OUT_L 0x2E  /**< Temperature output low byte */
#define LIS3MDL_REG_TEMP_OUT_H 0x2F  /**< Temperature output high byte */
#define LIS3MDL_REG_INT_CFG    0x30  /**< Interrupt configuration */
#define LIS3MDL_REG_INT_SRC    0x31  /**< Interrupt source */
#define LIS3MDL_REG_INT_THS_L  0x32  /**< Interrupt threshold low byte */
#define LIS3MDL_REG_INT_THS_H  0x33  /**< Interrupt threshold high byte */

#define LIS3MDL_WHO_AM_I_VAL   0x3D  /**< Expected WHO_AM_I value */

/* ───────────── Full-Scale Range ───────────── */

/**
 * @brief Full-scale selection for the magnetometer.
 */
typedef enum {
    LIS3MDL_RANGE_4_GAUSS  = 0x00,  /**< +/- 4 gauss  (6842 LSB/gauss) */
    LIS3MDL_RANGE_8_GAUSS  = 0x20,  /**< +/- 8 gauss  (3421 LSB/gauss) */
    LIS3MDL_RANGE_12_GAUSS = 0x40,  /**< +/- 12 gauss (2281 LSB/gauss) */
    LIS3MDL_RANGE_16_GAUSS = 0x60   /**< +/- 16 gauss (1711 LSB/gauss) */
} LIS3MDL_Range_t;

/* ───────────── Configuration ───────────── */

#define LIS3MDL_MAX_RETRIES    3     /**< Maximum I2C transaction retry count */

/* ───────────── Return Codes ───────────── */

typedef enum {
    LIS3MDL_OK = 0,                  /**< Operation succeeded */
    LIS3MDL_ERR_I2C,                 /**< I2C communication error */
    LIS3MDL_ERR_WHO_AM_I,            /**< WHO_AM_I mismatch */
    LIS3MDL_ERR_SELF_TEST,           /**< Self-test failed */
    LIS3MDL_ERR_TIMEOUT              /**< Data-ready timeout */
} LIS3MDL_Status_t;

/* ───────────── Handle ───────────── */

/**
 * @brief Driver instance handle.
 */
typedef struct {
    void        *i2c_handle;         /**< Platform I2C peripheral handle (e.g. I2C_HandleTypeDef*) */
    uint8_t      addr;               /**< 7-bit I2C address */
    LIS3MDL_Range_t range;           /**< Current full-scale range */
    float        sensitivity;        /**< LSB-to-gauss conversion factor */
    bool         initialized;        /**< True after successful init */
} LIS3MDL_Handle_t;

/* ───────────── Public API ───────────── */

/**
 * @brief Initialize the LIS3MDL sensor.
 *
 * Verifies WHO_AM_I, configures ODR to 80 Hz, enables BDU, and sets the
 * default full-scale range to +/- 4 gauss.
 *
 * @param[in,out] dev    Driver handle (i2c_handle and addr must be set).
 * @return LIS3MDL_OK on success, error code otherwise.
 */
LIS3MDL_Status_t LIS3MDL_Init(LIS3MDL_Handle_t *dev);

/**
 * @brief Read calibrated magnetic field in gauss.
 *
 * @param[in]  dev  Initialized driver handle.
 * @param[out] x    Magnetic field X axis (gauss).
 * @param[out] y    Magnetic field Y axis (gauss).
 * @param[out] z    Magnetic field Z axis (gauss).
 * @return LIS3MDL_OK on success, error code otherwise.
 */
LIS3MDL_Status_t LIS3MDL_ReadMag(LIS3MDL_Handle_t *dev, float *x, float *y, float *z);

/**
 * @brief Execute the built-in self-test procedure.
 *
 * Enables self-test mode, reads output, and checks against datasheet limits.
 *
 * @param[in] dev  Initialized driver handle.
 * @return LIS3MDL_OK if self-test passes, LIS3MDL_ERR_SELF_TEST otherwise.
 */
LIS3MDL_Status_t LIS3MDL_SelfTest(LIS3MDL_Handle_t *dev);

/**
 * @brief Change the magnetometer full-scale range.
 *
 * @param[in,out] dev    Initialized driver handle.
 * @param[in]     range  Desired full-scale range.
 * @return LIS3MDL_OK on success, error code otherwise.
 */
LIS3MDL_Status_t LIS3MDL_SetRange(LIS3MDL_Handle_t *dev, LIS3MDL_Range_t range);

#ifdef __cplusplus
}
#endif

#endif /* LIS3MDL_H */
