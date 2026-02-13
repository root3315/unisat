/**
 * @file mcp3008.c
 * @brief HAL driver implementation for MCP3008 10-bit 8-channel ADC (SPI)
 *
 * SPI command format and timing follow the Microchip MCP3008 datasheet
 * (DS21295C).  The 3-byte transfer sequence extracts a 10-bit result
 * from a single-ended channel.
 *
 * In SIMULATION_MODE the driver returns deterministic mock ADC values
 * without touching the SPI bus.
 *
 * @author UniSat CubeSat Team
 * @version 1.0.0
 */

#include "mcp3008.h"
#include <string.h>

/* ───────────── Platform SPI Abstraction ───────────── */

__attribute__((weak))
int MCP3008_Platform_SPI_Transfer(void *handle,
                                   const uint8_t *tx_data,
                                   uint8_t *rx_data,
                                   uint16_t len)
{
    (void)handle; (void)tx_data; (void)rx_data; (void)len;
    return -1;
}

__attribute__((weak))
void MCP3008_Platform_Delay(uint32_t ms)
{
    (void)ms;
}

/* ───────────── Public API ───────────── */

MCP3008_Status_t MCP3008_Init(MCP3008_Handle_t *dev)
{
    if (!dev) return MCP3008_ERR_SPI;

#ifdef SIMULATION_MODE
    dev->initialized = true;
    return MCP3008_OK;
#else
    if (!dev->spi_handle || !dev->cs_low || !dev->cs_high) {
        return MCP3008_ERR_SPI;
    }

    /* Perform a dummy read on channel 0 to synchronize the SPI clock */
    uint16_t dummy = 0;
    MCP3008_Status_t st = MCP3008_Read(dev, 0, &dummy);

    /* Mark as initialized even if dummy read fails (MCP3008 has no WHO_AM_I) */
    dev->initialized = true;

    /* Re-read to confirm SPI is working */
    st = MCP3008_Read(dev, 0, &dummy);
    if (st != MCP3008_OK) {
        dev->initialized = false;
        return st;
    }

    return MCP3008_OK;
#endif
}

MCP3008_Status_t MCP3008_Read(MCP3008_Handle_t *dev,
                               uint8_t channel, uint16_t *value)
{
    if (!dev || !value) return MCP3008_ERR_SPI;
    if (channel >= MCP3008_NUM_CHANNELS) return MCP3008_ERR_CHANNEL;

#ifdef SIMULATION_MODE
    /*
     * Return mock values that simulate 6 sun sensor photodiodes
     * and 2 auxiliary analog channels:
     *   CH0-5: Sun sensor values (varying illumination pattern)
     *   CH6:   Battery voltage divider (~512 = half Vref)
     *   CH7:   Temperature sensor (~300)
     */
    static const uint16_t mock_values[MCP3008_NUM_CHANNELS] = {
        750, 420, 180, 610, 330, 890, 512, 300
    };
    *value = mock_values[channel];
    return MCP3008_OK;
#else
    /*
     * MCP3008 SPI protocol (single-ended):
     *
     *   TX: [0x01] [0x80 | (ch << 4)] [0x00]
     *   RX: [xxxx] [xxxx xx 0 B9 B8]  [B7 B6 B5 B4 B3 B2 B1 B0]
     *
     * The 10-bit result is in the lower 2 bits of byte 1 and all of byte 2.
     */
    uint8_t tx[3] = {
        MCP3008_CMD_START,
        MCP3008_CMD_SINGLE | ((channel & 0x07) << 4),
        0x00
    };
    uint8_t rx[3] = { 0 };

    for (uint8_t attempt = 0; attempt < MCP3008_MAX_RETRIES; attempt++) {
        dev->cs_low();
        int ret = MCP3008_Platform_SPI_Transfer(dev->spi_handle, tx, rx, 3);
        dev->cs_high();

        if (ret == 0) {
            /* Extract 10-bit result */
            *value = (uint16_t)(((rx[1] & 0x03) << 8) | rx[2]);
            return MCP3008_OK;
        }
        MCP3008_Platform_Delay(1);
    }

    return MCP3008_ERR_SPI;
#endif
}

MCP3008_Status_t MCP3008_ReadVoltage(MCP3008_Handle_t *dev,
                                      uint8_t channel, float *voltage)
{
    if (!dev || !voltage) return MCP3008_ERR_SPI;

    uint16_t raw = 0;
    MCP3008_Status_t st = MCP3008_Read(dev, channel, &raw);
    if (st != MCP3008_OK) return st;

    /* Convert: V = raw * Vref / 1023 */
    *voltage = (float)raw * dev->vref / (float)MCP3008_MAX_VALUE;

    return MCP3008_OK;
}

MCP3008_Status_t MCP3008_SelfTest(MCP3008_Handle_t *dev)
{
    if (!dev || !dev->initialized) return MCP3008_ERR_SPI;

#ifdef SIMULATION_MODE
    /* Verify all mock channels return values within 10-bit range */
    for (uint8_t ch = 0; ch < MCP3008_NUM_CHANNELS; ch++) {
        uint16_t val = 0;
        MCP3008_Status_t st = MCP3008_Read(dev, ch, &val);
        if (st != MCP3008_OK) return MCP3008_ERR_SELF_TEST;
        if (val > MCP3008_MAX_VALUE) return MCP3008_ERR_SELF_TEST;
    }
    return MCP3008_OK;
#else
    /* Read all 8 channels and verify values are within 10-bit range */
    for (uint8_t ch = 0; ch < MCP3008_NUM_CHANNELS; ch++) {
        uint16_t val = 0;
        MCP3008_Status_t st = MCP3008_Read(dev, ch, &val);
        if (st != MCP3008_OK) return MCP3008_ERR_SELF_TEST;
        if (val > MCP3008_MAX_VALUE) return MCP3008_ERR_SELF_TEST;
    }

    return MCP3008_OK;
#endif
}
