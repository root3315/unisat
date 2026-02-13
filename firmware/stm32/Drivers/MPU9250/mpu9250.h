/**
 * @file mpu9250.h
 * @brief HAL driver for MPU-9250 9-axis IMU (SPI)
 *
 * Provides initialization, accelerometer, and gyroscope reading for the
 * InvenSense MPU-9250.  The internal AK8963 magnetometer is not exposed
 * here (use the LIS3MDL driver for magnetometer data).
 *
 * @note SPI mode: CPOL=0, CPHA=0 (Mode 0), max 1 MHz for registers, 20 MHz for data
 * @note Datasheet: InvenSense PS-MPU-9250A-01
 *
 * @author UniSat CubeSat Team
 * @version 1.0.0
 */

#ifndef MPU9250_H
#define MPU9250_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>

/* ───────────── Register Map ───────────── */

#define MPU9250_REG_SMPLRT_DIV      0x19  /**< Sample rate divider */
#define MPU9250_REG_CONFIG          0x1A  /**< DLPF configuration */
#define MPU9250_REG_GYRO_CONFIG     0x1B  /**< Gyroscope configuration */
#define MPU9250_REG_ACCEL_CONFIG    0x1C  /**< Accelerometer configuration */
#define MPU9250_REG_ACCEL_CONFIG2   0x1D  /**< Accelerometer configuration 2 */
#define MPU9250_REG_INT_PIN_CFG     0x37  /**< Interrupt pin configuration */
#define MPU9250_REG_INT_ENABLE      0x38  /**< Interrupt enable */
#define MPU9250_REG_INT_STATUS      0x3A  /**< Interrupt status */
#define MPU9250_REG_ACCEL_XOUT_H    0x3B  /**< Accelerometer X high byte */
#define MPU9250_REG_ACCEL_XOUT_L    0x3C  /**< Accelerometer X low byte */
#define MPU9250_REG_ACCEL_YOUT_H    0x3D  /**< Accelerometer Y high byte */
#define MPU9250_REG_ACCEL_YOUT_L    0x3E  /**< Accelerometer Y low byte */
#define MPU9250_REG_ACCEL_ZOUT_H    0x3F  /**< Accelerometer Z high byte */
#define MPU9250_REG_ACCEL_ZOUT_L    0x40  /**< Accelerometer Z low byte */
#define MPU9250_REG_TEMP_OUT_H      0x41  /**< Temperature high byte */
#define MPU9250_REG_TEMP_OUT_L      0x42  /**< Temperature low byte */
#define MPU9250_REG_GYRO_XOUT_H    0x43  /**< Gyroscope X high byte */
#define MPU9250_REG_GYRO_XOUT_L    0x44  /**< Gyroscope X low byte */
#define MPU9250_REG_GYRO_YOUT_H    0x45  /**< Gyroscope Y high byte */
#define MPU9250_REG_GYRO_YOUT_L    0x46  /**< Gyroscope Y low byte */
#define MPU9250_REG_GYRO_ZOUT_H    0x47  /**< Gyroscope Z high byte */
#define MPU9250_REG_GYRO_ZOUT_L    0x48  /**< Gyroscope Z low byte */
#define MPU9250_REG_USER_CTRL      0x6A  /**< User control */
#define MPU9250_REG_PWR_MGMT_1     0x6B  /**< Power management 1 */
#define MPU9250_REG_PWR_MGMT_2     0x6C  /**< Power management 2 */
#define MPU9250_REG_WHO_AM_I       0x75  /**< Device identity (expected 0x71) */

#define MPU9250_WHO_AM_I_VAL       0x71  /**< Expected WHO_AM_I for MPU-9250 */
#define MPU9250_READ_FLAG          0x80  /**< SPI read flag (set bit 7) */

/* ───────────── Full-Scale Ranges ───────────── */

/**
 * @brief Gyroscope full-scale selection.
 */
typedef enum {
    MPU9250_GYRO_250DPS  = 0x00,  /**< +/- 250 deg/s  (131 LSB/deg/s) */
    MPU9250_GYRO_500DPS  = 0x08,  /**< +/- 500 deg/s  (65.5 LSB/deg/s) */
    MPU9250_GYRO_1000DPS = 0x10,  /**< +/- 1000 deg/s (32.8 LSB/deg/s) */
    MPU9250_GYRO_2000DPS = 0x18   /**< +/- 2000 deg/s (16.4 LSB/deg/s) */
} MPU9250_GyroRange_t;

/**
 * @brief Accelerometer full-scale selection.
 */
typedef enum {
    MPU9250_ACCEL_2G  = 0x00,  /**< +/- 2g  (16384 LSB/g) */
    MPU9250_ACCEL_4G  = 0x08,  /**< +/- 4g  (8192 LSB/g) */
    MPU9250_ACCEL_8G  = 0x10,  /**< +/- 8g  (4096 LSB/g) */
    MPU9250_ACCEL_16G = 0x18   /**< +/- 16g (2048 LSB/g) */
} MPU9250_AccelRange_t;

/* ───────────── Configuration ───────────── */

#define MPU9250_MAX_RETRIES    3  /**< Maximum SPI transaction retry count */

/* ───────────── Return Codes ───────────── */

typedef enum {
    MPU9250_OK = 0,                  /**< Operation succeeded */
    MPU9250_ERR_SPI,                 /**< SPI communication error */
    MPU9250_ERR_WHO_AM_I,            /**< WHO_AM_I mismatch */
    MPU9250_ERR_SELF_TEST,           /**< Self-test failed */
    MPU9250_ERR_TIMEOUT              /**< Data-ready timeout */
} MPU9250_Status_t;

/* ───────────── Handle ───────────── */

/**
 * @brief Driver instance handle.
 */
typedef struct {
    void                *spi_handle;   /**< Platform SPI peripheral handle */
    void               (*cs_low)(void);  /**< Assert chip select (drive low) */
    void               (*cs_high)(void); /**< De-assert chip select (drive high) */
    MPU9250_GyroRange_t  gyro_range;   /**< Current gyroscope range */
    MPU9250_AccelRange_t accel_range;  /**< Current accelerometer range */
    float                gyro_sens;    /**< Gyro sensitivity (LSB per deg/s) */
    float                accel_sens;   /**< Accel sensitivity (LSB per g) */
    bool                 initialized;  /**< True after successful init */
} MPU9250_Handle_t;

/* ───────────── Public API ───────────── */

/**
 * @brief Initialize the MPU-9250.
 *
 * Wakes the device, verifies WHO_AM_I, configures DLPF, and sets default
 * ranges (gyro +/- 250 dps, accel +/- 2g).
 *
 * @param[in,out] dev  Driver handle (spi_handle, cs_low, cs_high must be set).
 * @return MPU9250_OK on success, error code otherwise.
 */
MPU9250_Status_t MPU9250_Init(MPU9250_Handle_t *dev);

/**
 * @brief Read calibrated gyroscope data in degrees per second.
 *
 * @param[in]  dev  Initialized driver handle.
 * @param[out] gx   Gyro X axis (deg/s).
 * @param[out] gy   Gyro Y axis (deg/s).
 * @param[out] gz   Gyro Z axis (deg/s).
 * @return MPU9250_OK on success, error code otherwise.
 */
MPU9250_Status_t MPU9250_ReadGyro(MPU9250_Handle_t *dev,
                                    float *gx, float *gy, float *gz);

/**
 * @brief Read calibrated accelerometer data in g.
 *
 * @param[in]  dev  Initialized driver handle.
 * @param[out] ax   Accel X axis (g).
 * @param[out] ay   Accel Y axis (g).
 * @param[out] az   Accel Z axis (g).
 * @return MPU9250_OK on success, error code otherwise.
 */
MPU9250_Status_t MPU9250_ReadAccel(MPU9250_Handle_t *dev,
                                     float *ax, float *ay, float *az);

/**
 * @brief Execute the built-in self-test.
 *
 * Enables self-test mode on gyro and accelerometer, reads output shift,
 * and validates against factory trim values.
 *
 * @param[in] dev  Initialized driver handle.
 * @return MPU9250_OK if self-test passes.
 */
MPU9250_Status_t MPU9250_SelfTest(MPU9250_Handle_t *dev);

#ifdef __cplusplus
}
#endif

#endif /* MPU9250_H */
