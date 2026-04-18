/**
 * @file comm.c
 * @brief Communication subsystem (UHF/S-band) implementation.
 *
 * AX.25 link-layer framing is delegated to the streaming decoder
 * (firmware/stm32/Drivers/AX25). comm.c is a thin byte pump between
 * the UART ring buffer and that decoder — see spec §4.10 for the
 * threading model and the dependency inversion.
 */

#include "comm.h"
#include "ccsds.h"
#include "config.h"
#include "ax25_api.h"
#include <string.h>

#ifndef SIMULATION_MODE
#include "stm32f4xx_hal.h"
#include "cmsis_os2.h"
extern UART_HandleTypeDef huart1;
extern UART_HandleTypeDef huart2;
#endif

static COMM_Status_t comm_status;
static uint8_t uhf_rx_buffer[COMM_RX_BUFFER_SIZE];
/* TX ring buffer — used by the target-build `COMM_Send` DMA path
 * (wired in the non-SIM branch). On host it's present but unused;
 * the attribute silences -Wunused-variable without wrapping the
 * declaration in #ifndef, keeping the host/target layouts identical. */
__attribute__((unused)) static uint8_t uhf_tx_buffer[COMM_TX_BUFFER_SIZE];
static volatile uint16_t uhf_rx_head = 0;
static volatile uint16_t uhf_rx_tail = 0;

/* One AX.25 decoder instance per RX channel. Owned by this file;
 * only comm_rx_task (or host tests) calls into it. */
static AX25_Decoder_t g_uhf_decoder;

/* Weak sink for decoded info payloads. The real implementation lives
 * in a future CCSDS dispatcher (Track 1b); until then the symbol
 * resolves here and simply discards the payload. Test harnesses and
 * other translation units may override by providing a strong symbol. */
__attribute__((weak))
void CCSDS_Dispatcher_Submit(const uint8_t *data, uint16_t n) {
    (void)data; (void)n;
}

void COMM_Init(void) {
    memset(&comm_status, 0, sizeof(comm_status));
    uhf_rx_head = 0;
    uhf_rx_tail = 0;
    AX25_DecoderInit(&g_uhf_decoder);

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
        uhf_rx_tail = (uint16_t)((uhf_rx_tail + 1U) % COMM_RX_BUFFER_SIZE);
    }

    if (count > 0) {
        comm_status.packets_received++;
#ifndef SIMULATION_MODE
        comm_status.last_rx_timestamp = HAL_GetTick();
#endif
    }

    return count;
}

bool COMM_SendAX25(CommChannel_t channel,
                    const char *dst_call, uint8_t dst_ssid,
                    const char *src_call, uint8_t src_ssid,
                    const uint8_t *info, uint16_t info_len) {
    AX25_Address_t dst = { .ssid = dst_ssid };
    AX25_Address_t src = { .ssid = src_ssid };

    /* Copy up to 6 callsign chars or stop at NUL. cppcheck's
     * arrayIndexOutOfBounds checker cannot track that the `!= '\0'`
     * short-circuit bounds `n` to the string's actual length —
     * callers pass NUL-terminated literals like "CQ" (3 bytes)
     * where the loop exits at n=2 before touching dst_call[3..5].
     * Suppress the false positive inline so the surrounding real
     * warnings stay visible. */
    size_t n;
    /* cppcheck-suppress arrayIndexOutOfBoundsCond */
    /* cppcheck-suppress arrayIndexOutOfBounds */
    for (n = 0; n < 6 && dst_call[n] != '\0'; n++) { dst.callsign[n] = dst_call[n]; }
    dst.callsign[n] = '\0';
    /* cppcheck-suppress arrayIndexOutOfBoundsCond */
    /* cppcheck-suppress arrayIndexOutOfBounds */
    for (n = 0; n < 6 && src_call[n] != '\0'; n++) { src.callsign[n] = src_call[n]; }
    src.callsign[n] = '\0';

    uint8_t buf[AX25_MAX_FRAME_BYTES];
    uint16_t frame_len = 0;
    if (!AX25_EncodeUiFrame(&dst, &src, 0xF0, info, info_len,
                             buf, sizeof(buf), &frame_len)) {
        comm_status.errors++;
        return false;
    }
    return COMM_Send(channel, buf, frame_len);
}

bool COMM_SendBeacon(void) {
    /* Spec §7.2: beacon is a 48-byte flat layout carried as the info
     * field of a CCSDS Space Packet, which is carried as the info
     * field of an AX.25 UI frame. Full layered TX path:
     *   48 B raw  -> Telemetry_PackBeacon
     *   +CCSDS    -> CCSDS_BuildPacket + CCSDS_Serialize
     *   +AX.25    -> COMM_SendAX25 */
    extern uint16_t Telemetry_PackBeacon(uint8_t *buf, uint16_t max);
    uint8_t raw[48];
    if (Telemetry_PackBeacon(raw, sizeof(raw)) != 48) {
        comm_status.errors++;
        return false;
    }

    CCSDS_Packet_t packet;
    CCSDS_BuildPacket(&packet, APID_BEACON, CCSDS_TELEMETRY, 0,
                      raw, sizeof(raw));

    uint8_t ccsds_buf[CCSDS_MAX_PACKET_SIZE];
    uint16_t ccsds_len = CCSDS_Serialize(&packet, ccsds_buf,
                                          sizeof(ccsds_buf));
    if (ccsds_len == 0) {
        comm_status.errors++;
        return false;
    }

    return COMM_SendAX25(COMM_CHANNEL_UHF, "CQ", 0, "UN8SAT", 1,
                         ccsds_buf, ccsds_len);
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
    uint16_t next = (uint16_t)((uhf_rx_head + 1U) % COMM_RX_BUFFER_SIZE);
    if (next != uhf_rx_tail) {
        uhf_rx_buffer[uhf_rx_head] = byte;
        uhf_rx_head = next;
    }
}

void COMM_ProcessRxBuffer(void) {
    /* Drain the ring buffer one byte at a time through the AX.25
     * streaming decoder. On a completed frame the info payload is
     * forwarded to the CCSDS dispatcher. Counters mirrored into
     * COMM_Status_t so existing telemetry sees link-layer health. */
    while (uhf_rx_tail != uhf_rx_head) {
        uint8_t byte = uhf_rx_buffer[uhf_rx_tail];
        uhf_rx_tail = (uint16_t)((uhf_rx_tail + 1U) % COMM_RX_BUFFER_SIZE);

        AX25_UiFrame_t frame;
        bool ready = false;
        AX25_DecoderPushByte(&g_uhf_decoder, byte, &frame, &ready);

        if (ready) {
            CCSDS_Dispatcher_Submit(frame.info, frame.info_len);
        }
    }

    /* Mirror decoder stats into COMM_Status_t. */
    comm_status.ax25_frames_ok       = g_uhf_decoder.frames_ok;
    comm_status.ax25_fcs_errors      = g_uhf_decoder.frames_fcs_err;
    comm_status.ax25_frame_errors    = g_uhf_decoder.frames_other_err
                                      + g_uhf_decoder.frames_stuffing_err;
    comm_status.ax25_overflow_errors = g_uhf_decoder.frames_overflow;
}

#ifndef SIMULATION_MODE

static void CommRxTask(void *arg) {
    (void)arg;
    for (;;) {
        COMM_ProcessRxBuffer();
        osDelay(10);  /* 10 ms period per spec §4.10 */
    }
}

void COMM_StartTask(void) {
    const osThreadAttr_t attr = {
        .name = "comm_rx",
        .stack_size = AX25_DECODER_TASK_STACK,
        .priority = osPriorityAboveNormal,
    };
    osThreadNew(CommRxTask, NULL, &attr);
}

#else

void COMM_StartTask(void) { /* no-op under SITL */ }

#endif  /* !SIMULATION_MODE */
