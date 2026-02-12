/**
 * @file watchdog.h
 * @brief Hardware and software watchdog management
 */

#ifndef WATCHDOG_H
#define WATCHDOG_H

#include <stdint.h>
#include <stdbool.h>

/** Task identifiers for watchdog monitoring */
typedef enum {
    TASK_SENSOR = 0,
    TASK_TELEMETRY,
    TASK_COMM,
    TASK_ADCS,
    TASK_PAYLOAD,
    TASK_COUNT
} WatchdogTask_t;

void Watchdog_Init(void);
void Watchdog_Feed(WatchdogTask_t task);
bool Watchdog_IsTaskAlive(WatchdogTask_t task);
void Watchdog_CheckAll(void);
uint32_t Watchdog_GetLastFeedTime(WatchdogTask_t task);
void Watchdog_Enable(void);
void Watchdog_Disable(void);
void Watchdog_FeedHardware(void);

#endif /* WATCHDOG_H */
