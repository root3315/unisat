/**
 * @file error_handler.h
 * @brief Error handling and safe mode management
 */

#ifndef ERROR_HANDLER_H
#define ERROR_HANDLER_H

#include <stdint.h>
#include <stdbool.h>

/** Error severity levels */
typedef enum {
    ERROR_DEBUG = 0,
    ERROR_INFO,
    ERROR_WARNING,
    ERROR_ERROR,
    ERROR_CRITICAL
} ErrorSeverity_t;

/** Error codes */
typedef enum {
    ERR_NONE = 0,
    ERR_SENSOR_TIMEOUT,
    ERR_COMM_FAILURE,
    ERR_LOW_BATTERY,
    ERR_CRITICAL_BATTERY,
    ERR_ADCS_FAILURE,
    ERR_GNSS_NO_FIX,
    ERR_WATCHDOG_TIMEOUT,
    ERR_MEMORY_CORRUPT,
    ERR_TEMPERATURE_HIGH,
    ERR_TEMPERATURE_LOW,
    ERR_PAYLOAD_FAILURE,
    ERR_EEPROM_WRITE,
    ERR_SAFE_MODE_ENTER
} ErrorCode_t;

/** Error log entry */
typedef struct {
    uint32_t timestamp;
    ErrorCode_t code;
    ErrorSeverity_t severity;
    uint8_t subsystem;
    char message[32];
} ErrorEntry_t;

void Error_Init(void);
void Error_Log(ErrorCode_t code, ErrorSeverity_t severity, const char *msg);
void Error_Handler(ErrorCode_t code);
void Error_EnterSafeMode(ErrorCode_t reason);
void Error_ExitSafeMode(void);
bool Error_IsInSafeMode(void);
uint16_t Error_GetCount(void);
ErrorEntry_t Error_GetLast(void);
void Error_WriteToEEPROM(ErrorEntry_t *entry);
uint16_t Error_ReadFromEEPROM(ErrorEntry_t *entries, uint16_t max_count);
void Error_ClearLog(void);

#endif /* ERROR_HANDLER_H */
