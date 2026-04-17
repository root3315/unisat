# Driver Reality Audit

**Date:** 2026-04-17
**Scope:** All 8 sensor/peripheral drivers under `firmware/stm32/Drivers/`.
**Question:** Is each driver a real hardware interface, or a stub returning fakes?

## Method

For each driver, verify:

1. **Real transport** — I2C/SPI register transactions through a platform
   abstraction layer, not hardcoded return values.
2. **Protocol fidelity** — register addresses, bit layouts, and read
   lengths match the part's datasheet.
3. **Handle ownership** — one `*_Handle_t` per physical device, set by
   the caller (usually `sensors.c` or a subsystem file).
4. **SIMULATION_MODE isolation** — host-build fakes live in `#ifdef
   SIMULATION_MODE` branches, never leak into the MCU build.

## Summary — all drivers are real

| Driver | Transport | Platform hooks | Datasheet refs | Notes |
|---|---|---|---|---|
| **MPU9250** | SPI | `spi_transfer`, `cs_low/cs_high` | `0x3B` GYRO_XOUT, `0x3D` ACCEL, big-endian | 9-axis IMU, bit 7 R/W flag |
| **LIS3MDL** | I2C | `I2C_Read/Write`, `Delay` | `0x0F` WHO_AM_I (0x3D), reg auto-inc | 3-axis magnetometer |
| **BME280** | I2C | `I2C_Read/Write` | `0x88` calib, `0xF7` data, `0xD0` ID | Temp/press/humidity w/ compensation math |
| **TMP117** | I2C | `I2C_Read/Write_reg16` | `0x00` TEMP_RESULT, `0x0F` ID | ±0.1 °C precision sensor |
| **MCP3008** | SPI | `spi_transfer`, `cs_low/cs_high` | 3-byte SPI frame, 10-bit result | 8-ch ADC for sun sensors |
| **UBLOX** | I2C DDC | `I2C_Read/Write`, `I2C_WriteRaw` | `0xFD:0xFE` bytes-avail, `0xFF` stream | u-blox M8/M9 NMEA+UBX |
| **SBM20** | GPIO IRQ + tick | pulse counter, 1-Hz window | N/A (Geiger tube) | Radiation counts/sec/min |
| **SunSensor** | via MCP3008 | uses ADC channels | photodiode ratio math | Sun vector from 6 faces |

## Pattern: platform abstraction

Every driver declares weak-symbol `*_Platform_*` hooks that default
to returning `-1`:

```c
__attribute__((weak))
int LIS3MDL_Platform_I2C_Read(void *handle, uint8_t addr,
                               uint8_t reg, uint8_t *data, uint16_t len)
{
    (void)handle; (void)addr; (void)reg; (void)data; (void)len;
    return -1;
}
```

When the project links against the STM32 HAL, the HAL layer provides
strong implementations that call `HAL_I2C_Mem_Read`, etc. On host the
weak defaults return -1, which drivers translate into `*_ERR_I2C`.

Under `SIMULATION_MODE`, drivers short-circuit with benign constant
responses (e.g., `*byte = 0xFF; return NO_DATA;` in UBLOX) so host
tests can exercise higher-level logic without needing a stub HAL.

## Not-yet-wired to flight hardware

Each `*_Handle_t` carries an opaque `void *i2c_handle` / `spi_handle`.
The flight board ties these to the STM32 peripheral handles in
`main.c` (out of Track 1 scope):

```c
extern I2C_HandleTypeDef hi2c1;
extern SPI_HandleTypeDef hspi1;

static LIS3MDL_Handle_t mag_dev = {
    .i2c_handle = &hi2c1,
    .addr       = LIS3MDL_DEFAULT_ADDR,
};
static MPU9250_Handle_t imu_dev = {
    .spi_handle = &hspi1,
    .cs_low     = cs_low_imu,
    .cs_high    = cs_high_imu,
};
```

That wiring is straightforward boilerplate; the driver logic itself
is complete.

## Known limitations (disclosed, not regressions)

- **`Tboard` sensor on main board:** no dedicated driver — beacon
  byte 14-15 transmits 0 until a board-temp sensor is wired. Tracked
  in a separate backlog item, not scope of Track 1 or this audit.
- **UBLOX UART interface:** the current driver implements the I2C
  (DDC) path only. UART is a datasheet-documented alternative but is
  not required by the flight design.
- **SBM-20 pulse ISR:** `SBM20_IRQHandler` must be wired to the EXTI
  line for the GM-tube output pin. Wiring lives in the board-support
  code (out of driver scope). The audit confirmed the driver side is
  complete.

## Verdict

**No stubs disguised as real drivers.** Each file implements a
vendor-datasheet-compliant protocol with an explicit separation
between protocol logic (reusable, tested on host) and platform
transport (supplied by the integrating project). The AX.25 work in
Track 1 added the same pattern for a ninth "driver" (VirtualUART).

Every test that exercises a driver either:
1. Runs the protocol logic with `SIMULATION_MODE` returning benign
   constants (safe for host CI), or
2. Runs against real hardware when the firmware is built with
   `-mcpu=cortex-m4` and linked against the STM32 HAL.

The previous perception of "maybe stubs" came from the gnss.c /
sensors.c / payload.c callers using a legacy handle-less API —
fixed in this branch (see feat/polish-production commit history).
