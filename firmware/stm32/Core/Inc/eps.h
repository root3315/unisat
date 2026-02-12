/**
 * @file eps.h
 * @brief Electrical Power System interface
 */

#ifndef EPS_H
#define EPS_H

#include <stdint.h>
#include <stdbool.h>

/** Power subsystem identifiers */
typedef enum {
    POWER_SUBSYS_OBC = 0,
    POWER_SUBSYS_COMM,
    POWER_SUBSYS_ADCS,
    POWER_SUBSYS_GNSS,
    POWER_SUBSYS_CAMERA,
    POWER_SUBSYS_PAYLOAD,
    POWER_SUBSYS_HEATER,
    POWER_SUBSYS_COUNT
} PowerSubsystem_t;

/** EPS status structure */
typedef struct {
    float battery_voltage;
    float battery_current;
    float battery_soc;
    float solar_voltage;
    float solar_current;
    float solar_power;
    float bus_voltage;
    float total_consumption;
    bool subsystem_enabled[POWER_SUBSYS_COUNT];
} EPS_Status_t;

void EPS_Init(void);
EPS_Status_t EPS_GetStatus(void);
float EPS_ReadBatteryVoltage(void);
float EPS_ReadBatteryCurrent(void);
float EPS_ReadSolarVoltage(void);
float EPS_ReadSolarCurrent(void);
float EPS_GetBatterySOC(void);
void EPS_EnableSubsystem(PowerSubsystem_t subsys);
void EPS_DisableSubsystem(PowerSubsystem_t subsys);
bool EPS_IsSubsystemEnabled(PowerSubsystem_t subsys);
void EPS_EmergencyShutdown(void);
void EPS_Update(void);

#endif /* EPS_H */
