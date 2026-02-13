/**
 * @file mcp3008.h
 * @brief HAL driver for MCP3008 10-bit 8-channel ADC (SPI)
 *
 * The MCP3008 is a successive-approximation ADC with SPI interface.
 * It provides 8 single-ended input channels with 10-bit resolution.
 *
 * @note SPI mode: CPOL=0, CPHA=0 (Mode 0), max 3.6 MHz at 5V / 1.35 MHz at 2.7V
 * @note Datasheet: Microchip DS21295
 *
 * @author UniSat CubeSat Team
 * @version 1.0.0
 */

#ifndef MCP3008_H
#define MCP3008_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>

/* ───────────── Channel Definitions ───────────── */

#define MCP3008_NUM_CHANNELS    8     /**< Number of input channels */
#define MCP3008_MAX_VALUE       1023  /**< Maximum 10-bit ADC value */

/* ───────────── SPI Command Format ───────────── */

/**
 * MCP3008 SPI command (3-byte transfer):
 *
 *   Byte 0: 0x01              (start bit)
 *   Byte 1: [SGL/DIFF][D2][D1][D0][x][x][x][x]
 *           SGL/DIFF = 1 for single-ended
 *           D2:D0 = channel number (0-7)
 *   Byte 2: 0x00              (clock out result)
 *
 * Response comes in bytes 1-2:
 *   Byte 1: [x][x][x][x][x][0][B9][B8]
 *   Byte 2: [B7][B6][B5][B4][B3][B2][B1][B0]
 */
#define MCP3008_CMD_START       0x01  /**< Start bit */
#define MCP3008_CMD_SINGLE      0x80  /**< Single-ended mode flag */
#define MCP3008_CMD_DIFF        0x00  /**< Differential mode flag */

/* ───────────── Configuration ───────────── */

#define MCP3008_MAX_RETRIES     3     /**< Maximum SPI transaction retry count */

/* ───────────── Return Codes ───────────── */

typedef enum {
    MCP3008_OK = 0,                  /**< Operation succeeded */
    MCP3008_ERR_SPI,                 /**< SPI communication error */
    MCP3008_ERR_CHANNEL,             /**< Invalid channel number */
    MCP3008_ERR_SELF_TEST            /**< Self-test failed */
} MCP3008_Status_t;

/* ───────────── Handle ───────────── */

/**
 * @brief Driver instance handle.
 */
typedef struct {
    void  *spi_handle;               /**< Platform SPI peripheral handle */
    void (*cs_low)(void);            /**< Assert chip select (drive low) */
    void (*cs_high)(void);           /**< De-assert chip select (drive high) */
    float  vref;                     /**< Reference voltage (V) for conversion */
    bool   initialized;              /**< True after successful init */
} MCP3008_Handle_t;

/* ───────────── Public API ───────────── */

/**
 * @brief Initialize the MCP3008 ADC.
 *
 * Validates the handle and performs a dummy read to synchronize the
 * SPI interface.
 *
 * @param[in,out] dev  Driver handle (spi_handle, cs_low, cs_high, vref must be set).
 * @return MCP3008_OK on success, error code otherwise.
 */
MCP3008_Status_t MCP3008_Init(MCP3008_Handle_t *dev);

/**
 * @brief Read a single channel (10-bit raw value).
 *
 * Performs a single-ended conversion on the specified channel.
 *
 * @param[in]  dev      Initialized driver handle.
 * @param[in]  channel  Channel number (0-7).
 * @param[out] value    Raw 10-bit ADC value (0-1023).
 * @return MCP3008_OK on success, error code otherwise.
 */
MCP3008_Status_t MCP3008_Read(MCP3008_Handle_t *dev,
                               uint8_t channel, uint16_t *value);

/**
 * @brief Read a single channel and convert to voltage.
 *
 * @param[in]  dev      Initialized driver handle.
 * @param[in]  channel  Channel number (0-7).
 * @param[out] voltage  Voltage in volts (0 to Vref).
 * @return MCP3008_OK on success, error code otherwise.
 */
MCP3008_Status_t MCP3008_ReadVoltage(MCP3008_Handle_t *dev,
                                      uint8_t channel, float *voltage);

/**
 * @brief Execute a basic self-test.
 *
 * Reads all 8 channels and verifies each value is within 10-bit range.
 *
 * @param[in] dev  Initialized driver handle.
 * @return MCP3008_OK if self-test passes.
 */
MCP3008_Status_t MCP3008_SelfTest(MCP3008_Handle_t *dev);

#ifdef __cplusplus
}
#endif

#endif /* MCP3008_H */
