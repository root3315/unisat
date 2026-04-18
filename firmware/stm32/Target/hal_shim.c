/**
 ******************************************************************************
 *  UniSat — weak HAL shim
 *
 *  Provides weak implementations of the STM32Cube HAL entry points the
 *  existing firmware drivers call (HAL_I2C_Mem_Read, HAL_SPI_TransmitReceive,
 *  HAL_UART_Transmit, HAL_UART_Receive, HAL_ADC_*, HAL_Init, …).
 *
 *  Purpose
 *  -------
 *  Until scripts/setup_stm32_hal.sh has been run and STM32CubeF4 HAL
 *  has been placed at firmware/stm32/Drivers/STM32F4xx_HAL_Driver/,
 *  the repo must still link cleanly under arm-none-eabi so CI can
 *  produce a .elf / .bin / size report for the startup + clock code
 *  added in the preceding commits.
 *
 *  Each shim returns HAL_ERROR (or 0 for HAL_GetTick fallback) and
 *  leaves every status-only "init" call a pure no-op. This is the
 *  minimum needed to satisfy the linker — the firmware will not read
 *  sensors or transmit beacons with this shim linked, but the boot,
 *  vector table, fault handlers, and clock tree are all exercised on
 *  real hardware.
 *
 *  Override mechanism
 *  ------------------
 *  Every function is declared __attribute__((weak)), so once the real
 *  STM32Cube HAL .c files are included in the build (CMakeLists.txt
 *  detects them and switches target_sources), their strong symbols
 *  win and the shim is silently replaced. This means the same
 *  firmware source tree builds into either a "does-nothing-on-hw"
 *  smoke-test image or a full production image depending solely on
 *  whether the HAL has been fetched.
 ******************************************************************************
 */

#include <stdint.h>
#include <stddef.h>

/* HAL status codes match the STM32Cube HAL_StatusTypeDef enum so a
 * driver checking == HAL_OK behaves identically regardless of which
 * implementation is linked. Values pulled from stm32f4xx_hal_def.h.
 */
typedef enum {
    HAL_OK       = 0x00U,
    HAL_ERROR    = 0x01U,
    HAL_BUSY     = 0x02U,
    HAL_TIMEOUT  = 0x03U
} HAL_StatusTypeDef;

/* Opaque handle types — drivers only pass pointers, they never
 * dereference fields inside the shim. */
typedef struct I2C_HandleTypeDef_s  I2C_HandleTypeDef;
typedef struct SPI_HandleTypeDef_s  SPI_HandleTypeDef;
typedef struct UART_HandleTypeDef_s UART_HandleTypeDef;
typedef struct ADC_HandleTypeDef_s  ADC_HandleTypeDef;
typedef struct TIM_HandleTypeDef_s  TIM_HandleTypeDef;


/* ==================================================================
 *  Top-level HAL_Init / HAL_DeInit
 * ================================================================== */

__attribute__((weak)) HAL_StatusTypeDef HAL_Init(void)
{
    /* The real HAL_Init enables prefetch + calls HAL_MspInit. Our
     * SystemInit() in system_stm32f4xx.c already configured VTOR and
     * the FPU; flash-prefetch is set by SystemClock_Config(). Nothing
     * else to do in the stub. */
    return HAL_OK;
}

__attribute__((weak)) HAL_StatusTypeDef HAL_DeInit(void)
{
    return HAL_OK;
}


/* ==================================================================
 *  I2C — used by LIS3MDL, BME280, TMP117, u-blox GNSS drivers.
 * ================================================================== */

__attribute__((weak)) HAL_StatusTypeDef HAL_I2C_Init(I2C_HandleTypeDef *h)
{
    (void)h;
    return HAL_OK;
}

__attribute__((weak)) HAL_StatusTypeDef HAL_I2C_Mem_Read(
    I2C_HandleTypeDef *h, uint16_t dev, uint16_t reg,
    uint16_t reg_size, uint8_t *buf, uint16_t len, uint32_t timeout)
{
    (void)h; (void)dev; (void)reg; (void)reg_size;
    (void)buf; (void)len; (void)timeout;
    return HAL_ERROR;
}

__attribute__((weak)) HAL_StatusTypeDef HAL_I2C_Mem_Write(
    I2C_HandleTypeDef *h, uint16_t dev, uint16_t reg,
    uint16_t reg_size, uint8_t *buf, uint16_t len, uint32_t timeout)
{
    (void)h; (void)dev; (void)reg; (void)reg_size;
    (void)buf; (void)len; (void)timeout;
    return HAL_ERROR;
}

__attribute__((weak)) HAL_StatusTypeDef HAL_I2C_Master_Transmit(
    I2C_HandleTypeDef *h, uint16_t dev, uint8_t *buf,
    uint16_t len, uint32_t timeout)
{
    (void)h; (void)dev; (void)buf; (void)len; (void)timeout;
    return HAL_ERROR;
}

__attribute__((weak)) HAL_StatusTypeDef HAL_I2C_Master_Receive(
    I2C_HandleTypeDef *h, uint16_t dev, uint8_t *buf,
    uint16_t len, uint32_t timeout)
{
    (void)h; (void)dev; (void)buf; (void)len; (void)timeout;
    return HAL_ERROR;
}


/* ==================================================================
 *  SPI — used by MPU9250 and MCP3008 drivers.
 * ================================================================== */

__attribute__((weak)) HAL_StatusTypeDef HAL_SPI_Init(SPI_HandleTypeDef *h)
{
    (void)h;
    return HAL_OK;
}

__attribute__((weak)) HAL_StatusTypeDef HAL_SPI_TransmitReceive(
    SPI_HandleTypeDef *h, uint8_t *tx, uint8_t *rx,
    uint16_t len, uint32_t timeout)
{
    (void)h; (void)tx; (void)timeout;
    if (rx != NULL) {
        for (uint16_t i = 0; i < len; ++i) { rx[i] = 0; }
    }
    return HAL_ERROR;
}

__attribute__((weak)) HAL_StatusTypeDef HAL_SPI_Transmit(
    SPI_HandleTypeDef *h, uint8_t *tx, uint16_t len, uint32_t timeout)
{
    (void)h; (void)tx; (void)len; (void)timeout;
    return HAL_ERROR;
}

__attribute__((weak)) HAL_StatusTypeDef HAL_SPI_Receive(
    SPI_HandleTypeDef *h, uint8_t *rx, uint16_t len, uint32_t timeout)
{
    (void)h; (void)timeout;
    if (rx != NULL) {
        for (uint16_t i = 0; i < len; ++i) { rx[i] = 0; }
    }
    return HAL_ERROR;
}


/* ==================================================================
 *  UART — used by the UHF modem and debug VCP.
 * ================================================================== */

__attribute__((weak)) HAL_StatusTypeDef HAL_UART_Init(UART_HandleTypeDef *h)
{
    (void)h;
    return HAL_OK;
}

__attribute__((weak)) HAL_StatusTypeDef HAL_UART_Transmit(
    UART_HandleTypeDef *h, uint8_t *buf, uint16_t len, uint32_t timeout)
{
    (void)h; (void)buf; (void)len; (void)timeout;
    return HAL_ERROR;
}

__attribute__((weak)) HAL_StatusTypeDef HAL_UART_Receive(
    UART_HandleTypeDef *h, uint8_t *buf, uint16_t len, uint32_t timeout)
{
    (void)h; (void)timeout;
    if (buf != NULL) {
        for (uint16_t i = 0; i < len; ++i) { buf[i] = 0; }
    }
    return HAL_ERROR;
}


/* ==================================================================
 *  ADC — used by the solar-panel voltage monitor.
 * ================================================================== */

__attribute__((weak)) HAL_StatusTypeDef HAL_ADC_Init(ADC_HandleTypeDef *h)
{
    (void)h;
    return HAL_OK;
}

__attribute__((weak)) HAL_StatusTypeDef HAL_ADC_Start(ADC_HandleTypeDef *h)
{
    (void)h;
    return HAL_OK;
}

__attribute__((weak)) HAL_StatusTypeDef HAL_ADC_Stop(ADC_HandleTypeDef *h)
{
    (void)h;
    return HAL_OK;
}

__attribute__((weak)) HAL_StatusTypeDef HAL_ADC_PollForConversion(
    ADC_HandleTypeDef *h, uint32_t timeout)
{
    (void)h; (void)timeout;
    return HAL_ERROR;
}

__attribute__((weak)) uint32_t HAL_ADC_GetValue(ADC_HandleTypeDef *h)
{
    (void)h;
    return 0U;
}


/* ==================================================================
 *  TIM + IWDG — used by the watchdog task.
 * ================================================================== */

__attribute__((weak)) HAL_StatusTypeDef HAL_TIM_Base_Init(TIM_HandleTypeDef *h)
{
    (void)h;
    return HAL_OK;
}

__attribute__((weak)) HAL_StatusTypeDef HAL_TIM_Base_Start(TIM_HandleTypeDef *h)
{
    (void)h;
    return HAL_OK;
}

typedef struct { uint32_t _padding; } IWDG_HandleTypeDef;

__attribute__((weak)) HAL_StatusTypeDef HAL_IWDG_Init(IWDG_HandleTypeDef *h)
{
    (void)h;
    return HAL_OK;
}

__attribute__((weak)) HAL_StatusTypeDef HAL_IWDG_Refresh(IWDG_HandleTypeDef *h)
{
    (void)h;
    return HAL_OK;
}


/* ==================================================================
 *  GPIO — used transparently by drivers for /CS and interrupt lines.
 * ================================================================== */

typedef struct GPIO_TypeDef_s GPIO_TypeDef;

typedef enum { GPIO_PIN_RESET = 0, GPIO_PIN_SET = 1 } GPIO_PinState;

__attribute__((weak)) void HAL_GPIO_WritePin(
    GPIO_TypeDef *port, uint16_t pin, GPIO_PinState state)
{
    (void)port; (void)pin; (void)state;
}

__attribute__((weak)) GPIO_PinState HAL_GPIO_ReadPin(
    GPIO_TypeDef *port, uint16_t pin)
{
    (void)port; (void)pin;
    return GPIO_PIN_RESET;
}

__attribute__((weak)) void HAL_GPIO_TogglePin(
    GPIO_TypeDef *port, uint16_t pin)
{
    (void)port; (void)pin;
}
