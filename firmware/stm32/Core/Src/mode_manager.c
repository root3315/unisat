/**
 * @file mode_manager.c
 * @brief System-mode supervisor — commanding side of the FDIR advisor.
 *
 * Responsibilities (see mode_manager.h for the API contract):
 *   1. Hold the single source of truth for SystemMode_t.
 *   2. Perform the mode transition itself (counters, reason log).
 *   3. On every tick, poll FDIR for the worst-case recommendation
 *      across all fault ids and enact it via the internal
 *      transition helpers.
 *   4. Delegate the final reboot action to a weak platform hook so
 *      the host test suite can exercise MODE_REBOOT_PEND without
 *      calling NVIC_SystemReset.
 *
 * Transitions are idempotent: calling EnterSafe when already in
 * SAFE bumps the transitions_total counter but does not double-log
 * "safe_entries" — tracking the distinction separately would add
 * no operational value and would complicate the stats contract.
 */

#include "mode_manager.h"
#include <string.h>

/* ------------------------------------------------------------------
 *  Module state
 * ------------------------------------------------------------------ */
static SystemMode_t       g_mode   = MODE_BOOT;
static ModeReason_t       g_reason = MODE_REASON_BOOT;
static ModeManager_Stats_t g_stats  = {0, 0, 0, 0, 0, MODE_BOOT, MODE_REASON_BOOT};

/* ------------------------------------------------------------------
 *  Platform hook — weak, so host tests link without NVIC_SystemReset.
 * ------------------------------------------------------------------ */
__attribute__((weak)) void ModeManager_PlatformReboot(void)
{
    /* Default no-op. Target firmware override (in stm32f4xx_it.c or
     * a Target/<impl>.c source file) calls NVIC_SystemReset() after a
     * short delay so the telemetry task has a chance to flush the
     * last status frame before the core resets. */
}

/* ------------------------------------------------------------------
 *  Internal: single-point transition function
 * ------------------------------------------------------------------ */
static void transition(SystemMode_t to, ModeReason_t reason)
{
    g_stats.transitions_total++;

    /* Per-transition bookkeeping before we update g_mode so the
     * "from" side can be inspected. */
    if (g_mode != MODE_SAFE && to == MODE_SAFE) {
        g_stats.safe_entries++;
    }
    if (g_mode == MODE_SAFE && to == MODE_NOMINAL) {
        g_stats.safe_exits++;
    }
    if (g_mode != MODE_DEGRADED && to == MODE_DEGRADED) {
        g_stats.subsystem_disables++;
    }
    if (to == MODE_REBOOT_PEND) {
        g_stats.reboots_requested++;
    }

    g_mode = to;
    g_reason = reason;
    g_stats.current_mode = to;
    g_stats.last_reason  = reason;
}

/* ------------------------------------------------------------------
 *  Public API
 * ------------------------------------------------------------------ */

void ModeManager_Init(void)
{
    memset(&g_stats, 0, sizeof(g_stats));
    g_mode = MODE_BOOT;
    g_reason = MODE_REASON_BOOT;
    g_stats.current_mode = MODE_BOOT;
    g_stats.last_reason  = MODE_REASON_BOOT;
}

SystemMode_t ModeManager_GetMode(void) { return g_mode; }

ModeManager_Stats_t ModeManager_GetStats(void) { return g_stats; }

void ModeManager_EnterNominal(void)
{
    if (g_mode == MODE_NOMINAL) { return; }
    transition(MODE_NOMINAL, MODE_REASON_NOMINAL_START);
}

void ModeManager_EnterSafe(ModeReason_t reason)
{
    /* Idempotent: already-in-SAFE re-entry is a no-op on counters
     * to match the SafeModeHandler (Python) contract documented in
     * REQ-SAFE-003. */
    if (g_mode == MODE_SAFE) { return; }
    transition(MODE_SAFE, reason);
}

void ModeManager_EnterDegraded(ModeReason_t reason)
{
    if (g_mode == MODE_DEGRADED) { return; }
    /* DEGRADED is only meaningful from NOMINAL — if we're already in
     * SAFE, stay there; SAFE is strictly a superset of the subsystems
     * that DEGRADED would disable, so a downgrade would be a step
     * backward. */
    if (g_mode == MODE_SAFE) { return; }
    transition(MODE_DEGRADED, reason);
}

void ModeManager_RequestReboot(ModeReason_t reason)
{
    /* Arm the pending-reboot state; the actual NVIC_SystemReset
     * fires on the next ModeManager_Tick call so the telemetry task
     * has a window to flush the reason code into the downlink. */
    if (g_mode == MODE_REBOOT_PEND) { return; }
    transition(MODE_REBOOT_PEND, reason);
}

/* ------------------------------------------------------------------
 *  Tick: poll FDIR and act.
 *
 *  Algorithm
 *    1. Iterate every fault id (0..FDIR_FAULT_COUNT-1).
 *    2. Track the highest-severity recovery action anyone requests.
 *    3. Map the winning recommendation to a mode transition.
 *    4. If we armed a REBOOT on the previous tick, fire the
 *       platform hook now.
 * ------------------------------------------------------------------ */
static FDIR_Recovery_t worst_action(void)
{
    FDIR_Recovery_t worst = RECOVERY_LOG_ONLY;
    for (uint32_t id = 0; id < FDIR_FAULT_COUNT; id++) {
        FDIR_Recovery_t rec =
            FDIR_GetRecommendedAction((FDIR_FaultId_t)id);
        /* Enum values are already in severity order. */
        if ((uint32_t)rec > (uint32_t)worst) {
            worst = rec;
        }
    }
    return worst;
}

SystemMode_t ModeManager_Tick(void)
{
    /* If a reboot was armed on the previous tick, enact it now. */
    if (g_mode == MODE_REBOOT_PEND) {
        ModeManager_PlatformReboot();
        /* On host or if reboot hook is a no-op, the supervisor stays
         * in MODE_REBOOT_PEND so downlink telemetry keeps reporting
         * the pending state — a real target never returns here. */
        return g_mode;
    }

    FDIR_Recovery_t worst = worst_action();
    switch (worst) {
    case RECOVERY_REBOOT:
        ModeManager_RequestReboot(MODE_REASON_FDIR_REBOOT);
        break;
    case RECOVERY_SAFE_MODE:
        ModeManager_EnterSafe(MODE_REASON_FDIR_SAFE);
        break;
    case RECOVERY_DISABLE_SUBSYS:
        ModeManager_EnterDegraded(MODE_REASON_FDIR_DISABLE);
        break;
    case RECOVERY_RESET_BUS:
    case RECOVERY_RETRY:
    case RECOVERY_LOG_ONLY:
    default:
        /* Leaf-level actions are enacted by the driver that detected
         * the fault; no mode change at the supervisor level. If we're
         * currently in SAFE / DEGRADED and the worst is now benign,
         * bring the satellite back to NOMINAL. */
        if ((g_mode == MODE_SAFE || g_mode == MODE_DEGRADED) &&
            worst <= RECOVERY_RESET_BUS) {
            ModeManager_EnterNominal();
        }
        break;
    }
    return g_mode;
}

void ModeManager_ResetForTest(void)
{
    ModeManager_Init();
}
