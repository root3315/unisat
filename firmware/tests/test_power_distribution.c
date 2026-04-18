/**
 * @file test_power_distribution.c
 * @brief PDU load-shedding + channel-control tests (Phase 7 follow-up).
 *
 * power_distribution.c was the last module with zero tests after the
 * Phase 5 coverage push. It drives one of the safety-critical
 * behaviours (priority-ordered load shedding) that keeps the
 * satellite alive under an eclipse-induced power brownout, so
 * leaving it untested was the highest-impact gap in the coverage
 * audit.
 *
 * Scenarios covered
 * -----------------
 *   1. PDU_Init defaults — 4 essential channels enabled, 4 optional
 *      disabled, priorities match the static table.
 *   2. PDU_EnableChannel / DisableChannel happy path.
 *   3. PDU_DisableChannel refuses to disable OBC (channel 0).
 *   4. Out-of-range channel index is ignored (no crash, no state change).
 *   5. PDU_SetPriority mutates the priority; range-check respected.
 *   6. PDU_LoadShed does nothing when demand <= available.
 *   7. PDU_LoadShed sheds lowest-priority channels first.
 *   8. PDU_LoadShed never disables OBC even under extreme shortage.
 *   9. PDU_Update computes total_current / total_power from enabled
 *      channels' current_draw_a.
 *
 * Host-only; links the real power_distribution.c.
 */

#include "unity/unity.h"
#include "../stm32/EPS/power_distribution.h"
#include <string.h>

void setUp(void)    { PDU_Init(); }
void tearDown(void) { /* nothing */ }


/* ------------------------------------------------------------------
 *  1. Init defaults
 * ------------------------------------------------------------------ */
void test_init_default_channel_layout(void)
{
    setUp();
    PDU_Status_t s = PDU_GetStatus();

    /* Four "essential" channels enabled (OBC / UHF / ADCS / GNSS),
     * four "optional" disabled (CAMERA / PAYLOAD / HEATER / SBAND). */
    for (uint8_t i = 0; i < 4; i++) {
        TEST_ASSERT_TRUE(s.channels[i].enabled);
    }
    for (uint8_t i = 4; i < PDU_MAX_CHANNELS; i++) {
        TEST_ASSERT_FALSE(s.channels[i].enabled);
    }

    /* Priorities non-zero on every channel (OBC highest, SBAND lowest). */
    TEST_ASSERT_EQUAL(10, s.channels[0].priority);  /* OBC */
    TEST_ASSERT_EQUAL( 2, s.channels[7].priority);  /* SBAND */
}


/* ------------------------------------------------------------------
 *  2. Enable / Disable happy path
 * ------------------------------------------------------------------ */
void test_enable_then_disable_channel(void)
{
    setUp();
    /* Channel 4 (CAMERA) starts disabled. */
    TEST_ASSERT_FALSE(PDU_GetStatus().channels[4].enabled);

    PDU_EnableChannel(4);
    TEST_ASSERT_TRUE(PDU_GetStatus().channels[4].enabled);

    PDU_DisableChannel(4);
    TEST_ASSERT_FALSE(PDU_GetStatus().channels[4].enabled);
}


/* ------------------------------------------------------------------
 *  3. OBC is un-disable-able
 * ------------------------------------------------------------------ */
void test_obc_cannot_be_disabled(void)
{
    setUp();
    TEST_ASSERT_TRUE(PDU_GetStatus().channels[0].enabled);
    PDU_DisableChannel(0);
    TEST_ASSERT_TRUE(PDU_GetStatus().channels[0].enabled);  /* still on */
}


/* ------------------------------------------------------------------
 *  4. Out-of-range channel index is a no-op
 * ------------------------------------------------------------------ */
void test_out_of_range_channel_noop(void)
{
    setUp();
    /* Capture state, perform no-op calls, compare bytewise. */
    PDU_Status_t before = PDU_GetStatus();
    PDU_EnableChannel(99);
    PDU_DisableChannel(99);
    PDU_SetPriority(99, 255);
    PDU_Status_t after = PDU_GetStatus();
    TEST_ASSERT_EQUAL_MEMORY(&before, &after, sizeof(before));
}


/* ------------------------------------------------------------------
 *  5. SetPriority mutates the per-channel value
 * ------------------------------------------------------------------ */
void test_set_priority_updates_channel(void)
{
    setUp();
    uint8_t before = PDU_GetStatus().channels[5].priority;
    PDU_SetPriority(5, 99);
    TEST_ASSERT_NOT_EQUAL(before, PDU_GetStatus().channels[5].priority);
    TEST_ASSERT_EQUAL(99, PDU_GetStatus().channels[5].priority);
}


/* ------------------------------------------------------------------
 *  6. LoadShed leaves state alone when demand fits available power
 * ------------------------------------------------------------------ */
void test_load_shed_no_op_when_power_sufficient(void)
{
    setUp();
    PDU_Status_t before = PDU_GetStatus();

    /* 100 W at 5 V = 20 A, far above any nominal demand. */
    PDU_LoadShed(100.0f);

    PDU_Status_t after = PDU_GetStatus();
    /* Every channel's enable bit identical. */
    for (uint8_t i = 0; i < PDU_MAX_CHANNELS; i++) {
        TEST_ASSERT_EQUAL(before.channels[i].enabled,
                          after.channels[i].enabled);
    }
}


/* ------------------------------------------------------------------
 *  7. LoadShed drops lowest-priority channels first
 * ------------------------------------------------------------------ */
void test_load_shed_drops_lowest_priority_first(void)
{
    setUp();
    /* Enable everything — demand now exceeds what any modest
     * brownout budget can cover. */
    for (uint8_t i = 0; i < PDU_MAX_CHANNELS; i++) {
        PDU_EnableChannel(i);
    }

    /* Shed at 1 W (0.2 A at 5 V). Only the highest-priority loads
     * should survive, OBC guaranteed. */
    PDU_LoadShed(1.0f);
    PDU_Status_t s = PDU_GetStatus();

    TEST_ASSERT_TRUE(s.channels[0].enabled);   /* OBC always */
    /* SBAND (priority 2) and CAMERA (priority 3) are the lowest —
     * must be shed first. */
    TEST_ASSERT_FALSE(s.channels[7].enabled);  /* SBAND */
    TEST_ASSERT_FALSE(s.channels[4].enabled);  /* CAMERA */
}


/* ------------------------------------------------------------------
 *  8. Even under zero power, OBC stays up
 * ------------------------------------------------------------------ */
void test_load_shed_never_disables_obc(void)
{
    setUp();
    for (uint8_t i = 0; i < PDU_MAX_CHANNELS; i++) {
        PDU_EnableChannel(i);
    }
    PDU_LoadShed(0.001f);  /* 0.2 mA budget */
    TEST_ASSERT_TRUE(PDU_GetStatus().channels[0].enabled);
}


/* ------------------------------------------------------------------
 *  9. Update recomputes aggregate counters from per-channel draw
 * ------------------------------------------------------------------ */
void test_update_computes_aggregate_totals(void)
{
    setUp();
    /* PDU_Status_t is returned by value so we cannot inject non-zero
     * current_draw_a values from the test; verify instead that
     * PDU_Update produces the expected zero-draw tally on a freshly-
     * initialised PDU (every current_draw_a is 0 by Init's memset).
     * The counter-incrementing path on active_channels is the main
     * branch exercised here. */
    PDU_Update();
    PDU_Status_t after = PDU_GetStatus();

    TEST_ASSERT_EQUAL(4U, after.active_channels);   /* 4 essentials */
    TEST_ASSERT_TRUE(after.total_current <= 0.0001f);
    TEST_ASSERT_TRUE(after.total_power   <= 0.0001f);

    /* Enable a fifth channel and confirm active_channels bumps to 5. */
    PDU_EnableChannel(4);
    PDU_Update();
    TEST_ASSERT_EQUAL(5U, PDU_GetStatus().active_channels);
}


int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_init_default_channel_layout);
    RUN_TEST(test_enable_then_disable_channel);
    RUN_TEST(test_obc_cannot_be_disabled);
    RUN_TEST(test_out_of_range_channel_noop);
    RUN_TEST(test_set_priority_updates_channel);
    RUN_TEST(test_load_shed_no_op_when_power_sufficient);
    RUN_TEST(test_load_shed_drops_lowest_priority_first);
    RUN_TEST(test_load_shed_never_disables_obc);
    RUN_TEST(test_update_computes_aggregate_totals);
    return UNITY_END();
}
