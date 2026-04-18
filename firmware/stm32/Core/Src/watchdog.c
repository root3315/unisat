/**
 * @file watchdog.c
 * @brief Hardware + software watchdog, integrated with FDIR.
 *
 * Per-task liveness is tracked via last_feed_time[]; the hardware
 * IWDG is kicked from the dedicated WatchdogTask at a cadence well
 * below the IWDG reload window so a missing feed turns into a
 * deterministic reset rather than a hang.
 *
 * When Watchdog_CheckAll detects a task that has not fed within
 * WATCHDOG_TIMEOUT_MS:
 *   1. Error_Log captures the event into the on-board log.
 *   2. FDIR_Report(FAULT_WATCHDOG_TASK_MISS) is called so the
 *      escalation-window logic decides whether this is a one-off
 *      glitch or the 3rd miss inside 60 s (→ REBOOT).
 *   3. Error_Handler is invoked with ERR_WATCHDOG_TIMEOUT; it
 *      consults FDIR_GetRecommendedAction to decide between a
 *      local retry, safe-mode entry, or a clean reboot.
 */

#include "watchdog.h"
#include "error_handler.h"
#include "fdir.h"
#include "config.h"
#include <string.h>

#ifndef SIMULATION_MODE
#include "stm32f4xx_hal.h"
static IWDG_HandleTypeDef hiwdg;
#else
static uint32_t sim_tick = 0;
static uint32_t HAL_GetTick(void) { return sim_tick += 100; }
#endif

static uint32_t last_feed_time[TASK_COUNT];
static bool watchdog_enabled = false;

void Watchdog_Init(void) {
    memset(last_feed_time, 0, sizeof(last_feed_time));

#ifndef SIMULATION_MODE
    hiwdg.Instance = IWDG;
    hiwdg.Init.Prescaler = IWDG_PRESCALER_256;
    hiwdg.Init.Reload = 4095;
    HAL_IWDG_Init(&hiwdg);
#endif

    watchdog_enabled = true;
}

void Watchdog_Feed(WatchdogTask_t task) {
    if (task < TASK_COUNT) {
#ifndef SIMULATION_MODE
        last_feed_time[task] = HAL_GetTick();
#else
        last_feed_time[task] = HAL_GetTick();
#endif
    }
}

bool Watchdog_IsTaskAlive(WatchdogTask_t task) {
    if (task >= TASK_COUNT) return false;
    if (!watchdog_enabled) return true;

#ifndef SIMULATION_MODE
    uint32_t elapsed = HAL_GetTick() - last_feed_time[task];
#else
    uint32_t elapsed = HAL_GetTick() - last_feed_time[task];
#endif

    return elapsed < WATCHDOG_TIMEOUT_MS;
}

void Watchdog_CheckAll(void) {
    if (!watchdog_enabled) return;

    for (uint8_t i = 0; i < TASK_COUNT; i++) {
        if (!Watchdog_IsTaskAlive((WatchdogTask_t)i)) {
            Error_Log(ERR_WATCHDOG_TIMEOUT, ERROR_CRITICAL,
                      "Task watchdog timeout");
            /* Route the event into the FDIR advisor so the per-fault
             * escalation window (3 misses inside 60 s → REBOOT)
             * applies. Error_Handler then consults FDIR to decide
             * between log-only, safe-mode, or reboot. */
            FDIR_Report(FAULT_WATCHDOG_TASK_MISS);
            Error_Handler(ERR_WATCHDOG_TIMEOUT);
        }
    }
}

uint32_t Watchdog_GetLastFeedTime(WatchdogTask_t task) {
    if (task >= TASK_COUNT) return 0;
    return last_feed_time[task];
}

void Watchdog_Enable(void) {
    watchdog_enabled = true;
}

void Watchdog_Disable(void) {
    watchdog_enabled = false;
}

void Watchdog_FeedHardware(void) {
#ifndef SIMULATION_MODE
    HAL_IWDG_Refresh(&hiwdg);
#endif
}
