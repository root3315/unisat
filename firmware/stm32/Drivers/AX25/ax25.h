/**
 * @file ax25.h
 * @brief AX.25 v2.2 link layer — pure stateless API.
 *
 * Zero HAL or FreeRTOS dependencies. All buffers are caller-provided
 * or on the stack. See design spec §5.1.
 */
#ifndef AX25_H
#define AX25_H

#include "ax25_types.h"

/**
 * CRC-16/X.25 per REQ-AX25-006 / REQ-AX25-022.
 *
 * Parameters: poly=0x1021, init=0xFFFF, refin=true, refout=true,
 * xorout=0xFFFF. Reference vector (mandatory, asserted in tests):
 *   ax25_fcs_crc16("123456789", 9) == 0x906E.
 *
 * Implementation uses the reflected polynomial 0x8408 with a
 * right-shift LSB-first algorithm so byte-boundary and stuffing
 * arithmetic stays consistent with AX.25 v2.2 §3.12.
 */
uint16_t ax25_fcs_crc16(const uint8_t *data, size_t len);

/**
 * Bit-level stuffing per REQ-AX25-007 / REQ-AX25-016.
 *
 * Walks the input as an LSB-first bit stream; after every five
 * consecutive 1-bits a 0-bit is inserted. Output is packed LSB-first
 * into whole bytes (last byte may have unused high bits).
 *
 * Returns the number of output bytes written, or 0 on buffer overflow.
 * State is tracked across byte boundaries — byte-wise stuffing is
 * explicitly incorrect and will fail the shared golden vectors.
 */
size_t ax25_bit_stuff(const uint8_t *in, size_t in_len,
                      uint8_t *out, size_t out_cap);

/**
 * Inverse of ax25_bit_stuff. Drops a 0-bit that follows five 1-bits;
 * six consecutive 1-bits is an AX.25 protocol violation (the stuffer
 * should have inserted a 0).
 *
 * Returns bytes written. On failure returns 0 and (if @p status is
 * non-NULL) writes the reason: AX25_ERR_STUFFING_VIOLATION on 6 ones,
 * AX25_ERR_BUFFER_OVERFLOW if @p out_cap is exceeded.
 */
size_t ax25_bit_unstuff(const uint8_t *in, size_t in_len,
                        uint8_t *out, size_t out_cap,
                        ax25_status_t *status);

#endif /* AX25_H */
