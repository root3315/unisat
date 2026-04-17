/**
 * @file ax25.c
 * @brief AX.25 v2.2 link layer — implementation.
 *
 * See docs/communication_protocol.md §7 for wire format and
 * docs/superpowers/specs/2026-04-17-track1-ax25-design.md §5.1
 * for design choices.
 */

#include "ax25.h"

/* CRC-16/X.25 per REQ-AX25-006 / REQ-AX25-022.
 *
 * AX.25 transmits bits LSB-first, so the FCS uses the reflected
 * polynomial 0x8408 (bit-reverse of 0x1021) with right-shift.
 * Init value 0xFFFF and final XOR with 0xFFFF are AX.25 standard.
 *
 * Oracle (asserted in test_ax25_fcs.c):
 *   ax25_fcs_crc16("123456789", 9) == 0x906E.
 */
uint16_t ax25_fcs_crc16(const uint8_t *data, size_t len) {
  uint16_t crc = 0xFFFF;
  for (size_t i = 0; i < len; i++) {
    crc ^= data[i];
    for (int b = 0; b < 8; b++) {
      if (crc & 1) {
        crc = (uint16_t)((crc >> 1) ^ 0x8408);
      } else {
        crc >>= 1;
      }
    }
  }
  return (uint16_t)~crc;
}

/* Write one LSB-first bit into buf[bit_idx/8], advancing *bit_idx. */
static int push_bit(uint8_t *buf, size_t cap, size_t *bit_idx, int bit) {
  size_t byte = *bit_idx / 8;
  size_t shift = *bit_idx % 8;
  if (byte >= cap) return 0;
  if (shift == 0) buf[byte] = 0;
  if (bit) buf[byte] |= (uint8_t)(1u << shift);
  (*bit_idx)++;
  return 1;
}

static int read_bit(const uint8_t *buf, size_t bit_idx) {
  return (buf[bit_idx / 8] >> (bit_idx % 8)) & 1;
}

size_t ax25_bit_stuff(const uint8_t *in, size_t in_len,
                      uint8_t *out, size_t out_cap) {
  if (in == NULL || out == NULL) return 0;
  size_t out_bit = 0;
  int ones = 0;

  const size_t total_bits = in_len * 8;
  for (size_t i = 0; i < total_bits; i++) {
    int bit = read_bit(in, i);
    if (!push_bit(out, out_cap, &out_bit, bit)) return 0;
    if (bit == 1) {
      ones++;
      if (ones == 5) {
        if (!push_bit(out, out_cap, &out_bit, 0)) return 0;
        ones = 0;
      }
    } else {
      ones = 0;
    }
  }
  return (out_bit + 7) / 8;  /* round up to whole bytes */
}

static int is_valid_callsign_char(char c) {
  return (c >= 'A' && c <= 'Z') ||
         (c >= '0' && c <= '9') ||
         c == ' ';
}

ax25_status_t ax25_encode_address(const ax25_address_t *addr,
                                   bool is_last, uint8_t out[7]) {
  if (addr == NULL || out == NULL) return AX25_ERR_ADDRESS_INVALID;
  if (addr->ssid > 15) return AX25_ERR_ADDRESS_INVALID;

  char padded[6] = { ' ', ' ', ' ', ' ', ' ', ' ' };
  size_t n = 0;
  while (n < 6 && addr->callsign[n] != '\0') {
    if (!is_valid_callsign_char(addr->callsign[n])) {
      return AX25_ERR_ADDRESS_INVALID;
    }
    padded[n] = addr->callsign[n];
    n++;
  }
  /* If string is ≥7 chars, reject. */
  if (n == 6 && addr->callsign[6] != '\0') {
    return AX25_ERR_ADDRESS_INVALID;
  }

  for (int i = 0; i < 6; i++) {
    out[i] = (uint8_t)((unsigned char)padded[i] << 1);
  }
  /* CRRSSIDH: C=0 (response), RR=11, SSID shifted left 1, H-bit last. */
  out[6] = (uint8_t)(0x60 | ((addr->ssid & 0x0F) << 1) | (is_last ? 1 : 0));
  return AX25_OK;
}

ax25_status_t ax25_decode_address(const uint8_t in[7],
                                   bool *is_last,
                                   ax25_address_t *out) {
  if (in == NULL || out == NULL) return AX25_ERR_ADDRESS_INVALID;

  for (int i = 0; i < 6; i++) {
    char c = (char)(in[i] >> 1);
    if (!is_valid_callsign_char(c)) return AX25_ERR_ADDRESS_INVALID;
    out->callsign[i] = c;
  }
  out->callsign[6] = '\0';
  /* Trim trailing spaces. */
  for (int i = 5; i >= 0 && out->callsign[i] == ' '; i--) {
    out->callsign[i] = '\0';
  }

  uint8_t ssid_byte = in[6];
  /* RR bits must both be set (standard AX.25 encoding). */
  if ((ssid_byte & 0x60) != 0x60) return AX25_ERR_ADDRESS_INVALID;
  out->ssid = (ssid_byte >> 1) & 0x0F;
  if (is_last) *is_last = (ssid_byte & 1) != 0;
  return AX25_OK;
}

size_t ax25_bit_unstuff(const uint8_t *in, size_t in_len,
                        uint8_t *out, size_t out_cap,
                        ax25_status_t *status) {
  if (in == NULL || out == NULL) {
    if (status) *status = AX25_ERR_BUFFER_OVERFLOW;
    return 0;
  }
  size_t out_bit = 0;
  int ones = 0;

  const size_t total_bits = in_len * 8;
  for (size_t i = 0; i < total_bits; i++) {
    int bit = read_bit(in, i);
    if (ones == 5) {
      if (bit == 0) {
        /* Stuffed bit — drop. */
        ones = 0;
        continue;
      }
      /* Six consecutive 1s inside a frame is a protocol violation. */
      if (status) *status = AX25_ERR_STUFFING_VIOLATION;
      return 0;
    }
    if (!push_bit(out, out_cap, &out_bit, bit)) {
      if (status) *status = AX25_ERR_BUFFER_OVERFLOW;
      return 0;
    }
    ones = (bit == 1) ? ones + 1 : 0;
  }
  if (status) *status = AX25_OK;
  return (out_bit + 7) / 8;
}
