/**
 * @file command_dispatcher.c
 * @brief HMAC-authenticated CCSDS command dispatcher with anti-replay.
 *
 * Provides the strong definition of CCSDS_Dispatcher_Submit that
 * overrides the weak no-op in comm.c.  Wire format expected at the
 * streaming-decoder output:
 *
 *     [ 4-byte counter (big-endian) ][ body bytes ][ HMAC tag 32 B ]
 *       \____________ authenticated ____________/
 *
 * Pipeline for every incoming frame:
 *   1. Length check (>= REPLAY_COUNTER_SIZE + 1 body + HMAC_SHA256_TAG_SIZE).
 *   2. HMAC recompute over counter||body, constant-time compare to tag.
 *   3. Counter extract + sliding-window replay filter.
 *   4. Forward body to the registered handler.
 *
 * Any failure at step 1-3 is silently dropped — a dropped frame is
 * indistinguishable from a lost frame to an off-path attacker, which
 * forecloses both spoof and replay oracle attacks. The rejection
 * reason is captured in the stats struct for downlink telemetry.
 *
 * Closes both T1 (injection) and T2 (replay) from
 * docs/security/ax25_threat_model.md.
 */

#include "command_dispatcher.h"
#include "hmac_sha256.h"
#include <string.h>

/* ------------------------------------------------------------------
 *  Module state — all static, zero-initialised at image load.
 * ------------------------------------------------------------------ */

static uint8_t  g_key[64];
static size_t   g_key_len = 0;

static CommandHandler_t g_handler = NULL;
static CommandDispatcher_Stats_t g_stats = { 0, 0, 0, 0, 0 };

/* Sliding-window state.
 *   g_high_counter : highest counter value ever accepted (0 = none yet)
 *   g_window       : bit i (0..REPLAY_WINDOW_BITS-1) tells whether the
 *                    counter value (g_high_counter - i) has been
 *                    accepted already. Bit 0 => g_high_counter itself.
 *   g_window_valid : set once g_high_counter has been bumped at least
 *                    once; guards against the degenerate "counter=0
 *                    already seen" path at boot.
 */
static uint32_t g_high_counter = 0;
static uint64_t g_window       = 0;
static bool     g_window_valid = false;


/* ------------------------------------------------------------------
 *  Public API
 * ------------------------------------------------------------------ */

void CommandDispatcher_SetKey(const uint8_t *key, size_t key_len)
{
    if (key == NULL || key_len == 0 || key_len > sizeof(g_key)) {
        g_key_len = 0;
        memset(g_key, 0, sizeof(g_key));
        /* New key epoch -> fresh counter window. */
        g_high_counter = 0;
        g_window       = 0;
        g_window_valid = false;
        return;
    }
    memcpy(g_key, key, key_len);
    g_key_len = key_len;
    /* Same rationale for re-key: even if the same key is re-installed,
     * treating it as a new epoch is the conservative choice — the
     * operator who re-installed the key owns the counter reset. */
    g_high_counter = 0;
    g_window       = 0;
    g_window_valid = false;
}

void CommandDispatcher_SetHandler(CommandHandler_t handler)
{
    g_handler = handler;
}

CommandDispatcher_Stats_t CommandDispatcher_GetStats(void)
{
    /* Emit a snapshot with the current highest_counter so ground can
     * correlate "highest counter seen" with the replay-reject count. */
    CommandDispatcher_Stats_t s = g_stats;
    s.highest_counter = g_high_counter;
    return s;
}

void CommandDispatcher_ResetStats(void)
{
    memset(&g_stats, 0, sizeof(g_stats));
}

void CommandDispatcher_ResetReplayWindow(void)
{
    g_high_counter = 0;
    g_window       = 0;
    g_window_valid = false;
}


/* ------------------------------------------------------------------
 *  Internal: replay-window gate.
 *  Returns true if `counter` should be accepted (and updates state).
 *  Returns false on any replay condition.
 * ------------------------------------------------------------------ */
static bool replay_window_check_and_update(uint32_t counter)
{
    /* Counter = 0 is reserved as the "never seen" sentinel. Senders
     * must start at 1; any frame with counter = 0 is rejected. This
     * also prevents a power-on replay of a pre-recorded counter=0
     * frame that would otherwise be indistinguishable from a fresh
     * boot-time state. */
    if (counter == 0U) {
        return false;
    }

    if (!g_window_valid) {
        /* First-ever accepted counter for this key epoch. */
        g_high_counter = counter;
        g_window       = 1ULL;           /* bit 0 = this counter */
        g_window_valid = true;
        return true;
    }

    if (counter > g_high_counter) {
        uint32_t shift = counter - g_high_counter;
        if (shift >= REPLAY_WINDOW_BITS) {
            /* Large forward jump — drop the entire old window, this
             * counter is the new top and every earlier slot is unseen. */
            g_window = 1ULL;
        } else {
            g_window = (g_window << shift) | 1ULL;
        }
        g_high_counter = counter;
        return true;
    }

    /* counter <= g_high_counter — must be within the window and unseen. */
    uint32_t diff = g_high_counter - counter;
    if (diff >= REPLAY_WINDOW_BITS) {
        /* Older than the window can represent. Always reject. */
        return false;
    }

    uint64_t mask = (uint64_t)1U << diff;
    if ((g_window & mask) != 0U) {
        /* Already accepted this counter. Replay. */
        return false;
    }

    g_window |= mask;
    return true;
}


/* ------------------------------------------------------------------
 *  Strong definition — overrides the weak no-op in comm.c.
 * ------------------------------------------------------------------ */
void CCSDS_Dispatcher_Submit(const uint8_t *data, uint16_t len)
{
    /* 1. Length: must hold at least counter + 1 body byte + tag. */
    const uint16_t min_len = (uint16_t)(REPLAY_COUNTER_SIZE + 1U +
                                         HMAC_SHA256_TAG_SIZE);
    if (data == NULL || len < min_len) {
        g_stats.rejected_too_short++;
        return;
    }

    if (g_key_len == 0) {
        /* No key installed — refuse everything. Counts against bad_tag
         * so a "rekey but forgot to install" scenario is observable. */
        g_stats.rejected_bad_tag++;
        return;
    }

    /* 2. HMAC verify. The authenticated span is counter(4) + body,
     *    i.e. everything except the trailing 32-byte tag. */
    const uint16_t auth_len = (uint16_t)(len - HMAC_SHA256_TAG_SIZE);
    const uint8_t *auth     = data;
    const uint8_t *tag      = &data[auth_len];

    uint8_t expected[HMAC_SHA256_TAG_SIZE];
    hmac_sha256(g_key, g_key_len, auth, auth_len, expected);

    if (!hmac_sha256_verify(expected, tag)) {
        g_stats.rejected_bad_tag++;
        return;
    }

    /* 3. Replay-window check using the authenticated counter bytes.
     *    Big-endian so wire-format matches CCSDS conventions. */
    uint32_t counter =
          ((uint32_t)data[0] << 24)
        | ((uint32_t)data[1] << 16)
        | ((uint32_t)data[2] <<  8)
        | ((uint32_t)data[3]      );

    if (!replay_window_check_and_update(counter)) {
        g_stats.rejected_replay++;
        return;
    }

    /* 4. Dispatch the body (after the counter, before the tag). */
    const uint8_t *body     = &data[REPLAY_COUNTER_SIZE];
    const uint16_t body_len = (uint16_t)(auth_len - REPLAY_COUNTER_SIZE);

    g_stats.accepted++;
    if (g_handler != NULL) {
        g_handler(body, body_len);
    }
}
