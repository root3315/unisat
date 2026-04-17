/**
 * @file fdir_persistent.c
 * @brief .noinit-backed persistent fault ring with CRC validation.
 *
 * The ring and its header live in a .noinit SRAM section (see
 * firmware/stm32/Target/STM32F446RETx_FLASH.ld) so the contents
 * survive a soft reset but are undefined on cold boot. A magic
 * number + CRC-32 over the payload distinguish the two cases:
 *
 *   * valid magic && matching CRC   -> log carried over from pre-reboot
 *   * anything else (cold boot, bit flip, wrong layout after firmware
 *     update)                        -> wipe, start fresh
 *
 * The CRC is re-computed on every Record / NoteRebootReason so a
 * warm boot only trusts data that was intact just before reset.
 *
 * On host (SIMULATION_MODE) the .noinit placement is ignored; the
 * ring lives in plain .bss and starts zeroed on every process
 * launch. The API contract still works end-to-end and the unit
 * test exercises Init + Record + Snapshot + Wipe against that
 * backing.
 */

#include "fdir_persistent.h"
#include <string.h>

/* ------------------------------------------------------------------
 *  .noinit placement macros — on target maps to the dedicated
 *  linker section; on host the attribute is a no-op.
 * ------------------------------------------------------------------ */
#if defined(SIMULATION_MODE)
#  define NOINIT_ATTR
#else
#  define NOINIT_ATTR  __attribute__((section(".noinit")))
#endif

/* ------------------------------------------------------------------
 *  Backing storage in .noinit. Deliberately NOT zero-initialised —
 *  the invariant is "trust only if magic + CRC match".
 * ------------------------------------------------------------------ */
static FDIR_PersistentHeader_t  g_hdr NOINIT_ATTR;
static FDIR_PersistentEntry_t   g_ring[FDIR_PERSISTENT_CAPACITY] NOINIT_ATTR;

/* ------------------------------------------------------------------
 *  CRC-32 (same polynomial as key_store.c — IEEE 802.3).
 * ------------------------------------------------------------------ */
static uint32_t crc32_update(uint32_t crc, const uint8_t *buf, size_t len)
{
    for (size_t i = 0; i < len; ++i) {
        crc ^= buf[i];
        for (unsigned b = 0; b < 8U; ++b) {
            uint32_t mask = (uint32_t)-(int32_t)(crc & 1U);
            crc = (crc >> 1) ^ (0xEDB88320U & mask);
        }
    }
    return crc;
}

/* Compute CRC over the header (with crc32 field zeroed) + ring. */
static uint32_t compute_crc(void)
{
    uint32_t crc = 0xFFFFFFFFU;
    FDIR_PersistentHeader_t view = g_hdr;
    view.crc32 = 0U;
    crc = crc32_update(crc, (const uint8_t *)&view, sizeof(view));
    crc = crc32_update(crc, (const uint8_t *)g_ring, sizeof(g_ring));
    return crc ^ 0xFFFFFFFFU;
}

/* Recompute and write the stored CRC. */
static void refresh_crc(void)
{
    g_hdr.crc32 = compute_crc();
}

/* Cold-reset the storage: zero everything INCLUDING the magic. A
 * subsequent Init() sees an invalid magic and takes the cold path
 * (sets magic, leaves counters at 0, returns false). This makes
 * Wipe + Init equivalent to "first power-on" for unit tests. */
static void wipe_storage(void)
{
    memset(&g_hdr, 0, sizeof(g_hdr));
    memset(g_ring, 0, sizeof(g_ring));
    /* magic deliberately left at 0 so next Init sees it as cold. */
}

/* Internal helper: mark storage as valid (call after first use /
 * after a cold-boot arm). Separate from wipe_storage so the two
 * paths are obvious at every call site. */
static void arm_storage(void)
{
    g_hdr.magic = FDIR_PERSISTENT_MAGIC;
    refresh_crc();
}

/* ------------------------------------------------------------------
 *  Public API
 * ------------------------------------------------------------------ */

/* Init result cache — populated by FDIR_Persistent_Init, read by
 * GetMeta. Set to false on cold/corrupt, true on warm-with-payload. */
static bool g_last_init_valid = false;

bool FDIR_Persistent_Init(void)
{
    if (g_hdr.magic != FDIR_PERSISTENT_MAGIC) {
        /* Cold boot or garbage in .noinit — zero the backing and arm
         * it with MAGIC + fresh CRC so subsequent Record calls land
         * in a known-valid layout. reboot_count stays at 0: this is
         * the first boot, not a warm restart. */
        wipe_storage();
        arm_storage();
        g_last_init_valid = false;
        return false;
    }

    if (g_hdr.count > FDIR_PERSISTENT_CAPACITY ||
        g_hdr.head  >= FDIR_PERSISTENT_CAPACITY) {
        /* Header survived but pointer values are out of range — almost
         * certainly a partial write interrupted by reset. Nuke it. */
        wipe_storage();
        arm_storage();
        g_last_init_valid = false;
        return false;
    }

    uint32_t expected = g_hdr.crc32;
    uint32_t got      = compute_crc();
    if (expected != got) {
        wipe_storage();
        arm_storage();
        g_last_init_valid = false;
        return false;
    }

    /* Survived intact — bump the reboot counter and refresh CRC so the
     * next boot also validates. */
    g_hdr.reboot_count += 1U;
    refresh_crc();
    g_last_init_valid = true;
    return true;
}

void FDIR_Persistent_Record(FDIR_FaultId_t fault,
                             FDIR_Recovery_t recovery,
                             SystemMode_t mode)
{
    /* Defensive: if caller forgot Init, treat header as invalid and
     * wipe so we don't accidentally write into garbage .noinit. */
    if (g_hdr.magic != FDIR_PERSISTENT_MAGIC) {
        wipe_storage();
        arm_storage();
    }

    FDIR_PersistentEntry_t *slot = &g_ring[g_hdr.head];
    slot->timestamp_ms = FDIR_GetTick();
    slot->total_count  = 0U;   /* set by caller via Record variant if needed */
    slot->fault_id     = (uint16_t)fault;
    slot->recovery     = (uint8_t)recovery;
    slot->mode         = (uint8_t)mode;
    slot->reserved     = 0U;

    g_hdr.head = (uint8_t)((g_hdr.head + 1U) % FDIR_PERSISTENT_CAPACITY);
    if (g_hdr.count < FDIR_PERSISTENT_CAPACITY) {
        g_hdr.count++;
    }
    refresh_crc();
}

void FDIR_Persistent_NoteRebootReason(ModeReason_t reason)
{
    if (g_hdr.magic != FDIR_PERSISTENT_MAGIC) {
        wipe_storage();
        arm_storage();
    }
    g_hdr.reboot_reason = (uint8_t)reason;
    refresh_crc();
}

uint8_t FDIR_Persistent_Snapshot(FDIR_PersistentEntry_t *out, uint8_t max)
{
    if (g_hdr.count == 0U) { return 0U; }
    if (out == NULL || max == 0U) { return g_hdr.count; }

    uint8_t to_copy = (max < g_hdr.count) ? max : g_hdr.count;

    /* Walk newest-first. head points to the next write slot, so the
     * most-recent entry is at (head - 1) mod capacity. */
    uint8_t idx = (uint8_t)((g_hdr.head + FDIR_PERSISTENT_CAPACITY - 1U)
                             % FDIR_PERSISTENT_CAPACITY);
    for (uint8_t i = 0; i < to_copy; ++i) {
        out[i] = g_ring[idx];
        idx = (uint8_t)((idx + FDIR_PERSISTENT_CAPACITY - 1U)
                         % FDIR_PERSISTENT_CAPACITY);
    }
    return to_copy;
}

FDIR_PersistentMeta_t FDIR_Persistent_GetMeta(void)
{
    FDIR_PersistentMeta_t m = {0U, 0U, 0U, false};
    if (g_hdr.magic == FDIR_PERSISTENT_MAGIC) {
        m.count           = g_hdr.count;
        m.reboot_reason   = g_hdr.reboot_reason;
        m.reboot_count    = g_hdr.reboot_count;
        m.valid_after_reset = g_last_init_valid;
    }
    return m;
}

void FDIR_Persistent_Wipe(void)
{
    wipe_storage();
    g_last_init_valid = false;
}
