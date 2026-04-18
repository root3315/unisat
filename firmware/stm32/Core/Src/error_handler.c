/**
 * @file error_handler.c
 * @brief Error handling and safe mode management
 */

#include "error_handler.h"
#include "eps.h"
#include "comm.h"
#include "config.h"
#include <string.h>

#ifndef SIMULATION_MODE
#include "stm32f4xx_hal.h"
#else
static uint32_t sim_tick = 0;
static uint32_t HAL_GetTick(void) { return sim_tick += 100; }
#endif

#define ERROR_LOG_MAX_ENTRIES 64
#define EEPROM_ERROR_BASE_ADDR 0x100

static ErrorEntry_t error_log[ERROR_LOG_MAX_ENTRIES];
static uint16_t error_count = 0;
static uint16_t error_log_index = 0;
static bool in_safe_mode = false;

void Error_Init(void) {
    memset(error_log, 0, sizeof(error_log));
    error_count = 0;
    error_log_index = 0;
    in_safe_mode = false;
}

void Error_Log(ErrorCode_t code, ErrorSeverity_t severity, const char *msg) {
    ErrorEntry_t entry;
    entry.timestamp = HAL_GetTick();
    entry.code = code;
    entry.severity = severity;
    entry.subsystem = 0;

    if (msg != NULL) {
        strncpy(entry.message, msg, sizeof(entry.message) - 1);
        entry.message[sizeof(entry.message) - 1] = '\0';
    } else {
        entry.message[0] = '\0';
    }

    error_log[error_log_index] = entry;
    error_log_index = (uint16_t)((error_log_index + 1U) % ERROR_LOG_MAX_ENTRIES);
    error_count++;

    if (severity >= ERROR_ERROR) {
        Error_WriteToEEPROM(&entry);
    }
}

void Error_Handler(ErrorCode_t code) {
    switch (code) {
        case ERR_CRITICAL_BATTERY:
            EPS_EmergencyShutdown();
            Error_EnterSafeMode(code);
            break;

        case ERR_LOW_BATTERY:
            /* Disable non-essential subsystems */
            EPS_DisableSubsystem(POWER_SUBSYS_CAMERA);
            EPS_DisableSubsystem(POWER_SUBSYS_PAYLOAD);
            break;

        case ERR_WATCHDOG_TIMEOUT:
            Error_EnterSafeMode(code);
            break;

        case ERR_TEMPERATURE_HIGH:
        case ERR_TEMPERATURE_LOW:
            /* Reduce power consumption */
            EPS_DisableSubsystem(POWER_SUBSYS_CAMERA);
            break;

        case ERR_COMM_FAILURE:
            /* Will be handled by safe mode check in main loop */
            break;

        default:
            break;
    }
}

void Error_EnterSafeMode(ErrorCode_t reason) {
    if (in_safe_mode) return;

    in_safe_mode = true;
    Error_Log(ERR_SAFE_MODE_ENTER, ERROR_CRITICAL, "Entering safe mode");

    /* Disable all non-essential subsystems */
    EPS_DisableSubsystem(POWER_SUBSYS_CAMERA);
    EPS_DisableSubsystem(POWER_SUBSYS_PAYLOAD);
    EPS_DisableSubsystem(POWER_SUBSYS_HEATER);

    /* Keep OBC, COMM, and basic ADCS (detumbling) active */
    (void)reason;
}

void Error_ExitSafeMode(void) {
    in_safe_mode = false;

    /* Re-enable subsystems based on config */
    if (config.camera.enabled) {
        EPS_EnableSubsystem(POWER_SUBSYS_CAMERA);
    }
    if (config.payload.enabled) {
        EPS_EnableSubsystem(POWER_SUBSYS_PAYLOAD);
    }
}

bool Error_IsInSafeMode(void) {
    return in_safe_mode;
}

uint16_t Error_GetCount(void) {
    return error_count;
}

ErrorEntry_t Error_GetLast(void) {
    uint16_t idx = (error_log_index == 0) ?
                    ERROR_LOG_MAX_ENTRIES - 1 : error_log_index - 1;
    return error_log[idx];
}

void Error_WriteToEEPROM(ErrorEntry_t *entry) {
#ifndef SIMULATION_MODE
    /* Write to backup SRAM as EEPROM substitute */
    uint32_t addr = EEPROM_ERROR_BASE_ADDR +
                    (error_count % 16) * sizeof(ErrorEntry_t);
    uint32_t *src = (uint32_t *)entry;
    for (uint16_t i = 0; i < sizeof(ErrorEntry_t) / 4; i++) {
        extern void OBC_BackupWrite(uint32_t addr, uint32_t data);
        OBC_BackupWrite(addr + i * 4, src[i]);
    }
#else
    (void)entry;
#endif
}

uint16_t Error_ReadFromEEPROM(ErrorEntry_t *entries, uint16_t max_count) {
    (void)entries;
    (void)max_count;
    return 0;
}

void Error_ClearLog(void) {
    memset(error_log, 0, sizeof(error_log));
    error_count = 0;
    error_log_index = 0;
}
