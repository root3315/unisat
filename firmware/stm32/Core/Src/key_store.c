/**
 * @file key_store.c
 * @brief Persistent, CRC-protected HMAC-key store with A/B atomic rotation.
 *
 * Design summary is in key_store.h. This file implements:
 *   1. Serialisation: [ magic(1) | gen(4) | key(32) | crc(4) ]  = 41 B.
 *   2. CRC-32 (IEEE 802.3, poly 0xEDB88320) over magic+gen+key.
 *   3. Boot-time slot picker: choose the slot with the highest valid
 *      generation. Ignore slots with bad magic (erased) or bad CRC
 *      (torn write). Ties impossible — the rotation protocol ensures
 *      strictly increasing generations.
 *   4. In-memory active cache so CommandDispatcher_SetKey sees a fast
 *      path without re-reading flash on every command.
 *   5. A default in-memory platform backend used when the target
 *      build has not overridden key_store_platform_{read,write,erase}
 *      — this lets the host tests exercise the whole lifecycle
 *      (init → rotate → init again) entirely in RAM.
 *
 * The generation counter being strictly increasing protects against
 * replay of a stale rotation command: an attacker cannot "downgrade"
 * to an earlier key by replaying the older rotation frame because
 * key_store_rotate() rejects new_gen <= current_gen with
 * KEY_STORE_STALE_GEN.
 */

#include "key_store.h"
#include <string.h>

/* ------------------------------------------------------------------
 *  Internal record layout
 * ------------------------------------------------------------------ */
#define HDR_MAGIC_OFFSET   0U
#define HDR_GEN_OFFSET     1U
#define HDR_KEY_OFFSET     5U
#define HDR_CRC_OFFSET     (HDR_KEY_OFFSET + KEY_STORE_MAX_KEY_LEN)
/* Total on-disk record size = HDR_CRC_OFFSET + 4 = 41 B. */
_Static_assert(KEY_STORE_RECORD_SIZE == HDR_CRC_OFFSET + 4U,
               "KEY_STORE_RECORD_SIZE inconsistent with layout");


/* ------------------------------------------------------------------
 *  In-memory cache of the active slot
 * ------------------------------------------------------------------ */
typedef struct {
    bool     present;
    uint32_t generation;
    uint8_t  key[KEY_STORE_MAX_KEY_LEN];
    size_t   key_len;
    uint8_t  active_slot;   /* 0 or 1 — which slot is live */
} ActiveCache_t;

static ActiveCache_t g_active = { false, 0U, {0}, 0U, 0U };


/* ------------------------------------------------------------------
 *  CRC-32 (IEEE 802.3 — same polynomial used everywhere else in the
 *  firmware, e.g. the FreeRTOS heap integrity check).
 * ------------------------------------------------------------------ */
static uint32_t crc32(const uint8_t *buf, size_t len)
{
    uint32_t crc = 0xFFFFFFFFU;
    for (size_t i = 0; i < len; ++i) {
        crc ^= buf[i];
        for (unsigned b = 0; b < 8U; ++b) {
            uint32_t mask = (uint32_t)-(int32_t)(crc & 1U);
            crc = (crc >> 1) ^ (0xEDB88320U & mask);
        }
    }
    return crc ^ 0xFFFFFFFFU;
}


/* ------------------------------------------------------------------
 *  Default in-memory platform backend
 *
 *  These are weak so that a target-build platform override in, e.g.,
 *  firmware/stm32/Target/key_store_flash.c can replace them. The
 *  default implementation backs the store with two 41-byte arrays
 *  initialised to 0xFF (the erased-flash pattern).
 * ------------------------------------------------------------------ */
static uint8_t g_slot_mem[KEY_STORE_SLOTS][KEY_STORE_RECORD_SIZE];
static bool    g_mem_initialised = false;

static void ensure_mem_initialised(void)
{
    if (!g_mem_initialised) {
        for (uint8_t s = 0; s < KEY_STORE_SLOTS; ++s) {
            memset(g_slot_mem[s], 0xFF, KEY_STORE_RECORD_SIZE);
        }
        g_mem_initialised = true;
    }
}

__attribute__((weak))
bool key_store_platform_read(uint8_t slot_index,
                              uint8_t *buf, size_t len)
{
    if (slot_index >= KEY_STORE_SLOTS || buf == NULL ||
        len != KEY_STORE_RECORD_SIZE) {
        return false;
    }
    ensure_mem_initialised();
    memcpy(buf, g_slot_mem[slot_index], len);
    return true;
}

__attribute__((weak))
bool key_store_platform_write(uint8_t slot_index,
                               const uint8_t *buf, size_t len)
{
    if (slot_index >= KEY_STORE_SLOTS || buf == NULL ||
        len != KEY_STORE_RECORD_SIZE) {
        return false;
    }
    ensure_mem_initialised();
    memcpy(g_slot_mem[slot_index], buf, len);
    return true;
}

__attribute__((weak))
bool key_store_platform_erase(uint8_t slot_index)
{
    if (slot_index >= KEY_STORE_SLOTS) { return false; }
    ensure_mem_initialised();
    memset(g_slot_mem[slot_index], 0xFF, KEY_STORE_RECORD_SIZE);
    return true;
}


/* ------------------------------------------------------------------
 *  Serialisation helpers
 * ------------------------------------------------------------------ */

static void be_write_u32(uint8_t *dst, uint32_t v)
{
    dst[0] = (uint8_t)((v >> 24) & 0xFFU);
    dst[1] = (uint8_t)((v >> 16) & 0xFFU);
    dst[2] = (uint8_t)((v >>  8) & 0xFFU);
    dst[3] = (uint8_t)( v        & 0xFFU);
}

static uint32_t be_read_u32(const uint8_t *src)
{
    return ((uint32_t)src[0] << 24)
         | ((uint32_t)src[1] << 16)
         | ((uint32_t)src[2] <<  8)
         | ((uint32_t)src[3]      );
}

/* Parse a raw slot into (generation, key, key_len) via the heuristic
 * "key ends at the last non-0xFF byte". Returns true on valid record,
 * false if magic is wrong or CRC mismatches. */
static bool parse_record(const uint8_t *raw,
                         uint32_t *out_gen,
                         uint8_t *out_key,
                         size_t *out_key_len)
{
    if (raw[HDR_MAGIC_OFFSET] != KEY_STORE_MAGIC) {
        return false;
    }

    /* Verify CRC over [magic | gen | key]. */
    uint32_t expected = crc32(raw, HDR_CRC_OFFSET);
    uint32_t got      = be_read_u32(&raw[HDR_CRC_OFFSET]);
    if (expected != got) {
        return false;
    }

    /* Derive effective key length: trailing bytes equal to 0xFF are
     * the pad from a shorter key; the actual material ends at the
     * last non-0xFF byte. A 32-byte HMAC-SHA256 key uses all 32
     * slots so the strip-trailing-FF rule returns 32. */
    size_t klen = KEY_STORE_MAX_KEY_LEN;
    while (klen > KEY_STORE_MIN_KEY_LEN &&
           raw[HDR_KEY_OFFSET + klen - 1U] == 0xFFU) {
        --klen;
    }

    if (out_gen    != NULL) { *out_gen = be_read_u32(&raw[HDR_GEN_OFFSET]); }
    if (out_key    != NULL) { memcpy(out_key, &raw[HDR_KEY_OFFSET], klen); }
    if (out_key_len != NULL) { *out_key_len = klen; }
    return true;
}

static void serialise_record(uint8_t *raw,
                             uint32_t generation,
                             const uint8_t *key, size_t key_len)
{
    raw[HDR_MAGIC_OFFSET] = KEY_STORE_MAGIC;
    be_write_u32(&raw[HDR_GEN_OFFSET], generation);

    /* Pad unused key bytes with 0xFF so parse_record() can recover
     * the true key_len via the strip-trailing-FF rule. */
    memset(&raw[HDR_KEY_OFFSET], 0xFF, KEY_STORE_MAX_KEY_LEN);
    memcpy(&raw[HDR_KEY_OFFSET], key, key_len);

    uint32_t crc = crc32(raw, HDR_CRC_OFFSET);
    be_write_u32(&raw[HDR_CRC_OFFSET], crc);
}


/* ------------------------------------------------------------------
 *  Public API
 * ------------------------------------------------------------------ */

KeyStoreStatus_t key_store_init(void)
{
    g_active.present = false;
    g_active.generation = 0U;
    g_active.key_len = 0U;

    uint8_t  raw[KEY_STORE_RECORD_SIZE];
    uint8_t  tmp_key[KEY_STORE_MAX_KEY_LEN];
    size_t   tmp_len;
    uint32_t tmp_gen;

    for (uint8_t slot = 0; slot < KEY_STORE_SLOTS; ++slot) {
        if (!key_store_platform_read(slot, raw, sizeof(raw))) {
            continue;
        }
        if (!parse_record(raw, &tmp_gen, tmp_key, &tmp_len)) {
            continue;
        }
        if (!g_active.present || tmp_gen > g_active.generation) {
            g_active.present    = true;
            g_active.generation = tmp_gen;
            g_active.key_len    = tmp_len;
            g_active.active_slot = slot;
            memcpy(g_active.key, tmp_key, tmp_len);
        }
    }

    return g_active.present ? KEY_STORE_OK : KEY_STORE_EMPTY;
}

KeyStoreStatus_t key_store_get_active(uint8_t *key_buf,
                                       size_t *key_len,
                                       uint32_t *generation)
{
    if (key_buf == NULL || key_len == NULL) { return KEY_STORE_BAD_INPUT; }
    if (!g_active.present) { return KEY_STORE_EMPTY; }

    memcpy(key_buf, g_active.key, g_active.key_len);
    *key_len = g_active.key_len;
    if (generation != NULL) { *generation = g_active.generation; }
    return KEY_STORE_OK;
}

KeyStoreStatus_t key_store_rotate(const uint8_t *new_key,
                                   size_t new_len,
                                   uint32_t new_gen)
{
    if (new_key == NULL ||
        new_len < KEY_STORE_MIN_KEY_LEN ||
        new_len > KEY_STORE_MAX_KEY_LEN) {
        return KEY_STORE_BAD_INPUT;
    }
    if (g_active.present && new_gen <= g_active.generation) {
        return KEY_STORE_STALE_GEN;
    }

    /* Write to the *inactive* slot so the active one survives a
     * torn write. If no slot is active yet (first rotation after
     * factory reset) we pick slot 0. */
    uint8_t target_slot = g_active.present ?
                          (uint8_t)(1U - g_active.active_slot) : 0U;

    uint8_t raw[KEY_STORE_RECORD_SIZE];
    serialise_record(raw, new_gen, new_key, new_len);

    if (!key_store_platform_write(target_slot, raw, sizeof(raw))) {
        return KEY_STORE_BACKEND_FAIL;
    }

    /* Read back + verify CRC so a silent backend corruption is
     * detected before the slot is considered active. */
    uint8_t verify[KEY_STORE_RECORD_SIZE];
    if (!key_store_platform_read(target_slot, verify, sizeof(verify))) {
        return KEY_STORE_BACKEND_FAIL;
    }
    if (memcmp(raw, verify, sizeof(raw)) != 0) {
        return KEY_STORE_CRC_FAIL;
    }

    /* Promote the new slot to active in the in-memory cache. The
     * higher-generation slot will be chosen automatically by the
     * next key_store_init() on a warm reboot, so no additional
     * "pointer bit" needs to be persisted. */
    g_active.present     = true;
    g_active.generation  = new_gen;
    g_active.key_len     = new_len;
    g_active.active_slot = target_slot;
    memcpy(g_active.key, new_key, new_len);

    return KEY_STORE_OK;
}

KeyStoreStatus_t key_store_wipe(void)
{
    for (uint8_t s = 0; s < KEY_STORE_SLOTS; ++s) {
        if (!key_store_platform_erase(s)) {
            return KEY_STORE_BACKEND_FAIL;
        }
    }
    g_active.present = false;
    g_active.generation = 0U;
    g_active.key_len = 0U;
    memset(g_active.key, 0, sizeof(g_active.key));
    return KEY_STORE_OK;
}

uint32_t key_store_active_generation(void)
{
    return g_active.present ? g_active.generation : 0U;
}
