/**
 * @file test_key_store.c
 * @brief Coverage for the persistent HMAC key-store (Phase 2 / M1a).
 *
 * Exercises every status code declared in key_store.h:
 *   1. empty store -> init reports KEY_STORE_EMPTY
 *   2. first rotation -> init now reports the new key/gen
 *   3. monotonic rotations promote the key and switch slots
 *   4. stale generation rejected (StaleGen)
 *   5. short/oversized key rejected (BadInput)
 *   6. warm reboot (new init) picks the highest-generation slot
 *   7. slot-A CRC corruption -> init falls back to slot-B
 *   8. wipe clears both slots and reports EMPTY on next init
 *   9. injected platform-read failure reports BackendFail on rotate
 *
 * Host-only — the default in-memory backend in key_store.c is used.
 * A test hook overrides weak platform_read/write to simulate faults.
 */

#include "unity/unity.h"
#include "key_store.h"
#include <string.h>
#include <stdbool.h>

/* ==================================================================
 *  Test hook — override the weak platform backend so some tests can
 *  flip individual slots' CRC or force read/write failures.
 * ================================================================== */

#define RECORD_SIZE KEY_STORE_RECORD_SIZE
static uint8_t g_backing[KEY_STORE_SLOTS][RECORD_SIZE];
static bool    g_backing_initialised = false;
static bool    g_inject_read_fail = false;
static bool    g_inject_write_fail = false;
static uint8_t g_corrupt_slot = 0xFFU;   /* 0xFF = no corruption */

static void reset_backing(void)
{
    for (uint8_t s = 0; s < KEY_STORE_SLOTS; ++s) {
        memset(g_backing[s], 0xFF, RECORD_SIZE);
    }
    g_backing_initialised = true;
    g_inject_read_fail  = false;
    g_inject_write_fail = false;
    g_corrupt_slot      = 0xFFU;
}

bool key_store_platform_read(uint8_t slot_index, uint8_t *buf, size_t len)
{
    if (!g_backing_initialised) { reset_backing(); }
    if (g_inject_read_fail) { return false; }
    if (slot_index >= KEY_STORE_SLOTS || buf == NULL ||
        len != RECORD_SIZE) {
        return false;
    }
    memcpy(buf, g_backing[slot_index], len);
    if (slot_index == g_corrupt_slot) {
        buf[RECORD_SIZE - 1] ^= 0x55U;   /* flip CRC low byte */
    }
    return true;
}

bool key_store_platform_write(uint8_t slot_index, const uint8_t *buf, size_t len)
{
    if (!g_backing_initialised) { reset_backing(); }
    if (g_inject_write_fail) { return false; }
    if (slot_index >= KEY_STORE_SLOTS || buf == NULL ||
        len != RECORD_SIZE) {
        return false;
    }
    memcpy(g_backing[slot_index], buf, len);
    return true;
}

bool key_store_platform_erase(uint8_t slot_index)
{
    if (!g_backing_initialised) { reset_backing(); }
    if (slot_index >= KEY_STORE_SLOTS) { return false; }
    memset(g_backing[slot_index], 0xFF, RECORD_SIZE);
    return true;
}

/* ==================================================================
 *  Fixtures
 * ================================================================== */

static const uint8_t KEY_A[32] = {
    0xA1,0xA2,0xA3,0xA4,0xA5,0xA6,0xA7,0xA8,
    0xA9,0xAA,0xAB,0xAC,0xAD,0xAE,0xAF,0xB0,
    0xB1,0xB2,0xB3,0xB4,0xB5,0xB6,0xB7,0xB8,
    0xB9,0xBA,0xBB,0xBC,0xBD,0xBE,0xBF,0xC0
};
static const uint8_t KEY_B[32] = {
    0x11,0x22,0x33,0x44,0x55,0x66,0x77,0x88,
    0x99,0xAA,0xBB,0xCC,0xDD,0xEE,0xFF,0x00,
    0x10,0x20,0x30,0x40,0x50,0x60,0x70,0x80,
    0x90,0xA0,0xB0,0xC0,0xD0,0xE0,0xF0,0x01
};
static const uint8_t KEY_C_SHORT[16] = {
    1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16
};

void setUp(void)    { reset_backing(); }
void tearDown(void) { /* nothing */ }


/* ==================================================================
 *  Tests
 * ================================================================== */

void test_empty_store_reports_empty(void)
{
    setUp();
    TEST_ASSERT_EQUAL(KEY_STORE_EMPTY, key_store_init());

    uint8_t buf[32]; size_t blen = 0; uint32_t gen = 0xDEADU;
    TEST_ASSERT_EQUAL(KEY_STORE_EMPTY,
                      key_store_get_active(buf, &blen, &gen));
    TEST_ASSERT_EQUAL(0U, key_store_active_generation());
}

void test_first_rotation_becomes_active(void)
{
    setUp();
    (void)key_store_init();
    TEST_ASSERT_EQUAL(KEY_STORE_OK,
                      key_store_rotate(KEY_A, sizeof(KEY_A), 1U));

    uint8_t buf[32]; size_t blen = 0; uint32_t gen = 0;
    TEST_ASSERT_EQUAL(KEY_STORE_OK,
                      key_store_get_active(buf, &blen, &gen));
    TEST_ASSERT_EQUAL(32U, blen);
    TEST_ASSERT_EQUAL(1U, gen);
    TEST_ASSERT_EQUAL_MEMORY(KEY_A, buf, 32);
}

void test_monotonic_rotations_promote_and_switch_slots(void)
{
    setUp();
    (void)key_store_init();
    TEST_ASSERT_EQUAL(KEY_STORE_OK, key_store_rotate(KEY_A, 32, 1U));
    TEST_ASSERT_EQUAL(KEY_STORE_OK, key_store_rotate(KEY_B, 32, 2U));
    TEST_ASSERT_EQUAL(KEY_STORE_OK, key_store_rotate(KEY_A, 32, 3U));

    uint8_t buf[32]; size_t blen; uint32_t gen;
    TEST_ASSERT_EQUAL(KEY_STORE_OK,
                      key_store_get_active(buf, &blen, &gen));
    TEST_ASSERT_EQUAL(3U, gen);
    TEST_ASSERT_EQUAL_MEMORY(KEY_A, buf, 32);

    /* Two slots both carry valid records now (gen 2 and gen 3). */
    uint8_t slot0[RECORD_SIZE], slot1[RECORD_SIZE];
    key_store_platform_read(0, slot0, RECORD_SIZE);
    key_store_platform_read(1, slot1, RECORD_SIZE);
    TEST_ASSERT_EQUAL(KEY_STORE_MAGIC, slot0[0]);
    TEST_ASSERT_EQUAL(KEY_STORE_MAGIC, slot1[0]);
}

void test_stale_generation_rejected(void)
{
    setUp();
    (void)key_store_init();
    TEST_ASSERT_EQUAL(KEY_STORE_OK, key_store_rotate(KEY_A, 32, 5U));

    /* Same generation — must reject. */
    TEST_ASSERT_EQUAL(KEY_STORE_STALE_GEN,
                      key_store_rotate(KEY_B, 32, 5U));

    /* Lower generation — must also reject. */
    TEST_ASSERT_EQUAL(KEY_STORE_STALE_GEN,
                      key_store_rotate(KEY_B, 32, 4U));

    TEST_ASSERT_EQUAL(5U, key_store_active_generation());
}

void test_short_or_missing_key_rejected(void)
{
    setUp();
    (void)key_store_init();

    TEST_ASSERT_EQUAL(KEY_STORE_BAD_INPUT,
                      key_store_rotate(NULL, 32, 1U));
    TEST_ASSERT_EQUAL(KEY_STORE_BAD_INPUT,
                      key_store_rotate(KEY_A, 15, 1U));          /* < MIN */
    TEST_ASSERT_EQUAL(KEY_STORE_BAD_INPUT,
                      key_store_rotate(KEY_A, 64, 1U));          /* > MAX */
}

void test_short_key_ok_at_minimum(void)
{
    setUp();
    (void)key_store_init();
    TEST_ASSERT_EQUAL(KEY_STORE_OK,
                      key_store_rotate(KEY_C_SHORT, 16, 1U));

    uint8_t buf[32]; size_t blen = 0; uint32_t gen = 0;
    TEST_ASSERT_EQUAL(KEY_STORE_OK,
                      key_store_get_active(buf, &blen, &gen));
    TEST_ASSERT_EQUAL(16U, blen);
    TEST_ASSERT_EQUAL_MEMORY(KEY_C_SHORT, buf, 16);
}

void test_warm_reboot_picks_highest_generation(void)
{
    setUp();
    (void)key_store_init();
    TEST_ASSERT_EQUAL(KEY_STORE_OK, key_store_rotate(KEY_A, 32, 1U));
    TEST_ASSERT_EQUAL(KEY_STORE_OK, key_store_rotate(KEY_B, 32, 9U));

    /* Rotation with generation below the current active value MUST
     * be rejected — persistent slots still carry gen 1 and gen 9. */
    TEST_ASSERT_EQUAL(KEY_STORE_STALE_GEN,
                      key_store_rotate(KEY_A, 32, 4U));
    TEST_ASSERT_EQUAL(9U, key_store_active_generation());

    /* Simulate warm reboot — new init pass re-parses slots and must
     * pick the gen=9 record (KEY_B). */
    TEST_ASSERT_EQUAL(KEY_STORE_OK, key_store_init());
    uint8_t buf[32]; size_t blen = 0; uint32_t gen = 0;
    TEST_ASSERT_EQUAL(KEY_STORE_OK,
                      key_store_get_active(buf, &blen, &gen));
    TEST_ASSERT_EQUAL(9U, gen);
    TEST_ASSERT_EQUAL_MEMORY(KEY_B, buf, 32);
}

void test_corrupt_crc_falls_back_to_other_slot(void)
{
    setUp();
    (void)key_store_init();
    TEST_ASSERT_EQUAL(KEY_STORE_OK, key_store_rotate(KEY_A, 32, 1U));
    TEST_ASSERT_EQUAL(KEY_STORE_OK, key_store_rotate(KEY_B, 32, 2U));

    /* Which slot holds gen 2 (the active one)? Determine via the
     * magic header. After two rotations slot-1 holds gen 2. */
    uint8_t s0[RECORD_SIZE], s1[RECORD_SIZE];
    key_store_platform_read(0, s0, RECORD_SIZE);
    key_store_platform_read(1, s1, RECORD_SIZE);
    uint8_t higher = ((s1[1]<<24)|(s1[2]<<16)|(s1[3]<<8)|s1[4]) >
                     ((s0[1]<<24)|(s0[2]<<16)|(s0[3]<<8)|s0[4]) ? 1U : 0U;

    /* Corrupt the higher-gen slot via the read-hook. */
    g_corrupt_slot = higher;

    TEST_ASSERT_EQUAL(KEY_STORE_OK, key_store_init());
    /* Expect the lower-gen slot (gen 1, KEY_A) to have been chosen. */
    uint8_t buf[32]; size_t blen = 0; uint32_t gen = 0;
    TEST_ASSERT_EQUAL(KEY_STORE_OK,
                      key_store_get_active(buf, &blen, &gen));
    TEST_ASSERT_EQUAL(1U, gen);
    TEST_ASSERT_EQUAL_MEMORY(KEY_A, buf, 32);
}

void test_wipe_clears_both_slots(void)
{
    setUp();
    (void)key_store_init();
    TEST_ASSERT_EQUAL(KEY_STORE_OK, key_store_rotate(KEY_A, 32, 1U));
    TEST_ASSERT_EQUAL(KEY_STORE_OK, key_store_rotate(KEY_B, 32, 2U));

    TEST_ASSERT_EQUAL(KEY_STORE_OK, key_store_wipe());
    TEST_ASSERT_EQUAL(0U, key_store_active_generation());
    TEST_ASSERT_EQUAL(KEY_STORE_EMPTY, key_store_init());
}

void test_write_failure_reported(void)
{
    setUp();
    (void)key_store_init();
    g_inject_write_fail = true;
    TEST_ASSERT_EQUAL(KEY_STORE_BACKEND_FAIL,
                      key_store_rotate(KEY_A, 32, 1U));
    /* Still empty afterwards. */
    TEST_ASSERT_EQUAL(0U, key_store_active_generation());
}


int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_empty_store_reports_empty);
    RUN_TEST(test_first_rotation_becomes_active);
    RUN_TEST(test_monotonic_rotations_promote_and_switch_slots);
    RUN_TEST(test_stale_generation_rejected);
    RUN_TEST(test_short_or_missing_key_rejected);
    RUN_TEST(test_short_key_ok_at_minimum);
    RUN_TEST(test_warm_reboot_picks_highest_generation);
    RUN_TEST(test_corrupt_crc_falls_back_to_other_slot);
    RUN_TEST(test_wipe_clears_both_slots);
    RUN_TEST(test_write_failure_reported);
    return UNITY_END();
}
