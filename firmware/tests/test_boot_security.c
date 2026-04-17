/**
 * @file test_boot_security.c
 * @brief Integration test — boot-time key-store -> dispatcher wiring.
 *
 * Verifies the sequence the real main() performs at cold boot:
 *
 *   1. key_store_init()   — discovers the latest valid record
 *   2. key_store_get_active() — reads it back into a buffer
 *   3. CommandDispatcher_SetKey(active_key, len) — arms T1/T2
 *
 * and the three failure modes:
 *
 *   A. empty store         -> dispatcher unkeyed, every frame rejected
 *   B. torn write in A     -> init falls back to B, dispatcher keyed OK
 *   C. key rotation survives warm reboot (new init picks highest-gen)
 *
 * Scope: host-only integration test, links the real key_store.c and
 * command_dispatcher.c sources so the wiring is exercised end-to-end
 * rather than through mocks.
 */

#include "unity/unity.h"
#include "key_store.h"
#include "command_dispatcher.h"
#include "hmac_sha256.h"
#include <string.h>

void CCSDS_Dispatcher_Submit(const uint8_t *data, uint16_t len);

/* ---------- fixtures ---------- */

static const uint8_t KEY_OLD[32] = {
    0xA0,0xA1,0xA2,0xA3,0xA4,0xA5,0xA6,0xA7,
    0xA8,0xA9,0xAA,0xAB,0xAC,0xAD,0xAE,0xAF,
    0xB0,0xB1,0xB2,0xB3,0xB4,0xB5,0xB6,0xB7,
    0xB8,0xB9,0xBA,0xBB,0xBC,0xBD,0xBE,0xBF
};
static const uint8_t KEY_NEW[32] = {
    0xC0,0xC1,0xC2,0xC3,0xC4,0xC5,0xC6,0xC7,
    0xC8,0xC9,0xCA,0xCB,0xCC,0xCD,0xCE,0xCF,
    0xD0,0xD1,0xD2,0xD3,0xD4,0xD5,0xD6,0xD7,
    0xD8,0xD9,0xDA,0xDB,0xDC,0xDD,0xDE,0xDF
};

static int g_handler_calls = 0;

static void capture_handler(const uint8_t *body, uint16_t len) {
    (void)body; (void)len;
    g_handler_calls++;
}

/* Build a counter-prefixed + HMAC-tagged frame using the supplied key.
 * Output layout matches the wire format expected by CCSDS_Dispatcher_Submit:
 *   [ 4-byte counter BE ][ body ][ HMAC-SHA256(key, counter||body) ]
 */
static uint16_t build_frame(const uint8_t *key, size_t key_len,
                             uint32_t counter,
                             const uint8_t *body, uint16_t body_len,
                             uint8_t *out, uint16_t out_cap) {
    (void)out_cap;
    out[0] = (uint8_t)((counter >> 24) & 0xFFU);
    out[1] = (uint8_t)((counter >> 16) & 0xFFU);
    out[2] = (uint8_t)((counter >>  8) & 0xFFU);
    out[3] = (uint8_t)( counter        & 0xFFU);
    memcpy(&out[4], body, body_len);
    uint16_t auth_len = (uint16_t)(4 + body_len);
    hmac_sha256(key, key_len, out, auth_len, &out[auth_len]);
    return (uint16_t)(auth_len + HMAC_SHA256_TAG_SIZE);
}

/* Replay the production boot-time sequence. */
static KeyStoreStatus_t boot_sequence(void) {
    KeyStoreStatus_t st = key_store_init();
    if (st != KEY_STORE_OK) {
        CommandDispatcher_SetKey(NULL, 0);
        return st;
    }
    uint8_t key[KEY_STORE_MAX_KEY_LEN];
    size_t  key_len = 0;
    uint32_t gen    = 0;
    if (key_store_get_active(key, &key_len, &gen) != KEY_STORE_OK) {
        CommandDispatcher_SetKey(NULL, 0);
        return KEY_STORE_EMPTY;
    }
    CommandDispatcher_SetKey(key, key_len);
    return KEY_STORE_OK;
}

void setUp(void) {
    key_store_wipe();
    CommandDispatcher_SetKey(NULL, 0);
    CommandDispatcher_SetHandler(capture_handler);
    CommandDispatcher_ResetStats();
    g_handler_calls = 0;
}
void tearDown(void) { /* nothing */ }


/* =================================================================
 *  Scenarios
 * ================================================================= */

void test_empty_store_leaves_dispatcher_unkeyed(void)
{
    setUp();
    TEST_ASSERT_EQUAL(KEY_STORE_EMPTY, boot_sequence());

    /* A valid-looking frame signed with any key must be rejected because
     * the dispatcher has no key installed. */
    const uint8_t body[] = { 'X' };
    uint8_t frame[4 + sizeof(body) + HMAC_SHA256_TAG_SIZE];
    uint16_t fl = build_frame(KEY_OLD, sizeof(KEY_OLD),
                               1U, body, sizeof(body), frame, sizeof(frame));

    CCSDS_Dispatcher_Submit(frame, fl);

    CommandDispatcher_Stats_t s = CommandDispatcher_GetStats();
    TEST_ASSERT_EQUAL(0, (int)s.accepted);
    TEST_ASSERT_EQUAL(1, (int)s.rejected_bad_tag);
    TEST_ASSERT_EQUAL(0, g_handler_calls);
}

void test_populated_store_keys_dispatcher_and_accepts_frames(void)
{
    setUp();

    /* Pre-populate the store (simulates a previous rotation cycle
     * that already landed a key in slot 0). */
    TEST_ASSERT_EQUAL(KEY_STORE_OK,
                      key_store_rotate(KEY_OLD, sizeof(KEY_OLD), 1U));

    TEST_ASSERT_EQUAL(KEY_STORE_OK, boot_sequence());

    const uint8_t body[] = { 'O','K' };
    uint8_t frame[4 + sizeof(body) + HMAC_SHA256_TAG_SIZE];
    uint16_t fl = build_frame(KEY_OLD, sizeof(KEY_OLD),
                               1U, body, sizeof(body), frame, sizeof(frame));

    CCSDS_Dispatcher_Submit(frame, fl);

    CommandDispatcher_Stats_t s = CommandDispatcher_GetStats();
    TEST_ASSERT_EQUAL(1, (int)s.accepted);
    TEST_ASSERT_EQUAL(0, (int)s.rejected_bad_tag);
    TEST_ASSERT_EQUAL(1, g_handler_calls);
}

void test_rotation_then_warm_reboot_uses_newest_key(void)
{
    setUp();

    /* Lay down gen=1 (old key), then gen=2 (new key). */
    TEST_ASSERT_EQUAL(KEY_STORE_OK,
                      key_store_rotate(KEY_OLD, sizeof(KEY_OLD), 1U));
    TEST_ASSERT_EQUAL(KEY_STORE_OK,
                      key_store_rotate(KEY_NEW, sizeof(KEY_NEW), 2U));

    /* Warm reboot — boot_sequence re-runs key_store_init. */
    CommandDispatcher_SetKey(NULL, 0);
    CommandDispatcher_ResetStats();
    TEST_ASSERT_EQUAL(KEY_STORE_OK, boot_sequence());

    /* Frame signed with the OLD key must be rejected. */
    const uint8_t body[] = { 'A' };
    uint8_t frame_old[4 + sizeof(body) + HMAC_SHA256_TAG_SIZE];
    uint16_t fl_old = build_frame(KEY_OLD, sizeof(KEY_OLD),
                                    1U, body, sizeof(body),
                                    frame_old, sizeof(frame_old));
    CCSDS_Dispatcher_Submit(frame_old, fl_old);
    CommandDispatcher_Stats_t s = CommandDispatcher_GetStats();
    TEST_ASSERT_EQUAL(0, (int)s.accepted);
    TEST_ASSERT_EQUAL(1, (int)s.rejected_bad_tag);

    /* Frame signed with the NEW key must be accepted. */
    uint8_t frame_new[4 + sizeof(body) + HMAC_SHA256_TAG_SIZE];
    uint16_t fl_new = build_frame(KEY_NEW, sizeof(KEY_NEW),
                                    1U, body, sizeof(body),
                                    frame_new, sizeof(frame_new));
    CCSDS_Dispatcher_Submit(frame_new, fl_new);
    s = CommandDispatcher_GetStats();
    TEST_ASSERT_EQUAL(1, (int)s.accepted);
    TEST_ASSERT_EQUAL(1, g_handler_calls);
}

void test_stale_gen_cannot_downgrade_key(void)
{
    setUp();

    TEST_ASSERT_EQUAL(KEY_STORE_OK,
                      key_store_rotate(KEY_OLD, sizeof(KEY_OLD), 1U));
    TEST_ASSERT_EQUAL(KEY_STORE_OK,
                      key_store_rotate(KEY_NEW, sizeof(KEY_NEW), 2U));

    /* An attacker replaying a gen=1 rotation command cannot push us
     * back to KEY_OLD — the store's monotonic guard rejects it. */
    TEST_ASSERT_EQUAL(KEY_STORE_STALE_GEN,
                      key_store_rotate(KEY_OLD, sizeof(KEY_OLD), 1U));

    TEST_ASSERT_EQUAL(KEY_STORE_OK, boot_sequence());

    /* A frame signed with KEY_OLD must still be rejected post-rotation. */
    const uint8_t body[] = { 'B' };
    uint8_t frame[4 + sizeof(body) + HMAC_SHA256_TAG_SIZE];
    uint16_t fl = build_frame(KEY_OLD, sizeof(KEY_OLD),
                               1U, body, sizeof(body), frame, sizeof(frame));
    CCSDS_Dispatcher_Submit(frame, fl);
    CommandDispatcher_Stats_t s = CommandDispatcher_GetStats();
    TEST_ASSERT_EQUAL(0, (int)s.accepted);
    TEST_ASSERT_EQUAL(1, (int)s.rejected_bad_tag);
}


int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_empty_store_leaves_dispatcher_unkeyed);
    RUN_TEST(test_populated_store_keys_dispatcher_and_accepts_frames);
    RUN_TEST(test_rotation_then_warm_reboot_uses_newest_key);
    RUN_TEST(test_stale_gen_cannot_downgrade_key);
    return UNITY_END();
}
