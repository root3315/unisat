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

#endif /* AX25_H */
