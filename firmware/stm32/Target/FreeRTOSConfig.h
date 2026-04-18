/**
 ******************************************************************************
 *  UniSat — FreeRTOS configuration for STM32F446RE + CMSIS-RTOSv2.
 *
 *  Values tuned for the UniSat OBC:
 *    * CPU @ 168 MHz
 *    * heap_4 with 24 KB (24 * 1024 B) — enough for 6 tasks + queues,
 *      leaves plenty of SRAM for .data/.bss
 *    * Tickless idle disabled for simplicity (pulls in low-power
 *      tuning separately if needed)
 *    * 2ms systick period (500 Hz) — lets CMSIS-RTOSv2 osDelayUntil
 *      achieve its advertised resolution
 *
 *  Matches the default layout STM32CubeMX generates for F4 + CMSIS-OS
 *  + heap_4, minus the options UniSat does not use (no co-routines,
 *  no trace, no stats runtime formatting).
 ******************************************************************************
 */
#ifndef FREERTOS_CONFIG_H
#define FREERTOS_CONFIG_H

#include <stdint.h>

/* CMSIS-RTOSv2 wrapper (freertos_os2.h) uses `#include CMSIS_device_header`
 * — define it up-front so the CMSIS core declarations (IRQn_Type,
 * SysTick, NVIC_Set/GetPriority) are visible before kernel sources
 * reference them. */
#define CMSIS_device_header "stm32f4xx.h"

extern uint32_t SystemCoreClock;

/* ───────────── General ───────────── */

#define configUSE_PREEMPTION                 1
#define configSUPPORT_STATIC_ALLOCATION      1
#define configSUPPORT_DYNAMIC_ALLOCATION     1
#define configUSE_IDLE_HOOK                  0
#define configUSE_TICK_HOOK                  0
#define configCPU_CLOCK_HZ                   ((uint32_t)168000000U)
#define configTICK_RATE_HZ                   ((TickType_t)500)
/* CMSIS-RTOSv2 mapping requires 56 priorities and no port-optimised
 * task selection (cmsis_os2 needs the generic O(n) picker). */
#define configMAX_PRIORITIES                 56
#define configMINIMAL_STACK_SIZE             ((uint16_t)128)
#define configTOTAL_HEAP_SIZE                ((size_t)(24 * 1024))
#define configMAX_TASK_NAME_LEN              16
#define configUSE_16_BIT_TICKS               0
#define configIDLE_SHOULD_YIELD              1
#define configUSE_MUTEXES                    1
#define configUSE_RECURSIVE_MUTEXES          1
#define configUSE_COUNTING_SEMAPHORES        1
#define configUSE_PORT_OPTIMISED_TASK_SELECTION 0
#define INCLUDE_eTaskGetState                 1
#define configUSE_TASK_NOTIFICATIONS         1
#define configUSE_TRACE_FACILITY             1
#define configUSE_QUEUE_SETS                 1

/* ───────────── Debug + health ───────────── */

#define configCHECK_FOR_STACK_OVERFLOW       2
#define configUSE_MALLOC_FAILED_HOOK         1
#define configGENERATE_RUN_TIME_STATS        0
#define configUSE_STATS_FORMATTING_FUNCTIONS 0

/* ───────────── Software timers ───────────── */

#define configUSE_TIMERS                     1
#define configTIMER_TASK_PRIORITY            2
#define configTIMER_QUEUE_LENGTH             10
#define configTIMER_TASK_STACK_DEPTH         ((uint16_t)256)

/* ───────────── Coroutines (disabled) ───────────── */

#define configUSE_CO_ROUTINES                0

/* ───────────── API functions to expose ───────────── */

#define INCLUDE_vTaskPrioritySet             1
#define INCLUDE_uxTaskPriorityGet            1
#define INCLUDE_vTaskDelete                  1
#define INCLUDE_vTaskCleanUpResources        0
#define INCLUDE_vTaskSuspend                 1
#define INCLUDE_vTaskDelayUntil              1
#define INCLUDE_vTaskDelay                   1
#define INCLUDE_xTaskGetSchedulerState       1
#define INCLUDE_xTimerPendFunctionCall       1
#define INCLUDE_xQueueGetMutexHolder         1
#define INCLUDE_uxTaskGetStackHighWaterMark  1

/* ───────────── Cortex-M specific ───────────── */

#ifdef __NVIC_PRIO_BITS
  #define configPRIO_BITS                    __NVIC_PRIO_BITS
#else
  #define configPRIO_BITS                    4
#endif

#define configLIBRARY_LOWEST_INTERRUPT_PRIORITY     15
#define configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY 5

#define configKERNEL_INTERRUPT_PRIORITY \
        (configLIBRARY_LOWEST_INTERRUPT_PRIORITY << (8 - configPRIO_BITS))
#define configMAX_SYSCALL_INTERRUPT_PRIORITY \
        (configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY << (8 - configPRIO_BITS))

/* ───────────── ISR + exception handlers ─────────────
 *
 * FreeRTOS overrides PendSV / SVC / SysTick with its port.c strong
 * symbols. The #defines below let application code refer to the
 * CMSIS names while the kernel keeps its own. */
/* Map SVC and PendSV to the stock CMSIS names so the vector table
 * can hand off to the kernel. SysTick is OWNED by cmsis_os2.c — it
 * calls osSystickHandler → xPortSysTickHandler → vTaskStep internally,
 * so mapping xPortSysTickHandler here would collide with the
 * wrapper's own definition. */
#define vPortSVCHandler      SVC_Handler
#define xPortPendSVHandler   PendSV_Handler

/* ───────────── Run-time stats hook (no-op) ───────────── */

#define portCONFIGURE_TIMER_FOR_RUN_TIME_STATS()
#define portGET_RUN_TIME_COUNTER_VALUE()      0

#define configASSERT(x) ((void)0)

#endif /* FREERTOS_CONFIG_H */
