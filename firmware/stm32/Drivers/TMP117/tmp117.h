/**
 * @file tmp117.h
 * @brief HAL driver for TMP117 high-accuracy digital temperature sensor (I2C)
 *
 * The TMP117 provides 16-bit temperature readings with 0.0078125 deg C / LSB
 * resolution and +/- 0.1 C accuracy across -20 to +50 C.
 *
 * @note I2C address: 0x48 (ADD0 = GND), 0x49, 0x4A, 0x4B
 * @note Datasheet: Texas Instruments SNOSD49
 *
 * @author UniSat CubeSat Team
 * @version 1.0.0
 */

#ifndef TMP117_H
#define TMP117_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>

/* ───────────── I2C Address ───────────── */

#define TMP117_I2C_ADDR_GND    0x48  /**< ADD0 = GND */
#define TMP117_I2C_ADDR_VDD    0x49  /**< ADD0 = V+ */
#define TMP117_I2C_ADDR_SDA    0x4A  /**< ADD0 = SDA */
#define TMP117_I2C_ADDR_SCL    0x4B  /**< ADD0 = SCL */
#define TMP117_DEFAULT_ADDR    TMP117_I2C_ADDR_GND

/* ───────────── Register Map ───────────── */

#define TMP117_REG_TEMP_RESULT 0x00  /**< Temperature result (16-bit, R) */
#define TMP117_REG_CONFIG      0x01  /**< Configuration register (R/W) */
#define TMP117_REG_T_HIGH_LIM  0x02  /**< High limit (R/W) */
#define TMP117_REG_T_LOW_LIM   0x03  /**< Low limit (R/W) */
#define TMP117_REG_EEPROM_UL   0x04  /**< EEPROM unlock register */
#define TMP117_REG_EEPROM1     0x05  /**< EEPROM 1 (48 bits general purpose) */
#define TMP117_REG_EEPROM2     0x06  /**< EEPROM 2 */
#define TMP117_REG_TEMP_OFFSET 0x07  /**< Temperature offset register */
#define TMP117_REG_EEPROM3     0x08  /**< EEPROM 3 */
#define TMP117_REG_DEVICE_ID   0x0F  /**< Device ID (expected 0x0117) */

#define TMP117_DEVICE_ID_VAL   0x0117 /**< Expected device ID */

/* ───────────── Configuration Bits ───────────── */

#define TMP117_CFG_DATA_READY  (1u << 13)  /**< Data ready flag (bit 13) */
#define TMP117_CFG_MOD_CC      (0u << 10)  /**< Continuous conversion mode */
#define TMP117_CFG_MOD_OS      (3u << 10)  /**< One-shot mode */
#define TMP117_CFG_AVG_NONE    (0u << 5)   /**< No averaging */
#define TMP117_CFG_AVG_8       (1u << 5)   /**< 8-sample averaging */
#define TMP117_CFG_AVG_32      (2u << 5)   /**< 32-sample averaging */
#define TMP117_CFG_AVG_64      (3u << 5)   /**< 64-sample averaging */
#define TMP117_CFG_CONV_15_5MS (0u << 7)   /**< 15.5 ms conversion cycle */
#define TMP117_CFG_CONV_125MS  (1u << 7)   /**< 125 ms conversion cycle */
#define TMP117_CFG_CONV_250MS  (2u << 7)   /**< 250 ms conversion cycle */
#define TMP117_CFG_CONV_500MS  (3u << 7)   /**< 500 ms conversion cycle */
#define TMP117_CFG_CONV_1S     (4u << 7)   /**< 1 s conversion cycle */
#define TMP117_CFG_CONV_4S     (5u << 7)   /**< 4 s conversion cycle */
#define TMP117_CFG_CONV_8S     (6u << 7)   /**< 8 s conversion cycle */
#define TMP117_CFG_CONV_16S    (7u << 7)   /**< 16 s conversion cycle */
#define TMP117_CFG_SOFT_RESET  (1u << 1)   /**< Software reset */

/* ───────────── Constants ───────────── */

/** Resolution: 7.8125 mC per LSB */
#define TMP117_RESOLUTION      0.0078125f

#define TMP117_MAX_RETRIES     3  /**< Maximum I2C transaction retry count */

/* ───────────── Return Codes ───────────── */

typedef enum {
    TMP117_OK = 0,                   /**< Operation succeeded */
    TMP117_ERR_I2C,                  /**< I2C communication error */
    TMP117_ERR_DEVICE_ID,            /**< Device ID mismatch */
    TMP117_ERR_TIMEOUT,              /**< Data-ready timeout */
    TMP117_ERR_SELF_TEST             /**< Self-test failed */
} TMP117_Status_t;

/* ───────────── Handle ───────────── */

/**
 * @brief Driver instance handle.
 */
typedef struct {
    void    *i2c_handle;             /**< Platform I2C peripheral handle */
    uint8_t  addr;                   /**< 7-bit I2C address */
    bool     initialized;            /**< True after successful init */
} TMP117_Handle_t;

/* ───────────── Public API ───────────── */

/**
 * @brief Initialize the TMP117 sensor.
 *
 * Performs a soft reset, verifies device ID, and configures for continuous
 * conversion with no averaging (fastest response).
 *
 * @param[in,out] dev  Driver handle (i2c_handle and addr must be set).
 * @return TMP117_OK on success, error code otherwise.
 */
TMP117_Status_t TMP117_Init(TMP117_Handle_t *dev);

/**
 * @brief Read the current temperature.
 *
 * Waits for data-ready flag and returns the compensated temperature
 * with 0.0078125 C resolution.
 *
 * @param[in]  dev   Initialized driver handle.
 * @param[out] temp  Temperature in degrees Celsius.
 * @return TMP117_OK on success, error code otherwise.
 */
TMP117_Status_t TMP117_Read(TMP117_Handle_t *dev, float *temp);

/**
 * @brief Execute a basic self-test.
 *
 * Verifies device ID and checks that a temperature reading is within
 * the TMP117 operational range (-55 to +150 C).
 *
 * @param[in] dev  Initialized driver handle.
 * @return TMP117_OK if self-test passes.
 */
TMP117_Status_t TMP117_SelfTest(TMP117_Handle_t *dev);

#ifdef __cplusplus
}
#endif

#endif /* TMP117_H */
