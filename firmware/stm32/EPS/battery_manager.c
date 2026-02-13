/**
 * @file battery_manager.c
 * @brief Battery SOC tracking, charge/discharge protection
 */

#include "battery_manager.h"
#include <string.h>

static BatteryStatus_t batt_status;

void BatteryManager_Init(void) {
    memset(&batt_status, 0, sizeof(batt_status));
    batt_status.state = BATT_STATE_IDLE;
    batt_status.charge_enabled = true;
    batt_status.discharge_enabled = true;
    batt_status.soc_percent = 50.0f;
}

/**
 * @brief Estimate SOC from voltage using lookup table
 *
 * Simplified linear model for 18650 Li-ion cells
 */
static float estimate_soc(float pack_voltage) {
    float cell_v = pack_voltage / (float)BATT_CELLS;

    if (cell_v >= 4.20f) return 100.0f;
    if (cell_v >= 4.10f) return 90.0f + (cell_v - 4.10f) / 0.10f * 10.0f;
    if (cell_v >= 3.90f) return 70.0f + (cell_v - 3.90f) / 0.20f * 20.0f;
    if (cell_v >= 3.70f) return 40.0f + (cell_v - 3.70f) / 0.20f * 30.0f;
    if (cell_v >= 3.50f) return 20.0f + (cell_v - 3.50f) / 0.20f * 20.0f;
    if (cell_v >= 3.30f) return 5.0f + (cell_v - 3.30f) / 0.20f * 15.0f;
    if (cell_v >= 3.00f) return (cell_v - 3.00f) / 0.30f * 5.0f;
    return 0.0f;
}

void BatteryManager_Update(float voltage, float current, float temperature) {
    batt_status.voltage = voltage;
    batt_status.current = current;
    batt_status.temperature = temperature;
    batt_status.soc_percent = estimate_soc(voltage);

    /* Energy estimation (simplified) */
    batt_status.energy_wh = batt_status.soc_percent / 100.0f * 30.0f;

    /* Overcharge protection */
    if (voltage >= BATT_CHARGE_CUTOFF_V) {
        batt_status.charge_enabled = false;
        batt_status.state = BATT_STATE_FULL;
    } else {
        batt_status.charge_enabled = true;
    }

    /* Over-discharge protection */
    if (voltage <= BATT_DISCHARGE_CUTOFF_V) {
        batt_status.discharge_enabled = false;
        batt_status.state = BATT_STATE_CRITICAL;
    } else {
        batt_status.discharge_enabled = true;
    }

    /* Temperature protection */
    if (temperature > BATT_TEMP_MAX_C || temperature < BATT_TEMP_MIN_C) {
        batt_status.charge_enabled = false;
        batt_status.state = BATT_STATE_FAULT;
    }

    /* Update state */
    if (batt_status.state != BATT_STATE_FAULT &&
        batt_status.state != BATT_STATE_CRITICAL &&
        batt_status.state != BATT_STATE_FULL) {

        if (current > 0.05f) {
            batt_status.state = BATT_STATE_CHARGING;
        } else if (current < -0.05f) {
            batt_status.state = BATT_STATE_DISCHARGING;
        } else {
            batt_status.state = BATT_STATE_IDLE;
        }

        if (batt_status.soc_percent < 20.0f) {
            batt_status.state = BATT_STATE_LOW;
        }
    }
}

BatteryStatus_t BatteryManager_GetStatus(void) {
    return batt_status;
}

bool BatteryManager_IsChargeAllowed(void) {
    return batt_status.charge_enabled;
}

bool BatteryManager_IsDischargeAllowed(void) {
    return batt_status.discharge_enabled;
}

float BatteryManager_GetSOC(void) {
    return batt_status.soc_percent;
}
