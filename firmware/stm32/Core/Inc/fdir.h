/**
 * @file fdir.h
 * @brief Fault Detection, Isolation, Recovery (FDIR) for the UniSat OBC.
 *
 * The FDIR subsystem is the satellite's autonomous watchdog above
 * the hardware IWDG. It maintains a fault table where every
 * anomaly the flight software can detect gets:
 *
 *   * a persistent counter    (how many times has this happened?)
 *   * a recent-window counter (how often lately?)
 *   * a primary recovery action
 *   * an escalation recovery action triggered once the per-fault
 *     counter crosses its escalation threshold inside the recent
 *     window.
 *
 * The recovery actions form a strict severity ladder so that
 * repeated low-severity faults eventually escalate into a reboot
 * instead of spinning forever on log-only.
 *
 *     LOG_ONLY
 *       └─► RETRY              (transient — re-try the operation)
 *             └─► RESET_BUS    (reset the peripheral / bus)
 *                   └─► DISABLE_SUBSYS  (isolate: turn the failing
 *                                        subsystem off; mission can
 *                                        continue in a degraded mode)
 *                         └─► SAFE_MODE (put the satellite into
 *                                        safe-hold — beacon only,
 *                                        minimum power, stable
 *                                        attitude, wait for ground)
 *                               └─► REBOOT  (NVIC_SystemReset after
 *                                            logging the reason into
 *                                            the non-volatile fault
 *                                            record for post-mortem)
 *
 * The table itself is a POD array so unit tests can cover every
 * transition without spinning FreeRTOS — each fault is exercised by
 * calling FDIR_Report and reading FDIR_GetRecommendedAction.
 */
#ifndef FDIR_H
#define FDIR_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/** Recent-window width for escalation, in milliseconds. Faults that
 *  fire more often than `threshold / window` escalate; slower
 *  recurrences reset the recent-counter back to 1.  Default 60 s
 *  matches the housekeeping-telemetry downlink cadence so every
 *  escalation is observable in at most one pass. */
#define FDIR_RECENT_WINDOW_MS     60000U

/** Maximum number of fault IDs. Keep this +1 when adding entries so
 *  the compile-time size check in fdir.c stays in sync. */
#define FDIR_FAULT_COUNT          12U

/** Recovery actions, in severity order. */
typedef enum {
    RECOVERY_LOG_ONLY       = 0,
    RECOVERY_RETRY          = 1,
    RECOVERY_RESET_BUS      = 2,
    RECOVERY_DISABLE_SUBSYS = 3,
    RECOVERY_SAFE_MODE      = 4,
    RECOVERY_REBOOT         = 5
} FDIR_Recovery_t;

/** Fault identifiers. Ordered by rough subsystem; values pinned so
 *  downlink telemetry can decode them without a lookup table. */
typedef enum {
    FAULT_WATCHDOG_TASK_MISS   =  0,  /* FreeRTOS task stopped feeding */
    FAULT_I2C_BUS_STUCK        =  1,  /* I2C SDA/SCL hang, no ACK      */
    FAULT_SPI_TIMEOUT          =  2,  /* SPI transfer never returns    */
    FAULT_SENSOR_OUT_OF_RANGE  =  3,  /* sensor value outside spec     */
    FAULT_BATTERY_UNDERVOLT    =  4,  /* EPS battery below safe floor  */
    FAULT_OVER_TEMPERATURE     =  5,  /* on-board temp > limit         */
    FAULT_UNDER_TEMPERATURE    =  6,  /* on-board temp < limit         */
    FAULT_STACK_OVERFLOW       =  7,  /* FreeRTOS stack check tripped  */
    FAULT_HEAP_EXHAUST         =  8,  /* pvPortMalloc returned NULL    */
    FAULT_PLL_UNLOCK           =  9,  /* RCC clock tree anomaly        */
    FAULT_COMM_LOSS            = 10,  /* no uplink in >24 h            */
    FAULT_KEYSTORE_EMPTY       = 11   /* boot with no valid HMAC key   */
} FDIR_FaultId_t;


/** Per-fault runtime state. */
typedef struct {
    uint32_t total_count;      /* lifetime occurrences                 */
    uint32_t recent_count;     /* occurrences inside current window    */
    uint32_t window_start_ms;  /* HAL_GetTick at start of recent window */
    uint32_t last_event_ms;    /* HAL_GetTick at most recent Report    */
    /* Grayscale severity tracking (see FDIR_ReportGrayscale).
     *
     *   severity_ema : exponential moving average of the last
     *                  severity samples (0..255). Uses a shift-based
     *                  update so there is no division on a hot path.
     *   severity_peak: worst sample observed inside the recent window
     *                  — clamps back down when FDIR_ClearRecent fires. */
    uint32_t severity_ema;
    uint32_t severity_peak;
} FDIR_FaultState_t;

/** Grayscale severity bands used by FDIR_ReportGrayscale. The bands
 *  map analogue sensor drift onto the same recovery ladder the
 *  binary FDIR_Report drives, so a gradually-worsening sensor can
 *  escalate without a hard fault ever tripping. */
#define FDIR_SEVERITY_NOMINAL   0U    /* no action needed              */
#define FDIR_SEVERITY_WATCH     64U   /* within margin, keep watching  */
#define FDIR_SEVERITY_WARNING   128U  /* drift exceeds tolerance       */
#define FDIR_SEVERITY_MAJOR     192U  /* drift triggers DISABLE_SUBSYS */
#define FDIR_SEVERITY_CRITICAL  255U  /* drift triggers SAFE_MODE      */


/** Static per-fault configuration — immutable after FDIR_Init. */
typedef struct {
    FDIR_FaultId_t  id;
    const char     *name;
    FDIR_Recovery_t primary;
    FDIR_Recovery_t escalation;
    uint32_t        escalation_threshold;  /* recent_count that triggers */
} FDIR_FaultEntry_t;


/** Aggregate snapshot for telemetry. */
typedef struct {
    uint32_t total_faults;
    uint32_t total_recoveries_invoked;
    uint32_t escalations;          /* how many times escalation fired */
    uint32_t reboots_scheduled;    /* REBOOT recommended (actually
                                      executed or not is orthogonal) */
    uint32_t safe_mode_entries;
} FDIR_Stats_t;


/* =================================================================
 *  API
 * ================================================================= */

/** One-shot initialisation. Zeroes per-fault state, resets stats,
 *  binds the static fault-table. Call after SystemClock_Config and
 *  before any task starts reporting faults. */
void FDIR_Init(void);

/** Report a fault occurrence. Increments the counters and updates
 *  the recent-window bookkeeping. Safe to call from any FreeRTOS
 *  task; protected by a local critical section so concurrent
 *  writers cannot corrupt the counters. */
void FDIR_Report(FDIR_FaultId_t id);

/** Report a graded (grayscale) severity sample for a fault.
 *
 *  Complements the binary FDIR_Report for anomalies that live on a
 *  continuum rather than a clean fired/not-fired boundary — sensor
 *  drift, thermal warming, slowly-degrading link margin. ``sample``
 *  is a 0..255 severity level (use the FDIR_SEVERITY_* constants).
 *  The module maintains an exponential moving average per fault,
 *  and the recommendation is computed from whichever of the binary
 *  recent-count or the EMA crosses the severity ladder first.
 *
 *  Calling FDIR_ReportGrayscale with a high sample value DOES still
 *  bump the binary recent_count so a sensor that pins to CRITICAL
 *  several samples in a row eventually escalates via the regular
 *  recent-window threshold as well. */
void FDIR_ReportGrayscale(FDIR_FaultId_t id, uint8_t sample);

/** Return the recovery action the FDIR recommends for the current
 *  state of a given fault. If the recent-window count is at or
 *  above escalation_threshold, the escalation action is returned;
 *  otherwise the primary action. Callers (safe-mode manager,
 *  subsystem supervisors) are expected to react — the FDIR itself
 *  does not invoke the recovery, it only advises. */
FDIR_Recovery_t FDIR_GetRecommendedAction(FDIR_FaultId_t id);

/** Read the per-fault state (lifetime + recent counters). */
const FDIR_FaultState_t *FDIR_GetState(FDIR_FaultId_t id);

/** Look up the immutable configuration for a fault id. */
const FDIR_FaultEntry_t *FDIR_GetEntry(FDIR_FaultId_t id);

/** Aggregate stats snapshot (telemetry). */
FDIR_Stats_t FDIR_GetStats(void);

/** Clear the recent-window counter for a given fault. Used by a
 *  successful retry / bus-reset to tell FDIR "the subsystem is
 *  healthy again, don't escalate on the next glitch". */
void FDIR_ClearRecent(FDIR_FaultId_t id);

/** Reset all counters — factory-reset path, unit-test fixtures,
 *  never called in production. */
void FDIR_ResetAll(void);

/** Hook for unit tests (and the simulation) — lets the test inject
 *  a deterministic ms tick without linking HAL. Defined __weak in
 *  fdir.c so a target build uses the real HAL_GetTick. */
uint32_t FDIR_GetTick(void);


#endif /* FDIR_H */
