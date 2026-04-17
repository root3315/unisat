/**
 * @file ax25_api.h
 * @brief Project-facing AX.25 facade (embedded-HAL naming convention).
 *
 * See ADR-002 for the rationale behind the two naming styles. The
 * pure library at ax25.h uses Google C++ snake_case; this header
 * provides thin `static inline` wrappers with the UniSat firmware's
 * PascalCase convention so that callers in comm.c, telemetry.c etc.
 * can include just this one file and stay stylistically consistent.
 */
#ifndef AX25_API_H
#define AX25_API_H

#include "ax25.h"
#include "ax25_decoder.h"

/* Project-style type aliases. */
typedef ax25_address_t  AX25_Address_t;
typedef ax25_ui_frame_t AX25_UiFrame_t;
typedef ax25_status_t   AX25_Status_t;
typedef ax25_decoder_t  AX25_Decoder_t;

static inline bool AX25_EncodeUiFrame(
    const AX25_Address_t *dst, const AX25_Address_t *src,
    uint8_t pid, const uint8_t *info, uint16_t info_len,
    uint8_t *out_buf, uint16_t out_cap, uint16_t *out_len) {
  size_t len_tmp = 0;
  ax25_status_t s = ax25_encode_ui_frame(
      dst, src, pid, info, info_len, out_buf, out_cap, &len_tmp);
  if (out_len) *out_len = (uint16_t)len_tmp;
  return s == AX25_OK;
}

static inline void AX25_DecoderInit(AX25_Decoder_t *d) {
  ax25_decoder_init(d);
}

static inline void AX25_DecoderReset(AX25_Decoder_t *d) {
  ax25_decoder_reset(d);
}

static inline bool AX25_DecoderPushByte(
    AX25_Decoder_t *d, uint8_t byte,
    AX25_UiFrame_t *out_frame, bool *frame_ready) {
  return ax25_decoder_push_byte(d, byte, out_frame, frame_ready) == AX25_OK;
}

#endif /* AX25_API_H */
