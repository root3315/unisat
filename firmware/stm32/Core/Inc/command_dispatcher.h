/**
 * @file command_dispatcher.h
 * @brief CCSDS telecommand dispatcher — HMAC-SHA256 + anti-replay.
 *
 * Wire format of the frame delivered to CCSDS_Dispatcher_Submit:
 *
 *     ┌──────────────────┬───────────────┬───────────────────────┐
 *     │  4-byte counter  │   body bytes  │    HMAC-SHA256 tag    │
 *     │   (big-endian)   │  (CCSDS pkt)  │      (32 bytes)       │
 *     └──────────────────┴───────────────┴───────────────────────┘
 *      \_________________ authenticated _____________/
 *
 *  The dispatcher:
 *    1. Rejects frames shorter than 4 + 1 + 32 = 37 bytes.
 *    2. Recomputes HMAC over (counter || body) and verifies in
 *       constant time against the trailing 32-byte tag.
 *    3. Extracts the 32-bit counter and feeds it through a sliding-
 *       window replay filter:
 *         * window half-depth = REPLAY_WINDOW_BITS (64);
 *         * bitmap records which of the last 64 counters have already
 *           been accepted;
 *         * any counter that is duplicate, older than (last − 63), or
 *           equal to zero is rejected without invoking the handler.
 *    4. On success, forwards only the body bytes (without counter and
 *       tag) to the registered handler, preserving the existing
 *       Track-1b handler contract.
 *
 *  Closes threat T1 (injection) *and* T2 (replay) from
 *  docs/security/ax25_threat_model.md. The dispatcher drops all
 *  rejected frames silently: no NAK, no error telemetry ping — an
 *  attacker cannot distinguish a replayed frame from packet loss.
 */
#ifndef COMMAND_DISPATCHER_H
#define COMMAND_DISPATCHER_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/** Size of the authenticated replay counter, in bytes, big-endian. */
#define REPLAY_COUNTER_SIZE   4U

/** Depth of the sliding-window replay filter (bits = distinct counters). */
#define REPLAY_WINDOW_BITS    64U

typedef void (*CommandHandler_t)(const uint8_t *ccsds_packet, uint16_t len);

/** Install the shared 256-bit key. Call once at boot — also resets
 *  the replay window (every rekey is a fresh counter epoch). Passing
 *  key=NULL or key_len=0 puts the dispatcher into refuse-all state. */
void CommandDispatcher_SetKey(const uint8_t *key, size_t key_len);

/** Register the handler invoked on every successfully authenticated +
 *  non-replayed command. NULL means "just count, don't dispatch". */
void CommandDispatcher_SetHandler(CommandHandler_t handler);

/** Per-dispatcher counters — exposed for telemetry. */
typedef struct {
    uint32_t accepted;
    uint32_t rejected_too_short;
    uint32_t rejected_bad_tag;
    uint32_t rejected_replay;
    uint32_t highest_counter;   /* max counter observed; 0 if none */
} CommandDispatcher_Stats_t;

CommandDispatcher_Stats_t CommandDispatcher_GetStats(void);
void CommandDispatcher_ResetStats(void);

/** Force-reset the replay window without changing the key. Intended
 *  for operations procedures (e.g. a signed "reset counter" command)
 *  not normal dispatch. Zero counters land back at the refuse-all
 *  state until the first accepted frame bumps highest_counter to 1. */
void CommandDispatcher_ResetReplayWindow(void);

#endif /* COMMAND_DISPATCHER_H */
