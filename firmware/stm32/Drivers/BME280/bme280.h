/**
 * @file bme280.h
 * @brief HAL driver for BME280 environmental sensor (I2C)
 *
 * Provides initialization and combined reading of temperature, pressure,
 * and humidity from the Bosch BME280.
 *
 * @note I2C address: 0x76 (SDO = GND) or 0x77 (SDO = VDD)
 * @note Datasheet: Bosch BST-BME280-DS002
 *
 * @author UniSat CubeSat Team
 * @version 1.0.0
 */

#ifndef BME280_H
#define BME280_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>

/* ───────────── I2C Address ───────────── */

#define BME280_I2C_ADDR_LOW    0x76  /**< SDO connected to GND */
#define BME280_I2C_ADDR_HIGH   0x77  /**< SDO connected to VDD */
#define BME280_DEFAULT_ADDR    BME280_I2C_ADDR_LOW

/* ───────────── Register Map ───────────── */

#define BME280_REG_CHIP_ID     0xD0  /**< Chip identification (expected 0x60) */
#define BME280_REG_RESET       0xE0  /**< Soft reset register (write 0xB6) */
#define BME280_REG_CTRL_HUM    0xF2  /**< Humidity oversampling control */
#define BME280_REG_STATUS      0xF3  /**< Device status */
#define BME280_REG_CTRL_MEAS   0xF4  /**< Temp/press oversampling & mode */
#define BME280_REG_CONFIG      0xF5  /**< Standby, filter, SPI config */
#define BME280_REG_PRESS_MSB   0xF7  /**< Pressure data MSB [19:12] */
#define BME280_REG_PRESS_LSB   0xF8  /**< Pressure data LSB [11:4] */
#define BME280_REG_PRESS_XLSB  0xF9  /**< Pressure data XLSB [3:0] */
#define BME280_REG_TEMP_MSB    0xFA  /**< Temperature data MSB [19:12] */
#define BME280_REG_TEMP_LSB    0xFB  /**< Temperature data LSB [11:4] */
#define BME280_REG_TEMP_XLSB   0xFC  /**< Temperature data XLSB [3:0] */
#define BME280_REG_HUM_MSB     0xFD  /**< Humidity data MSB [15:8] */
#define BME280_REG_HUM_LSB     0xFE  /**< Humidity data LSB [7:0] */

/* Calibration data registers */
#define BME280_REG_CALIB00     0x88  /**< Calibration block 1 start (26 bytes) */
#define BME280_REG_CALIB26     0xE1  /**< Calibration block 2 start (7 bytes) */

#define BME280_CHIP_ID_VAL     0x60  /**< Expected chip ID */
#define BME280_RESET_VAL       0xB6  /**< Soft reset command */

/* ───────────── Configuration ───────────── */

#define BME280_MAX_RETRIES     3     /**< Maximum I2C transaction retry count */

/* ───────────── Return Codes ───────────── */

typedef enum {
    BME280_OK = 0,                   /**< Operation succeeded */
    BME280_ERR_I2C,                  /**< I2C communication error */
    BME280_ERR_CHIP_ID,              /**< Chip ID mismatch */
    BME280_ERR_TIMEOUT,              /**< Measurement timeout */
    BME280_ERR_SELF_TEST             /**< Self-test failed */
} BME280_Status_t;

/* ───────────── Calibration Data ───────────── */

/**
 * @brief Trimming/compensation parameters read from device NVM.
 */
typedef struct {
    /* Temperature */
    uint16_t dig_T1;
    int16_t  dig_T2;
    int16_t  dig_T3;
    /* Pressure */
    uint16_t dig_P1;
    int16_t  dig_P2;
    int16_t  dig_P3;
    int16_t  dig_P4;
    int16_t  dig_P5;
    int16_t  dig_P6;
    int16_t  dig_P7;
    int16_t  dig_P8;
    int16_t  dig_P9;
    /* Humidity */
    uint8_t  dig_H1;
    int16_t  dig_H2;
    uint8_t  dig_H3;
    int16_t  dig_H4;
    int16_t  dig_H5;
    int8_t   dig_H6;
} BME280_CalibData_t;

/* ───────────── Handle ───────────── */

/**
 * @brief Driver instance handle.
 */
typedef struct {
    void              *i2c_handle;   /**< Platform I2C peripheral handle */
    uint8_t            addr;         /**< 7-bit I2C address */
    BME280_CalibData_t calib;        /**< Compensation parameters */
    int32_t            t_fine;       /**< Fine temperature for compensation */
    bool               initialized;  /**< True after successful init */
} BME280_Handle_t;

/* ───────────── Public API ───────────── */

/**
 * @brief Initialize the BME280 sensor.
 *
 * Performs soft reset, verifies chip ID, reads calibration data, and
 * configures the sensor for weather monitoring mode (1x oversampling,
 * forced mode).
 *
 * @param[in,out] dev  Driver handle (i2c_handle and addr must be set).
 * @return BME280_OK on success, error code otherwise.
 */
BME280_Status_t BME280_Init(BME280_Handle_t *dev);

/**
 * @brief Trigger a measurement and read compensated results.
 *
 * Starts a forced-mode conversion, waits for completion, and returns
 * compensated temperature, pressure, and humidity.
 *
 * @param[in]  dev   Initialized driver handle.
 * @param[out] temp  Temperature in degrees Celsius.
 * @param[out] press Pressure in hectopascals (hPa / mbar).
 * @param[out] hum   Relative humidity in percent (0-100).
 * @return BME280_OK on success, error code otherwise.
 */
BME280_Status_t BME280_Read(BME280_Handle_t *dev,
                             float *temp, float *press, float *hum);

/**
 * @brief Execute a basic self-test.
 *
 * Verifies chip ID and checks that a forced measurement produces values
 * within plausible physical ranges.
 *
 * @param[in] dev  Initialized driver handle.
 * @return BME280_OK if self-test passes, BME280_ERR_SELF_TEST otherwise.
 */
BME280_Status_t BME280_SelfTest(BME280_Handle_t *dev);

#ifdef __cplusplus
}
#endif

#endif /* BME280_H */
