/**
 * @file ax25_types.h
 * @brief AX.25 v2.2 link layer — shared types.
 *
 * See docs/superpowers/specs/2026-04-17-track1-ax25-design.md §5.1
 * for design rationale.
 */
#ifndef AX25_TYPES_H
#define AX25_TYPES_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "config.h"

typedef enum {
  AX25_OK = 0,
  AX25_ERR_FLAG_MISSING,
  AX25_ERR_FCS_MISMATCH,
  AX25_ERR_INFO_TOO_LONG,
  AX25_ERR_FRAME_TOO_LONG,
  AX25_ERR_BUFFER_OVERFLOW,
  AX25_ERR_ADDRESS_INVALID,
  AX25_ERR_CONTROL_INVALID,
  AX25_ERR_PID_INVALID,
  AX25_ERR_STUFFING_VIOLATION
} ax25_status_t;

typedef struct {
  char    callsign[7];   /* NUL-terminated; 1..6 ASCII A-Z, 0-9, or space */
  uint8_t ssid;          /* 0..15 */
} ax25_address_t;

typedef struct {
  ax25_address_t dst;
  ax25_address_t src;
  uint8_t        control;        /* 0x03 for UI frame */
  uint8_t        pid;            /* 0xF0 (no layer 3) */
  uint8_t        info[AX25_MAX_INFO_LEN];
  uint16_t       info_len;
  uint16_t       fcs;            /* received FCS, little-endian on wire */
  bool           fcs_valid;
} ax25_ui_frame_t;

/**
 * Streaming decoder state.
 *
 * One instance per RX channel. NOT thread-safe: the owning task
 * (e.g. comm_rx_task) has exclusive access. No heap allocation —
 * the assembly buffer is embedded in the struct.
 */
typedef enum {
  AX25_STATE_HUNT = 0,   /* scanning for opening 0x7E flag */
  AX25_STATE_FRAME       /* inside frame, collecting bits  */
} ax25_decoder_state_t;

typedef struct {
  uint8_t              buf[AX25_MAX_FRAME_BYTES];
  size_t               len;          /* bytes assembled so far        */
  uint16_t             shift_reg;    /* bit-level packing accumulator */
  uint8_t              bit_count;    /* bits currently in shift_reg   */
  uint8_t              ones_run;     /* consecutive-1 counter         */
  ax25_decoder_state_t state;
  uint32_t             frames_ok;
  uint32_t             frames_fcs_err;
  uint32_t             frames_overflow;
  uint32_t             frames_stuffing_err;
  uint32_t             frames_other_err;
} ax25_decoder_t;

#endif /* AX25_TYPES_H */
