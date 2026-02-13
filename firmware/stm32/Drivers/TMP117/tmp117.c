/**
 * @file tmp117.c
 * @brief HAL driver implementation for TMP117 high-accuracy temperature sensor
 *
 * The TMP117 uses big-endian 16-bit registers.  Temperature is a signed
 * 16-bit value where 1 LSB = 0.0078125 C (7.8125 mC).
 *
 * In SIMULATION_MODE the driver returns deterministic mock data without
 * touching the I2C bus.
 *
 * @author UniSat CubeSat Team
 * @version 1.0.0
 */

#include "tmp117.h"
#include <string.h>

/* ───────────── Platform I2C Abstraction ───────────── */

__attribute__((weak))
int TMP117_Platform_I2C_Write(void *handle, uint8_t addr,
                               uint8_t reg, const uint8_t *data, uint16_t len)
{
    (void)handle; (void)addr; (void)reg; (void)data; (void)len;
    return -1;
}

__attribute__((weak))
int TMP117_Platform_I2C_Read(void *handle, uint8_t addr,
                              uint8_t reg, uint8_t *data, uint16_t len)
{
    (void)handle; (void)addr; (void)reg; (void)data; (void)len;
    return -1;
}

__attribute__((weak))
void TMP117_Platform_Delay(uint32_t ms)
{
    (void)ms;
}

/* ───────────── Internal Helpers ───────────── */

/**
 * @brief Write a 16-bit register (big-endian) with retry logic.
 */
static TMP117_Status_t tmp117_write_reg16(TMP117_Handle_t *dev,
                                           uint8_t reg, uint16_t val)
{
#ifdef SIMULATION_MODE
    (void)dev; (void)reg; (void)val;
    return TMP117_OK;
#else
    uint8_t buf[2] = { (uint8_t)(val >> 8), (uint8_t)(val & 0xFF) };
    for (uint8_t attempt = 0; attempt < TMP117_MAX_RETRIES; attempt++) {
        if (TMP117_Platform_I2C_Write(dev->i2c_handle, dev->addr,
                                       reg, buf, 2) == 0) {
            return TMP117_OK;
        }
        TMP117_Platform_Delay(2);
    }
    return TMP117_ERR_I2C;
#endif
}

/**
 * @brief Read a 16-bit register (big-endian) with retry logic.
 */
static TMP117_Status_t tmp117_read_reg16(TMP117_Handle_t *dev,
                                          uint8_t reg, uint16_t *val)
{
#ifdef SIMULATION_MODE
    (void)dev; (void)reg;
    *val = 0;
    return TMP117_OK;
#else
    uint8_t buf[2];
    for (uint8_t attempt = 0; attempt < TMP117_MAX_RETRIES; attempt++) {
        if (TMP117_Platform_I2C_Read(dev->i2c_handle, dev->addr,
                                      reg, buf, 2) == 0) {
            *val = (uint16_t)(buf[0] << 8 | buf[1]);
            return TMP117_OK;
        }
        TMP117_Platform_Delay(2);
    }
    return TMP117_ERR_I2C;
#endif
}

/* ───────────── Public API ───────────── */

TMP117_Status_t TMP117_Init(TMP117_Handle_t *dev)
{
    if (!dev) return TMP117_ERR_I2C;

#ifdef SIMULATION_MODE
    dev->initialized = true;
    return TMP117_OK;
#else
    if (!dev->i2c_handle) return TMP117_ERR_I2C;

    TMP117_Status_t st;

    /* Soft reset */
    st = tmp117_write_reg16(dev, TMP117_REG_CONFIG, TMP117_CFG_SOFT_RESET);
    if (st != TMP117_OK) return st;
    TMP117_Platform_Delay(5); /* tReset = 2 ms typ. */

    /* Verify Device ID */
    uint16_t dev_id = 0;
    st = tmp117_read_reg16(dev, TMP117_REG_DEVICE_ID, &dev_id);
    if (st != TMP117_OK) return st;
    if (dev_id != TMP117_DEVICE_ID_VAL) return TMP117_ERR_DEVICE_ID;

    /*
     * Configure:
     *   Continuous conversion mode (MOD = 00)
     *   No averaging (AVG = 00)
     *   15.5 ms conversion cycle (CONV = 000)
     * Register value = 0x0000 (all defaults after reset, which is fine)
     */
    st = tmp117_write_reg16(dev, TMP117_REG_CONFIG,
                             TMP117_CFG_MOD_CC | TMP117_CFG_AVG_NONE |
                             TMP117_CFG_CONV_15_5MS);
    if (st != TMP117_OK) return st;

    dev->initialized = true;
    return TMP117_OK;
#endif
}

TMP117_Status_t TMP117_Read(TMP117_Handle_t *dev, float *temp)
{
    if (!dev || !dev->initialized || !temp) {
        return TMP117_ERR_I2C;
    }

#ifdef SIMULATION_MODE
    /* Mock value: typical satellite bus temperature */
    *temp = 21.375f;
    return TMP117_OK;
#else
    TMP117_Status_t st;
    uint16_t cfg = 0;

    /* Wait for data ready (CONFIG bit 13) */
    uint16_t timeout = 200;
    do {
        st = tmp117_read_reg16(dev, TMP117_REG_CONFIG, &cfg);
        if (st != TMP117_OK) return st;
        if (cfg & TMP117_CFG_DATA_READY) break;
        TMP117_Platform_Delay(1);
    } while (--timeout);

    if (!(cfg & TMP117_CFG_DATA_READY)) {
        return TMP117_ERR_TIMEOUT;
    }

    /* Read 16-bit temperature register (big-endian, signed) */
    uint16_t raw = 0;
    st = tmp117_read_reg16(dev, TMP117_REG_TEMP_RESULT, &raw);
    if (st != TMP117_OK) return st;

    /*
     * Convert to Celsius:
     *   T = raw * 0.0078125
     * raw is a signed 16-bit two's complement value.
     */
    int16_t raw_signed = (int16_t)raw;
    *temp = (float)raw_signed * TMP117_RESOLUTION;

    return TMP117_OK;
#endif
}

TMP117_Status_t TMP117_SelfTest(TMP117_Handle_t *dev)
{
    if (!dev || !dev->initialized) return TMP117_ERR_I2C;

#ifdef SIMULATION_MODE
    return TMP117_OK;
#else
    /* Verify device ID */
    uint16_t dev_id = 0;
    TMP117_Status_t st = tmp117_read_reg16(dev, TMP117_REG_DEVICE_ID, &dev_id);
    if (st != TMP117_OK) return TMP117_ERR_SELF_TEST;
    if (dev_id != TMP117_DEVICE_ID_VAL) return TMP117_ERR_SELF_TEST;

    /* Read temperature and check operational range (-55 to +150 C) */
    float t = 0;
    st = TMP117_Read(dev, &t);
    if (st != TMP117_OK) return TMP117_ERR_SELF_TEST;

    if (t < -55.0f || t > 150.0f) return TMP117_ERR_SELF_TEST;

    return TMP117_OK;
#endif
}
