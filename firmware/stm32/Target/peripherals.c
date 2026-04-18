/**
 ******************************************************************************
 *  UniSat — STM32 peripheral handle definitions.
 *
 *  STM32CubeMX normally generates this file alongside main.c; here we
 *  ship the handles manually so the ARM target build links without a
 *  CubeMX round-trip. The handle *structs* live here, the peripheral
 *  *initialisation* (clock gate on + register setup) stays in
 *  system_init.c's weak MX_*_Init functions.
 *
 *  Drivers reference these handles via `extern` declarations in their
 *  own .c files (comm.c → huart1, huart2; eps.c / obc.c → hadc1). Any
 *  future driver that needs a new peripheral adds its handle here.
 ******************************************************************************
 */

#include "stm32f4xx_hal.h"

/* USART1 — UHF modem TX/RX.
 * USART2 — debug / ST-Link VCP. */
UART_HandleTypeDef huart1;
UART_HandleTypeDef huart2;

/* I2C1 — sensor bus (LIS3MDL / BME280 / TMP117 / u-blox). */
I2C_HandleTypeDef  hi2c1;

/* SPI1 — MPU9250 + MCP3008, sharing /CS lines managed in software. */
SPI_HandleTypeDef  hspi1;

/* ADC1 — battery voltage, CPU-die temp (internal channel). */
ADC_HandleTypeDef  hadc1;

/* TIM2 — free-running 32-bit counter used by the WCET probe and
 * as a SysTick fallback if an HAL module (re-)initialises SysTick. */
TIM_HandleTypeDef  htim2;

/* IWDG — independent hardware watchdog (wakes and resets if not
 * refreshed by the watchdog task). */
IWDG_HandleTypeDef hiwdg;
