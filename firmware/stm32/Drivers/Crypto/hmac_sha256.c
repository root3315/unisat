/**
 * @file hmac_sha256.c
 * @brief RFC 2104 HMAC-SHA256 reference implementation.
 */

#include "hmac_sha256.h"
#include <string.h>

void hmac_sha256(const uint8_t *key, size_t key_len,
                 const uint8_t *msg, size_t msg_len,
                 uint8_t tag_out[HMAC_SHA256_TAG_SIZE]) {
    uint8_t k_ipad[SHA256_BLOCK_SIZE];
    uint8_t k_opad[SHA256_BLOCK_SIZE];
    uint8_t k_norm[SHA256_BLOCK_SIZE];

    /* Normalize key to exactly the block size: hash down if longer, zero-pad
     * if shorter.  RFC 2104 §2. */
    memset(k_norm, 0, sizeof(k_norm));
    if (key_len > SHA256_BLOCK_SIZE) {
        sha256(key, key_len, k_norm);
    } else {
        memcpy(k_norm, key, key_len);
    }

    for (int i = 0; i < SHA256_BLOCK_SIZE; i++) {
        k_ipad[i] = k_norm[i] ^ 0x36;
        k_opad[i] = k_norm[i] ^ 0x5c;
    }

    sha256_ctx_t ctx;
    uint8_t inner_digest[SHA256_DIGEST_SIZE];

    /* inner = H(k_ipad || msg) */
    sha256_init(&ctx);
    sha256_update(&ctx, k_ipad, SHA256_BLOCK_SIZE);
    sha256_update(&ctx, msg, msg_len);
    sha256_final(&ctx, inner_digest);

    /* outer = H(k_opad || inner) */
    sha256_init(&ctx);
    sha256_update(&ctx, k_opad, SHA256_BLOCK_SIZE);
    sha256_update(&ctx, inner_digest, SHA256_DIGEST_SIZE);
    sha256_final(&ctx, tag_out);
}

int hmac_sha256_verify(const uint8_t a[HMAC_SHA256_TAG_SIZE],
                       const uint8_t b[HMAC_SHA256_TAG_SIZE]) {
    /* Constant-time XOR-accumulate. Do NOT early-exit on mismatch. */
    uint8_t diff = 0;
    for (size_t i = 0; i < HMAC_SHA256_TAG_SIZE; i++) {
        diff |= a[i] ^ b[i];
    }
    return diff == 0;
}
