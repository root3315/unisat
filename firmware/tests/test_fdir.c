/**
 * @file test_fdir.c
 * @brief Unit tests for the FDIR subsystem (Phase 3).
 *
 * Exercises the whole advisory flow:
 *   1. Init + empty state
 *   2. Single Report -> primary action recommended
 *   3. Count threshold -> escalation action returned
 *   4. Cross-fault isolation: reporting fault-A does not affect B
 *   5. Recent-window sliding: stale events do NOT escalate
 *   6. ClearRecent resets to primary while preserving total_count
 *   7. ResetAll zeroes everything
 *   8. Out-of-range id doesn't crash, returns LOG_ONLY
 *   9. Stats counters track aggregate behaviour
 */

#include "unity/unity.h"
#include "fdir.h"
#include <string.h>

/* Override the weak tick hook so tests drive a deterministic clock. */
static uint32_t g_mock_tick = 0U;
uint32_t FDIR_GetTick(void) { return g_mock_tick; }

void setUp(void)
{
    g_mock_tick = 0U;
    FDIR_Init();
}
void tearDown(void) { /* nothing */ }


/* ------------------------------------------------------------------
 * 1. Empty state
 * ------------------------------------------------------------------ */
void test_empty_state_after_init(void)
{
    setUp();
    const FDIR_FaultState_t *s = FDIR_GetState(FAULT_I2C_BUS_STUCK);
    TEST_ASSERT_NOT_NULL(s);
    TEST_ASSERT_EQUAL(0U, s->total_count);
    TEST_ASSERT_EQUAL(0U, s->recent_count);

    FDIR_Stats_t st = FDIR_GetStats();
    TEST_ASSERT_EQUAL(0U, st.total_faults);
    TEST_ASSERT_EQUAL(0U, st.escalations);
    TEST_ASSERT_EQUAL(0U, st.reboots_scheduled);
}


/* ------------------------------------------------------------------
 * 2. Single Report -> primary action
 * ------------------------------------------------------------------ */
void test_single_report_returns_primary(void)
{
    setUp();
    FDIR_Report(FAULT_SPI_TIMEOUT);

    const FDIR_FaultEntry_t *e = FDIR_GetEntry(FAULT_SPI_TIMEOUT);
    TEST_ASSERT_NOT_NULL(e);
    TEST_ASSERT_EQUAL(e->primary,
                      FDIR_GetRecommendedAction(FAULT_SPI_TIMEOUT));

    const FDIR_FaultState_t *s = FDIR_GetState(FAULT_SPI_TIMEOUT);
    TEST_ASSERT_EQUAL(1U, s->total_count);
    TEST_ASSERT_EQUAL(1U, s->recent_count);
}


/* ------------------------------------------------------------------
 * 3. Count threshold -> escalation
 * ------------------------------------------------------------------ */
void test_escalation_after_threshold(void)
{
    setUp();
    const FDIR_FaultEntry_t *e = FDIR_GetEntry(FAULT_I2C_BUS_STUCK);

    for (uint32_t i = 1U; i < e->escalation_threshold; ++i) {
        FDIR_Report(FAULT_I2C_BUS_STUCK);
        TEST_ASSERT_EQUAL(e->primary,
                          FDIR_GetRecommendedAction(FAULT_I2C_BUS_STUCK));
    }

    /* The threshold-th report must flip us to escalation. */
    FDIR_Report(FAULT_I2C_BUS_STUCK);
    TEST_ASSERT_EQUAL(e->escalation,
                      FDIR_GetRecommendedAction(FAULT_I2C_BUS_STUCK));
}


/* ------------------------------------------------------------------
 * 4. Cross-fault isolation
 * ------------------------------------------------------------------ */
void test_cross_fault_isolation(void)
{
    setUp();
    /* Pump FAULT_SPI_TIMEOUT until it escalates. */
    const FDIR_FaultEntry_t *spi = FDIR_GetEntry(FAULT_SPI_TIMEOUT);
    for (uint32_t i = 0; i < spi->escalation_threshold; ++i) {
        FDIR_Report(FAULT_SPI_TIMEOUT);
    }
    TEST_ASSERT_EQUAL(spi->escalation,
                      FDIR_GetRecommendedAction(FAULT_SPI_TIMEOUT));

    /* I2C must still be at primary (default state). */
    const FDIR_FaultEntry_t *i2c = FDIR_GetEntry(FAULT_I2C_BUS_STUCK);
    TEST_ASSERT_EQUAL(i2c->primary,
                      FDIR_GetRecommendedAction(FAULT_I2C_BUS_STUCK));
    const FDIR_FaultState_t *s = FDIR_GetState(FAULT_I2C_BUS_STUCK);
    TEST_ASSERT_EQUAL(0U, s->total_count);
}


/* ------------------------------------------------------------------
 * 5. Recent-window sliding: stale events must not escalate.
 * ------------------------------------------------------------------ */
void test_recent_window_slides(void)
{
    setUp();
    const FDIR_FaultEntry_t *e = FDIR_GetEntry(FAULT_SENSOR_OUT_OF_RANGE);

    /* Pump almost to the threshold inside one window. */
    for (uint32_t i = 0; i < e->escalation_threshold - 1U; ++i) {
        FDIR_Report(FAULT_SENSOR_OUT_OF_RANGE);
    }
    TEST_ASSERT_EQUAL(e->primary,
                      FDIR_GetRecommendedAction(FAULT_SENSOR_OUT_OF_RANGE));

    /* Skip past the recent window. The next report must start a fresh
     * recent window (recent_count = 1) so the old events don't push
     * us over the threshold. */
    g_mock_tick += FDIR_RECENT_WINDOW_MS + 1U;
    FDIR_Report(FAULT_SENSOR_OUT_OF_RANGE);

    const FDIR_FaultState_t *s = FDIR_GetState(FAULT_SENSOR_OUT_OF_RANGE);
    TEST_ASSERT_EQUAL(1U, s->recent_count);
    TEST_ASSERT_EQUAL(e->escalation_threshold, s->total_count);
    TEST_ASSERT_EQUAL(e->primary,
                      FDIR_GetRecommendedAction(FAULT_SENSOR_OUT_OF_RANGE));
}


/* ------------------------------------------------------------------
 * 6. ClearRecent resets to primary but preserves total.
 * ------------------------------------------------------------------ */
void test_clear_recent_preserves_total(void)
{
    setUp();
    const FDIR_FaultEntry_t *e = FDIR_GetEntry(FAULT_OVER_TEMPERATURE);
    for (uint32_t i = 0; i < e->escalation_threshold; ++i) {
        FDIR_Report(FAULT_OVER_TEMPERATURE);
    }
    TEST_ASSERT_EQUAL(e->escalation,
                      FDIR_GetRecommendedAction(FAULT_OVER_TEMPERATURE));

    FDIR_ClearRecent(FAULT_OVER_TEMPERATURE);

    const FDIR_FaultState_t *s = FDIR_GetState(FAULT_OVER_TEMPERATURE);
    TEST_ASSERT_EQUAL(0U, s->recent_count);
    TEST_ASSERT_EQUAL(e->escalation_threshold, s->total_count);
    TEST_ASSERT_EQUAL(e->primary,
                      FDIR_GetRecommendedAction(FAULT_OVER_TEMPERATURE));
}


/* ------------------------------------------------------------------
 * 7. ResetAll zeroes everything.
 * ------------------------------------------------------------------ */
void test_reset_all_zeroes_state(void)
{
    setUp();
    FDIR_Report(FAULT_BATTERY_UNDERVOLT);
    FDIR_Report(FAULT_BATTERY_UNDERVOLT);
    FDIR_ResetAll();

    const FDIR_FaultState_t *s = FDIR_GetState(FAULT_BATTERY_UNDERVOLT);
    TEST_ASSERT_EQUAL(0U, s->total_count);
    FDIR_Stats_t st = FDIR_GetStats();
    TEST_ASSERT_EQUAL(0U, st.total_faults);
}


/* ------------------------------------------------------------------
 * 8. Out-of-range id doesn't crash.
 * ------------------------------------------------------------------ */
void test_out_of_range_id_is_safe(void)
{
    setUp();
    FDIR_Report((FDIR_FaultId_t)99);                 /* ignored */
    TEST_ASSERT_EQUAL(RECOVERY_LOG_ONLY,
                      FDIR_GetRecommendedAction((FDIR_FaultId_t)99));
    TEST_ASSERT_NULL(FDIR_GetState((FDIR_FaultId_t)99));
    TEST_ASSERT_NULL(FDIR_GetEntry((FDIR_FaultId_t)99));
    FDIR_ClearRecent((FDIR_FaultId_t)99);            /* no-op */

    FDIR_Stats_t st = FDIR_GetStats();
    TEST_ASSERT_EQUAL(0U, st.total_faults);
}


/* ------------------------------------------------------------------
 * 9. Aggregate stats tracking.
 * ------------------------------------------------------------------ */
void test_aggregate_stats(void)
{
    setUp();
    const FDIR_FaultEntry_t *bat = FDIR_GetEntry(FAULT_BATTERY_UNDERVOLT);

    FDIR_Report(FAULT_BATTERY_UNDERVOLT);   /* primary = SAFE_MODE */
    FDIR_Report(FAULT_BATTERY_UNDERVOLT);   /* at threshold -> escalation = REBOOT */

    FDIR_Stats_t st = FDIR_GetStats();
    TEST_ASSERT_EQUAL(2U, st.total_faults);
    TEST_ASSERT_TRUE(st.safe_mode_entries >= 1U);
    TEST_ASSERT_TRUE(st.reboots_scheduled >= 1U);
    TEST_ASSERT_EQUAL(bat->escalation,
                      FDIR_GetRecommendedAction(FAULT_BATTERY_UNDERVOLT));
}


int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_empty_state_after_init);
    RUN_TEST(test_single_report_returns_primary);
    RUN_TEST(test_escalation_after_threshold);
    RUN_TEST(test_cross_fault_isolation);
    RUN_TEST(test_recent_window_slides);
    RUN_TEST(test_clear_recent_preserves_total);
    RUN_TEST(test_reset_all_zeroes_state);
    RUN_TEST(test_out_of_range_id_is_safe);
    RUN_TEST(test_aggregate_stats);
    return UNITY_END();
}
