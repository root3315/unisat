/**
 * @file battery_manager.h
 * @brief Battery monitoring and protection
 */

#ifndef BATTERY_MANAGER_H
#define BATTERY_MANAGER_H

#include <stdint.h>
#include <stdbool.h>

#define BATT_CELLS              4
#define BATT_CELL_MAX_V         4.2f
#define BATT_CELL_MIN_V         3.0f
#define BATT_CELL_NOMINAL_V     3.7f
#define BATT_CHARGE_CUTOFF_V    (BATT_CELL_MAX_V * BATT_CELLS)
#define BATT_DISCHARGE_CUTOFF_V (BATT_CELL_MIN_V * BATT_CELLS)
#define BATT_TEMP_MAX_C         45.0f
#define BATT_TEMP_MIN_C         -10.0f

typedef enum {
    BATT_STATE_IDLE = 0,
    BATT_STATE_CHARGING,
    BATT_STATE_DISCHARGING,
    BATT_STATE_FULL,
    BATT_STATE_LOW,
    BATT_STATE_CRITICAL,
    BATT_STATE_FAULT
} BatteryState_t;

typedef struct {
    float voltage;
    float current;
    float temperature;
    float soc_percent;
    float energy_wh;
    uint32_t cycle_count;
    BatteryState_t state;
    bool charge_enabled;
    bool discharge_enabled;
} BatteryStatus_t;

void BatteryManager_Init(void);
void BatteryManager_Update(float voltage, float current, float temperature);
BatteryStatus_t BatteryManager_GetStatus(void);
bool BatteryManager_IsChargeAllowed(void);
bool BatteryManager_IsDischargeAllowed(void);
float BatteryManager_GetSOC(void);

#endif /* BATTERY_MANAGER_H */
