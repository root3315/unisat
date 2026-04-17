/**
 * @file sha256.h
 * @brief FIPS 180-4 SHA-256 — streaming API, no dependencies.
 *
 * Used by hmac_sha256 for AX.25 / CCSDS command authentication
 * (Track 1b). Stdlib-only, safe to call from any context including
 * flight-software task context (does not malloc, does not use
 * system time). Not hardened against side-channel attacks — for
 * that, wire in the STM32 hardware CRYP peripheral at integration
 * time.
 */
#ifndef SHA256_H
#define SHA256_H

#include <stdint.h>
#include <stddef.h>

#define SHA256_DIGEST_SIZE 32
#define SHA256_BLOCK_SIZE  64

typedef struct {
    uint32_t state[8];
    uint64_t bit_count;
    uint8_t  buffer[SHA256_BLOCK_SIZE];
    size_t   buffer_len;
} sha256_ctx_t;

void sha256_init(sha256_ctx_t *ctx);
void sha256_update(sha256_ctx_t *ctx, const uint8_t *data, size_t len);
void sha256_final(sha256_ctx_t *ctx, uint8_t digest[SHA256_DIGEST_SIZE]);

/** Convenience: single-shot hash. */
void sha256(const uint8_t *data, size_t len, uint8_t digest[SHA256_DIGEST_SIZE]);

#endif /* SHA256_H */
