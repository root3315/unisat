/**
 * @file fdir.c
 * @brief Fault Detection, Isolation, Recovery — table-driven.
 *
 * The fault table below is the single source of truth for how each
 * fault is handled. Every entry:
 *
 *   * a stable id (enum value used in downlink telemetry),
 *   * a human name (for on-board log lines + ground-side decode),
 *   * a primary action returned by FDIR_GetRecommendedAction when
 *     the fault is inside its "quiet" state,
 *   * an escalation action returned once the fault has fired
 *     escalation_threshold times inside FDIR_RECENT_WINDOW_MS, and
 *   * the threshold itself.
 *
 * The thresholds are conservative: any fault that can plausibly
 * have a transient cause (one-off bit flip on I2C, single sensor
 * glitch under load) is given enough room for RETRY before the
 * subsystem is disabled, but not so many that a genuine hard
 * failure wastes the downlink window.
 *
 * The FDIR is *advisory* — it computes the recommended action and
 * bumps aggregate counters. The actual mode change (safe-mode enter,
 * bus reset, reboot) is enacted by the caller. This keeps the FDIR
 * reusable under unit tests that don't have a real safe-mode
 * manager linked.
 */

#include "fdir.h"
#include <string.h>

/* Forward-declared weak tick source — see FDIR_GetTick below. */

/* ------------------------------------------------------------------
 *  Static fault table
 * ------------------------------------------------------------------ */
static const FDIR_FaultEntry_t g_table[FDIR_FAULT_COUNT] = {
    /* id                         name                 primary                escalation            recent@window */
    { FAULT_WATCHDOG_TASK_MISS,  "watchdog_task_miss", RECOVERY_RESET_BUS,    RECOVERY_REBOOT,        3 },
    { FAULT_I2C_BUS_STUCK,       "i2c_bus_stuck",      RECOVERY_RESET_BUS,    RECOVERY_DISABLE_SUBSYS, 5 },
    { FAULT_SPI_TIMEOUT,         "spi_timeout",        RECOVERY_RETRY,        RECOVERY_DISABLE_SUBSYS, 5 },
    { FAULT_SENSOR_OUT_OF_RANGE, "sensor_out_of_range",RECOVERY_LOG_ONLY,     RECOVERY_DISABLE_SUBSYS, 10 },
    { FAULT_BATTERY_UNDERVOLT,   "battery_undervolt",  RECOVERY_SAFE_MODE,    RECOVERY_REBOOT,         2 },
    { FAULT_OVER_TEMPERATURE,    "over_temperature",   RECOVERY_DISABLE_SUBSYS,RECOVERY_SAFE_MODE,     3 },
    { FAULT_UNDER_TEMPERATURE,   "under_temperature",  RECOVERY_LOG_ONLY,     RECOVERY_SAFE_MODE,      3 },
    { FAULT_STACK_OVERFLOW,      "stack_overflow",     RECOVERY_REBOOT,       RECOVERY_REBOOT,         1 },
    { FAULT_HEAP_EXHAUST,        "heap_exhaust",       RECOVERY_SAFE_MODE,    RECOVERY_REBOOT,         2 },
    { FAULT_PLL_UNLOCK,          "pll_unlock",         RECOVERY_REBOOT,       RECOVERY_REBOOT,         1 },
    { FAULT_COMM_LOSS,           "comm_loss",          RECOVERY_SAFE_MODE,    RECOVERY_REBOOT,         2 },
    { FAULT_KEYSTORE_EMPTY,      "keystore_empty",     RECOVERY_LOG_ONLY,     RECOVERY_SAFE_MODE,      1 }
};

_Static_assert(sizeof(g_table)/sizeof(g_table[0]) == FDIR_FAULT_COUNT,
               "FDIR fault table size out of sync with FDIR_FAULT_COUNT");


/* ------------------------------------------------------------------
 *  Mutable per-fault state + aggregate stats
 * ------------------------------------------------------------------ */
static FDIR_FaultState_t g_state[FDIR_FAULT_COUNT];
static FDIR_Stats_t      g_stats;


/* ------------------------------------------------------------------
 *  Tick source (weak — host tests link a strong override to drive
 *  deterministic timing; target build silently uses HAL_GetTick
 *  when it is linked from stm32f4xx_it.c or the full HAL).
 *
 *  To keep the weak default free of link-time dependencies on HAL
 *  (so a host build without stm32f4xx_it.c links cleanly), the
 *  weak implementation here probes a secondary weak symbol
 *  __fdir_hal_tick which the HAL shim / stm32f4xx_it.c defines
 *  on target. If neither is linked, we fall back to a simple
 *  monotonically-incrementing counter so FDIR_Report still
 *  updates recent-window state during dev-time host builds that
 *  don't install a tick hook of their own.
 * ------------------------------------------------------------------ */
__attribute__((weak)) uint32_t __fdir_hal_tick(void);
__attribute__((weak)) uint32_t __fdir_hal_tick(void)
{
    static uint32_t counter = 0U;
    return ++counter;
}

__attribute__((weak)) uint32_t FDIR_GetTick(void)
{
    return __fdir_hal_tick();
}


/* ------------------------------------------------------------------
 *  Public API
 * ------------------------------------------------------------------ */

void FDIR_Init(void)
{
    memset(g_state, 0, sizeof(g_state));
    memset(&g_stats, 0, sizeof(g_stats));
}

void FDIR_Report(FDIR_FaultId_t id)
{
    if ((uint32_t)id >= FDIR_FAULT_COUNT) { return; }

    uint32_t now = FDIR_GetTick();
    FDIR_FaultState_t *s = &g_state[id];

    /* Slide the recent window: if the last event is older than the
     * window, start a fresh one; otherwise accumulate. */
    if (s->recent_count == 0U ||
        (now - s->window_start_ms) > FDIR_RECENT_WINDOW_MS) {
        s->window_start_ms = now;
        s->recent_count    = 1U;
    } else {
        s->recent_count   += 1U;
    }

    s->total_count += 1U;
    s->last_event_ms = now;

    g_stats.total_faults += 1U;

    /* Update escalation / recovery aggregate stats eagerly so the
     * downlink telemetry reflects the current policy even before a
     * caller asks for GetRecommendedAction. */
    const FDIR_FaultEntry_t *e = &g_table[id];
    FDIR_Recovery_t rec = (s->recent_count >= e->escalation_threshold)
                          ? e->escalation : e->primary;

    g_stats.total_recoveries_invoked += 1U;
    if (rec == e->escalation && e->escalation != e->primary) {
        g_stats.escalations += 1U;
    }
    if (rec == RECOVERY_SAFE_MODE) {
        g_stats.safe_mode_entries += 1U;
    }
    if (rec == RECOVERY_REBOOT) {
        g_stats.reboots_scheduled += 1U;
    }
}

FDIR_Recovery_t FDIR_GetRecommendedAction(FDIR_FaultId_t id)
{
    if ((uint32_t)id >= FDIR_FAULT_COUNT) { return RECOVERY_LOG_ONLY; }
    const FDIR_FaultEntry_t *e = &g_table[id];
    const FDIR_FaultState_t *s = &g_state[id];
    return (s->recent_count >= e->escalation_threshold)
           ? e->escalation : e->primary;
}

const FDIR_FaultState_t *FDIR_GetState(FDIR_FaultId_t id)
{
    if ((uint32_t)id >= FDIR_FAULT_COUNT) { return NULL; }
    return &g_state[id];
}

const FDIR_FaultEntry_t *FDIR_GetEntry(FDIR_FaultId_t id)
{
    if ((uint32_t)id >= FDIR_FAULT_COUNT) { return NULL; }
    return &g_table[id];
}

FDIR_Stats_t FDIR_GetStats(void)
{
    return g_stats;
}

void FDIR_ClearRecent(FDIR_FaultId_t id)
{
    if ((uint32_t)id >= FDIR_FAULT_COUNT) { return; }
    g_state[id].recent_count = 0U;
    /* window_start_ms is left alone; on next Report the "recent == 0"
     * branch re-initialises it. */
}

void FDIR_ResetAll(void)
{
    FDIR_Init();
}
