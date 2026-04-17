/**
 * @file test_command_dispatcher.c
 * @brief Dispatcher HMAC + anti-replay tests (Track 1b, Phase 2).
 *
 * Wire format exercised here:
 *     [ 4-byte counter BE ][ body ][ HMAC tag 32 B ]
 *
 * Coverage:
 *   Authentication (T1):
 *     1. valid counter + valid tag            -> accepted, handler fired
 *     2. valid counter, tampered tag          -> rejected_bad_tag
 *     3. frame shorter than counter+1+tag     -> rejected_too_short
 *     4. key not installed                    -> every frame rejected
 *
 *   Replay window (T2):
 *     5. same counter delivered twice         -> 2nd frame replay
 *     6. monotonic counters 1..N accepted
 *     7. out-of-order within window accepted once, duplicate replayed
 *     8. counter older than window dropped
 *     9. counter == 0 refused (reserved sentinel)
 *    10. rekey resets the window (same counter reusable afterwards)
 *    11. ResetReplayWindow() behaves like rekey for the counter state
 */

#include "unity/unity.h"
#include "command_dispatcher.h"
#include "hmac_sha256.h"
#include <string.h>

/* Forward declaration of the strong symbol under test. */
void CCSDS_Dispatcher_Submit(const uint8_t *data, uint16_t len);

/* ---------- test-local mock handler ---------- */
static uint8_t  g_captured[256];
static uint16_t g_captured_len;
static int      g_handler_calls;

static void test_handler(const uint8_t *data, uint16_t len)
{
    if (len > sizeof(g_captured)) { len = sizeof(g_captured); }
    memcpy(g_captured, data, len);
    g_captured_len = len;
    g_handler_calls++;
}

static const uint8_t KEY[32] = {
    0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,
    0x09,0x0A,0x0B,0x0C,0x0D,0x0E,0x0F,0x10,
    0x11,0x12,0x13,0x14,0x15,0x16,0x17,0x18,
    0x19,0x1A,0x1B,0x1C,0x1D,0x1E,0x1F,0x20,
};

/* ---------- helpers ---------- */

/* Build an authenticated frame:
 *   out = [counter BE][body][HMAC-SHA256(key, counter||body)]
 * Caller must ensure out_cap >= 4 + body_len + 32.
 * Returns total frame length. */
static uint16_t build_frame(uint32_t counter,
                            const uint8_t *body, uint16_t body_len,
                            uint8_t *out, uint16_t out_cap)
{
    (void)out_cap;
    out[0] = (uint8_t)((counter >> 24) & 0xFFU);
    out[1] = (uint8_t)((counter >> 16) & 0xFFU);
    out[2] = (uint8_t)((counter >>  8) & 0xFFU);
    out[3] = (uint8_t)( counter        & 0xFFU);
    memcpy(&out[4], body, body_len);
    uint16_t auth_len = (uint16_t)(4 + body_len);
    hmac_sha256(KEY, sizeof(KEY), out, auth_len, &out[auth_len]);
    return (uint16_t)(auth_len + HMAC_SHA256_TAG_SIZE);
}

void setUp(void)
{
    CommandDispatcher_SetKey(KEY, sizeof(KEY));
    CommandDispatcher_SetHandler(test_handler);
    CommandDispatcher_ResetStats();
    memset(g_captured, 0, sizeof(g_captured));
    g_captured_len = 0;
    g_handler_calls = 0;
}
void tearDown(void) { /* nothing */ }


/* =================================================================
 *  Authentication tests (T1)
 * ================================================================= */

void test_valid_counter_and_tag_dispatches(void)
{
    setUp();
    const uint8_t body[] = { 'H','e','l','l','o' };
    uint8_t frame[4 + sizeof(body) + HMAC_SHA256_TAG_SIZE];
    uint16_t fl = build_frame(1U, body, sizeof(body), frame, sizeof(frame));

    CCSDS_Dispatcher_Submit(frame, fl);

    CommandDispatcher_Stats_t s = CommandDispatcher_GetStats();
    TEST_ASSERT_EQUAL(1, (int)s.accepted);
    TEST_ASSERT_EQUAL(0, (int)s.rejected_bad_tag);
    TEST_ASSERT_EQUAL(0, (int)s.rejected_replay);
    TEST_ASSERT_EQUAL(1U, s.highest_counter);
    TEST_ASSERT_EQUAL(1, g_handler_calls);
    TEST_ASSERT_EQUAL_MEMORY(body, g_captured, sizeof(body));
}

void test_tampered_tag_rejected(void)
{
    setUp();
    const uint8_t body[] = { 'H','i' };
    uint8_t frame[4 + sizeof(body) + HMAC_SHA256_TAG_SIZE];
    uint16_t fl = build_frame(1U, body, sizeof(body), frame, sizeof(frame));
    frame[fl - 1] ^= 0xFFU;                  /* flip last tag byte */

    CCSDS_Dispatcher_Submit(frame, fl);

    CommandDispatcher_Stats_t s = CommandDispatcher_GetStats();
    TEST_ASSERT_EQUAL(0, (int)s.accepted);
    TEST_ASSERT_EQUAL(1, (int)s.rejected_bad_tag);
    TEST_ASSERT_EQUAL(0, g_handler_calls);
}

void test_too_short_rejected(void)
{
    setUp();
    uint8_t tiny[36] = { 0 };                 /* one byte below minimum */
    CCSDS_Dispatcher_Submit(tiny, sizeof(tiny));
    CommandDispatcher_Stats_t s = CommandDispatcher_GetStats();
    TEST_ASSERT_EQUAL(1, (int)s.rejected_too_short);
    TEST_ASSERT_EQUAL(0, g_handler_calls);
}

void test_no_key_rejects_everything(void)
{
    setUp();
    CommandDispatcher_SetKey(NULL, 0);

    const uint8_t body[] = { 'X' };
    uint8_t frame[4 + sizeof(body) + HMAC_SHA256_TAG_SIZE] = { 0 };
    frame[3] = 1U;                            /* counter = 1 */
    memcpy(&frame[4], body, sizeof(body));
    /* tag bytes left zero — meaningless, length only */

    CCSDS_Dispatcher_Submit(frame, (uint16_t)sizeof(frame));

    CommandDispatcher_Stats_t s = CommandDispatcher_GetStats();
    TEST_ASSERT_EQUAL(0, (int)s.accepted);
    TEST_ASSERT_EQUAL(1, (int)s.rejected_bad_tag);
    TEST_ASSERT_EQUAL(0, g_handler_calls);
}


/* =================================================================
 *  Replay-window tests (T2)
 * ================================================================= */

void test_duplicate_counter_is_replay(void)
{
    setUp();
    const uint8_t body[] = { 'A','B','C' };
    uint8_t frame[4 + sizeof(body) + HMAC_SHA256_TAG_SIZE];
    uint16_t fl = build_frame(42U, body, sizeof(body), frame, sizeof(frame));

    CCSDS_Dispatcher_Submit(frame, fl);          /* first delivery  */
    CCSDS_Dispatcher_Submit(frame, fl);          /* exact replay    */

    CommandDispatcher_Stats_t s = CommandDispatcher_GetStats();
    TEST_ASSERT_EQUAL(1, (int)s.accepted);
    TEST_ASSERT_EQUAL(1, (int)s.rejected_replay);
    TEST_ASSERT_EQUAL(1, g_handler_calls);
}

void test_monotonic_counters_accepted(void)
{
    setUp();
    const uint8_t body[] = { 'x' };
    for (uint32_t c = 1; c <= 100; ++c) {
        uint8_t frame[4 + sizeof(body) + HMAC_SHA256_TAG_SIZE];
        uint16_t fl = build_frame(c, body, sizeof(body), frame, sizeof(frame));
        CCSDS_Dispatcher_Submit(frame, fl);
    }
    CommandDispatcher_Stats_t s = CommandDispatcher_GetStats();
    TEST_ASSERT_EQUAL(100, (int)s.accepted);
    TEST_ASSERT_EQUAL(0,   (int)s.rejected_replay);
    TEST_ASSERT_EQUAL(100U, s.highest_counter);
}

void test_out_of_order_within_window_accepted_once(void)
{
    setUp();
    const uint8_t body[] = { 'y' };
    uint8_t frame[4 + sizeof(body) + HMAC_SHA256_TAG_SIZE];

    /* Take highest_counter to 10 first. */
    for (uint32_t c = 1; c <= 10; ++c) {
        uint16_t fl = build_frame(c, body, sizeof(body), frame, sizeof(frame));
        CCSDS_Dispatcher_Submit(frame, fl);
    }

    /* Now deliver counter = 5 (inside window, already seen). */
    uint16_t fl5 = build_frame(5U, body, sizeof(body), frame, sizeof(frame));
    CCSDS_Dispatcher_Submit(frame, fl5);

    CommandDispatcher_Stats_t s = CommandDispatcher_GetStats();
    TEST_ASSERT_EQUAL(10, (int)s.accepted);
    TEST_ASSERT_EQUAL(1,  (int)s.rejected_replay);

    /* And a counter we skipped on purpose — e.g. we jump from 10 to
     * 12, then later backfill 11: must be accepted exactly once. */
    uint16_t fl12 = build_frame(12U, body, sizeof(body), frame, sizeof(frame));
    CCSDS_Dispatcher_Submit(frame, fl12);
    uint16_t fl11 = build_frame(11U, body, sizeof(body), frame, sizeof(frame));
    CCSDS_Dispatcher_Submit(frame, fl11);       /* first time for 11 */
    CCSDS_Dispatcher_Submit(frame, fl11);       /* duplicate         */

    s = CommandDispatcher_GetStats();
    TEST_ASSERT_EQUAL(12, (int)s.accepted);
    TEST_ASSERT_EQUAL(2,  (int)s.rejected_replay);
    TEST_ASSERT_EQUAL(12U, s.highest_counter);
}

void test_counter_older_than_window_dropped(void)
{
    setUp();
    const uint8_t body[] = { 'z' };

    /* Each submission gets its own backing buffer so build_frame does
     * not overwrite an in-flight frame's bytes. */
    uint8_t f200[4 + sizeof(body) + HMAC_SHA256_TAG_SIZE];
    uint8_t f100[4 + sizeof(body) + HMAC_SHA256_TAG_SIZE];
    uint8_t f137[4 + sizeof(body) + HMAC_SHA256_TAG_SIZE];
    uint8_t f136[4 + sizeof(body) + HMAC_SHA256_TAG_SIZE];

    uint16_t L200 = build_frame(200U, body, sizeof(body), f200, sizeof(f200));
    uint16_t L100 = build_frame(100U, body, sizeof(body), f100, sizeof(f100));
    uint16_t L137 = build_frame(137U, body, sizeof(body), f137, sizeof(f137));
    uint16_t L136 = build_frame(136U, body, sizeof(body), f136, sizeof(f136));

    /* Advance highest_counter to 200. */
    CCSDS_Dispatcher_Submit(f200, L200);

    /* 100 is 100 ticks behind 200 → outside the 64-wide window → rejected. */
    CCSDS_Dispatcher_Submit(f100, L100);

    /* 137 is 63 ticks behind 200 → inside window, fresh → accepted.
     * 136 is 64 ticks behind → exactly at the boundary, rejected. */
    CCSDS_Dispatcher_Submit(f137, L137);
    CCSDS_Dispatcher_Submit(f136, L136);

    CommandDispatcher_Stats_t s = CommandDispatcher_GetStats();
    TEST_ASSERT_EQUAL(2, (int)s.accepted);           /* 200, 137 */
    TEST_ASSERT_EQUAL(2, (int)s.rejected_replay);    /* 100, 136 */
    TEST_ASSERT_EQUAL(200U, s.highest_counter);
}

void test_counter_zero_rejected(void)
{
    setUp();
    const uint8_t body[] = { 'q' };
    uint8_t frame[4 + sizeof(body) + HMAC_SHA256_TAG_SIZE];
    uint16_t fl = build_frame(0U, body, sizeof(body), frame, sizeof(frame));

    CCSDS_Dispatcher_Submit(frame, fl);

    CommandDispatcher_Stats_t s = CommandDispatcher_GetStats();
    TEST_ASSERT_EQUAL(0, (int)s.accepted);
    TEST_ASSERT_EQUAL(1, (int)s.rejected_replay);
    TEST_ASSERT_EQUAL(0U, s.highest_counter);
}

void test_rekey_resets_window(void)
{
    setUp();
    const uint8_t body[] = { 'r' };
    uint8_t frame[4 + sizeof(body) + HMAC_SHA256_TAG_SIZE];

    uint16_t fl = build_frame(50U, body, sizeof(body), frame, sizeof(frame));
    CCSDS_Dispatcher_Submit(frame, fl);

    /* Reinstall the same key — new epoch, window reset. */
    CommandDispatcher_SetKey(KEY, sizeof(KEY));
    CommandDispatcher_ResetStats();

    /* Counter 50 should now be accepted again (fresh epoch). */
    fl = build_frame(50U, body, sizeof(body), frame, sizeof(frame));
    CCSDS_Dispatcher_Submit(frame, fl);

    CommandDispatcher_Stats_t s = CommandDispatcher_GetStats();
    TEST_ASSERT_EQUAL(1, (int)s.accepted);
    TEST_ASSERT_EQUAL(0, (int)s.rejected_replay);
    TEST_ASSERT_EQUAL(50U, s.highest_counter);
}

void test_reset_replay_window_behaves_like_rekey(void)
{
    setUp();
    const uint8_t body[] = { 's' };
    uint8_t frame[4 + sizeof(body) + HMAC_SHA256_TAG_SIZE];

    uint16_t fl = build_frame(99U, body, sizeof(body), frame, sizeof(frame));
    CCSDS_Dispatcher_Submit(frame, fl);
    CommandDispatcher_Stats_t s1 = CommandDispatcher_GetStats();
    TEST_ASSERT_EQUAL(99U, s1.highest_counter);

    CommandDispatcher_ResetReplayWindow();
    CommandDispatcher_ResetStats();

    CCSDS_Dispatcher_Submit(frame, fl);                /* 99 again */
    CommandDispatcher_Stats_t s2 = CommandDispatcher_GetStats();
    TEST_ASSERT_EQUAL(1, (int)s2.accepted);
    TEST_ASSERT_EQUAL(0, (int)s2.rejected_replay);
    TEST_ASSERT_EQUAL(99U, s2.highest_counter);
}


int main(void)
{
    UNITY_BEGIN();

    /* Authentication (T1) */
    RUN_TEST(test_valid_counter_and_tag_dispatches);
    RUN_TEST(test_tampered_tag_rejected);
    RUN_TEST(test_too_short_rejected);
    RUN_TEST(test_no_key_rejects_everything);

    /* Anti-replay (T2) */
    RUN_TEST(test_duplicate_counter_is_replay);
    RUN_TEST(test_monotonic_counters_accepted);
    RUN_TEST(test_out_of_order_within_window_accepted_once);
    RUN_TEST(test_counter_older_than_window_dropped);
    RUN_TEST(test_counter_zero_rejected);
    RUN_TEST(test_rekey_resets_window);
    RUN_TEST(test_reset_replay_window_behaves_like_rekey);

    return UNITY_END();
}
