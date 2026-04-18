/**
 * @file mode_manager.h
 * @brief System-mode supervisor — enacts FDIR recovery recommendations.
 *
 * The FDIR module (fdir.h) is advisory: it tracks faults, counts
 * them, and returns a recommended recovery action. mode_manager is
 * the commanding counterpart — it translates those recommendations
 * into real state changes on the flight software:
 *
 *   RECOVERY_SAFE_MODE  -> ModeManager_EnterSafeMode(reason)
 *   RECOVERY_DISABLE_SUBSYS -> subsystem disable hook
 *   RECOVERY_REBOOT     -> logged + NVIC_SystemReset on target /
 *                          noop on host so tests don't self-terminate
 *
 * One-shot supervisor poll is designed to run from the WatchdogTask
 * every second. It walks every fault id, asks FDIR for the
 * recommendation, and escalates to the highest-severity action any
 * fault is currently requesting. Idempotent — re-entering SAFE_MODE
 * while already there is a no-op.
 *
 * Keeping the supervisor in a separate module (not inside fdir.c)
 * preserves the advisory contract: unit tests that link only fdir.c
 * never pull in NVIC_SystemReset or the subsystem disable table.
 */
#ifndef MODE_MANAGER_H
#define MODE_MANAGER_H

#include <stdint.h>
#include <stdbool.h>
#include "fdir.h"

/** Satellite-level operating mode. */
typedef enum {
    MODE_BOOT        = 0,  /* post-reset, before nominal entry        */
    MODE_NOMINAL     = 1,  /* full-function, all subsystems enabled   */
    MODE_SAFE        = 2,  /* beacon-only, reduced power              */
    MODE_DEGRADED    = 3,  /* one or more subsystems disabled         */
    MODE_REBOOT_PEND = 4   /* reboot armed, next poll fires it        */
} SystemMode_t;

/** Reason codes tracked per mode transition. Numbered densely so the
 *  enum fits in a uint8_t telemetry field. */
typedef enum {
    MODE_REASON_BOOT            = 0,
    MODE_REASON_NOMINAL_START   = 1,
    MODE_REASON_FDIR_SAFE       = 2,
    MODE_REASON_FDIR_REBOOT     = 3,
    MODE_REASON_FDIR_DISABLE    = 4,
    MODE_REASON_COMM_LOSS       = 5,
    MODE_REASON_MANUAL_GROUND   = 6
} ModeReason_t;

/** Cumulative transition accounting for downlink telemetry. */
typedef struct {
    uint32_t transitions_total;
    uint32_t safe_entries;
    uint32_t safe_exits;
    uint32_t subsystem_disables;
    uint32_t reboots_requested;
    SystemMode_t current_mode;
    ModeReason_t last_reason;
} ModeManager_Stats_t;

/** One-shot boot initialiser. Mode starts at MODE_BOOT and the first
 *  call to ModeManager_EnterNominal() after subsystems are up bumps
 *  it to MODE_NOMINAL. Safe to call repeatedly; second call is a
 *  no-op. */
void ModeManager_Init(void);

/** Runtime supervisor tick — call at ≥ 1 Hz from WatchdogTask.
 *  Polls every FDIR fault id, selects the highest-severity recovery
 *  recommendation across all of them, and drives the corresponding
 *  mode transition. Returns the mode in effect after the poll. */
SystemMode_t ModeManager_Tick(void);

/** Direct transitions — callable from subsystem init, command
 *  handler, or unit test. All are idempotent w.r.t. the current
 *  mode (re-entering SAFE while already in SAFE is a no-op). */
void ModeManager_EnterNominal(void);
void ModeManager_EnterSafe(ModeReason_t reason);
void ModeManager_EnterDegraded(ModeReason_t reason);
void ModeManager_RequestReboot(ModeReason_t reason);

/** Current mode query (also exported through GetStats). */
SystemMode_t ModeManager_GetMode(void);

/** Telemetry snapshot. */
ModeManager_Stats_t ModeManager_GetStats(void);

/** Reset all counters + force mode back to BOOT. Test-fixture only;
 *  never called in production. */
void ModeManager_ResetForTest(void);

/** Platform hook — on target this calls NVIC_SystemReset(). On host
 *  (SIMULATION_MODE) the weak default is a no-op so unit tests do
 *  not self-terminate. Override with a strong symbol in the test
 *  harness to inject failures. */
void ModeManager_PlatformReboot(void);


#endif /* MODE_MANAGER_H */
