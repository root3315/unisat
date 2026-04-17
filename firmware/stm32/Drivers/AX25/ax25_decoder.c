/**
 * @file ax25_decoder.c
 * @brief AX.25 streaming decoder implementation.
 *
 * Bit-level state machine per spec §5.1, REQ-AX25-017..024.
 */

#include "ax25_decoder.h"
#include "ax25.h"
#include <string.h>

void ax25_decoder_init(ax25_decoder_t *d) {
  if (d == NULL) return;
  memset(d, 0, sizeof(*d));
  d->state = AX25_STATE_HUNT;
}

void ax25_decoder_reset(ax25_decoder_t *d) {
  /* Preserve counters; reset only the per-frame state. */
  if (d == NULL) return;
  d->len = 0;
  d->shift_reg = 0;
  d->bit_count = 0;
  d->ones_run = 0;
  d->state = AX25_STATE_HUNT;
}

/* Push one de-stuffed bit into the assembly buffer (LSB-first packing).
 * Returns 1 on success, 0 on overflow (with frames_overflow already
 * incremented and decoder reset). */
static int append_bit(ax25_decoder_t *d, int bit) {
  d->shift_reg |= (uint16_t)(bit & 1) << d->bit_count;
  d->bit_count++;
  if (d->bit_count == 8) {
    if (d->len >= AX25_MAX_FRAME_BYTES) {
      d->frames_overflow++;
      ax25_decoder_reset(d);
      return 0;
    }
    d->buf[d->len++] = (uint8_t)(d->shift_reg & 0xFF);
    d->shift_reg = 0;
    d->bit_count = 0;
  }
  return 1;
}

static void emit_frame_if_valid(ax25_decoder_t *d,
                                 ax25_ui_frame_t *out, bool *ready) {
  /* Discard any trailing partial byte. */
  d->shift_reg = 0;
  d->bit_count = 0;

  /* REQ-AX25-023: empty payload between flags is an idle pattern —
   * ignore silently. */
  if (d->len < 18) {
    ax25_decoder_reset(d);
    return;
  }

  ax25_status_t st = ax25_decode_ui_frame(d->buf, d->len, out);
  if (st == AX25_OK) {
    d->frames_ok++;
    if (ready) *ready = true;
  } else if (st == AX25_ERR_FCS_MISMATCH) {
    d->frames_fcs_err++;
  } else {
    d->frames_other_err++;
  }
  /* Always reset per-frame state; keep counters. */
  d->len = 0;
}

ax25_status_t ax25_decoder_push_byte(ax25_decoder_t *d, uint8_t byte,
                                      ax25_ui_frame_t *out_frame,
                                      bool *frame_ready) {
  if (d == NULL) return AX25_ERR_BUFFER_OVERFLOW;
  if (frame_ready) *frame_ready = false;

  if (byte == 0x7E) {
    /* Flag byte — boundary.  Never appears inside a correctly stuffed
     * frame because bit-stuffing ensures no byte-aligned 0x7E. */
    if (d->state == AX25_STATE_HUNT) {
      /* Opening flag. */
      d->state = AX25_STATE_FRAME;
      d->len = 0;
      d->shift_reg = 0;
      d->bit_count = 0;
      d->ones_run = 0;
      return AX25_OK;
    }
    /* Closing flag — try to emit, then stay ready for the next frame. */
    emit_frame_if_valid(d, out_frame, frame_ready);
    /* A closing flag may also serve as the opening flag of the next
     * frame (REQ-AX25-023 back-to-back frames). */
    d->state = AX25_STATE_FRAME;
    d->len = 0;
    d->shift_reg = 0;
    d->bit_count = 0;
    d->ones_run = 0;
    return AX25_OK;
  }

  if (d->state == AX25_STATE_HUNT) {
    /* Idle bytes outside any frame — ignore. */
    return AX25_OK;
  }

  /* Inside FRAME: consume 8 bits LSB-first with de-stuffing. */
  for (int b = 0; b < 8; b++) {
    int bit = (byte >> b) & 1;
    if (d->ones_run == 5) {
      if (bit == 0) {
        /* Stuffed bit — drop. */
        d->ones_run = 0;
        continue;
      }
      /* Six consecutive 1s — REQ-AX25-024: reset, byte stays consumed. */
      d->frames_stuffing_err++;
      ax25_decoder_reset(d);
      return AX25_ERR_STUFFING_VIOLATION;
    }
    if (!append_bit(d, bit)) {
      /* Overflow already logged and decoder reset. */
      return AX25_ERR_FRAME_TOO_LONG;
    }
    d->ones_run = (bit == 1) ? d->ones_run + 1 : 0;
  }
  return AX25_OK;
}
