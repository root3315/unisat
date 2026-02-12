/**
 * @file eps.c
 * @brief Electrical Power System implementation
 */

#include "eps.h"
#include "error_handler.h"
#include "config.h"
#include <string.h>

#ifndef SIMULATION_MODE
#include "stm32f4xx_hal.h"
extern ADC_HandleTypeDef hadc1;
#endif

static EPS_Status_t eps_status;

/* Power consumption estimates per subsystem (watts) */
static const float subsys_power_w[POWER_SUBSYS_COUNT] = {
    0.5f,   /* OBC */
    1.5f,   /* COMM */
    0.8f,   /* ADCS */
    0.3f,   /* GNSS */
    2.0f,   /* Camera */
    0.5f,   /* Payload */
    1.0f    /* Heater */
};

void EPS_Init(void) {
    memset(&eps_status, 0, sizeof(eps_status));

    /* Enable essential subsystems by default */
    eps_status.subsystem_enabled[POWER_SUBSYS_OBC] = true;
    eps_status.subsystem_enabled[POWER_SUBSYS_COMM] = true;

    if (config.adcs.enabled)
        eps_status.subsystem_enabled[POWER_SUBSYS_ADCS] = true;
    if (config.gnss.enabled)
        eps_status.subsystem_enabled[POWER_SUBSYS_GNSS] = true;
    if (config.camera.enabled)
        eps_status.subsystem_enabled[POWER_SUBSYS_CAMERA] = true;
    if (config.payload.enabled)
        eps_status.subsystem_enabled[POWER_SUBSYS_PAYLOAD] = true;
}

static float read_adc_voltage(uint8_t channel) {
#ifndef SIMULATION_MODE
    ADC_ChannelConfTypeDef sConfig = {0};
    sConfig.Channel = channel;
    sConfig.Rank = 1;
    sConfig.SamplingTime = ADC_SAMPLETIME_84CYCLES;

    HAL_ADC_ConfigChannel(&hadc1, &sConfig);
    HAL_ADC_Start(&hadc1);

    if (HAL_ADC_PollForConversion(&hadc1, IO_TIMEOUT_MS) == HAL_OK) {
        uint32_t raw = HAL_ADC_GetValue(&hadc1);
        HAL_ADC_Stop(&hadc1);
        return (float)raw * 3.3f / 4096.0f;
    }
    HAL_ADC_Stop(&hadc1);
    return 0.0f;
#else
    (void)channel;
    return 3.7f;
#endif
}

float EPS_ReadBatteryVoltage(void) {
    /* Voltage divider: 10k/10k, so actual = ADC * 2 */
    float adc_v = read_adc_voltage(0);
    eps_status.battery_voltage = adc_v * 2.0f;
    return eps_status.battery_voltage;
}

float EPS_ReadBatteryCurrent(void) {
    /* INA219 or shunt resistor: 0.1 ohm, gain = 50 */
    float adc_v = read_adc_voltage(1);
    eps_status.battery_current = adc_v / (0.1f * 50.0f);
    return eps_status.battery_current;
}

float EPS_ReadSolarVoltage(void) {
    float adc_v = read_adc_voltage(2);
    eps_status.solar_voltage = adc_v * 3.0f; /* Divider ratio 3:1 */
    return eps_status.solar_voltage;
}

float EPS_ReadSolarCurrent(void) {
    float adc_v = read_adc_voltage(3);
    eps_status.solar_current = adc_v / (0.1f * 50.0f);
    return eps_status.solar_current;
}

float EPS_GetBatterySOC(void) {
    float voltage = eps_status.battery_voltage;
    float cell_v = voltage / (float)EPS_BATTERY_CELLS;

    /* Simple linear SOC estimation for Li-ion */
    float soc;
    if (cell_v >= 4.2f) soc = 100.0f;
    else if (cell_v <= 3.0f) soc = 0.0f;
    else soc = (cell_v - 3.0f) / (4.2f - 3.0f) * 100.0f;

    eps_status.battery_soc = soc;
    return soc;
}

EPS_Status_t EPS_GetStatus(void) {
    EPS_ReadBatteryVoltage();
    EPS_ReadBatteryCurrent();
    EPS_ReadSolarVoltage();
    EPS_ReadSolarCurrent();
    EPS_GetBatterySOC();

    eps_status.solar_power = eps_status.solar_voltage *
                              eps_status.solar_current;

    /* Calculate total consumption */
    eps_status.total_consumption = 0.0f;
    for (uint8_t i = 0; i < POWER_SUBSYS_COUNT; i++) {
        if (eps_status.subsystem_enabled[i]) {
            eps_status.total_consumption += subsys_power_w[i];
        }
    }

    eps_status.bus_voltage = eps_status.battery_voltage;
    return eps_status;
}

void EPS_EnableSubsystem(PowerSubsystem_t subsys) {
    if (subsys >= POWER_SUBSYS_COUNT) return;
    eps_status.subsystem_enabled[subsys] = true;

#ifndef SIMULATION_MODE
    /* Toggle GPIO to enable power rail */
#endif
}

void EPS_DisableSubsystem(PowerSubsystem_t subsys) {
    if (subsys >= POWER_SUBSYS_COUNT) return;
    /* Never disable OBC */
    if (subsys == POWER_SUBSYS_OBC) return;
    eps_status.subsystem_enabled[subsys] = false;

#ifndef SIMULATION_MODE
    /* Toggle GPIO to disable power rail */
#endif
}

bool EPS_IsSubsystemEnabled(PowerSubsystem_t subsys) {
    if (subsys >= POWER_SUBSYS_COUNT) return false;
    return eps_status.subsystem_enabled[subsys];
}

void EPS_EmergencyShutdown(void) {
    for (uint8_t i = 1; i < POWER_SUBSYS_COUNT; i++) {
        if (i != POWER_SUBSYS_COMM) {
            EPS_DisableSubsystem((PowerSubsystem_t)i);
        }
    }
    Error_Log(ERR_CRITICAL_BATTERY, ERROR_CRITICAL, "Emergency shutdown");
}

void EPS_Update(void) {
    float soc = EPS_GetBatterySOC();

    if (soc < EPS_CRITICAL_THRESH) {
        Error_Handler(ERR_CRITICAL_BATTERY);
    } else if (soc < EPS_LOW_BATTERY_THRESH) {
        Error_Handler(ERR_LOW_BATTERY);
    }
}
