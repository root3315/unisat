/**
 * @file watchdog.c
 * @brief Hardware and software watchdog implementation
 */

#include "watchdog.h"
#include "error_handler.h"
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
