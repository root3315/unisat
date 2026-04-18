/**
 * @file ublox.c
 * @brief HAL driver implementation for u-blox GNSS receiver (I2C DDC)
 *
 * Implements the u-blox DDC (I2C) interface and UBX binary protocol
 * for configuration and data retrieval.  Register addresses and protocol
 * details follow the u-blox M8 Receiver Description (UBX-13003221).
 *
 * In SIMULATION_MODE the driver returns mock GNSS data without
 * touching the I2C bus.
 *
 * @author UniSat CubeSat Team
 * @version 1.0.0
 */

#include "ublox.h"
#include <string.h>

/* ───────────── Platform I2C Abstraction ───────────── */

__attribute__((weak))
int UBLOX_Platform_I2C_Write(void *handle, uint8_t addr,
                              uint8_t reg, const uint8_t *data, uint16_t len)
{
    (void)handle; (void)addr; (void)reg; (void)data; (void)len;
    return -1;
}

__attribute__((weak))
int UBLOX_Platform_I2C_Read(void *handle, uint8_t addr,
                             uint8_t reg, uint8_t *data, uint16_t len)
{
    (void)handle; (void)addr; (void)reg; (void)data; (void)len;
    return -1;
}

/**
 * @brief Platform-provided raw I2C write (no register address).
 *
 * Used to send UBX frames where the first byte is part of the payload,
 * not a register address.
 */
__attribute__((weak))
int UBLOX_Platform_I2C_WriteRaw(void *handle, uint8_t addr,
                                 const uint8_t *data, uint16_t len)
{
    (void)handle; (void)addr; (void)data; (void)len;
    return -1;
}

__attribute__((weak))
void UBLOX_Platform_Delay(uint32_t ms)
{
    (void)ms;
}

/* ───────────── Internal Helpers ───────────── */

/**
 * @brief Read from a DDC register with retry logic.
 */
__attribute__((unused)) static UBLOX_Status_t ublox_read_reg(UBLOX_Handle_t *dev,
                                      uint8_t reg, uint8_t *buf, uint16_t len)
{
#ifdef SIMULATION_MODE
    (void)dev; (void)reg;
    memset(buf, 0, len);
    return UBLOX_OK;
#else
    for (uint8_t attempt = 0; attempt < UBLOX_MAX_RETRIES; attempt++) {
        if (UBLOX_Platform_I2C_Read(dev->i2c_handle, dev->addr,
                                     reg, buf, len) == 0) {
            return UBLOX_OK;
        }
        UBLOX_Platform_Delay(5);
    }
    return UBLOX_ERR_I2C;
#endif
}

/**
 * @brief Send raw bytes to the DDC port with retry logic.
 */
__attribute__((unused)) static UBLOX_Status_t ublox_write_raw(UBLOX_Handle_t *dev,
                                       const uint8_t *data, uint16_t len)
{
#ifdef SIMULATION_MODE
    (void)dev; (void)data; (void)len;
    return UBLOX_OK;
#else
    for (uint8_t attempt = 0; attempt < UBLOX_MAX_RETRIES; attempt++) {
        if (UBLOX_Platform_I2C_WriteRaw(dev->i2c_handle, dev->addr,
                                         data, len) == 0) {
            return UBLOX_OK;
        }
        UBLOX_Platform_Delay(5);
    }
    return UBLOX_ERR_I2C;
#endif
}

/**
 * @brief Compute UBX checksum (Fletcher-8 over class, id, length, payload).
 */
__attribute__((unused)) static void ublox_checksum(const uint8_t *data, uint16_t len,
                            uint8_t *ck_a, uint8_t *ck_b)
{
    *ck_a = 0;
    *ck_b = 0;
    for (uint16_t i = 0; i < len; i++) {
        *ck_a += data[i];
        *ck_b += *ck_a;
    }
}

/* ───────────── Public API ───────────── */

UBLOX_Status_t UBLOX_Init(UBLOX_Handle_t *dev)
{
    if (!dev) return UBLOX_ERR_I2C;

#ifdef SIMULATION_MODE
    dev->initialized = true;
    return UBLOX_OK;
#else
    if (!dev->i2c_handle) return UBLOX_ERR_I2C;

    UBLOX_Status_t st;

    /* Verify communication by reading bytes-available register */
    uint16_t avail = 0;
    st = UBLOX_BytesAvailable(dev, &avail);
    if (st != UBLOX_OK) return st;

    /*
     * Configure DDC port (UBX-CFG-PRT):
     * - Disable NMEA output on DDC
     * - Enable UBX input + output
     *
     * Payload (20 bytes):
     *   portID=0 (DDC), txReady=0, mode=0x42<<1 (addr),
     *   reserved=0, inProtoMask=0x0001 (UBX only),
     *   outProtoMask=0x0001 (UBX only), flags=0, reserved2=0
     */
    uint8_t cfg_prt[20];
    memset(cfg_prt, 0, sizeof(cfg_prt));
    cfg_prt[0]  = 0x00;               /* portID = DDC (I2C) */
    cfg_prt[4]  = (UBLOX_I2C_DEFAULT_ADDR << 1); /* slave address in mode field */
    cfg_prt[12] = 0x01; cfg_prt[13] = 0x00; /* inProtoMask: UBX only */
    cfg_prt[14] = 0x01; cfg_prt[15] = 0x00; /* outProtoMask: UBX only */

    st = UBLOX_Configure(dev, UBLOX_UBX_CLASS_CFG, UBLOX_UBX_CFG_PRT,
                          cfg_prt, sizeof(cfg_prt));
    if (st != UBLOX_OK) return st;
    UBLOX_Platform_Delay(100);

    /*
     * Set navigation rate to 1 Hz (UBX-CFG-RATE):
     *   measRate=1000ms, navRate=1, timeRef=GPS
     */
    uint8_t cfg_rate[6] = {
        0xE8, 0x03,  /* measRate = 1000 ms (little-endian) */
        0x01, 0x00,  /* navRate = 1 cycle */
        0x01, 0x00   /* timeRef = GPS time */
    };
    st = UBLOX_Configure(dev, UBLOX_UBX_CLASS_CFG, UBLOX_UBX_CFG_RATE,
                          cfg_rate, sizeof(cfg_rate));
    if (st != UBLOX_OK) return st;

    /*
     * Enable NAV-PVT message on DDC port (UBX-CFG-MSG):
     *   msgClass=0x01, msgID=0x07, rate[DDC]=1
     */
    uint8_t cfg_msg[8];
    memset(cfg_msg, 0, sizeof(cfg_msg));
    cfg_msg[0] = UBLOX_UBX_CLASS_NAV;
    cfg_msg[1] = UBLOX_UBX_NAV_PVT;
    cfg_msg[2] = 1; /* DDC port rate = every navigation solution */

    st = UBLOX_Configure(dev, UBLOX_UBX_CLASS_CFG, UBLOX_UBX_CFG_MSG,
                          cfg_msg, sizeof(cfg_msg));
    if (st != UBLOX_OK) return st;

    dev->initialized = true;
    return UBLOX_OK;
#endif
}

UBLOX_Status_t UBLOX_ReadByte(UBLOX_Handle_t *dev, uint8_t *byte)
{
    if (!dev || !dev->initialized || !byte) return UBLOX_ERR_I2C;

#ifdef SIMULATION_MODE
    /* Return padding byte (0xFF means no data in u-blox DDC protocol) */
    *byte = 0xFF;
    return UBLOX_ERR_NO_DATA;
#else
    /* Check if data is available first */
    uint16_t avail = 0;
    UBLOX_Status_t st = UBLOX_BytesAvailable(dev, &avail);
    if (st != UBLOX_OK) return st;
    if (avail == 0) return UBLOX_ERR_NO_DATA;

    /* Read one byte from the data stream register */
    return ublox_read_reg(dev, UBLOX_REG_DATA_STREAM, byte, 1);
#endif
}

UBLOX_Status_t UBLOX_ReadBytes(UBLOX_Handle_t *dev, uint8_t *buf,
                                uint16_t len, uint16_t *read)
{
    if (!dev || !dev->initialized || !buf || !read) return UBLOX_ERR_I2C;

#ifdef SIMULATION_MODE
    (void)len;   /* SIM path doesn't draw from the bus — len is
                  * still part of the public API for target builds. */
    *read = 0;
    return UBLOX_ERR_NO_DATA;
#else
    uint16_t avail = 0;
    UBLOX_Status_t st = UBLOX_BytesAvailable(dev, &avail);
    if (st != UBLOX_OK) return st;

    if (avail == 0) {
        *read = 0;
        return UBLOX_ERR_NO_DATA;
    }

    /* Read the lesser of available bytes and requested length */
    uint16_t to_read = (avail < len) ? avail : len;
    st = ublox_read_reg(dev, UBLOX_REG_DATA_STREAM, buf, to_read);
    if (st != UBLOX_OK) return st;

    *read = to_read;
    return UBLOX_OK;
#endif
}

UBLOX_Status_t UBLOX_BytesAvailable(UBLOX_Handle_t *dev, uint16_t *avail)
{
    if (!dev || !avail) return UBLOX_ERR_I2C;

#ifdef SIMULATION_MODE
    *avail = 0;
    return UBLOX_OK;
#else
    uint8_t buf[2];
    UBLOX_Status_t st = ublox_read_reg(dev, UBLOX_REG_BYTES_HI, buf, 2);
    if (st != UBLOX_OK) return st;

    /* Big-endian: buf[0] = high byte, buf[1] = low byte */
    *avail = (uint16_t)(buf[0] << 8 | buf[1]);

    /* u-blox returns 0xFFFF when no device is present */
    if (*avail == 0xFFFF) {
        *avail = 0;
        return UBLOX_ERR_I2C;
    }

    return UBLOX_OK;
#endif
}

UBLOX_Status_t UBLOX_Configure(UBLOX_Handle_t *dev,
                                uint8_t cls, uint8_t id,
                                const uint8_t *payload, uint16_t payload_len)
{
    if (!dev) return UBLOX_ERR_I2C;

#ifdef SIMULATION_MODE
    (void)cls; (void)id; (void)payload; (void)payload_len;
    return UBLOX_OK;
#else
    /*
     * UBX frame format:
     *   [SYNC1][SYNC2][CLASS][ID][LEN_L][LEN_H][PAYLOAD...][CK_A][CK_B]
     *
     * Total frame length = 8 + payload_len
     */
    uint16_t frame_len = 8 + payload_len;
    uint8_t frame[frame_len];

    frame[0] = UBLOX_UBX_SYNC1;
    frame[1] = UBLOX_UBX_SYNC2;
    frame[2] = cls;
    frame[3] = id;
    frame[4] = (uint8_t)(payload_len & 0xFF);
    frame[5] = (uint8_t)(payload_len >> 8);

    if (payload && payload_len > 0) {
        memcpy(&frame[6], payload, payload_len);
    }

    /* Checksum over: class, id, length, payload */
    uint8_t ck_a, ck_b;
    ublox_checksum(&frame[2], 4 + payload_len, &ck_a, &ck_b);
    frame[6 + payload_len] = ck_a;
    frame[7 + payload_len] = ck_b;

    return ublox_write_raw(dev, frame, frame_len);
#endif
}

UBLOX_Status_t UBLOX_SelfTest(UBLOX_Handle_t *dev)
{
    if (!dev || !dev->initialized) return UBLOX_ERR_I2C;

#ifdef SIMULATION_MODE
    return UBLOX_OK;
#else
    /* Verify we can read the bytes-available register without error */
    uint16_t avail = 0;
    UBLOX_Status_t st = UBLOX_BytesAvailable(dev, &avail);
    if (st != UBLOX_OK) return UBLOX_ERR_SELF_TEST;

    /*
     * Poll MON-VER to verify the receiver responds to UBX commands.
     * Send a poll request (empty payload) and wait for a response.
     */
    st = UBLOX_Configure(dev, UBLOX_UBX_CLASS_MON, UBLOX_UBX_MON_VER, NULL, 0);
    if (st != UBLOX_OK) return UBLOX_ERR_SELF_TEST;

    /* Wait up to 1 second for a response */
    uint16_t timeout = 100;
    do {
        UBLOX_Platform_Delay(10);
        st = UBLOX_BytesAvailable(dev, &avail);
        if (st != UBLOX_OK) return UBLOX_ERR_SELF_TEST;
        if (avail > 0) return UBLOX_OK;
    } while (--timeout);

    /* No response within timeout — receiver may be in cold start */
    return UBLOX_ERR_SELF_TEST;
#endif
}
