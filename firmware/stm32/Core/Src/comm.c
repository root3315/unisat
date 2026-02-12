/**
 * @file comm.c
 * @brief Communication subsystem (UHF/S-band) implementation
 */

#include "comm.h"
#include "ccsds.h"
#include "config.h"
#include <string.h>

#ifndef SIMULATION_MODE
#include "stm32f4xx_hal.h"
extern UART_HandleTypeDef huart1;
extern UART_HandleTypeDef huart2;
#endif

static COMM_Status_t comm_status;
static uint8_t uhf_rx_buffer[COMM_RX_BUFFER_SIZE];
static uint8_t uhf_tx_buffer[COMM_TX_BUFFER_SIZE];
static volatile uint16_t uhf_rx_head = 0;
static volatile uint16_t uhf_rx_tail = 0;

void COMM_Init(void) {
    memset(&comm_status, 0, sizeof(comm_status));
    uhf_rx_head = 0;
    uhf_rx_tail = 0;

#ifndef SIMULATION_MODE
    if (config.comm.uhf_enabled) {
        HAL_UART_Receive_IT(&huart1, &uhf_rx_buffer[0], 1);
    }
#endif
}

COMM_Status_t COMM_GetStatus(void) {
    return comm_status;
}

bool COMM_Send(CommChannel_t channel, const uint8_t *data, uint16_t length) {
    if (length == 0 || length > COMM_TX_BUFFER_SIZE) return false;

#ifndef SIMULATION_MODE
    UART_HandleTypeDef *uart;

    if (channel == COMM_CHANNEL_UHF && config.comm.uhf_enabled) {
        uart = &huart1;
    } else if (channel == COMM_CHANNEL_SBAND && config.comm.sband_enabled) {
        uart = &huart2;
    } else {
        return false;
    }

    memcpy(uhf_tx_buffer, data, length);

    for (uint8_t retry = 0; retry < IO_MAX_RETRIES; retry++) {
        HAL_StatusTypeDef status = HAL_UART_Transmit(uart, uhf_tx_buffer,
                                                      length, IO_TIMEOUT_MS);
        if (status == HAL_OK) {
            comm_status.packets_sent++;
            comm_status.last_tx_timestamp = HAL_GetTick();
            return true;
        }
        HAL_Delay(IO_RETRY_DELAY_MS);
    }

    comm_status.errors++;
    return false;
#else
    (void)channel;
    (void)data;
    comm_status.packets_sent++;
    return true;
#endif
}

uint16_t COMM_Receive(CommChannel_t channel, uint8_t *buffer,
                       uint16_t max_length) {
    (void)channel;

    uint16_t count = 0;
    while (uhf_rx_tail != uhf_rx_head && count < max_length) {
        buffer[count++] = uhf_rx_buffer[uhf_rx_tail];
        uhf_rx_tail = (uhf_rx_tail + 1) % COMM_RX_BUFFER_SIZE;
    }

    if (count > 0) {
        comm_status.packets_received++;
#ifndef SIMULATION_MODE
        comm_status.last_rx_timestamp = HAL_GetTick();
#endif
    }

    return count;
}

bool COMM_SendBeacon(void) {
    uint8_t buffer[CCSDS_MAX_PACKET_SIZE];
    uint16_t len = 0;

    /* Build beacon packet via telemetry module */
    extern uint16_t Telemetry_PackBeacon(uint8_t *buf, uint16_t max);
    len = Telemetry_PackBeacon(buffer, sizeof(buffer));

    if (len > 0) {
        return COMM_Send(COMM_CHANNEL_UHF, buffer, len);
    }
    return false;
}

int8_t COMM_GetRSSI(CommChannel_t channel) {
    (void)channel;
    return comm_status.rssi;
}

bool COMM_IsConnected(CommChannel_t channel) {
    uint32_t timeout = 60000; /* 60 seconds */
#ifndef SIMULATION_MODE
    uint32_t now = HAL_GetTick();
#else
    uint32_t now = 0;
#endif

    if (channel == COMM_CHANNEL_UHF) {
        return (now - comm_status.last_rx_timestamp) < timeout;
    }
    return false;
}

void COMM_UART_RxCallback(CommChannel_t channel, uint8_t byte) {
    (void)channel;
    uint16_t next = (uhf_rx_head + 1) % COMM_RX_BUFFER_SIZE;
    if (next != uhf_rx_tail) {
        uhf_rx_buffer[uhf_rx_head] = byte;
        uhf_rx_head = next;
    }
}

void COMM_ProcessRxBuffer(void) {
    /* Placeholder for AX.25 frame parsing */
}
