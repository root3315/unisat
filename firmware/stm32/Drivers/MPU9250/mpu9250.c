/**
 * @file mpu9250.c
 * @brief HAL driver implementation for MPU-9250 9-axis IMU (SPI)
 *
 * Register addresses and sensitivity values follow the InvenSense
 * MPU-9250 Product Specification (PS-MPU-9250A-01, Rev 1.1).
 *
 * In SIMULATION_MODE the driver returns deterministic mock data without
 * touching the SPI bus.
 *
 * @author UniSat CubeSat Team
 * @version 1.0.0
 */

#include "mpu9250.h"
#include <string.h>
#include <math.h>

/* ───────────── Platform SPI Abstraction ───────────── */

/**
 * @brief Platform-provided SPI transfer (weak symbol — override per target).
 *
 * Simultaneously transmits @p tx_data and receives into @p rx_data.
 * CS assertion/de-assertion is handled by the driver via function pointers.
 *
 * @return 0 on success, non-zero on error.
 */
__attribute__((weak))
int MPU9250_Platform_SPI_Transfer(void *handle,
                                   const uint8_t *tx_data,
                                   uint8_t *rx_data,
                                   uint16_t len)
{
    (void)handle; (void)tx_data; (void)rx_data; (void)len;
    return -1;
}

__attribute__((weak))
void MPU9250_Platform_Delay(uint32_t ms)
{
    (void)ms;
}

/* ───────────── Internal Helpers ───────────── */

/**
 * @brief Write a single register via SPI with retry logic.
 */
static MPU9250_Status_t mpu9250_write_reg(MPU9250_Handle_t *dev,
                                            uint8_t reg, uint8_t val)
{
#ifdef SIMULATION_MODE
    (void)dev; (void)reg; (void)val;
    return MPU9250_OK;
#else
    uint8_t tx[2] = { reg & 0x7F, val }; /* Bit 7 = 0 for write */
    uint8_t rx[2];

    for (uint8_t attempt = 0; attempt < MPU9250_MAX_RETRIES; attempt++) {
        dev->cs_low();
        int ret = MPU9250_Platform_SPI_Transfer(dev->spi_handle, tx, rx, 2);
        dev->cs_high();
        if (ret == 0) return MPU9250_OK;
        MPU9250_Platform_Delay(1);
    }
    return MPU9250_ERR_SPI;
#endif
}

/**
 * @brief Read one or more registers via SPI with retry logic.
 */
static MPU9250_Status_t mpu9250_read_reg(MPU9250_Handle_t *dev,
                                           uint8_t reg, uint8_t *buf, uint16_t len)
{
#ifdef SIMULATION_MODE
    (void)dev; (void)reg;
    memset(buf, 0, len);
    return MPU9250_OK;
#else
    /* First byte: register address with read flag (bit 7 = 1) */
    uint8_t tx[len + 1];
    uint8_t rx[len + 1];
    memset(tx, 0, sizeof(tx));
    tx[0] = reg | MPU9250_READ_FLAG;

    for (uint8_t attempt = 0; attempt < MPU9250_MAX_RETRIES; attempt++) {
        dev->cs_low();
        int ret = MPU9250_Platform_SPI_Transfer(dev->spi_handle, tx, rx, len + 1);
        dev->cs_high();
        if (ret == 0) {
            memcpy(buf, &rx[1], len);
            return MPU9250_OK;
        }
        MPU9250_Platform_Delay(1);
    }
    return MPU9250_ERR_SPI;
#endif
}

/**
 * @brief Compute gyroscope sensitivity for a given range.
 */
static float mpu9250_gyro_sensitivity(MPU9250_GyroRange_t range)
{
    switch (range) {
        case MPU9250_GYRO_250DPS:  return 131.0f;
        case MPU9250_GYRO_500DPS:  return 65.5f;
        case MPU9250_GYRO_1000DPS: return 32.8f;
        case MPU9250_GYRO_2000DPS: return 16.4f;
        default:                    return 131.0f;
    }
}

/**
 * @brief Compute accelerometer sensitivity for a given range.
 */
static float mpu9250_accel_sensitivity(MPU9250_AccelRange_t range)
{
    switch (range) {
        case MPU9250_ACCEL_2G:  return 16384.0f;
        case MPU9250_ACCEL_4G:  return 8192.0f;
        case MPU9250_ACCEL_8G:  return 4096.0f;
        case MPU9250_ACCEL_16G: return 2048.0f;
        default:                 return 16384.0f;
    }
}

/* ───────────── Public API ───────────── */

MPU9250_Status_t MPU9250_Init(MPU9250_Handle_t *dev)
{
    if (!dev) return MPU9250_ERR_SPI;

#ifdef SIMULATION_MODE
    dev->gyro_range  = MPU9250_GYRO_250DPS;
    dev->accel_range = MPU9250_ACCEL_2G;
    dev->gyro_sens   = mpu9250_gyro_sensitivity(dev->gyro_range);
    dev->accel_sens  = mpu9250_accel_sensitivity(dev->accel_range);
    dev->initialized = true;
    return MPU9250_OK;
#else
    if (!dev->spi_handle || !dev->cs_low || !dev->cs_high) {
        return MPU9250_ERR_SPI;
    }

    MPU9250_Status_t st;

    /* 1. Reset device: PWR_MGMT_1 bit 7 = H_RESET */
    st = mpu9250_write_reg(dev, MPU9250_REG_PWR_MGMT_1, 0x80);
    if (st != MPU9250_OK) return st;
    MPU9250_Platform_Delay(100); /* Wait for reset to complete */

    /* 2. Wake up: auto-select best clock source (PLL if available) */
    st = mpu9250_write_reg(dev, MPU9250_REG_PWR_MGMT_1, 0x01);
    if (st != MPU9250_OK) return st;
    MPU9250_Platform_Delay(10);

    /* 3. Verify WHO_AM_I */
    uint8_t who = 0;
    st = mpu9250_read_reg(dev, MPU9250_REG_WHO_AM_I, &who, 1);
    if (st != MPU9250_OK) return st;
    if (who != MPU9250_WHO_AM_I_VAL) return MPU9250_ERR_WHO_AM_I;

    /* 4. Configure DLPF: bandwidth 92 Hz for gyro, 99 Hz for accel */
    st = mpu9250_write_reg(dev, MPU9250_REG_CONFIG, 0x02);
    if (st != MPU9250_OK) return st;

    /* 5. Sample rate divider = 0 (1 kHz / (1+0) = 1 kHz) */
    st = mpu9250_write_reg(dev, MPU9250_REG_SMPLRT_DIV, 0x00);
    if (st != MPU9250_OK) return st;

    /* 6. Gyro: +/- 250 dps, FCHOICE_B = 00 (use DLPF) */
    dev->gyro_range = MPU9250_GYRO_250DPS;
    dev->gyro_sens  = mpu9250_gyro_sensitivity(dev->gyro_range);
    st = mpu9250_write_reg(dev, MPU9250_REG_GYRO_CONFIG, (uint8_t)dev->gyro_range);
    if (st != MPU9250_OK) return st;

    /* 7. Accel: +/- 2g */
    dev->accel_range = MPU9250_ACCEL_2G;
    dev->accel_sens  = mpu9250_accel_sensitivity(dev->accel_range);
    st = mpu9250_write_reg(dev, MPU9250_REG_ACCEL_CONFIG, (uint8_t)dev->accel_range);
    if (st != MPU9250_OK) return st;

    /* 8. Accel DLPF: bandwidth 99 Hz */
    st = mpu9250_write_reg(dev, MPU9250_REG_ACCEL_CONFIG2, 0x02);
    if (st != MPU9250_OK) return st;

    /* 9. Enable data ready interrupt */
    st = mpu9250_write_reg(dev, MPU9250_REG_INT_ENABLE, 0x01);
    if (st != MPU9250_OK) return st;

    dev->initialized = true;
    return MPU9250_OK;
#endif
}

MPU9250_Status_t MPU9250_ReadGyro(MPU9250_Handle_t *dev,
                                    float *gx, float *gy, float *gz)
{
    if (!dev || !dev->initialized || !gx || !gy || !gz) {
        return MPU9250_ERR_SPI;
    }

#ifdef SIMULATION_MODE
    /* Mock: near-zero angular rate (satellite in slow tumble) */
    *gx =  0.15f;
    *gy = -0.08f;
    *gz =  0.22f;
    return MPU9250_OK;
#else
    /* Read 6 bytes starting at GYRO_XOUT_H (big-endian) */
    uint8_t raw[6];
    MPU9250_Status_t st = mpu9250_read_reg(dev, MPU9250_REG_GYRO_XOUT_H, raw, 6);
    if (st != MPU9250_OK) return st;

    int16_t raw_gx = (int16_t)((uint16_t)raw[0] << 8 | raw[1]);
    int16_t raw_gy = (int16_t)((uint16_t)raw[2] << 8 | raw[3]);
    int16_t raw_gz = (int16_t)((uint16_t)raw[4] << 8 | raw[5]);

    *gx = (float)raw_gx / dev->gyro_sens;
    *gy = (float)raw_gy / dev->gyro_sens;
    *gz = (float)raw_gz / dev->gyro_sens;

    return MPU9250_OK;
#endif
}

MPU9250_Status_t MPU9250_ReadAccel(MPU9250_Handle_t *dev,
                                     float *ax, float *ay, float *az)
{
    if (!dev || !dev->initialized || !ax || !ay || !az) {
        return MPU9250_ERR_SPI;
    }

#ifdef SIMULATION_MODE
    /* Mock: microgravity with small residual forces */
    *ax =  0.001f;
    *ay = -0.002f;
    *az =  0.003f;
    return MPU9250_OK;
#else
    /* Read 6 bytes starting at ACCEL_XOUT_H (big-endian) */
    uint8_t raw[6];
    MPU9250_Status_t st = mpu9250_read_reg(dev, MPU9250_REG_ACCEL_XOUT_H, raw, 6);
    if (st != MPU9250_OK) return st;

    int16_t raw_ax = (int16_t)((uint16_t)raw[0] << 8 | raw[1]);
    int16_t raw_ay = (int16_t)((uint16_t)raw[2] << 8 | raw[3]);
    int16_t raw_az = (int16_t)((uint16_t)raw[4] << 8 | raw[5]);

    *ax = (float)raw_ax / dev->accel_sens;
    *ay = (float)raw_ay / dev->accel_sens;
    *az = (float)raw_az / dev->accel_sens;

    return MPU9250_OK;
#endif
}

MPU9250_Status_t MPU9250_SelfTest(MPU9250_Handle_t *dev)
{
    if (!dev || !dev->initialized) return MPU9250_ERR_SPI;

#ifdef SIMULATION_MODE
    return MPU9250_OK;
#else
    MPU9250_Status_t st;
    float gx, gy, gz, ax, ay, az;

    /* 1. Read baseline values (average of 10 samples) */
    float base_gx = 0, base_gy = 0, base_gz = 0;
    float base_ax = 0, base_ay = 0, base_az = 0;

    for (int i = 0; i < 10; i++) {
        st = MPU9250_ReadGyro(dev, &gx, &gy, &gz);
        if (st != MPU9250_OK) return MPU9250_ERR_SELF_TEST;
        base_gx += gx;  base_gy += gy;  base_gz += gz;

        st = MPU9250_ReadAccel(dev, &ax, &ay, &az);
        if (st != MPU9250_OK) return MPU9250_ERR_SELF_TEST;
        base_ax += ax;  base_ay += ay;  base_az += az;

        MPU9250_Platform_Delay(2);
    }
    base_gx /= 10.0f;  base_gy /= 10.0f;  base_gz /= 10.0f;
    base_ax /= 10.0f;  base_ay /= 10.0f;  base_az /= 10.0f;

    /* 2. Enable self-test on all axes:
     *    GYRO_CONFIG:  XG_ST=1, YG_ST=1, ZG_ST=1, FS_SEL=00
     *    ACCEL_CONFIG: XA_ST=1, YA_ST=1, ZA_ST=1, AFS_SEL=00
     */
    st = mpu9250_write_reg(dev, MPU9250_REG_GYRO_CONFIG, 0xE0);
    if (st != MPU9250_OK) return MPU9250_ERR_SELF_TEST;
    st = mpu9250_write_reg(dev, MPU9250_REG_ACCEL_CONFIG, 0xE0);
    if (st != MPU9250_OK) return MPU9250_ERR_SELF_TEST;
    MPU9250_Platform_Delay(50);

    /* 3. Read self-test values (average of 10 samples) */
    float st_gx = 0, st_gy = 0, st_gz = 0;
    float st_ax = 0, st_ay = 0, st_az = 0;

    for (int i = 0; i < 10; i++) {
        st = MPU9250_ReadGyro(dev, &gx, &gy, &gz);
        if (st != MPU9250_OK) return MPU9250_ERR_SELF_TEST;
        st_gx += gx;  st_gy += gy;  st_gz += gz;

        st = MPU9250_ReadAccel(dev, &ax, &ay, &az);
        if (st != MPU9250_OK) return MPU9250_ERR_SELF_TEST;
        st_ax += ax;  st_ay += ay;  st_az += az;

        MPU9250_Platform_Delay(2);
    }
    st_gx /= 10.0f;  st_gy /= 10.0f;  st_gz /= 10.0f;
    st_ax /= 10.0f;  st_ay /= 10.0f;  st_az /= 10.0f;

    /* 4. Restore configuration */
    st = mpu9250_write_reg(dev, MPU9250_REG_GYRO_CONFIG, (uint8_t)dev->gyro_range);
    if (st != MPU9250_OK) return MPU9250_ERR_SELF_TEST;
    st = mpu9250_write_reg(dev, MPU9250_REG_ACCEL_CONFIG, (uint8_t)dev->accel_range);
    if (st != MPU9250_OK) return MPU9250_ERR_SELF_TEST;

    /* 5. Verify self-test response is non-trivial (> 0.5 dps and > 0.05 g shift) */
    float dg = fabsf(st_gx - base_gx) + fabsf(st_gy - base_gy) + fabsf(st_gz - base_gz);
    float da = fabsf(st_ax - base_ax) + fabsf(st_ay - base_ay) + fabsf(st_az - base_az);

    if (dg < 0.5f || da < 0.05f) {
        return MPU9250_ERR_SELF_TEST;
    }

    return MPU9250_OK;
#endif
}
