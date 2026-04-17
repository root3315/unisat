/**
 * @file test_command_dispatcher.c
 * @brief Dispatcher HMAC verification tests (Track 1b).
 *
 * Exercises CCSDS_Dispatcher_Submit end-to-end:
 *   1. Valid tag  -> handler fired, accepted++.
 *   2. Wrong tag  -> handler NOT fired, rejected_bad_tag++.
 *   3. Too-short  -> handler NOT fired, rejected_too_short++.
 *   4. No key     -> every frame rejected.
 */

#include "unity/unity.h"
#include "command_dispatcher.h"
#include "hmac_sha256.h"
#include <string.h>

/* Forward declaration of the strong symbol under test. */
void CCSDS_Dispatcher_Submit(const uint8_t *data, uint16_t len);

static uint8_t  g_captured[256];
static uint16_t g_captured_len;
static int      g_handler_calls;

static void test_handler(const uint8_t *data, uint16_t len) {
    if (len > sizeof(g_captured)) len = sizeof(g_captured);
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

void setUp(void) {
    CommandDispatcher_SetKey(KEY, sizeof(KEY));
    CommandDispatcher_SetHandler(test_handler);
    CommandDispatcher_ResetStats();
    memset(g_captured, 0, sizeof(g_captured));
    g_captured_len = 0;
    g_handler_calls = 0;
}
void tearDown(void) {}

void test_valid_tag_dispatches(void) {
    setUp();
    const uint8_t body[] = { 'H', 'e', 'l', 'l', 'o' };
    uint8_t frame[sizeof(body) + HMAC_SHA256_TAG_SIZE];
    memcpy(frame, body, sizeof(body));
    hmac_sha256(KEY, sizeof(KEY), body, sizeof(body),
                &frame[sizeof(body)]);

    CCSDS_Dispatcher_Submit(frame, (uint16_t)sizeof(frame));

    CommandDispatcher_Stats_t s = CommandDispatcher_GetStats();
    TEST_ASSERT_EQUAL(1, (int)s.accepted);
    TEST_ASSERT_EQUAL(0, (int)s.rejected_bad_tag);
    TEST_ASSERT_EQUAL(1, g_handler_calls);
    TEST_ASSERT_EQUAL_MEMORY(body, g_captured, sizeof(body));
}

void test_wrong_tag_rejected(void) {
    setUp();
    const uint8_t body[] = { 'H', 'i' };
    uint8_t frame[sizeof(body) + HMAC_SHA256_TAG_SIZE];
    memcpy(frame, body, sizeof(body));
    hmac_sha256(KEY, sizeof(KEY), body, sizeof(body),
                &frame[sizeof(body)]);
    frame[sizeof(frame) - 1] ^= 0xFF;  /* tamper last byte of tag */

    CCSDS_Dispatcher_Submit(frame, (uint16_t)sizeof(frame));

    CommandDispatcher_Stats_t s = CommandDispatcher_GetStats();
    TEST_ASSERT_EQUAL(0, (int)s.accepted);
    TEST_ASSERT_EQUAL(1, (int)s.rejected_bad_tag);
    TEST_ASSERT_EQUAL(0, g_handler_calls);
}

void test_too_short_rejected(void) {
    setUp();
    uint8_t tiny[8] = { 0 };
    CCSDS_Dispatcher_Submit(tiny, sizeof(tiny));
    CommandDispatcher_Stats_t s = CommandDispatcher_GetStats();
    TEST_ASSERT_EQUAL(1, (int)s.rejected_too_short);
    TEST_ASSERT_EQUAL(0, g_handler_calls);
}

void test_no_key_rejects_everything(void) {
    setUp();
    CommandDispatcher_SetKey(NULL, 0);

    const uint8_t body[] = { 'X' };
    uint8_t frame[sizeof(body) + HMAC_SHA256_TAG_SIZE] = { 0 };
    memcpy(frame, body, sizeof(body));
    /* Include a (meaningless) tag so length check passes. */

    CCSDS_Dispatcher_Submit(frame, (uint16_t)sizeof(frame));

    CommandDispatcher_Stats_t s = CommandDispatcher_GetStats();
    TEST_ASSERT_EQUAL(0, (int)s.accepted);
    TEST_ASSERT_EQUAL(1, (int)s.rejected_bad_tag);
    TEST_ASSERT_EQUAL(0, g_handler_calls);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_valid_tag_dispatches);
    RUN_TEST(test_wrong_tag_rejected);
    RUN_TEST(test_too_short_rejected);
    RUN_TEST(test_no_key_rejects_everything);
    return UNITY_END();
}
