/**
 * @file main.h
 * @brief UniSat main application header
 * @version 1.0.0
 *
 * Main header file for the UniSat CubeSat firmware.
 * Defines system-wide types, includes, and FreeRTOS task prototypes.
 */

#ifndef MAIN_H
#define MAIN_H

#include <stdint.h>
#include <stdbool.h>
#include <string.h>

#include "config.h"
#include "obc.h"
#include "eps.h"
#include "comm.h"
#include "adcs.h"
#include "sensors.h"
#include "gnss.h"
#include "payload.h"
#include "telemetry.h"
#include "watchdog.h"
#include "error_handler.h"
#include "ccsds.h"

/** Firmware version */
#define FIRMWARE_VERSION_MAJOR  1
#define FIRMWARE_VERSION_MINOR  0
#define FIRMWARE_VERSION_PATCH  0

/** FreeRTOS task stack sizes (words) */
#define SENSOR_TASK_STACK_SIZE    512
#define TELEMETRY_TASK_STACK_SIZE 512
#define COMM_TASK_STACK_SIZE      1024
#define ADCS_TASK_STACK_SIZE      1024
#define WATCHDOG_TASK_STACK_SIZE  256
#define PAYLOAD_TASK_STACK_SIZE   512

/** FreeRTOS task priorities */
#define SENSOR_TASK_PRIORITY      3
#define TELEMETRY_TASK_PRIORITY   2
#define COMM_TASK_PRIORITY        4
#define ADCS_TASK_PRIORITY        3
#define WATCHDOG_TASK_PRIORITY    5
#define PAYLOAD_TASK_PRIORITY     1

/** Message queue sizes */
#define TELEMETRY_QUEUE_SIZE   16
#define COMMAND_QUEUE_SIZE     8
#define ADCS_QUEUE_SIZE        8

/** System states */
typedef enum {
    SYSTEM_STATE_STARTUP = 0,
    SYSTEM_STATE_NOMINAL,
    SYSTEM_STATE_SAFE_MODE,
    SYSTEM_STATE_LOW_POWER,
    SYSTEM_STATE_DEPLOYMENT,
    SYSTEM_STATE_DETUMBLING
} SystemState_t;

/** Sensor data aggregate */
typedef struct {
    uint32_t timestamp;
    float mag_x, mag_y, mag_z;
    float gyro_x, gyro_y, gyro_z;
    float accel_x, accel_y, accel_z;
    float temperature;
    float pressure;
    float humidity;
    float temp_precise;
    uint16_t sun_sensor[6];
    uint32_t radiation_cps;
    float battery_voltage;
    float battery_current;
    float solar_voltage;
    double lat, lon, alt;
    float vel_x, vel_y, vel_z;
    uint8_t fix_type;
} SensorData_t;

/** FreeRTOS task entry points */
void SensorTask(void *argument);
void TelemetryTask(void *argument);
void CommTask(void *argument);
void ADCSTask(void *argument);
void WatchdogTask(void *argument);
void PayloadTask(void *argument);

/** System initialization */
void SystemClock_Config(void);
void MX_GPIO_Init(void);
void MX_I2C1_Init(void);
void MX_SPI1_Init(void);
void MX_USART1_UART_Init(void);
void MX_USART2_UART_Init(void);
void MX_ADC1_Init(void);
void MX_TIM2_Init(void);

#endif /* MAIN_H */
