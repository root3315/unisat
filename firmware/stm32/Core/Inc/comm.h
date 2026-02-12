/**
 * @file comm.h
 * @brief Communication subsystem interface (UHF/S-band)
 */

#ifndef COMM_H
#define COMM_H

#include <stdint.h>
#include <stdbool.h>

#define COMM_MAX_PACKET_SIZE    256
#define COMM_RX_BUFFER_SIZE     512
#define COMM_TX_BUFFER_SIZE     512

/** Communication channel */
typedef enum {
    COMM_CHANNEL_UHF = 0,
    COMM_CHANNEL_SBAND
} CommChannel_t;

/** Communication status */
typedef struct {
    bool uhf_connected;
    bool sband_connected;
    uint32_t packets_sent;
    uint32_t packets_received;
    uint32_t errors;
    int8_t rssi;
    uint32_t last_rx_timestamp;
    uint32_t last_tx_timestamp;
} COMM_Status_t;

void COMM_Init(void);
COMM_Status_t COMM_GetStatus(void);
bool COMM_Send(CommChannel_t channel, const uint8_t *data, uint16_t length);
uint16_t COMM_Receive(CommChannel_t channel, uint8_t *buffer, uint16_t max_length);
bool COMM_SendBeacon(void);
void COMM_SetChannel(CommChannel_t channel);
int8_t COMM_GetRSSI(CommChannel_t channel);
bool COMM_IsConnected(CommChannel_t channel);
void COMM_ProcessRxBuffer(void);
void COMM_UART_RxCallback(CommChannel_t channel, uint8_t byte);

#endif /* COMM_H */
