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
