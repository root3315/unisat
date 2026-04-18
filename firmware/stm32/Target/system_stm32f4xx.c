/**
 ******************************************************************************
 *  UniSat — CMSIS system bring-up for STM32F446RETx
 *
 *  Provides the two CMSIS-mandated symbols that every STM32 project must
 *  define:
 *
 *    SystemInit()      — called from Reset_Handler before main(). Sets up
 *                        the vector-table offset, enables the FPU, and
 *                        hands control back so that SystemClock_Config()
 *                        (defined in system_init.c) can promote the core
 *                        from HSI-16 MHz to HSE-PLL-168 MHz.
 *
 *    SystemCoreClock   — global integer tracking the current AHB (HCLK)
 *                        frequency in Hz. CMSIS code paths, FreeRTOS
 *                        port.c, and the HAL tick all read this value;
 *                        SystemClock_Config() rewrites it after each
 *                        PLL reconfiguration via SystemCoreClockUpdate.
 *
 *  This file is deliberately HAL-free. It manipulates the Cortex-M4
 *  System Control Block (SCB) and RCC registers directly through their
 *  memory-mapped addresses so the firmware links against the ARM
 *  toolchain even before STM32Cube HAL is fetched into the source tree
 *  (see scripts/setup_stm32_hal.sh). For the bring-up boot sequence
 *  that is the correct layering — HAL is only meaningful once clocks,
 *  FPU, and vector offset are already configured.
 ******************************************************************************
 */

#include <stdint.h>

/* ------------------------------------------------------------------
 *  Minimal register map — just the bits we actually touch here.
 * ------------------------------------------------------------------ */

#define SCB_VTOR_ADDR       (0xE000ED08UL)   /* Vector table offset       */
#define SCB_CPACR_ADDR      (0xE000ED88UL)   /* Coprocessor access ctrl   */

#define RCC_BASE_ADDR       (0x40023800UL)
#define RCC_CR              (*(volatile uint32_t *)(RCC_BASE_ADDR + 0x00))
#define RCC_CFGR            (*(volatile uint32_t *)(RCC_BASE_ADDR + 0x08))

#define FLASH_BASE_ADDR     (0x08000000UL)
#define VECT_TAB_OFFSET     (0x00000000UL)   /* firmware at flash base    */

/* ------------------------------------------------------------------
 *  SystemCoreClock — initial value reflects reset state (HSI 16 MHz).
 *  SystemClock_Config() will overwrite this to 168_000_000UL after the
 *  PLL has locked and the AHB prescaler is set.
 * ------------------------------------------------------------------ */
uint32_t SystemCoreClock = 16000000UL;

/* Lookup for SystemCoreClockUpdate below */
static const uint8_t AHB_PRESC_TABLE[16] = {
    0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 6, 7, 8, 9
};


/**
 * @brief  Called by Reset_Handler before main().
 *
 *  1. Force RCC to its post-reset configuration (HSI ON, no PLL) so
 *     a warm reboot from any state lands in a known starting point.
 *  2. Enable the single-precision FPU (CP10 + CP11 full access).
 *     Cortex-M4 boots with the FPU disabled; the first vector of FP
 *     code would otherwise fault.
 *  3. Relocate the vector table to FLASH_BASE + VECT_TAB_OFFSET via
 *     VTOR. This is a no-op when the image is already at 0x08000000
 *     but future bootloader layouts (e.g. 0x08008000 for a signed
 *     payload) only have to bump VECT_TAB_OFFSET.
 *
 *  Intentionally *does not* configure the clock tree — that's
 *  SystemClock_Config()'s job, called from main() so errors surface
 *  before FreeRTOS starts and can drive the error_handler.
 */
void SystemInit(void)
{
    /* --- 1. RCC sane starting point --- */
    RCC_CR   |= 0x00000001U;   /* HSION                             */
    RCC_CFGR  = 0x00000000U;   /* MCO off, PLL not selected, no div */
    RCC_CR   &= 0xFEF6FFFFU;   /* HSEON=0, CSSON=0, PLLON=0         */
    RCC_CR   &= 0xFFFBFFFFU;   /* HSEBYP=0                          */
    /* clear PLL config register left-overs — HAL does the same */
    *(volatile uint32_t *)(RCC_BASE_ADDR + 0x04) = 0x24003010U;
    /* disable all RCC interrupts — firmware uses polling here */
    *(volatile uint32_t *)(RCC_BASE_ADDR + 0x0C) = 0x00000000U;

    /* --- 2. Enable FPU (set CP10 + CP11 to Full Access) --- */
    *(volatile uint32_t *)SCB_CPACR_ADDR |= (0xFU << 20);

    /* --- 3. Vector table relocation --- */
    *(volatile uint32_t *)SCB_VTOR_ADDR =
        FLASH_BASE_ADDR | VECT_TAB_OFFSET;
}


/**
 * @brief Recompute SystemCoreClock from the current RCC configuration.
 *
 *  Walks the same register bits SystemClock_Config wrote, so any code
 *  path that changes the clock tree at runtime (power-saving, external
 *  oscillator failover) only has to call this to keep CMSIS in sync.
 *
 *  Supported sources: HSI (16 MHz), HSE (assumed 8 MHz on UniSat OBC
 *  board), PLL driven from either. Values outside these paths fall
 *  back to HSI so downstream timing code doesn't read a garbage zero.
 */
void SystemCoreClockUpdate(void)
{
    uint32_t sws = (RCC_CFGR >> 2) & 0x3U;
    uint32_t hclk;

    switch (sws) {
    case 0x0:  /* HSI used as SYSCLK */
        hclk = 16000000UL;
        break;

    case 0x1:  /* HSE used as SYSCLK */
        hclk = 8000000UL;   /* UniSat OBC crystal */
        break;

    case 0x2: {/* PLL_P used as SYSCLK */
        uint32_t pllcfgr = *(volatile uint32_t *)(RCC_BASE_ADDR + 0x04);
        uint32_t pllm    = pllcfgr & 0x3FU;
        uint32_t plln    = (pllcfgr >> 6) & 0x1FFU;
        uint32_t pllp    = (((pllcfgr >> 16) & 0x3U) + 1U) * 2U;
        uint32_t src     = (pllcfgr >> 22) & 0x1U;
        uint32_t vco_in  = (src ? 8000000UL : 16000000UL) / pllm;
        hclk = (vco_in * plln) / pllp;
        break;
    }

    default:
        hclk = 16000000UL;
        break;
    }

    /* Apply the AHB prescaler (HPRE bits in CFGR) */
    uint32_t hpre_bits = (RCC_CFGR >> 4) & 0xFU;
    SystemCoreClock = hclk >> AHB_PRESC_TABLE[hpre_bits];
}
