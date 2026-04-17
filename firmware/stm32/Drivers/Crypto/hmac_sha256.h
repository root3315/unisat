/**
 * @file hmac_sha256.h
 * @brief HMAC-SHA256 per RFC 2104.
 *
 * Protects CCSDS telecommand packets against injection and replay
 * (Track 1b). 256-bit output tag appended to the CCSDS info field
 * before AX.25 framing on the wire. See the threat model at
 * docs/security/ax25_threat_model.md (T1, T2).
 */
#ifndef HMAC_SHA256_H
#define HMAC_SHA256_H

#include "sha256.h"

#define HMAC_SHA256_TAG_SIZE SHA256_DIGEST_SIZE

/**
 * Compute a single-shot HMAC-SHA256.
 *
 * @param key       shared secret
 * @param key_len   secret length (any, hashed down if > 64)
 * @param msg       message bytes
 * @param msg_len   message length
 * @param tag_out   32-byte output
 */
void hmac_sha256(const uint8_t *key, size_t key_len,
                 const uint8_t *msg, size_t msg_len,
                 uint8_t tag_out[HMAC_SHA256_TAG_SIZE]);

/**
 * Constant-time tag comparison. Returns 1 if equal, 0 otherwise.
 * Use this instead of memcmp to avoid timing side-channels.
 */
int hmac_sha256_verify(const uint8_t a[HMAC_SHA256_TAG_SIZE],
                       const uint8_t b[HMAC_SHA256_TAG_SIZE]);

#endif /* HMAC_SHA256_H */
