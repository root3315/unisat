/**
 * @file fdir_persistent.h
 * @brief Warm-reboot-survivable fault log (Phase 7 / #4).
 *
 * A small ring buffer of fault events stored in the linker-reserved
 * .noinit SRAM section. Survives a soft reset (NVIC, WWDG, IWDG,
 * HardFault recovery) but is volatile across full power cycles —
 * the consumer validates by a magic-number + CRC32 pair before
 * trusting any entry.
 *
 * Typical usage
 * -------------
 *   * First boot ever (cold start): FDIR_Persistent_Init() sees an
 *     invalid magic, zeroes the ring + magic, starts fresh.
 *   * Subsequent reboot (soft reset, e.g. FDIR-REBOOT): the .noinit
 *     region is still there; Init sees the valid magic + CRC,
 *     preserves the ring, and the next boot's telemetry downlinks
 *     the pre-reboot fault tail — ground can correlate the reason.
 *   * On every fault: FDIR.Report also calls FDIR_Persistent_Record
 *     so the event is carried forward. Head-overwrite on ring wrap
 *     is OK: the 16 most recent faults are always visible.
 *
 * Storage footprint: 16 × 16 = 256 bytes ring + 16 bytes header =
 * 272 bytes SRAM in .noinit. Negligible next to the 128 KB total.
 *
 * Host semantics
 * --------------
 * On host (SIMULATION_MODE) the .noinit placement has no special
 * meaning — the backing array is plain .bss and is zeroed on each
 * process launch. The warm-reboot-survives invariant is only true
 * on target, but the API contract (validate + record + snapshot)
 * is testable end-to-end on host.
 */
#ifndef FDIR_PERSISTENT_H
#define FDIR_PERSISTENT_H

#include <stdint.h>
#include <stdbool.h>
#include "fdir.h"
#include "mode_manager.h"

/** Capacity of the ring buffer — newest N events kept. */
#define FDIR_PERSISTENT_CAPACITY  16U

/** Magic marker that distinguishes "valid log" from "uninitialised
 *  SRAM" after a cold boot. Printable ASCII 'F' 'D' 'I' 'R' LE. */
#define FDIR_PERSISTENT_MAGIC     0x52494446UL

/** Reboot-loop detection threshold.
 *
 *  Once the persistent ``reboot_count`` has advanced this high
 *  without a successful ground-side clear, main() engages the
 *  mode-supervisor's reboot suppression: further RECOVERY_REBOOT
 *  recommendations are diverted to SAFE mode so an intermittent
 *  fault at boot cannot trap the vehicle in an infinite reset
 *  cycle.  Three is chosen conservatively — two warm resets after
 *  a cold boot are plausible in a bad-cosmic-ray scenario, but a
 *  third strongly suggests a systematic fault that ground needs
 *  to see. */
#define FDIR_REBOOT_LOOP_THRESHOLD 3U

/** One event entry — 16 bytes. */
typedef struct {
    uint32_t       timestamp_ms;    /* FDIR_GetTick at Record time   */
    uint32_t       total_count;     /* FDIR total_count at Record    */
    uint16_t       fault_id;        /* FDIR_FaultId_t cast to u16    */
    uint8_t        recovery;        /* FDIR_Recovery_t recommendation */
    uint8_t        mode;            /* SystemMode_t at record time   */
    uint32_t       reserved;        /* padding to 16 B, future fields */
} FDIR_PersistentEntry_t;

/** Header placed in .noinit before the ring. 16 bytes. */
typedef struct {
    uint32_t magic;                 /* FDIR_PERSISTENT_MAGIC         */
    uint32_t crc32;                 /* over head + count + ring      */
    uint8_t  head;                  /* next write index 0..CAPACITY-1 */
    uint8_t  count;                 /* filled entries 1..CAPACITY     */
    uint8_t  reboot_reason;         /* last ModeReason_t before reset */
    uint8_t  padding;
    uint32_t reboot_count;          /* total reboots observed         */
} FDIR_PersistentHeader_t;


/** One-shot initialiser.
 *
 *  Returns true if the ring survived the reset (valid magic + CRC);
 *  the caller can then inspect the tail via FDIR_Persistent_Snapshot
 *  and downlink it. Returns false on cold-boot / corruption — the
 *  ring is reinitialised clean and all counters are zero.
 */
bool FDIR_Persistent_Init(void);

/** Record one event. Intended to be called from FDIR.Report (or the
 *  mode manager's transition helper). Safe to call before Init — on
 *  an invalid header we implicitly clear and start fresh. */
void FDIR_Persistent_Record(FDIR_FaultId_t fault,
                             FDIR_Recovery_t recovery,
                             SystemMode_t mode);

/** Note the last mode transition reason so the next boot can
 *  downlink "why we rebooted". Call from ModeManager_RequestReboot. */
void FDIR_Persistent_NoteRebootReason(ModeReason_t reason);

/** Fill `out` with up to `max` most-recent entries, newest first.
 *  Returns the number actually written. `out` may be NULL with
 *  max == 0 to probe the current fill level. */
uint8_t FDIR_Persistent_Snapshot(FDIR_PersistentEntry_t *out,
                                  uint8_t max);

/** Header snapshot for telemetry — magic/crc32 are not exported
 *  (implementation detail) but count / reboot_count / reason are. */
typedef struct {
    uint8_t  count;
    uint8_t  reboot_reason;
    uint32_t reboot_count;
    bool     valid_after_reset;      /* cached result of Init       */
} FDIR_PersistentMeta_t;

FDIR_PersistentMeta_t FDIR_Persistent_GetMeta(void);

/** Force-clear the ring. Test-fixture only. */
void FDIR_Persistent_Wipe(void);


#endif /* FDIR_PERSISTENT_H */
