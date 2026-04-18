/**
 * @file test_board_temp.c
 * @brief Unit tests for the Tboard facade.
 *
 * Strategy
 * --------
 * The BoardTemp module sits on top of the TMP117 driver. Rather
 * than link the real TMP117 — which in SIMULATION_MODE always
 * returns a constant 21.375 °C and gives us no control over
 * failure paths — this test supplies its own *strong* definitions
 * of TMP117_Init and TMP117_Read. They override the symbols from
 * tmp117.c at link time, so board_temp.c sees exactly the values
 * the test chooses.
 *
 * Test matrix
 * -----------
 *   1. Before the first Update, GetC returns 0 / invalid and
 *      GetScaled0p1 returns 0.
 *   2. A single successful Update populates the cache; GetC and
 *      GetScaled0p1 match expectations across nominal (25 °C) and
 *      extreme-cold (-40 °C) inputs.
 *   3. A bus failure on Update preserves the last good value.
 *   4. An out-of-range sensor reading is rejected and does not
 *      overwrite the cache.
 */

#include "unity/unity.h"
#include "board_temp.h"
#include "tmp117.h"
#include <stdint.h>

/* --- strong overrides of the TMP117 API --------------------------
 *
 * These replace the same-name weak symbols in tmp117.c (not linked
 * in this test target). The test drives the "sensor" via g_next_c
 * and g_read_fail.
 * ----------------------------------------------------------------- */
static float g_next_c    = 0.0f;
static int   g_read_fail = 0;
static int   g_init_fail = 0;

TMP117_Status_t TMP117_Init(TMP117_Handle_t *dev)
{
    (void)dev;
    return g_init_fail ? TMP117_ERR_I2C : TMP117_OK;
}

TMP117_Status_t TMP117_Read(TMP117_Handle_t *dev, float *temp)
{
    (void)dev;
    if (g_read_fail || temp == NULL) { return TMP117_ERR_I2C; }
    *temp = g_next_c;
    return TMP117_OK;
}

/* Silence unused-symbol warnings for the rest of the TMP117 API —
 * BoardTemp never calls them, but the linker may still look. */
TMP117_Status_t TMP117_SelfTest(TMP117_Handle_t *dev) { (void)dev; return TMP117_OK; }


void setUp(void)
{
    g_next_c    = 0.0f;
    g_read_fail = 0;
    g_init_fail = 0;
    (void)BoardTemp_Init();
}
void tearDown(void) { /* nothing */ }


void test_uninitialised_returns_zero_and_invalid(void)
{
    setUp();
    /* Fresh setUp calls Init but no Update yet. */
    bool v = true;
    float c = BoardTemp_GetC(&v);
    TEST_ASSERT_EQUAL(0, (int)(c * 1000.0f));
    TEST_ASSERT_FALSE(v);
    TEST_ASSERT_EQUAL(0, BoardTemp_GetScaled0p1());
}

void test_nominal_reading(void)
{
    setUp();
    g_next_c = 25.0f;
    TEST_ASSERT_TRUE(BoardTemp_Update());

    bool v = false;
    float c = BoardTemp_GetC(&v);
    TEST_ASSERT_TRUE(v);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 25.0f, c);
    TEST_ASSERT_EQUAL(250, BoardTemp_GetScaled0p1());
}

void test_extreme_cold_reading(void)
{
    setUp();
    g_next_c = -40.0f;
    TEST_ASSERT_TRUE(BoardTemp_Update());

    bool v;
    float c = BoardTemp_GetC(&v);
    TEST_ASSERT_TRUE(v);
    TEST_ASSERT_FLOAT_WITHIN(0.1f, -40.0f, c);
    TEST_ASSERT_EQUAL(-400, BoardTemp_GetScaled0p1());
}

void test_fractional_rounding(void)
{
    setUp();
    /* 15.05 °C * 10 = 150.5 -> 151 (round-away-from-zero). */
    g_next_c = 15.05f;
    TEST_ASSERT_TRUE(BoardTemp_Update());
    TEST_ASSERT_EQUAL(151, BoardTemp_GetScaled0p1());

    /* -0.05 °C -> -0.5 -> -1. */
    g_next_c = -0.05f;
    TEST_ASSERT_TRUE(BoardTemp_Update());
    TEST_ASSERT_EQUAL(-1, BoardTemp_GetScaled0p1());
}

void test_read_failure_preserves_last_good(void)
{
    setUp();
    g_next_c = 15.0f;
    TEST_ASSERT_TRUE(BoardTemp_Update());
    int16_t before = BoardTemp_GetScaled0p1();
    TEST_ASSERT_EQUAL(150, before);

    g_read_fail = 1;
    TEST_ASSERT_FALSE(BoardTemp_Update());

    bool v;
    float c = BoardTemp_GetC(&v);
    TEST_ASSERT_TRUE(v);
    TEST_ASSERT_FLOAT_WITHIN(0.1f, 15.0f, c);
    TEST_ASSERT_EQUAL(150, BoardTemp_GetScaled0p1());
}

void test_out_of_range_rejected(void)
{
    setUp();
    /* +200 °C — outside datasheet range. Update returns false and
     * cache stays uninitialised because we never had a good reading. */
    g_next_c = 200.0f;
    TEST_ASSERT_FALSE(BoardTemp_Update());

    bool v = true;
    (void)BoardTemp_GetC(&v);
    TEST_ASSERT_FALSE(v);
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_uninitialised_returns_zero_and_invalid);
    RUN_TEST(test_nominal_reading);
    RUN_TEST(test_extreme_cold_reading);
    RUN_TEST(test_fractional_rounding);
    RUN_TEST(test_read_failure_preserves_last_good);
    RUN_TEST(test_out_of_range_rejected);
    return UNITY_END();
}
