/**
 * @file obc.h
 * @brief On-Board Computer (OBC) management interface
 */

#ifndef OBC_H
#define OBC_H

#include <stdint.h>
#include <stdbool.h>

/** OBC status structure */
typedef struct {
    uint32_t uptime_seconds;
    uint32_t reset_count;
    float cpu_temperature;
    uint32_t free_heap;
    uint8_t current_state;
    uint16_t error_count;
} OBC_Status_t;

/** Initialize OBC subsystem */
void OBC_Init(void);

/** Get current OBC status */
OBC_Status_t OBC_GetStatus(void);

/** Increment uptime counter (call from 1s timer) */
void OBC_UpdateUptime(void);

/** Read MCU internal temperature sensor */
float OBC_ReadCpuTemperature(void);

/** Get available heap memory in bytes */
uint32_t OBC_GetFreeHeap(void);

/** Get total reset count from backup register */
uint32_t OBC_GetResetCount(void);

/** Perform software reset */
void OBC_SoftwareReset(void);

/** Enter low power mode */
void OBC_EnterLowPower(void);

/** Store data to backup SRAM */
void OBC_BackupWrite(uint32_t address, uint32_t data);

/** Read data from backup SRAM */
uint32_t OBC_BackupRead(uint32_t address);

#endif /* OBC_H */
