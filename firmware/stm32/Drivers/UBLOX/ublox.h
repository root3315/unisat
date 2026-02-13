/**
 * @file ublox.h
 * @brief HAL driver for u-blox GNSS receiver (I2C DDC / UART)
 *
 * Provides initialization, byte-level reading, and UBX protocol
 * configuration for u-blox GNSS modules (e.g. MAX-M8Q, NEO-M8N, NEO-M9N).
 *
 * The I2C interface uses the u-blox DDC (Display Data Channel) protocol:
 *   - Register 0xFD:0xFE = bytes available (16-bit, big-endian)
 *   - Register 0xFF = data stream
 *
 * @note I2C address: 0x42 (default, configurable via UBX-CFG-PRT)
 * @note Datasheet: u-blox M8 Receiver Description (UBX-13003221)
 *
 * @author UniSat CubeSat Team
 * @version 1.0.0
 */

#ifndef UBLOX_H
#define UBLOX_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>

/* ───────────── I2C Address ───────────── */

#define UBLOX_I2C_DEFAULT_ADDR  0x42  /**< Default DDC address */

/* ───────────── DDC Register Map ───────────── */

#define UBLOX_REG_BYTES_HI      0xFD  /**< Number of bytes available (high byte) */
#define UBLOX_REG_BYTES_LO      0xFE  /**< Number of bytes available (low byte) */
#define UBLOX_REG_DATA_STREAM   0xFF  /**< Data stream register */

/* ───────────── UBX Protocol Constants ───────────── */

#define UBLOX_UBX_SYNC1         0xB5  /**< UBX sync char 1 */
#define UBLOX_UBX_SYNC2         0x62  /**< UBX sync char 2 */

/** UBX Message Classes */
#define UBLOX_UBX_CLASS_NAV     0x01  /**< Navigation results */
#define UBLOX_UBX_CLASS_RXM     0x02  /**< Receiver manager */
#define UBLOX_UBX_CLASS_INF     0x04  /**< Information messages */
#define UBLOX_UBX_CLASS_ACK     0x05  /**< Ack/Nack messages */
#define UBLOX_UBX_CLASS_CFG     0x06  /**< Configuration */
#define UBLOX_UBX_CLASS_MON     0x0A  /**< Monitoring */

/** UBX Message IDs (commonly used) */
#define UBLOX_UBX_NAV_PVT       0x07  /**< Navigation PVT (Position, Velocity, Time) */
#define UBLOX_UBX_NAV_STATUS    0x03  /**< Receiver navigation status */
#define UBLOX_UBX_CFG_PRT       0x00  /**< Port configuration */
#define UBLOX_UBX_CFG_MSG       0x01  /**< Message configuration */
#define UBLOX_UBX_CFG_RATE      0x08  /**< Navigation/measurement rate */
#define UBLOX_UBX_CFG_NAV5      0x24  /**< Navigation engine settings */
#define UBLOX_UBX_CFG_GNSS      0x3E  /**< GNSS system configuration */
#define UBLOX_UBX_MON_VER       0x04  /**< Receiver/software version */
#define UBLOX_UBX_ACK_ACK       0x01  /**< Acknowledge */
#define UBLOX_UBX_ACK_NAK       0x00  /**< Not-acknowledge */

/** UBX-CFG-NAV5 dynamic models */
#define UBLOX_DYNMODEL_PORTABLE     0  /**< Portable */
#define UBLOX_DYNMODEL_STATIONARY   2  /**< Stationary */
#define UBLOX_DYNMODEL_PEDESTRIAN   3  /**< Pedestrian */
#define UBLOX_DYNMODEL_AUTOMOTIVE   4  /**< Automotive */
#define UBLOX_DYNMODEL_SEA          5  /**< Sea */
#define UBLOX_DYNMODEL_AIRBORNE_1G  6  /**< Airborne < 1g */
#define UBLOX_DYNMODEL_AIRBORNE_2G  7  /**< Airborne < 2g */
#define UBLOX_DYNMODEL_AIRBORNE_4G  8  /**< Airborne < 4g */

/* ───────────── Configuration ───────────── */

#define UBLOX_MAX_RETRIES       3     /**< Maximum I2C transaction retry count */
#define UBLOX_READ_TIMEOUT_MS   1000  /**< Max wait for data available */

/* ───────────── Return Codes ───────────── */

typedef enum {
    UBLOX_OK = 0,                    /**< Operation succeeded */
    UBLOX_ERR_I2C,                   /**< I2C communication error */
    UBLOX_ERR_NO_DATA,               /**< No data available */
    UBLOX_ERR_TIMEOUT,               /**< Operation timed out */
    UBLOX_ERR_NACK,                  /**< UBX NAK received */
    UBLOX_ERR_SELF_TEST              /**< Self-test failed */
} UBLOX_Status_t;

/* ───────────── Handle ───────────── */

/**
 * @brief Driver instance handle.
 */
typedef struct {
    void    *i2c_handle;             /**< Platform I2C peripheral handle */
    uint8_t  addr;                   /**< 7-bit I2C address */
    bool     initialized;            /**< True after successful init */
} UBLOX_Handle_t;

/* ───────────── Public API ───────────── */

/**
 * @brief Initialize the u-blox GNSS receiver.
 *
 * Verifies I2C communication, disables NMEA output on DDC port,
 * enables UBX protocol, and configures 1 Hz navigation rate.
 *
 * @param[in,out] dev  Driver handle (i2c_handle and addr must be set).
 * @return UBLOX_OK on success, error code otherwise.
 */
UBLOX_Status_t UBLOX_Init(UBLOX_Handle_t *dev);

/**
 * @brief Read a single byte from the DDC data stream.
 *
 * @param[in]  dev   Initialized driver handle.
 * @param[out] byte  Received byte.
 * @return UBLOX_OK on success, UBLOX_ERR_NO_DATA if buffer empty.
 */
UBLOX_Status_t UBLOX_ReadByte(UBLOX_Handle_t *dev, uint8_t *byte);

/**
 * @brief Read multiple bytes from the DDC data stream.
 *
 * @param[in]  dev   Initialized driver handle.
 * @param[out] buf   Receive buffer.
 * @param[in]  len   Number of bytes to read.
 * @param[out] read  Actual number of bytes read.
 * @return UBLOX_OK on success.
 */
UBLOX_Status_t UBLOX_ReadBytes(UBLOX_Handle_t *dev, uint8_t *buf,
                                uint16_t len, uint16_t *read);

/**
 * @brief Get the number of bytes available in the DDC buffer.
 *
 * @param[in]  dev     Initialized driver handle.
 * @param[out] avail   Number of bytes available.
 * @return UBLOX_OK on success.
 */
UBLOX_Status_t UBLOX_BytesAvailable(UBLOX_Handle_t *dev, uint16_t *avail);

/**
 * @brief Send a UBX configuration message.
 *
 * Builds the UBX frame (sync, class, id, length, payload, checksum)
 * and writes it to the DDC port.
 *
 * @param[in] dev      Initialized driver handle.
 * @param[in] cls      UBX message class.
 * @param[in] id       UBX message ID.
 * @param[in] payload  Payload data (may be NULL if payload_len == 0).
 * @param[in] payload_len  Payload length in bytes.
 * @return UBLOX_OK on success.
 */
UBLOX_Status_t UBLOX_Configure(UBLOX_Handle_t *dev,
                                uint8_t cls, uint8_t id,
                                const uint8_t *payload, uint16_t payload_len);

/**
 * @brief Execute a basic self-test.
 *
 * Verifies I2C communication by reading the bytes-available register.
 *
 * @param[in] dev  Initialized driver handle.
 * @return UBLOX_OK if self-test passes.
 */
UBLOX_Status_t UBLOX_SelfTest(UBLOX_Handle_t *dev);

#ifdef __cplusplus
}
#endif

#endif /* UBLOX_H */
