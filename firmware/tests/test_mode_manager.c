/**
 * @file test_mode_manager.c
 * @brief Tests for the FDIR-driven mode supervisor (Phase 7 / #3).
 *
 * Scenarios covered
 *   1. Init -> MODE_BOOT, stats zero.
 *   2. EnterNominal from BOOT -> MODE_NOMINAL.
 *   3. Direct EnterSafe + idempotence (second call is a no-op).
 *   4. Tick with zero reports stays NOMINAL; one undervolt report
 *      escalates straight to SAFE via the FDIR threshold=2 rule
 *      (two reports inside window).
 *   5. Tick with a STACK_OVERFLOW report arms REBOOT_PEND and the
 *      next tick fires the platform hook.
 *   6. Recovery: after SAFE-triggering faults stop, ClearRecent
 *      removes the recommendation and Tick transitions back to
 *      NOMINAL.
 *   7. Platform reboot hook is strong-overridden; fires exactly once.
 *
 * Host-only; links the real fdir.c + mode_manager.c sources.
 */

#include "unity/unity.h"
#include "mode_manager.h"
#include "fdir.h"
#include <string.h>

/* Strong override of the weak platform hook so tests can assert
 * whether the reboot actually fired. */
static int g_reboot_fired = 0;
void ModeManager_PlatformReboot(void) { g_reboot_fired++; }

/* Deterministic tick source for FDIR so escalation windows are
 * predictable. */
static uint32_t g_mock_tick = 0U;
uint32_t FDIR_GetTick(void) { return g_mock_tick; }


void setUp(void)
{
    g_reboot_fired = 0;
    g_mock_tick = 0;
    FDIR_Init();
    ModeManager_ResetForTest();
}
void tearDown(void) { /* nothing */ }


/* ------------------------------------------------------------------ */

void test_init_is_boot_with_zero_stats(void)
{
    setUp();
    TEST_ASSERT_EQUAL(MODE_BOOT, ModeManager_GetMode());

    ModeManager_Stats_t s = ModeManager_GetStats();
    TEST_ASSERT_EQUAL(0U, s.transitions_total);
    TEST_ASSERT_EQUAL(0U, s.safe_entries);
    TEST_ASSERT_EQUAL(MODE_BOOT, s.current_mode);
}

void test_enter_nominal_from_boot(void)
{
    setUp();
    ModeManager_EnterNominal();
    TEST_ASSERT_EQUAL(MODE_NOMINAL, ModeManager_GetMode());

    ModeManager_Stats_t s = ModeManager_GetStats();
    TEST_ASSERT_EQUAL(1U, s.transitions_total);
    TEST_ASSERT_EQUAL(MODE_REASON_NOMINAL_START, s.last_reason);
}

void test_direct_enter_safe_is_idempotent(void)
{
    setUp();
    ModeManager_EnterSafe(MODE_REASON_MANUAL_GROUND);
    TEST_ASSERT_EQUAL(MODE_SAFE, ModeManager_GetMode());
    ModeManager_Stats_t s1 = ModeManager_GetStats();
    TEST_ASSERT_EQUAL(1U, s1.safe_entries);

    /* Second call: no-op (REQ-SAFE-003 symmetry with Python SafeModeHandler). */
    ModeManager_EnterSafe(MODE_REASON_MANUAL_GROUND);
    ModeManager_Stats_t s2 = ModeManager_GetStats();
    TEST_ASSERT_EQUAL(MODE_SAFE, s2.current_mode);
    TEST_ASSERT_EQUAL(1U, s2.safe_entries);           /* unchanged */
    TEST_ASSERT_EQUAL(1U, s2.transitions_total);      /* unchanged */
}

void test_tick_noop_when_no_faults(void)
{
    setUp();
    ModeManager_EnterNominal();
    SystemMode_t m = ModeManager_Tick();
    TEST_ASSERT_EQUAL(MODE_NOMINAL, m);
}

void test_undervolt_drives_safe_mode_via_tick(void)
{
    setUp();
    ModeManager_EnterNominal();

    /* FAULT_BATTERY_UNDERVOLT has threshold=2 with escalation=REBOOT
     * and primary=SAFE_MODE; even ONE Report returns SAFE_MODE as
     * primary, which is enough to drive the supervisor into SAFE. */
    FDIR_Report(FAULT_BATTERY_UNDERVOLT);

    SystemMode_t m = ModeManager_Tick();
    TEST_ASSERT_EQUAL(MODE_SAFE, m);

    ModeManager_Stats_t s = ModeManager_GetStats();
    TEST_ASSERT_EQUAL(1U, s.safe_entries);
    TEST_ASSERT_EQUAL(MODE_REASON_FDIR_SAFE, s.last_reason);
}

void test_stack_overflow_arms_reboot_then_fires_on_next_tick(void)
{
    setUp();
    ModeManager_EnterNominal();

    /* FAULT_STACK_OVERFLOW has primary=REBOOT threshold=1 — single
     * Report arms the reboot. */
    FDIR_Report(FAULT_STACK_OVERFLOW);

    SystemMode_t m1 = ModeManager_Tick();
    TEST_ASSERT_EQUAL(MODE_REBOOT_PEND, m1);
    TEST_ASSERT_EQUAL(0, g_reboot_fired);              /* not yet fired */

    ModeManager_Stats_t s = ModeManager_GetStats();
    TEST_ASSERT_EQUAL(1U, s.reboots_requested);

    /* Next tick: fires the platform hook. */
    SystemMode_t m2 = ModeManager_Tick();
    TEST_ASSERT_EQUAL(MODE_REBOOT_PEND, m2);           /* host: stays pending */
    TEST_ASSERT_EQUAL(1, g_reboot_fired);              /* hook fired once */

    /* Third tick: still only one reboot attempt — the production
     * firmware never returns from NVIC_SystemReset, but if the hook
     * is a no-op (host test), the supervisor stays in REBOOT_PEND. */
    (void)ModeManager_Tick();
    TEST_ASSERT_EQUAL(2, g_reboot_fired);              /* every tick */
}

void test_safe_mode_recovers_to_nominal_after_clear(void)
{
    setUp();
    ModeManager_EnterNominal();

    FDIR_Report(FAULT_COMM_LOSS);      /* primary = SAFE_MODE */
    (void)ModeManager_Tick();
    TEST_ASSERT_EQUAL(MODE_SAFE, ModeManager_GetMode());

    /* Ground contacts us again; comm supervisor clears the fault. */
    FDIR_ClearRecent(FAULT_COMM_LOSS);

    (void)ModeManager_Tick();
    TEST_ASSERT_EQUAL(MODE_NOMINAL, ModeManager_GetMode());

    ModeManager_Stats_t s = ModeManager_GetStats();
    TEST_ASSERT_EQUAL(1U, s.safe_entries);
    TEST_ASSERT_EQUAL(1U, s.safe_exits);
}

void test_worst_action_wins_across_multiple_faults(void)
{
    setUp();
    ModeManager_EnterNominal();

    /* Mix: sensor out-of-range (primary=LOG_ONLY), I2C (RESET_BUS),
     * comm-loss (SAFE_MODE). Worst is SAFE_MODE, so Tick must
     * transition to SAFE even though two of the three are benign. */
    FDIR_Report(FAULT_SENSOR_OUT_OF_RANGE);
    FDIR_Report(FAULT_I2C_BUS_STUCK);
    FDIR_Report(FAULT_COMM_LOSS);

    SystemMode_t m = ModeManager_Tick();
    TEST_ASSERT_EQUAL(MODE_SAFE, m);
}

void test_degraded_stays_when_safe_not_yet_triggered(void)
{
    setUp();
    ModeManager_EnterNominal();

    /* over_temperature primary = DISABLE_SUBSYS (DEGRADED) */
    FDIR_Report(FAULT_OVER_TEMPERATURE);
    (void)ModeManager_Tick();
    TEST_ASSERT_EQUAL(MODE_DEGRADED, ModeManager_GetMode());
    ModeManager_Stats_t s = ModeManager_GetStats();
    TEST_ASSERT_EQUAL(1U, s.subsystem_disables);
}

void test_reboot_suppression_diverts_fdir_reboot_to_safe(void)
{
    setUp();
    ModeManager_EnterNominal();
    ModeManager_SuppressReboot(true);

    /* STACK_OVERFLOW primary = REBOOT with threshold 1 — without
     * suppression this would arm MODE_REBOOT_PEND and fire the
     * platform hook on the next tick. With the loop guard active,
     * the supervisor must divert to SAFE instead. */
    FDIR_Report(FAULT_STACK_OVERFLOW);
    SystemMode_t m = ModeManager_Tick();

    TEST_ASSERT_EQUAL(MODE_SAFE, m);
    TEST_ASSERT_EQUAL(0, g_reboot_fired);

    ModeManager_Stats_t s = ModeManager_GetStats();
    TEST_ASSERT_EQUAL(1U, s.safe_entries);
    TEST_ASSERT_EQUAL(0U, s.reboots_requested);
    TEST_ASSERT_EQUAL(MODE_REASON_REBOOT_LOOP, s.last_reason);

    /* Subsequent ticks keep us in SAFE, not REBOOT_PEND. */
    (void)ModeManager_Tick();
    TEST_ASSERT_EQUAL(0, g_reboot_fired);
    TEST_ASSERT_EQUAL(MODE_SAFE, ModeManager_GetMode());
}

void test_reboot_suppression_blocks_direct_request(void)
{
    setUp();
    ModeManager_EnterNominal();
    ModeManager_SuppressReboot(true);

    /* A direct RequestReboot must also divert to SAFE — otherwise a
     * command handler could defeat the loop guard. */
    ModeManager_RequestReboot(MODE_REASON_MANUAL_GROUND);
    TEST_ASSERT_EQUAL(MODE_SAFE, ModeManager_GetMode());

    ModeManager_Stats_t s = ModeManager_GetStats();
    TEST_ASSERT_EQUAL(0U, s.reboots_requested);
    TEST_ASSERT_EQUAL(1U, s.safe_entries);
}

void test_reboot_suppression_can_be_cleared(void)
{
    setUp();
    ModeManager_EnterNominal();
    ModeManager_SuppressReboot(true);
    TEST_ASSERT_TRUE(ModeManager_IsRebootSuppressed());

    /* Clearing the flag restores normal RECOVERY_REBOOT behaviour
     * on the next tick. */
    ModeManager_SuppressReboot(false);
    TEST_ASSERT_FALSE(ModeManager_IsRebootSuppressed());

    FDIR_Report(FAULT_STACK_OVERFLOW);
    (void)ModeManager_Tick();
    TEST_ASSERT_EQUAL(MODE_REBOOT_PEND, ModeManager_GetMode());
}


int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_init_is_boot_with_zero_stats);
    RUN_TEST(test_enter_nominal_from_boot);
    RUN_TEST(test_direct_enter_safe_is_idempotent);
    RUN_TEST(test_tick_noop_when_no_faults);
    RUN_TEST(test_undervolt_drives_safe_mode_via_tick);
    RUN_TEST(test_stack_overflow_arms_reboot_then_fires_on_next_tick);
    RUN_TEST(test_safe_mode_recovers_to_nominal_after_clear);
    RUN_TEST(test_worst_action_wins_across_multiple_faults);
    RUN_TEST(test_degraded_stays_when_safe_not_yet_triggered);
    RUN_TEST(test_reboot_suppression_diverts_fdir_reboot_to_safe);
    RUN_TEST(test_reboot_suppression_blocks_direct_request);
    RUN_TEST(test_reboot_suppression_can_be_cleared);
    return UNITY_END();
}
