/**
 * @file key_store.h
 * @brief Persistent, CRC-protected HMAC-key store with rotation.
 *
 * Stores up to two versioned key records in dedicated flash sectors
 * (A/B scheme for atomic update). Each record carries a 32-bit
 * monotonic generation counter and a CRC-32 over the key material
 * so a torn-write (power loss mid-erase) is detected at boot and
 * the surviving slot is used.
 *
 * Wire format of one record, big-endian:
 *
 *     +---------------+-----------------+-------------------+
 *     | generation(4) | key material(K) |    crc32(4)       |
 *     +---------------+-----------------+-------------------+
 *
 *  * generation : strictly increasing. Record with lower generation
 *                 is superseded at boot.
 *  * key        : K bytes, 16 <= K <= KEY_STORE_MAX_KEY_LEN (32).
 *  * crc32      : IEEE 802.3 polynomial 0xEDB88320, initial 0xFFFFFFFF,
 *                 final XOR 0xFFFFFFFF, over generation + key bytes.
 *
 * The active record is the one with the highest generation among the
 * two slots whose CRC checks out. If neither slot is valid the store
 * reports "no key" and the command dispatcher refuses every frame
 * (fail-closed). A magic byte MAGIC = 0x55 precedes each on-disk
 * record so a freshly-erased flash sector (all 0xFF) is trivially
 * distinguished from a "zero generation" legitimate record.
 *
 * Rotation protocol (called from an authenticated command handler):
 *   1. Caller validates `new_gen > current_gen` (monotonic).
 *   2. key_store_rotate() writes the new record into the INACTIVE
 *      slot, computes CRC, and verifies the read-back before
 *      returning KEY_STORE_OK. The previously-active slot stays
 *      untouched — if power fails between write and next boot, the
 *      surviving slot is still valid.
 *   3. At next boot key_store_init() selects the higher-generation
 *      slot, which is now the freshly-written one.
 *
 * Platform backend (flash I/O) is factored into three weak hooks
 * defined in this header; the host build supplies an in-memory
 * implementation in key_store.c itself, while a target build can
 * override the hooks with HAL_FLASHEx_Erase / HAL_FLASH_Program calls.
 */
#ifndef KEY_STORE_H
#define KEY_STORE_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

/** Maximum supported key length, in bytes (HMAC-SHA256 uses 32). */
#define KEY_STORE_MAX_KEY_LEN   32U

/** Minimum supported key length; anything shorter has < 128 bits of
 *  entropy and is rejected by key_store_rotate(). */
#define KEY_STORE_MIN_KEY_LEN   16U

/** Number of persistent slots (A/B atomic write scheme). */
#define KEY_STORE_SLOTS         2U

/** Magic byte preceding every on-disk record — distinguishes erased
 *  flash (0xFF) from an all-zero generation field. */
#define KEY_STORE_MAGIC         0x55U

/** Size of one serialised record: magic + gen + key + crc. */
#define KEY_STORE_RECORD_SIZE   (1U + 4U + KEY_STORE_MAX_KEY_LEN + 4U)

/** API status codes. */
typedef enum {
    KEY_STORE_OK           = 0,
    KEY_STORE_EMPTY        = 1,   /* both slots invalid / erased */
    KEY_STORE_BAD_INPUT    = 2,   /* key_len out of range, NULL ptr */
    KEY_STORE_STALE_GEN    = 3,   /* rotate with gen <= current */
    KEY_STORE_BACKEND_FAIL = 4,   /* platform flash I/O failed */
    KEY_STORE_CRC_FAIL     = 5,   /* read-back CRC mismatch */
} KeyStoreStatus_t;

/**
 * @brief Populate the in-RAM cache from the persistent backend.
 * @return KEY_STORE_OK if at least one slot is valid, otherwise
 *         KEY_STORE_EMPTY (dispatcher should refuse all frames).
 *
 * Must be called exactly once at boot before any other API.
 */
KeyStoreStatus_t key_store_init(void);

/**
 * @brief Fetch the currently-active key into the caller buffer.
 *
 * @param[out] key_buf   destination, must be >= KEY_STORE_MAX_KEY_LEN.
 * @param[out] key_len   length actually written (bytes).
 * @param[out] generation generation counter of the returned key.
 * @return KEY_STORE_OK / KEY_STORE_EMPTY / KEY_STORE_BAD_INPUT.
 */
KeyStoreStatus_t key_store_get_active(uint8_t *key_buf,
                                       size_t *key_len,
                                       uint32_t *generation);

/**
 * @brief Install a new key into the inactive slot and switch active.
 *
 * Rotation succeeds only when new_gen strictly exceeds the current
 * active generation. The previously-active slot is preserved until
 * the next rotation so a torn write (power loss between program
 * and verify) can fall back to the old key at next boot.
 *
 * @param new_key  pointer to fresh key material.
 * @param new_len  length of new key (must satisfy MIN <= len <= MAX).
 * @param new_gen  monotonically increasing generation counter.
 * @return KEY_STORE_OK on success; status code otherwise.
 */
KeyStoreStatus_t key_store_rotate(const uint8_t *new_key,
                                   size_t new_len,
                                   uint32_t new_gen);

/**
 * @brief Erase both slots. Intended only for factory-reset / test
 *        fixtures; a live flight image should never call this.
 */
KeyStoreStatus_t key_store_wipe(void);

/**
 * @brief Generation counter of the currently-active slot, or 0 if
 *        no slot is valid. Exposed for telemetry.
 */
uint32_t key_store_active_generation(void);


/* =================================================================
 *  Platform backend hooks — defined __attribute__((weak)) so target
 *  builds can override with HAL flash I/O while the host build uses
 *  the in-memory fallback provided in key_store.c.
 * ================================================================= */

/**
 * @brief Read one serialised record (KEY_STORE_RECORD_SIZE bytes) from
 *        persistent storage slot.
 */
bool key_store_platform_read(uint8_t slot_index,
                              uint8_t *buf, size_t len);

/**
 * @brief Write one serialised record to persistent storage slot.
 *        Implementation must erase the target sector first on flash.
 */
bool key_store_platform_write(uint8_t slot_index,
                               const uint8_t *buf, size_t len);

/**
 * @brief Erase one slot (all 0xFF). Optional — the library also calls
 *        write_raw with a zeroed buffer for wipe semantics.
 */
bool key_store_platform_erase(uint8_t slot_index);


#endif /* KEY_STORE_H */
