/**
 * @file config.h
 * @brief System configuration derived from mission_config.json
 * @version 1.0.0
 *
 * Auto-generated configuration header. Modify mission_config.json
 * and regenerate, or edit manually for custom builds.
 */

#ifndef CONFIG_H
#define CONFIG_H

#include <stdint.h>
#include <stdbool.h>

/* Mission Configuration */
#define MISSION_NAME            "UniSat-1"
#define MISSION_VERSION         "1.0.0"

/* MCU Configuration */
#define MCU_CLOCK_MHZ           180
#define MCU_RAM_KB              128
#define MCU_FLASH_KB            512

/* Subsystem Enable Flags */
#define OBC_ENABLED             true
#define EPS_ENABLED             true
#define COMM_ENABLED            true
#define ADCS_ENABLED            true
#define GNSS_ENABLED            true
#define CAMERA_ENABLED          true
#define PAYLOAD_ENABLED         true

/* EPS Configuration */
#define EPS_SOLAR_PANELS        6
#define EPS_PANEL_EFFICIENCY    0.295f
#define EPS_BATTERY_CAPACITY_WH 30.0f
#define EPS_BATTERY_CELLS       4
#define EPS_BUS_VOLTAGE         5.0f
#define EPS_LOW_BATTERY_THRESH  20.0f
#define EPS_CRITICAL_THRESH     10.0f

/* Communication Configuration */
#define COMM_UHF_ENABLED        true
#define COMM_UHF_FREQ_MHZ      437.0f
#define COMM_UHF_POWER_W       1.0f
#define COMM_UHF_BAUDRATE      9600
#define COMM_SBAND_ENABLED     true
#define COMM_SBAND_FREQ_MHZ    2400.0f
#define COMM_SBAND_POWER_W     2.0f
#define COMM_SBAND_RATE_KBPS   256

/* ADCS Configuration */
#define ADCS_MAGNETORQUERS      3
#define ADCS_REACTION_WHEELS    3
#define ADCS_SUN_SENSORS        6
#define ADCS_POINTING_ACC_DEG   1.0f

/* Watchdog Configuration */
#define WATCHDOG_TIMEOUT_MS     10000
#define WATCHDOG_FEED_PERIOD_MS 1000

/* Telemetry Configuration */
#define TELEMETRY_PERIOD_MS     1000
#define BEACON_PERIOD_MS        30000
#define MAX_TELEMETRY_PACKETS   256

/* I2C Addresses */
#define LIS3MDL_I2C_ADDR       0x1C
#define BME280_I2C_ADDR        0x76
#define TMP117_I2C_ADDR        0x48
#define UBLOX_I2C_ADDR         0x42

/* SPI Chip Select Pins */
#define MPU9250_CS_PIN          GPIO_PIN_4
#define MPU9250_CS_PORT         GPIOA
#define MCP3008_CS_PIN          GPIO_PIN_5
#define MCP3008_CS_PORT         GPIOA

/* UART Configuration */
#define UHF_UART                USART1
#define UHF_UART_BAUDRATE       9600
#define SBAND_UART              USART2
#define SBAND_UART_BAUDRATE     115200

/* I2C/SPI/UART Retry Configuration */
#define IO_MAX_RETRIES          3
#define IO_RETRY_DELAY_MS       10
/* 500 ms covers worst-case bit-stuffed AX.25 frame (~266 ms @ 9600 bps). */
#define IO_TIMEOUT_MS           500

/** Runtime configuration structure */
typedef struct {
    struct {
        bool enabled;
    } obc;
    struct {
        bool enabled;
        uint8_t solar_panels;
        float panel_efficiency;
        float battery_capacity_wh;
        float bus_voltage;
    } eps;
    struct {
        bool enabled;
        bool uhf_enabled;
        bool sband_enabled;
    } comm;
    struct {
        bool enabled;
        uint8_t magnetorquers;
        uint8_t reaction_wheels;
        uint8_t sun_sensors;
    } adcs;
    struct {
        bool enabled;
    } gnss;
    struct {
        bool enabled;
    } camera;
    struct {
        bool enabled;
    } payload;
} SystemConfig_t;

extern SystemConfig_t config;

void Config_Init(void);

/* AX.25 Link Layer Configuration (spec §5.1a).
 * All AX.25 hard limits surface as compile-time constants — no magic
 * numbers in library code. Tests may override via -D for boundary cases. */
#define ENABLE_AX25_FRAMING       true
#define AX25_MAX_INFO_LEN         256   /* AX.25 v2.2 info field hard max */
#define AX25_MAX_FRAME_BYTES      400   /* stuffed; 20% margin over +266 B */
#define AX25_RING_BUFFER_SIZE     512   /* 427 ms headroom @ 9600 bps     */
#define AX25_DECODER_TASK_STACK   1024  /* FreeRTOS stack, bytes          */

#endif /* CONFIG_H */
