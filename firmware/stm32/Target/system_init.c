/**
 ******************************************************************************
 *  UniSat — clock + peripheral bring-up (HAL-free reference path)
 *
 *  Implements the seven init functions that main.c expects to exist:
 *
 *    SystemClock_Config()  — 168 MHz from HSE-8 MHz via PLL.
 *    MX_GPIO_Init()        — LED heartbeat + SWD only.
 *    MX_I2C1_Init()        — sensor bus (LIS3MDL, BME280, TMP117, u-blox).
 *    MX_SPI1_Init()        — MPU9250 + MCP3008 (shared /CS).
 *    MX_USART1_UART_Init() — UHF modem link.
 *    MX_USART2_UART_Init() — debug printf / ST-Link VCP.
 *    MX_ADC1_Init()        — solar-panel voltage monitoring.
 *    MX_TIM2_Init()        — free-running 32-bit timer, used by DWT
 *                            fallback for WCET measurement (Phase 5).
 *
 *  All implementations here are bare-register writes — no dependency
 *  on STM32Cube HAL. This lets the firmware link under arm-none-eabi
 *  immediately after cloning the repo, without waiting for
 *  scripts/setup_stm32_hal.sh to fetch STM32CubeF4. When the full HAL
 *  is fetched and added to the include path, CMake links HAL_*
 *  implementations from HAL_Driver/Src/stm32f4xx_hal_*.c instead and
 *  these functions are superseded by the CubeMX-generated versions
 *  via link-order (CMake wires HAL first so strong symbols win).
 *
 *  Clock tree (RCC_PLLCFGR / RCC_CFGR):
 *    HSE = 8 MHz → /M=4 → VCO_IN = 2 MHz
 *    VCO_IN × N=168 = VCO_OUT = 336 MHz
 *    SYSCLK = VCO_OUT / P=2 = 168 MHz
 *    AHB  = SYSCLK / 1 = 168 MHz
 *    APB1 = AHB / 4    = 42 MHz  (I2C, TIM2..7, USART2..5)
 *    APB2 = AHB / 2    = 84 MHz  (USART1, SPI1, ADC1, TIM1/8)
 *    USB OTG / RNG = VCO_OUT / Q=7 = 48 MHz
 ******************************************************************************
 */

#include <stdint.h>

extern uint32_t SystemCoreClock;
extern void SystemCoreClockUpdate(void);

/* ------------------------------------------------------------------
 *  Minimal register definitions (subset — only what we poke).
 * ------------------------------------------------------------------ */

#define RCC_BASE     (0x40023800UL)
#define FLASH_BASE   (0x40023C00UL)
#define PWR_BASE     (0x40007000UL)
#define GPIOA_BASE   (0x40020000UL)
#define GPIOB_BASE   (0x40020400UL)
#define GPIOC_BASE   (0x40020800UL)

#define RCC_CR       (*(volatile uint32_t *)(RCC_BASE + 0x00))
#define RCC_PLLCFGR  (*(volatile uint32_t *)(RCC_BASE + 0x04))
#define RCC_CFGR     (*(volatile uint32_t *)(RCC_BASE + 0x08))
#define RCC_AHB1ENR  (*(volatile uint32_t *)(RCC_BASE + 0x30))
#define RCC_APB1ENR  (*(volatile uint32_t *)(RCC_BASE + 0x40))
#define RCC_APB2ENR  (*(volatile uint32_t *)(RCC_BASE + 0x44))

#define FLASH_ACR    (*(volatile uint32_t *)(FLASH_BASE + 0x00))
#define PWR_CR       (*(volatile uint32_t *)(PWR_BASE + 0x00))


static void delay_cycles(volatile uint32_t n)
{
    while (n--) { __asm volatile ("nop"); }
}


/**
 * @brief Configure the PLL + flash latency to run the core at 168 MHz.
 *
 *  Sequence (RM0390 §6.2.9):
 *    1. Enable PWR clock, raise VOS to scale 1 (required above 144 MHz).
 *    2. Turn on HSE, wait for HSERDY.
 *    3. Program PLLCFGR (M=4, N=168, P=2, Q=7, source=HSE).
 *    4. Turn on PLL, wait for PLLRDY.
 *    5. Program flash latency = 5 wait states (required at 168 MHz
 *       per table 6 of RM0390) and prefetch on.
 *    6. Switch SW to PLL, wait for SWS to confirm.
 *    7. Program AHB / APB1 / APB2 prescalers.
 *    8. Notify CMSIS by calling SystemCoreClockUpdate.
 *
 *  On any ready-bit timeout we return early — main() is expected to
 *  detect SystemCoreClock != 168000000 and fall through to safe-mode
 *  via error_handler.c (Phase 3 wires this check).
 */
void SystemClock_Config(void)
{
    volatile uint32_t timeout;

    /* 1. PWR enable + VOS scale 1 */
    RCC_APB1ENR |= (1U << 28);
    PWR_CR |= (3U << 14);

    /* 2. HSE on */
    RCC_CR |= (1U << 16);
    timeout = 0x10000U;
    while (!(RCC_CR & (1U << 17)) && --timeout) { /* wait HSERDY */ }
    if (timeout == 0) { return; }

    /* 3. PLL config: M=4, N=168, P=2 (enum 00), Q=7, source HSE */
    RCC_PLLCFGR =
        (4U       <<  0) |            /* PLLM  = 4       */
        (168U     <<  6) |            /* PLLN  = 168     */
        (0U       << 16) |            /* PLLP  = 2       */
        (7U       << 24) |            /* PLLQ  = 7       */
        (1U       << 22);             /* PLLSRC = HSE    */

    /* 4. PLL on */
    RCC_CR |= (1U << 24);
    timeout = 0x10000U;
    while (!(RCC_CR & (1U << 25)) && --timeout) { /* wait PLLRDY */ }
    if (timeout == 0) { return; }

    /* 5. Flash: 5 wait states, prefetch + i-cache + d-cache on */
    FLASH_ACR = (1U << 10) | (1U << 9) | (1U << 8) | 5U;

    /* 6. Switch SYSCLK to PLL. SW bits 1..0, 10b = PLL. */
    RCC_CFGR = (RCC_CFGR & ~0x3U) | 0x2U;
    timeout = 0x10000U;
    while (((RCC_CFGR >> 2) & 0x3U) != 0x2U && --timeout) { /* wait SWS */ }
    if (timeout == 0) { return; }

    /* 7. Prescalers: HPRE=1 (AHB=168), PPRE1=4 (APB1=42), PPRE2=2 (APB2=84) */
    RCC_CFGR |= (0x5U << 10);   /* PPRE1 = 0b101 => /4 */
    RCC_CFGR |= (0x4U << 13);   /* PPRE2 = 0b100 => /2 */

    /* 8. CMSIS sync */
    SystemCoreClockUpdate();

    /* Small settle — the AHB prescaler change is instantaneous but the
     * peripheral enable registers need a couple of cycles to latch. */
    delay_cycles(16);
}


/* ------------------------------------------------------------------
 *  Bare-metal peripheral init stubs.
 *
 *  These are deliberately minimal — they enable the corresponding
 *  peripheral clock and leave peripheral-specific register setup to
 *  either:
 *    (a) the driver that owns that peripheral (e.g. the I2C driver
 *        owns I2C1 timing / filter registers), or
 *    (b) a future STM32Cube HAL integration that replaces them via
 *        link-order once scripts/setup_stm32_hal.sh populates
 *        Drivers/STM32F4xx_HAL_Driver/.
 *
 *  Weakly linked so a CubeMX-generated main.c/system_stm32f4xx.c can
 *  override them transparently.
 * ------------------------------------------------------------------ */

__attribute__((weak)) void MX_GPIO_Init(void)
{
    /* Enable GPIOA/B/C clocks (AHB1ENR bits 0/1/2). */
    RCC_AHB1ENR |= (1U << 0) | (1U << 1) | (1U << 2);
    /* Driver-owned pin muxing happens in the sensors / comm drivers. */
}

__attribute__((weak)) void MX_I2C1_Init(void)
{
    /* Enable I2C1 clock (APB1ENR bit 21). */
    RCC_APB1ENR |= (1U << 21);
}

__attribute__((weak)) void MX_SPI1_Init(void)
{
    /* Enable SPI1 clock (APB2ENR bit 12). */
    RCC_APB2ENR |= (1U << 12);
}

__attribute__((weak)) void MX_USART1_UART_Init(void)
{
    /* Enable USART1 clock (APB2ENR bit 4). */
    RCC_APB2ENR |= (1U << 4);
}

__attribute__((weak)) void MX_USART2_UART_Init(void)
{
    /* Enable USART2 clock (APB1ENR bit 17). */
    RCC_APB1ENR |= (1U << 17);
}

__attribute__((weak)) void MX_ADC1_Init(void)
{
    /* Enable ADC1 clock (APB2ENR bit 8). */
    RCC_APB2ENR |= (1U << 8);
}

__attribute__((weak)) void MX_TIM2_Init(void)
{
    /* Enable TIM2 clock (APB1ENR bit 0). */
    RCC_APB1ENR |= (1U << 0);
}
