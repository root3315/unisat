/**
 * @file lis3mdl.c
 * @brief HAL driver implementation for LIS3MDL 3-axis magnetometer
 *
 * Uses I2C to communicate with the LIS3MDL.  Register addresses and
 * conversion factors are taken from the official ST datasheet (DocID026866).
 *
 * In SIMULATION_MODE the driver returns deterministic mock data without
 * touching the I2C bus.
 *
 * @author UniSat CubeSat Team
 * @version 1.0.0
 */

#include "lis3mdl.h"
#include <string.h>
#include <math.h>

/* ───────────── Platform I2C Abstraction ───────────── */

/**
 * @brief Platform-provided I2C write (weak symbol — override per target).
 */
__attribute__((weak))
int LIS3MDL_Platform_I2C_Write(void *handle, uint8_t addr,
                                uint8_t reg, const uint8_t *data, uint16_t len)
{
    (void)handle; (void)addr; (void)reg; (void)data; (void)len;
    return -1; /* Not implemented */
}

/**
 * @brief Platform-provided I2C read (weak symbol — override per target).
 */
__attribute__((weak))
int LIS3MDL_Platform_I2C_Read(void *handle, uint8_t addr,
                               uint8_t reg, uint8_t *data, uint16_t len)
{
    (void)handle; (void)addr; (void)reg; (void)data; (void)len;
    return -1; /* Not implemented */
}

/**
 * @brief Platform-provided millisecond delay (weak symbol).
 */
__attribute__((weak))
void LIS3MDL_Platform_Delay(uint32_t ms)
{
    (void)ms;
}

/* ───────────── Internal Helpers ───────────── */

/**
 * @brief Write a single register with retry logic.
 */
static LIS3MDL_Status_t lis3mdl_write_reg(LIS3MDL_Handle_t *dev,
                                           uint8_t reg, uint8_t val)
{
#ifdef SIMULATION_MODE
    (void)dev; (void)reg; (void)val;
    return LIS3MDL_OK;
#else
    for (uint8_t attempt = 0; attempt < LIS3MDL_MAX_RETRIES; attempt++) {
        if (LIS3MDL_Platform_I2C_Write(dev->i2c_handle, dev->addr,
                                        reg, &val, 1) == 0) {
            return LIS3MDL_OK;
        }
        LIS3MDL_Platform_Delay(2);
    }
    return LIS3MDL_ERR_I2C;
#endif
}

/**
 * @brief Read one or more registers with retry logic.
 */
static LIS3MDL_Status_t lis3mdl_read_reg(LIS3MDL_Handle_t *dev,
                                          uint8_t reg, uint8_t *buf, uint16_t len)
{
#ifdef SIMULATION_MODE
    (void)dev; (void)reg;
    memset(buf, 0, len);
    return LIS3MDL_OK;
#else
    for (uint8_t attempt = 0; attempt < LIS3MDL_MAX_RETRIES; attempt++) {
        if (LIS3MDL_Platform_I2C_Read(dev->i2c_handle, dev->addr,
                                       reg, buf, len) == 0) {
            return LIS3MDL_OK;
        }
        LIS3MDL_Platform_Delay(2);
    }
    return LIS3MDL_ERR_I2C;
#endif
}

/**
 * @brief Compute sensitivity (LSB/gauss) for a given range setting.
 */
static float lis3mdl_sensitivity(LIS3MDL_Range_t range)
{
    switch (range) {
        case LIS3MDL_RANGE_4_GAUSS:  return 6842.0f;
        case LIS3MDL_RANGE_8_GAUSS:  return 3421.0f;
        case LIS3MDL_RANGE_12_GAUSS: return 2281.0f;
        case LIS3MDL_RANGE_16_GAUSS: return 1711.0f;
        default:                      return 6842.0f;
    }
}

/* ───────────── Public API ───────────── */

LIS3MDL_Status_t LIS3MDL_Init(LIS3MDL_Handle_t *dev)
{
    if (!dev || !dev->i2c_handle) {
#ifdef SIMULATION_MODE
        if (dev) {
            dev->range       = LIS3MDL_RANGE_4_GAUSS;
            dev->sensitivity = lis3mdl_sensitivity(dev->range);
            dev->initialized = true;
        }
        return LIS3MDL_OK;
#else
        return LIS3MDL_ERR_I2C;
#endif
    }

    LIS3MDL_Status_t st;

    /* ── Verify WHO_AM_I ── */
    uint8_t who = 0;
    st = lis3mdl_read_reg(dev, LIS3MDL_REG_WHO_AM_I, &who, 1);
    if (st != LIS3MDL_OK) return st;

#ifndef SIMULATION_MODE
    if (who != LIS3MDL_WHO_AM_I_VAL) {
        return LIS3MDL_ERR_WHO_AM_I;
    }
#endif

    /*
     * CTRL_REG1: 0x7C
     *   TEMP_EN = 1 (bit 7)
     *   OM = 11  (ultra-high-performance XY, bits 6-5)
     *   DO = 100 (80 Hz ODR, bits 4-2)
     *   FAST_ODR = 0, ST = 0
     */
    st = lis3mdl_write_reg(dev, LIS3MDL_REG_CTRL_REG1, 0x7C);
    if (st != LIS3MDL_OK) return st;

    /*
     * CTRL_REG2: full-scale = +/- 4 gauss (default)
     */
    dev->range       = LIS3MDL_RANGE_4_GAUSS;
    dev->sensitivity = lis3mdl_sensitivity(dev->range);
    st = lis3mdl_write_reg(dev, LIS3MDL_REG_CTRL_REG2, (uint8_t)dev->range);
    if (st != LIS3MDL_OK) return st;

    /*
     * CTRL_REG3: 0x00 — continuous conversion mode
     */
    st = lis3mdl_write_reg(dev, LIS3MDL_REG_CTRL_REG3, 0x00);
    if (st != LIS3MDL_OK) return st;

    /*
     * CTRL_REG4: 0x0C — ultra-high-performance mode for Z axis
     */
    st = lis3mdl_write_reg(dev, LIS3MDL_REG_CTRL_REG4, 0x0C);
    if (st != LIS3MDL_OK) return st;

    /*
     * CTRL_REG5: 0x40 — block data update (BDU = 1)
     */
    st = lis3mdl_write_reg(dev, LIS3MDL_REG_CTRL_REG5, 0x40);
    if (st != LIS3MDL_OK) return st;

    dev->initialized = true;
    return LIS3MDL_OK;
}

LIS3MDL_Status_t LIS3MDL_ReadMag(LIS3MDL_Handle_t *dev,
                                   float *x, float *y, float *z)
{
    if (!dev || !dev->initialized || !x || !y || !z) {
        return LIS3MDL_ERR_I2C;
    }

#ifdef SIMULATION_MODE
    /* Return mock orbital magnetic field values (microtesla-scale in gauss) */
    *x = 0.25f;
    *y = -0.10f;
    *z = 0.42f;
    return LIS3MDL_OK;
#else
    /* Wait for data ready (STATUS_REG bit 3 = ZYXDA) */
    uint8_t status = 0;
    uint16_t timeout = 200; /* ~200 ms max wait at 80 Hz ODR */
    do {
        LIS3MDL_Status_t st = lis3mdl_read_reg(dev, LIS3MDL_REG_STATUS, &status, 1);
        if (st != LIS3MDL_OK) return st;
        if (status & 0x08) break;
        LIS3MDL_Platform_Delay(1);
    } while (--timeout);

    if (!(status & 0x08)) {
        return LIS3MDL_ERR_TIMEOUT;
    }

    /* Read 6 bytes starting from OUT_X_L (auto-increment via MSB of sub-address) */
    uint8_t raw[6];
    LIS3MDL_Status_t st = lis3mdl_read_reg(dev, LIS3MDL_REG_OUT_X_L | 0x80,
                                             raw, 6);
    if (st != LIS3MDL_OK) return st;

    /* Assemble 16-bit signed values (little-endian) */
    int16_t raw_x = (int16_t)((uint16_t)raw[1] << 8 | raw[0]);
    int16_t raw_y = (int16_t)((uint16_t)raw[3] << 8 | raw[2]);
    int16_t raw_z = (int16_t)((uint16_t)raw[5] << 8 | raw[4]);

    /* Convert to gauss */
    *x = (float)raw_x / dev->sensitivity;
    *y = (float)raw_y / dev->sensitivity;
    *z = (float)raw_z / dev->sensitivity;

    return LIS3MDL_OK;
#endif
}

LIS3MDL_Status_t LIS3MDL_SelfTest(LIS3MDL_Handle_t *dev)
{
    if (!dev || !dev->initialized) {
        return LIS3MDL_ERR_I2C;
    }

#ifdef SIMULATION_MODE
    return LIS3MDL_OK;
#else
    LIS3MDL_Status_t st;

    /* 1. Read baseline output (average of 5 samples) */
    float base_x = 0, base_y = 0, base_z = 0;
    for (int i = 0; i < 5; i++) {
        float bx, by, bz;
        st = LIS3MDL_ReadMag(dev, &bx, &by, &bz);
        if (st != LIS3MDL_OK) return st;
        base_x += bx;  base_y += by;  base_z += bz;
    }
    base_x /= 5.0f;  base_y /= 5.0f;  base_z /= 5.0f;

    /* 2. Enable self-test: CTRL_REG1 bit 0 = ST = 1 */
    st = lis3mdl_write_reg(dev, LIS3MDL_REG_CTRL_REG1, 0x7D);
    if (st != LIS3MDL_OK) return st;
    LIS3MDL_Platform_Delay(60); /* Wait for new data with self-test active */

    /* 3. Read self-test output (average of 5 samples) */
    float st_x = 0, st_y = 0, st_z = 0;
    for (int i = 0; i < 5; i++) {
        float sx, sy, sz;
        st = LIS3MDL_ReadMag(dev, &sx, &sy, &sz);
        if (st != LIS3MDL_OK) return st;
        st_x += sx;  st_y += sy;  st_z += sz;
    }
    st_x /= 5.0f;  st_y /= 5.0f;  st_z /= 5.0f;

    /* 4. Disable self-test: restore original CTRL_REG1 */
    st = lis3mdl_write_reg(dev, LIS3MDL_REG_CTRL_REG1, 0x7C);
    if (st != LIS3MDL_OK) return st;

    /* 5. Check deltas against datasheet limits for +/- 4 gauss:
     *    |delta_x| in [1.0, 3.0] gauss
     *    |delta_y| in [1.0, 3.0] gauss
     *    |delta_z| in [0.1, 1.0] gauss
     */
    float dx = fabsf(st_x - base_x);
    float dy = fabsf(st_y - base_y);
    float dz = fabsf(st_z - base_z);

    if (dx < 1.0f || dx > 3.0f ||
        dy < 1.0f || dy > 3.0f ||
        dz < 0.1f || dz > 1.0f) {
        return LIS3MDL_ERR_SELF_TEST;
    }

    return LIS3MDL_OK;
#endif
}

LIS3MDL_Status_t LIS3MDL_SetRange(LIS3MDL_Handle_t *dev, LIS3MDL_Range_t range)
{
    if (!dev || !dev->initialized) {
        return LIS3MDL_ERR_I2C;
    }

    LIS3MDL_Status_t st = lis3mdl_write_reg(dev, LIS3MDL_REG_CTRL_REG2, (uint8_t)range);
    if (st != LIS3MDL_OK) return st;

    dev->range       = range;
    dev->sensitivity = lis3mdl_sensitivity(range);
    return LIS3MDL_OK;
}
