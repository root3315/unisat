/**
 ******************************************************************************
 *  UniSat — project HAL configuration for STM32F446RE.
 *
 *  STM32Cube HAL relies on this file (included from stm32f4xx_hal.h) to
 *  know which sub-driver headers and features to expose. Normally
 *  STM32CubeMX generates it alongside `main.c`; this hand-written copy
 *  pins the set of modules UniSat actually uses so a CI target build
 *  links with no additional user input.
 *
 *  Enabled modules (must match the peripherals referenced under
 *  firmware/stm32/Drivers/ + firmware/stm32/Core/Src/):
 *      RCC, GPIO, CORTEX  — always
 *      DMA                — prerequisite for every stream-mode driver
 *      I2C                — LIS3MDL, BME280, TMP117, u-blox DDC
 *      SPI                — MPU9250, MCP3008
 *      UART               — USART1 (UHF modem) + USART2 (VCP debug)
 *      ADC                — MCP3008 analogue path + battery sensing
 *      TIM                — systick alternate + WCET probe
 *      IWDG               — independent watchdog (hardware-level WDT)
 *      FLASH              — key_store A/B sector program/erase
 *      PWR                — VOS scale for 168 MHz operation
 *
 *  Everything else (SDIO, DFSDM, CAN2, ...) is #undef'd so its code
 *  doesn't get pulled into the .elf — keeps the 90 % flash budget
 *  honest and speeds up the link by a few MB.
 ******************************************************************************
 */
#ifndef STM32F4xx_HAL_CONF_H
#define STM32F4xx_HAL_CONF_H

#ifdef __cplusplus
extern "C" {
#endif

/* ───────────── Module enable/disable ───────────── */

#define HAL_MODULE_ENABLED
#define HAL_ADC_MODULE_ENABLED
#define HAL_CORTEX_MODULE_ENABLED
#define HAL_DMA_MODULE_ENABLED
#define HAL_EXTI_MODULE_ENABLED
#define HAL_FLASH_MODULE_ENABLED
#define HAL_GPIO_MODULE_ENABLED
#define HAL_I2C_MODULE_ENABLED
#define HAL_IWDG_MODULE_ENABLED
#define HAL_PWR_MODULE_ENABLED
#define HAL_RCC_MODULE_ENABLED
#define HAL_SPI_MODULE_ENABLED
#define HAL_TIM_MODULE_ENABLED
#define HAL_UART_MODULE_ENABLED
#define HAL_USART_MODULE_ENABLED

/* ───────────── HAL assert + tick ───────────── */

/* Keep asserts compiled in for a debug build; the release profile can
 * strip them via `cmake -DCMAKE_BUILD_TYPE=Release` + -DNDEBUG. */
#define USE_FULL_ASSERT    0U

/* HAL tick source (1ms) — SysTick is the canonical choice for F4. */
#define TICK_INT_PRIORITY  ((uint32_t)0)
#define USE_RTOS           0U

/* ───────────── Oscillator + Voltage ───────────── */

#if !defined(HSE_VALUE)
  #define HSE_VALUE  ((uint32_t)8000000U)   /* UniSat crystal: 8 MHz */
#endif
#if !defined(HSE_STARTUP_TIMEOUT)
  #define HSE_STARTUP_TIMEOUT  ((uint32_t)100U)
#endif
#if !defined(HSI_VALUE)
  #define HSI_VALUE  ((uint32_t)16000000U)
#endif
#if !defined(LSI_VALUE)
  #define LSI_VALUE  ((uint32_t)32000U)
#endif
#if !defined(LSE_VALUE)
  #define LSE_VALUE  ((uint32_t)32768U)
#endif
#if !defined(LSE_STARTUP_TIMEOUT)
  #define LSE_STARTUP_TIMEOUT  ((uint32_t)5000U)
#endif
#if !defined(EXTERNAL_CLOCK_VALUE)
  #define EXTERNAL_CLOCK_VALUE  ((uint32_t)12288000U)
#endif
#if !defined(VDD_VALUE)
  #define VDD_VALUE  ((uint32_t)3300U)   /* mV */
#endif

#define PREFETCH_ENABLE    1U
#define INSTRUCTION_CACHE_ENABLE 1U
#define DATA_CACHE_ENABLE        1U

/* ───────────── HAL subsystem headers ───────────── */

#ifdef HAL_RCC_MODULE_ENABLED
  #include "stm32f4xx_hal_rcc.h"
#endif
#ifdef HAL_CORTEX_MODULE_ENABLED
  #include "stm32f4xx_hal_cortex.h"
#endif
#ifdef HAL_GPIO_MODULE_ENABLED
  #include "stm32f4xx_hal_gpio.h"
#endif
#ifdef HAL_EXTI_MODULE_ENABLED
  #include "stm32f4xx_hal_exti.h"
#endif
#ifdef HAL_DMA_MODULE_ENABLED
  #include "stm32f4xx_hal_dma.h"
#endif
#ifdef HAL_FLASH_MODULE_ENABLED
  #include "stm32f4xx_hal_flash.h"
#endif
#ifdef HAL_PWR_MODULE_ENABLED
  #include "stm32f4xx_hal_pwr.h"
#endif
#ifdef HAL_I2C_MODULE_ENABLED
  #include "stm32f4xx_hal_i2c.h"
#endif
#ifdef HAL_SPI_MODULE_ENABLED
  #include "stm32f4xx_hal_spi.h"
#endif
#ifdef HAL_UART_MODULE_ENABLED
  #include "stm32f4xx_hal_uart.h"
#endif
#ifdef HAL_USART_MODULE_ENABLED
  #include "stm32f4xx_hal_usart.h"
#endif
#ifdef HAL_ADC_MODULE_ENABLED
  #include "stm32f4xx_hal_adc.h"
#endif
#ifdef HAL_TIM_MODULE_ENABLED
  #include "stm32f4xx_hal_tim.h"
#endif
#ifdef HAL_IWDG_MODULE_ENABLED
  #include "stm32f4xx_hal_iwdg.h"
#endif

/* ───────────── assert stub ───────────── */

#if USE_FULL_ASSERT
  void assert_failed(uint8_t *file, uint32_t line);
  #define assert_param(expr) ((expr) ? (void)0U : assert_failed((uint8_t *)__FILE__, __LINE__))
#else
  #define assert_param(expr) ((void)0U)
#endif

#ifdef __cplusplus
}
#endif

#endif /* STM32F4xx_HAL_CONF_H */
