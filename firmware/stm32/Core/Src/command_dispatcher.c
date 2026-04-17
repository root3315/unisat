/**
 * @file command_dispatcher.c
 * @brief HMAC-authenticated CCSDS command dispatcher (Track 1b).
 *
 * Provides the strong definition of CCSDS_Dispatcher_Submit that
 * overrides the weak no-op in comm.c. Wire format received from the
 * streaming decoder:
 *
 *     [ CCSDS Space Packet (header + payload) ][ HMAC tag 32 B ]
 *
 * We recompute the tag over the CCSDS-packet bytes, compare it in
 * constant time, and drop the frame silently on mismatch. No reply
 * is sent — an attacker cannot distinguish a dropped spoof from a
 * lost real command.
 */

#include "command_dispatcher.h"
#include "hmac_sha256.h"
#include <string.h>

static uint8_t g_key[64];
static size_t  g_key_len = 0;
static CommandHandler_t g_handler = NULL;
static CommandDispatcher_Stats_t g_stats = {0};

void CommandDispatcher_SetKey(const uint8_t *key, size_t key_len) {
    if (key == NULL || key_len == 0 || key_len > sizeof(g_key)) {
        g_key_len = 0;
        return;
    }
    memcpy(g_key, key, key_len);
    g_key_len = key_len;
}

void CommandDispatcher_SetHandler(CommandHandler_t handler) {
    g_handler = handler;
}

CommandDispatcher_Stats_t CommandDispatcher_GetStats(void) {
    return g_stats;
}

void CommandDispatcher_ResetStats(void) {
    memset(&g_stats, 0, sizeof(g_stats));
}

/* Strong definition — overrides the weak no-op in comm.c. */
void CCSDS_Dispatcher_Submit(const uint8_t *data, uint16_t len) {
    if (data == NULL || len < HMAC_SHA256_TAG_SIZE + 1) {
        g_stats.rejected_too_short++;
        return;
    }
    if (g_key_len == 0) {
        /* No key installed — refuse everything. */
        g_stats.rejected_bad_tag++;
        return;
    }

    uint16_t body_len = (uint16_t)(len - HMAC_SHA256_TAG_SIZE);
    const uint8_t *body = data;
    const uint8_t *tag  = &data[body_len];

    uint8_t expected[HMAC_SHA256_TAG_SIZE];
    hmac_sha256(g_key, g_key_len, body, body_len, expected);

    if (!hmac_sha256_verify(expected, tag)) {
        g_stats.rejected_bad_tag++;
        return;
    }

    g_stats.accepted++;
    if (g_handler != NULL) {
        g_handler(body, body_len);
    }
}
