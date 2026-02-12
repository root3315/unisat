/**
 * @file main.c
 * @brief UniSat main firmware entry point
 *
 * Initializes all peripherals and creates FreeRTOS tasks
 * for each satellite subsystem.
 */

#include "main.h"
#include "config.h"

#ifndef SIMULATION_MODE
#include "cmsis_os2.h"
#include "stm32f4xx_hal.h"
#endif

/** Global system state */
static volatile SystemState_t system_state = SYSTEM_STATE_STARTUP;

/** Message queues */
#ifndef SIMULATION_MODE
static osMessageQueueId_t telemetryQueue;
static osMessageQueueId_t commandQueue;
static osMessageQueueId_t adcsQueue;
#endif

SystemConfig_t config;

void Config_Init(void) {
    config.obc.enabled = OBC_ENABLED;
    config.eps.enabled = EPS_ENABLED;
    config.eps.solar_panels = EPS_SOLAR_PANELS;
    config.eps.panel_efficiency = EPS_PANEL_EFFICIENCY;
    config.eps.battery_capacity_wh = EPS_BATTERY_CAPACITY_WH;
    config.eps.bus_voltage = EPS_BUS_VOLTAGE;
    config.comm.enabled = COMM_ENABLED;
    config.comm.uhf_enabled = COMM_UHF_ENABLED;
    config.comm.sband_enabled = COMM_SBAND_ENABLED;
    config.adcs.enabled = ADCS_ENABLED;
    config.adcs.magnetorquers = ADCS_MAGNETORQUERS;
    config.adcs.reaction_wheels = ADCS_REACTION_WHEELS;
    config.adcs.sun_sensors = ADCS_SUN_SENSORS;
    config.gnss.enabled = GNSS_ENABLED;
    config.camera.enabled = CAMERA_ENABLED;
    config.payload.enabled = PAYLOAD_ENABLED;
}

#ifndef SIMULATION_MODE

/**
 * @brief Application entry point
 */
int main(void) {
    HAL_Init();
    SystemClock_Config();

    /* Initialize peripherals */
    MX_GPIO_Init();
    MX_I2C1_Init();
    MX_SPI1_Init();
    MX_USART1_UART_Init();
    MX_USART2_UART_Init();
    MX_ADC1_Init();
    MX_TIM2_Init();

    /* Load configuration */
    Config_Init();

    /* Initialize subsystems */
    OBC_Init();
    if (config.eps.enabled) EPS_Init();
    if (config.comm.enabled) COMM_Init();
    if (config.adcs.enabled) ADCS_Init();
    if (config.gnss.enabled) GNSS_Init();
    Sensors_Init();
    CCSDS_Init();
    Telemetry_Init();
    Watchdog_Init();
    Error_Init();

    if (config.payload.enabled) {
        Payload_Init(PAYLOAD_RADIATION_MONITOR);
    }

    /* Create message queues */
    telemetryQueue = osMessageQueueNew(TELEMETRY_QUEUE_SIZE,
                                        sizeof(SensorData_t), NULL);
    commandQueue = osMessageQueueNew(COMMAND_QUEUE_SIZE,
                                      sizeof(uint8_t) * 64, NULL);
    adcsQueue = osMessageQueueNew(ADCS_QUEUE_SIZE,
                                   sizeof(SensorData_t), NULL);

    /* Create FreeRTOS tasks */
    const osThreadAttr_t sensor_attr = {
        .name = "SensorTask",
        .stack_size = SENSOR_TASK_STACK_SIZE * 4,
        .priority = (osPriority_t)SENSOR_TASK_PRIORITY
    };
    osThreadNew(SensorTask, NULL, &sensor_attr);

    const osThreadAttr_t telemetry_attr = {
        .name = "TelemetryTask",
        .stack_size = TELEMETRY_TASK_STACK_SIZE * 4,
        .priority = (osPriority_t)TELEMETRY_TASK_PRIORITY
    };
    osThreadNew(TelemetryTask, NULL, &telemetry_attr);

    const osThreadAttr_t comm_attr = {
        .name = "CommTask",
        .stack_size = COMM_TASK_STACK_SIZE * 4,
        .priority = (osPriority_t)COMM_TASK_PRIORITY
    };
    osThreadNew(CommTask, NULL, &comm_attr);

    const osThreadAttr_t adcs_attr = {
        .name = "ADCSTask",
        .stack_size = ADCS_TASK_STACK_SIZE * 4,
        .priority = (osPriority_t)ADCS_TASK_PRIORITY
    };
    osThreadNew(ADCSTask, NULL, &adcs_attr);

    const osThreadAttr_t watchdog_attr = {
        .name = "WatchdogTask",
        .stack_size = WATCHDOG_TASK_STACK_SIZE * 4,
        .priority = (osPriority_t)WATCHDOG_TASK_PRIORITY
    };
    osThreadNew(WatchdogTask, NULL, &watchdog_attr);

    const osThreadAttr_t payload_attr = {
        .name = "PayloadTask",
        .stack_size = PAYLOAD_TASK_STACK_SIZE * 4,
        .priority = (osPriority_t)PAYLOAD_TASK_PRIORITY
    };
    osThreadNew(PayloadTask, NULL, &payload_attr);

    system_state = SYSTEM_STATE_NOMINAL;

    /* Start FreeRTOS scheduler */
    osKernelStart();

    /* Should never reach here */
    while (1) {}
}

void SensorTask(void *argument) {
    (void)argument;
    SensorData_t data;
    uint32_t last_wake = HAL_GetTick();

    while (1) {
        memset(&data, 0, sizeof(data));
        data.timestamp = HAL_GetTick();

        if (config.adcs.enabled) {
            Sensors_ReadMagnetometer(&data.mag_x, &data.mag_y, &data.mag_z);
            Sensors_ReadIMU(&data.gyro_x, &data.gyro_y, &data.gyro_z,
                           &data.accel_x, &data.accel_y, &data.accel_z);
            Sensors_ReadSunSensors(data.sun_sensor);
        }

        Sensors_ReadEnvironment(&data.temperature, &data.pressure,
                                &data.humidity);
        Sensors_ReadPrecisionTemp(&data.temp_precise);

        if (config.payload.enabled) {
            Sensors_ReadRadiation(&data.radiation_cps);
        }

        data.battery_voltage = EPS_ReadBatteryVoltage();
        data.battery_current = EPS_ReadBatteryCurrent();
        data.solar_voltage = EPS_ReadSolarVoltage();

        if (config.gnss.enabled) {
            GNSS_GetPosition(&data.lat, &data.lon, &data.alt, &data.fix_type);
            GNSS_GetVelocity(&data.vel_x, &data.vel_y, &data.vel_z);
        }

        osMessageQueuePut(telemetryQueue, &data, 0, 100);
        osMessageQueuePut(adcsQueue, &data, 0, 0);

        Watchdog_Feed(TASK_SENSOR);

        uint32_t elapsed = HAL_GetTick() - last_wake;
        if (elapsed < TELEMETRY_PERIOD_MS) {
            osDelay(TELEMETRY_PERIOD_MS - elapsed);
        }
        last_wake = HAL_GetTick();
    }
}

void TelemetryTask(void *argument) {
    (void)argument;
    SensorData_t data;

    while (1) {
        if (osMessageQueueGet(telemetryQueue, &data, NULL, 2000) == osOK) {
            Telemetry_SendAllHousekeeping();
        }
        Watchdog_Feed(TASK_TELEMETRY);
    }
}

void CommTask(void *argument) {
    (void)argument;
    uint8_t rx_buffer[COMM_MAX_PACKET_SIZE];
    uint32_t beacon_timer = HAL_GetTick();

    while (1) {
        /* Check for incoming data */
        uint16_t rx_len = COMM_Receive(COMM_CHANNEL_UHF, rx_buffer,
                                        COMM_MAX_PACKET_SIZE);
        if (rx_len > 0) {
            CCSDS_Packet_t packet;
            if (CCSDS_Parse(rx_buffer, rx_len, &packet)) {
                /* Process telecommand */
                osMessageQueuePut(commandQueue, packet.data, 0, 100);
            }
        }

        /* Send beacon periodically */
        if (HAL_GetTick() - beacon_timer >= BEACON_PERIOD_MS) {
            COMM_SendBeacon();
            beacon_timer = HAL_GetTick();
        }

        Watchdog_Feed(TASK_COMM);
        osDelay(100);
    }
}

void ADCSTask(void *argument) {
    (void)argument;
    SensorData_t data;

    while (1) {
        if (osMessageQueueGet(adcsQueue, &data, NULL, 2000) == osOK) {
            float mag[3] = {data.mag_x, data.mag_y, data.mag_z};
            float gyro[3] = {data.gyro_x, data.gyro_y, data.gyro_z};
            float accel[3] = {data.accel_x, data.accel_y, data.accel_z};

            ADCS_Update(mag, gyro, accel, data.sun_sensor);
        }
        Watchdog_Feed(TASK_ADCS);
    }
}

void WatchdogTask(void *argument) {
    (void)argument;

    while (1) {
        Watchdog_CheckAll();
        Watchdog_FeedHardware();
        OBC_UpdateUptime();
        EPS_Update();
        osDelay(WATCHDOG_FEED_PERIOD_MS);
    }
}

void PayloadTask(void *argument) {
    (void)argument;

    while (1) {
        if (config.payload.enabled) {
            Payload_Update();
        }
        Watchdog_Feed(TASK_PAYLOAD);
        osDelay(5000);
    }
}

#endif /* SIMULATION_MODE */
