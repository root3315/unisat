/**
 ******************************************************************************
 *  UniSat — Cortex-M4 exception handlers
 *
 *  Strong definitions that override the .weak aliases declared in
 *  startup_stm32f446retx.s. We provide:
 *
 *    NMI_Handler          — spin (should never fire; CSS disabled).
 *    HardFault_Handler    — capture the fault stack frame and freeze.
 *    MemManage_Handler    — MPU violation (unused today, kept for hook).
 *    BusFault_Handler     — bus error (spin; enables post-mortem SWD).
 *    UsageFault_Handler   — undefined instruction / div-by-0 (spin).
 *    SVC_Handler          — intentionally left to the FreeRTOS port
 *                           shim (vPortSVCHandler) when CMSIS-OS2 is
 *                           linked; here it's only a fallback for the
 *                           pre-scheduler boot window.
 *    DebugMon_Handler     — debug monitor trap (spin).
 *    PendSV_Handler       — owned by FreeRTOS port.c (xPortPendSVHandler).
 *    SysTick_Handler      — increments HAL_tick then hands to
 *                           osSystickHandler when FreeRTOS is running.
 *
 *  The policy for the fault vectors is:
 *    * dump the exception stack frame into a persistent struct that
 *      error_handler.c reads on the next warm boot;
 *    * halt with BKPT #0 so attached ST-Link stops *at* the faulting
 *      instruction rather than somewhere down a default-handler loop;
 *    * fall through to an infinite loop if no debugger is present, so
 *      the watchdog (WWDG or IWDG) eventually resets the satellite
 *      and the on-board FDIR sees fault_reboot_count++.
 ******************************************************************************
 */

#include <stdint.h>

/*
 * Captured exception frame. .noinit keeps it across soft resets so
 * the post-mortem survives to the next boot's error_handler.
 * STM32F446 RCC_CSR flags let us tell a fault reset from a WWDG or
 * IWDG reset at the next power-up.
 */
typedef struct {
    uint32_t r0;
    uint32_t r1;
    uint32_t r2;
    uint32_t r3;
    uint32_t r12;
    uint32_t lr;        /* return address */
    uint32_t pc;        /* faulting instruction */
    uint32_t psr;
    uint32_t cfsr;      /* Configurable Fault Status Register */
    uint32_t hfsr;      /* HardFault Status Register          */
    uint32_t mmfar;     /* MemManage Fault Address Register   */
    uint32_t bfar;      /* BusFault Address Register          */
    uint32_t kind;      /* 1=Hard 2=MemManage 3=BusFault 4=Usage */
} FaultFrame_t;

/* Linker keeps this in SRAM across soft-resets via the LD NOLOAD trick
 * that error_handler.c already uses for its event log. For now keep it
 * in .bss — a dedicated noinit section is introduced in Phase 3 (FDIR).
 */
volatile FaultFrame_t g_last_fault;

/* Global ms counter, bumped by SysTick. Exposed as HAL_GetTick() below
 * so the existing firmware (main.c, telemetry.c, ...) keeps working
 * even in a build without the full STM32Cube HAL.
 */
static volatile uint32_t s_uwTick = 0U;


/* ------------------------------------------------------------------
 *  Helper: drop into the .cfsr / .hfsr style dump and halt.
 * ------------------------------------------------------------------ */
static void fault_capture(uint32_t *stack_frame, uint32_t kind)
{
    g_last_fault.r0   = stack_frame[0];
    g_last_fault.r1   = stack_frame[1];
    g_last_fault.r2   = stack_frame[2];
    g_last_fault.r3   = stack_frame[3];
    g_last_fault.r12  = stack_frame[4];
    g_last_fault.lr   = stack_frame[5];
    g_last_fault.pc   = stack_frame[6];
    g_last_fault.psr  = stack_frame[7];
    g_last_fault.cfsr  = *(volatile uint32_t *)0xE000ED28UL;
    g_last_fault.hfsr  = *(volatile uint32_t *)0xE000ED2CUL;
    g_last_fault.mmfar = *(volatile uint32_t *)0xE000ED34UL;
    g_last_fault.bfar  = *(volatile uint32_t *)0xE000ED38UL;
    g_last_fault.kind  = kind;

    /* If a debugger is attached, break. C_DEBUGEN is bit 0 of DHCSR. */
    if ((*(volatile uint32_t *)0xE000EDF0UL) & 0x1U) {
        __asm volatile ("bkpt #0");
    }

    /* Otherwise spin; WWDG / IWDG will recycle the board and the
     * next boot's error_handler will read g_last_fault. */
    while (1) { /* nothing */ }
}


/* ------------------------------------------------------------------
 *  Exception vectors — naked thunks to fault_capture().
 *  The __attribute__((naked)) avoids any prologue / epilogue so the
 *  captured stack pointer points exactly at the M4 exception frame
 *  laid down by hardware (8 words: r0..r3, r12, LR, PC, xPSR).
 * ------------------------------------------------------------------ */

__attribute__((naked)) void HardFault_Handler(void)
{
    __asm volatile (
        "tst   lr, #4            \n"   /* MSP vs PSP ?            */
        "ite   eq                \n"
        "mrseq r0, msp           \n"
        "mrsne r0, psp           \n"
        "mov   r1, #1            \n"   /* kind = Hard             */
        "b     fault_capture     \n"
    );
}

__attribute__((naked)) void MemManage_Handler(void)
{
    __asm volatile (
        "tst   lr, #4            \n"
        "ite   eq                \n"
        "mrseq r0, msp           \n"
        "mrsne r0, psp           \n"
        "mov   r1, #2            \n"
        "b     fault_capture     \n"
    );
}

__attribute__((naked)) void BusFault_Handler(void)
{
    __asm volatile (
        "tst   lr, #4            \n"
        "ite   eq                \n"
        "mrseq r0, msp           \n"
        "mrsne r0, psp           \n"
        "mov   r1, #3            \n"
        "b     fault_capture     \n"
    );
}

__attribute__((naked)) void UsageFault_Handler(void)
{
    __asm volatile (
        "tst   lr, #4            \n"
        "ite   eq                \n"
        "mrseq r0, msp           \n"
        "mrsne r0, psp           \n"
        "mov   r1, #4            \n"
        "b     fault_capture     \n"
    );
}

void NMI_Handler(void)
{
    /* CSS not enabled in this build; arriving here means an external
     * NMI line was asserted, which is a board anomaly. Spin for the
     * watchdog to reset the core. */
    while (1) { /* nothing */ }
}

void DebugMon_Handler(void)
{
    /* Not used — spin. */
    while (1) { /* nothing */ }
}


/* ------------------------------------------------------------------
 *  SysTick + weak HAL_GetTick shim.
 *
 *  FreeRTOS port.c provides a strong xPortSysTickHandler once the
 *  scheduler has started. Before that, and for any non-RTOS build,
 *  this handler keeps s_uwTick advancing so HAL_Delay() in boot
 *  code (SystemClock_Config flash-latency settle, MX_I2C_Init
 *  bus reset) has a real ms tick.
 * ------------------------------------------------------------------ */
void SysTick_Handler(void)
{
    s_uwTick++;
}

__attribute__((weak)) uint32_t HAL_GetTick(void)
{
    return s_uwTick;
}

__attribute__((weak)) void HAL_Delay(uint32_t ms)
{
    uint32_t start = s_uwTick;
    while ((s_uwTick - start) < ms) {
        /* polite idle — WFE lets the core power-gate between ticks */
        __asm volatile ("wfe");
    }
}

/* SVC and PendSV are owned by FreeRTOS — fall through to default
 * spin if the port.c wasn't linked (i.e. bare-metal smoke test). */
__attribute__((weak)) void SVC_Handler(void)    { while (1) { /* nothing */ } }
__attribute__((weak)) void PendSV_Handler(void) { while (1) { /* nothing */ } }
