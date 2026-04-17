/**
 * @file ax25_decoder.h
 * @brief AX.25 streaming decoder — first-class stateful type.
 *
 * Consumed byte-by-byte from the FreeRTOS comm_rx_task (see spec §4.10).
 * MUST NOT be called from interrupt context.
 */
#ifndef AX25_DECODER_H
#define AX25_DECODER_H

#include "ax25_types.h"

void ax25_decoder_init(ax25_decoder_t *d);
void ax25_decoder_reset(ax25_decoder_t *d);

/**
 * Feed ONE byte (LSB-first on the wire).
 *
 * Return values:
 *   AX25_OK               — byte consumed; *frame_ready == true means
 *                           *out_frame holds a newly decoded valid frame.
 *                           *frame_ready == false means no frame yet.
 *   AX25_ERR_STUFFING_VIOLATION  — six consecutive 1s seen; decoder
 *                           is reset to HUNT, counter incremented.
 *   AX25_ERR_FRAME_TOO_LONG — frame exceeded AX25_MAX_FRAME_BYTES;
 *                           decoder is reset to HUNT.
 *
 * The offending byte is treated as consumed (REQ-AX25-024). Never
 * reprocessed. Safe to call at any rate up to the CPU clock.
 */
ax25_status_t ax25_decoder_push_byte(
    ax25_decoder_t *d,
    uint8_t byte,
    ax25_ui_frame_t *out_frame,
    bool *frame_ready);

#endif /* AX25_DECODER_H */
