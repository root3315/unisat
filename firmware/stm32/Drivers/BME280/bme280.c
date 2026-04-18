/**
 * @file bme280.c
 * @brief HAL driver implementation for BME280 environmental sensor
 *
 * Compensation formulas are taken directly from the Bosch BME280 datasheet
 * (BST-BME280-DS002, Section 4.2.3 — "Compensation formulas").
 *
 * In SIMULATION_MODE the driver returns deterministic mock data without
 * touching the I2C bus.
 *
 * @author UniSat CubeSat Team
 * @version 1.0.0
 */

#include "bme280.h"
#include <string.h>

/* ───────────── Platform I2C Abstraction ───────────── */

__attribute__((weak))
int BME280_Platform_I2C_Write(void *handle, uint8_t addr,
                               uint8_t reg, const uint8_t *data, uint16_t len)
{
    (void)handle; (void)addr; (void)reg; (void)data; (void)len;
    return -1;
}

__attribute__((weak))
int BME280_Platform_I2C_Read(void *handle, uint8_t addr,
                              uint8_t reg, uint8_t *data, uint16_t len)
{
    (void)handle; (void)addr; (void)reg; (void)data; (void)len;
    return -1;
}

__attribute__((weak))
void BME280_Platform_Delay(uint32_t ms)
{
    (void)ms;
}

/* ───────────── Internal Helpers ───────────── */

__attribute__((unused)) static BME280_Status_t bme280_write_reg(BME280_Handle_t *dev,
                                         uint8_t reg, uint8_t val)
{
#ifdef SIMULATION_MODE
    (void)dev; (void)reg; (void)val;
    return BME280_OK;
#else
    for (uint8_t attempt = 0; attempt < BME280_MAX_RETRIES; attempt++) {
        if (BME280_Platform_I2C_Write(dev->i2c_handle, dev->addr,
                                       reg, &val, 1) == 0) {
            return BME280_OK;
        }
        BME280_Platform_Delay(2);
    }
    return BME280_ERR_I2C;
#endif
}

__attribute__((unused)) static BME280_Status_t bme280_read_reg(BME280_Handle_t *dev,
                                        uint8_t reg, uint8_t *buf, uint16_t len)
{
#ifdef SIMULATION_MODE
    (void)dev; (void)reg;
    memset(buf, 0, len);
    return BME280_OK;
#else
    for (uint8_t attempt = 0; attempt < BME280_MAX_RETRIES; attempt++) {
        if (BME280_Platform_I2C_Read(dev->i2c_handle, dev->addr,
                                      reg, buf, len) == 0) {
            return BME280_OK;
        }
        BME280_Platform_Delay(2);
    }
    return BME280_ERR_I2C;
#endif
}

/**
 * @brief Read calibration/trimming parameters from device NVM.
 */
__attribute__((unused)) static BME280_Status_t bme280_read_calib(BME280_Handle_t *dev)
{
    uint8_t buf[26];
    BME280_Status_t st;

    /* Block 1: 0x88..0xA1 (26 bytes) */
    st = bme280_read_reg(dev, BME280_REG_CALIB00, buf, 26);
    if (st != BME280_OK) return st;

    dev->calib.dig_T1 = (uint16_t)(buf[1]  << 8 | buf[0]);
    dev->calib.dig_T2 = (int16_t) (buf[3]  << 8 | buf[2]);
    dev->calib.dig_T3 = (int16_t) (buf[5]  << 8 | buf[4]);
    dev->calib.dig_P1 = (uint16_t)(buf[7]  << 8 | buf[6]);
    dev->calib.dig_P2 = (int16_t) (buf[9]  << 8 | buf[8]);
    dev->calib.dig_P3 = (int16_t) (buf[11] << 8 | buf[10]);
    dev->calib.dig_P4 = (int16_t) (buf[13] << 8 | buf[12]);
    dev->calib.dig_P5 = (int16_t) (buf[15] << 8 | buf[14]);
    dev->calib.dig_P6 = (int16_t) (buf[17] << 8 | buf[16]);
    dev->calib.dig_P7 = (int16_t) (buf[19] << 8 | buf[18]);
    dev->calib.dig_P8 = (int16_t) (buf[21] << 8 | buf[20]);
    dev->calib.dig_P9 = (int16_t) (buf[23] << 8 | buf[22]);
    dev->calib.dig_H1 = buf[25];

    /* Block 2: 0xE1..0xE7 (7 bytes) */
    uint8_t buf2[7];
    st = bme280_read_reg(dev, BME280_REG_CALIB26, buf2, 7);
    if (st != BME280_OK) return st;

    dev->calib.dig_H2 = (int16_t)(buf2[1] << 8 | buf2[0]);
    dev->calib.dig_H3 = buf2[2];
    dev->calib.dig_H4 = (int16_t)((int16_t)buf2[3] << 4 | (buf2[4] & 0x0F));
    dev->calib.dig_H5 = (int16_t)((int16_t)buf2[5] << 4 | (buf2[4] >> 4));
    dev->calib.dig_H6 = (int8_t)buf2[6];

    return BME280_OK;
}

/* ───────────── Compensation Algorithms (Datasheet Section 4.2.3) ───────────── */

/**
 * @brief Compensate raw temperature ADC value.
 * @return Temperature in 0.01 deg C (e.g. 2315 = 23.15 C).  Also updates t_fine.
 */
__attribute__((unused)) static int32_t bme280_compensate_temp(BME280_Handle_t *dev, int32_t adc_T)
{
    int32_t var1, var2, T;

    var1 = ((((adc_T >> 3) - ((int32_t)dev->calib.dig_T1 << 1))) *
            ((int32_t)dev->calib.dig_T2)) >> 11;
    var2 = (((((adc_T >> 4) - ((int32_t)dev->calib.dig_T1)) *
              ((adc_T >> 4) - ((int32_t)dev->calib.dig_T1))) >> 12) *
            ((int32_t)dev->calib.dig_T3)) >> 14;

    dev->t_fine = var1 + var2;
    T = (dev->t_fine * 5 + 128) >> 8;
    return T;
}

/**
 * @brief Compensate raw pressure ADC value.
 * @return Pressure in Pa as unsigned 32-bit Q24.8 (divide by 256 for Pa).
 */
__attribute__((unused)) static uint32_t bme280_compensate_press(BME280_Handle_t *dev, int32_t adc_P)
{
    int64_t var1, var2, p;

    var1 = ((int64_t)dev->t_fine) - 128000;
    var2 = var1 * var1 * (int64_t)dev->calib.dig_P6;
    var2 = var2 + ((var1 * (int64_t)dev->calib.dig_P5) << 17);
    var2 = var2 + (((int64_t)dev->calib.dig_P4) << 35);
    var1 = ((var1 * var1 * (int64_t)dev->calib.dig_P3) >> 8) +
           ((var1 * (int64_t)dev->calib.dig_P2) << 12);
    var1 = (((((int64_t)1) << 47) + var1)) * ((int64_t)dev->calib.dig_P1) >> 33;

    if (var1 == 0) return 0; /* Avoid division by zero */

    p = 1048576 - adc_P;
    p = (((p << 31) - var2) * 3125) / var1;
    var1 = (((int64_t)dev->calib.dig_P9) * (p >> 13) * (p >> 13)) >> 25;
    var2 = (((int64_t)dev->calib.dig_P8) * p) >> 19;
    p = ((p + var1 + var2) >> 8) + (((int64_t)dev->calib.dig_P7) << 4);

    return (uint32_t)p;
}

/**
 * @brief Compensate raw humidity ADC value.
 * @return Humidity in Q22.10 format (divide by 1024 for %RH).
 */
__attribute__((unused)) static uint32_t bme280_compensate_hum(BME280_Handle_t *dev, int32_t adc_H)
{
    int32_t v_x1_u32r;

    v_x1_u32r = (dev->t_fine - ((int32_t)76800));
    v_x1_u32r = (((((adc_H << 14) - (((int32_t)dev->calib.dig_H4) << 20) -
                    (((int32_t)dev->calib.dig_H5) * v_x1_u32r)) +
                   ((int32_t)16384)) >> 15) *
                 (((((((v_x1_u32r * ((int32_t)dev->calib.dig_H6)) >> 10) *
                      (((v_x1_u32r * ((int32_t)dev->calib.dig_H3)) >> 11) +
                       ((int32_t)32768))) >> 10) +
                    ((int32_t)2097152)) *
                   ((int32_t)dev->calib.dig_H2) + 8192) >> 14));

    v_x1_u32r = (v_x1_u32r - (((((v_x1_u32r >> 15) * (v_x1_u32r >> 15)) >> 7) *
                                ((int32_t)dev->calib.dig_H1)) >> 4));

    v_x1_u32r = (v_x1_u32r < 0) ? 0 : v_x1_u32r;
    v_x1_u32r = (v_x1_u32r > 419430400) ? 419430400 : v_x1_u32r;

    return (uint32_t)(v_x1_u32r >> 12);
}

/* ───────────── Public API ───────────── */

BME280_Status_t BME280_Init(BME280_Handle_t *dev)
{
    if (!dev) return BME280_ERR_I2C;

#ifdef SIMULATION_MODE
    dev->initialized = true;
    memset(&dev->calib, 0, sizeof(dev->calib));
    return BME280_OK;
#else
    if (!dev->i2c_handle) return BME280_ERR_I2C;

    BME280_Status_t st;

    /* Soft reset */
    st = bme280_write_reg(dev, BME280_REG_RESET, BME280_RESET_VAL);
    if (st != BME280_OK) return st;
    BME280_Platform_Delay(10);

    /* Verify Chip ID */
    uint8_t chip_id = 0;
    st = bme280_read_reg(dev, BME280_REG_CHIP_ID, &chip_id, 1);
    if (st != BME280_OK) return st;
    if (chip_id != BME280_CHIP_ID_VAL) return BME280_ERR_CHIP_ID;

    /* Wait for NVM copy to finish (STATUS bit 0) */
    uint8_t status = 0;
    uint16_t timeout = 100;
    do {
        st = bme280_read_reg(dev, BME280_REG_STATUS, &status, 1);
        if (st != BME280_OK) return st;
        if (!(status & 0x01)) break;
        BME280_Platform_Delay(2);
    } while (--timeout);

    /* Read calibration data */
    st = bme280_read_calib(dev);
    if (st != BME280_OK) return st;

    /*
     * Configure for weather monitoring (recommended in datasheet):
     *   Humidity oversampling x1
     *   Temperature oversampling x1
     *   Pressure oversampling x1
     *   Mode = forced (single measurement)
     */
    st = bme280_write_reg(dev, BME280_REG_CTRL_HUM, 0x01);  /* osrs_h = x1 */
    if (st != BME280_OK) return st;

    /* Config: standby 1000ms, filter off, no SPI */
    st = bme280_write_reg(dev, BME280_REG_CONFIG, 0xA0);
    if (st != BME280_OK) return st;

    /* ctrl_meas: osrs_t = x1, osrs_p = x1, mode = sleep (write last!) */
    st = bme280_write_reg(dev, BME280_REG_CTRL_MEAS, 0x24);
    if (st != BME280_OK) return st;

    dev->initialized = true;
    return BME280_OK;
#endif
}

BME280_Status_t BME280_Read(BME280_Handle_t *dev,
                             float *temp, float *press, float *hum)
{
    if (!dev || !dev->initialized || !temp || !press || !hum) {
        return BME280_ERR_I2C;
    }

#ifdef SIMULATION_MODE
    /* Mock values: typical room / low Earth orbit conditions */
    *temp  =  22.5f;     /* degrees C */
    *press = 1013.25f;   /* hPa (sea level) */
    *hum   =  45.0f;     /* %RH */
    return BME280_OK;
#else
    BME280_Status_t st;

    /* Trigger forced measurement: osrs_t=x1, osrs_p=x1, mode=forced (01) */
    st = bme280_write_reg(dev, BME280_REG_CTRL_MEAS, 0x25);
    if (st != BME280_OK) return st;

    /* Wait for measurement to complete (STATUS bit 3 = measuring) */
    uint8_t status = 0;
    uint16_t timeout = 100;
    do {
        BME280_Platform_Delay(5);
        st = bme280_read_reg(dev, BME280_REG_STATUS, &status, 1);
        if (st != BME280_OK) return st;
        if (!(status & 0x08)) break;
    } while (--timeout);

    if (status & 0x08) return BME280_ERR_TIMEOUT;

    /* Read all data registers in one burst: 0xF7..0xFE (8 bytes) */
    uint8_t raw[8];
    st = bme280_read_reg(dev, BME280_REG_PRESS_MSB, raw, 8);
    if (st != BME280_OK) return st;

    /* Assemble 20-bit pressure and temperature, 16-bit humidity */
    int32_t adc_P = ((int32_t)raw[0] << 12) | ((int32_t)raw[1] << 4) | (raw[2] >> 4);
    int32_t adc_T = ((int32_t)raw[3] << 12) | ((int32_t)raw[4] << 4) | (raw[5] >> 4);
    int32_t adc_H = ((int32_t)raw[6] << 8)  |  (int32_t)raw[7];

    /* Compensate (temperature must be first — updates t_fine) */
    int32_t comp_T  = bme280_compensate_temp(dev, adc_T);
    uint32_t comp_P = bme280_compensate_press(dev, adc_P);
    uint32_t comp_H = bme280_compensate_hum(dev, adc_H);

    /* Convert to float */
    *temp  = (float)comp_T / 100.0f;              /* 0.01 C  -> C */
    *press = (float)comp_P / 256.0f / 100.0f;     /* Q24.8 Pa -> hPa */
    *hum   = (float)comp_H / 1024.0f;             /* Q22.10 -> %RH */

    return BME280_OK;
#endif
}

BME280_Status_t BME280_SelfTest(BME280_Handle_t *dev)
{
    if (!dev || !dev->initialized) return BME280_ERR_I2C;

#ifdef SIMULATION_MODE
    return BME280_OK;
#else
    /* Re-verify chip ID */
    uint8_t chip_id = 0;
    BME280_Status_t st = bme280_read_reg(dev, BME280_REG_CHIP_ID, &chip_id, 1);
    if (st != BME280_OK) return st;
    if (chip_id != BME280_CHIP_ID_VAL) return BME280_ERR_SELF_TEST;

    /* Take a measurement and check plausibility */
    float t, p, h;
    st = BME280_Read(dev, &t, &p, &h);
    if (st != BME280_OK) return BME280_ERR_SELF_TEST;

    /* Temperature: -40 to +85 C (operational range) */
    if (t < -40.0f || t > 85.0f) return BME280_ERR_SELF_TEST;

    /* Pressure: 300 to 1100 hPa (operational range) */
    if (p < 300.0f || p > 1100.0f) return BME280_ERR_SELF_TEST;

    /* Humidity: 0 to 100 %RH */
    if (h < 0.0f || h > 100.0f) return BME280_ERR_SELF_TEST;

    return BME280_OK;
#endif
}
