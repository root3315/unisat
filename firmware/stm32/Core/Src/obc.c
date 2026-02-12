/**
 * @file obc.c
 * @brief On-Board Computer management implementation
 */

#include "obc.h"
#include "config.h"

#ifndef SIMULATION_MODE
#include "stm32f4xx_hal.h"
#include "cmsis_os2.h"
#else
#include <time.h>
static uint32_t sim_tick = 0;
static uint32_t HAL_GetTick(void) { return sim_tick++; }
#endif

static OBC_Status_t obc_status;
static uint32_t boot_time;

void OBC_Init(void) {
    memset(&obc_status, 0, sizeof(obc_status));
    boot_time = HAL_GetTick();
    obc_status.reset_count = OBC_GetResetCount();
    obc_status.current_state = 0;
}

OBC_Status_t OBC_GetStatus(void) {
    obc_status.cpu_temperature = OBC_ReadCpuTemperature();
    obc_status.free_heap = OBC_GetFreeHeap();
    return obc_status;
}

void OBC_UpdateUptime(void) {
    obc_status.uptime_seconds = (HAL_GetTick() - boot_time) / 1000;
}

float OBC_ReadCpuTemperature(void) {
#ifndef SIMULATION_MODE
    ADC_ChannelConfTypeDef sConfig = {0};
    sConfig.Channel = ADC_CHANNEL_TEMPSENSOR;
    sConfig.Rank = 1;
    sConfig.SamplingTime = ADC_SAMPLETIME_480CYCLES;

    extern ADC_HandleTypeDef hadc1;
    HAL_ADC_ConfigChannel(&hadc1, &sConfig);
    HAL_ADC_Start(&hadc1);

    if (HAL_ADC_PollForConversion(&hadc1, 100) == HAL_OK) {
        uint32_t raw = HAL_ADC_GetValue(&hadc1);
        float voltage = (float)raw * 3.3f / 4096.0f;
        float temp = ((voltage - 0.76f) / 0.0025f) + 25.0f;
        HAL_ADC_Stop(&hadc1);
        return temp;
    }
    HAL_ADC_Stop(&hadc1);
    return -999.0f;
#else
    return 35.0f;
#endif
}

uint32_t OBC_GetFreeHeap(void) {
#ifndef SIMULATION_MODE
    extern uint32_t _estack;
    extern uint32_t _Min_Stack_Size;
    volatile uint32_t sp;
    __asm volatile("mov %0, sp" : "=r"(sp));
    return sp - (uint32_t)&_Min_Stack_Size;
#else
    return 65536;
#endif
}

uint32_t OBC_GetResetCount(void) {
#ifndef SIMULATION_MODE
    return OBC_BackupRead(0);
#else
    return 0;
#endif
}

void OBC_SoftwareReset(void) {
#ifndef SIMULATION_MODE
    uint32_t count = OBC_GetResetCount();
    OBC_BackupWrite(0, count + 1);
    NVIC_SystemReset();
#endif
}

void OBC_EnterLowPower(void) {
#ifndef SIMULATION_MODE
    HAL_SuspendTick();
    HAL_PWR_EnterSLEEPMode(PWR_MAINREGULATOR_ON, PWR_SLEEPENTRY_WFI);
    HAL_ResumeTick();
#endif
}

void OBC_BackupWrite(uint32_t address, uint32_t data) {
#ifndef SIMULATION_MODE
    HAL_PWR_EnableBkUpAccess();
    *(__IO uint32_t *)(BKPSRAM_BASE + address) = data;
    HAL_PWR_DisableBkUpAccess();
#else
    (void)address;
    (void)data;
#endif
}

uint32_t OBC_BackupRead(uint32_t address) {
#ifndef SIMULATION_MODE
    return *(__IO uint32_t *)(BKPSRAM_BASE + address);
#else
    (void)address;
    return 0;
#endif
}
