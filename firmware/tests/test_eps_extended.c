/**
 * @file test_eps_extended.c
 * @brief Extended EPS coverage — MPPT perturb/observe + battery states.
 *
 * Complements the existing test_eps.c with a thorough sweep of the
 * battery manager state machine (every enum value reached from a
 * legitimate voltage/current/temperature input) and the MPPT
 * decision tree (power-up × voltage-up / power-up × voltage-down /
 * power-down × both signs).
 *
 * These paths were unhit in the baseline coverage report
 * (mppt.c ~11 %, battery_manager.c ~17 %) so each new test pushes
 * both modules into the high-60s / 70s line-coverage band.
 */

#include "unity/unity.h"
#include "../stm32/EPS/mppt.h"
#include "../stm32/EPS/battery_manager.h"
#include <math.h>

void setUp(void)    { MPPT_Init(); BatteryManager_Init(); }
void tearDown(void) { /* nothing */ }


/* =================================================================
 *  MPPT — every branch of Perturb & Observe
 * ================================================================= */

void test_mppt_init_defaults(void)
{
    setUp();
    MPPT_Status_t s = MPPT_GetStatus();
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.0f, s.voltage);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.0f, s.current);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.5f, s.duty_cycle);
}

void test_mppt_duty_clamps_at_upper_bound(void)
{
    setUp();
    /* Drive duty repeatedly upward by feeding monotonically-rising
     * power with rising voltage — Perturb & Observe will keep
     * perturb_direction = +1 until the clamp hits MPPT_MAX_DUTY. */
    for (int i = 0; i < 200; i++) {
        float v = 4.0f + (float)i * 0.01f;
        float c = 0.5f + (float)i * 0.001f;
        MPPT_Update(v, c);
    }
    MPPT_Status_t s = MPPT_GetStatus();
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, MPPT_MAX_DUTY, s.duty_cycle);
}

void test_mppt_duty_clamps_at_lower_bound(void)
{
    setUp();
    /* Drive the P&O decision tree so perturb_direction stays -1.
     * Required pattern: voltage monotonically INCREASES while power
     * monotonically DECREASES — that's the "power down, voltage up"
     * branch which sets direction = -1 on every update. Duty walks
     * downward until MPPT_MIN_DUTY clamps it. */
    for (int i = 0; i < 200; i++) {
        float v = 4.0f + (float)i * 0.01f;           /* voltage up   */
        float c = 1.0f - (float)i * 0.005f;          /* current down */
        if (c < 0.01f) c = 0.01f;
        MPPT_Update(v, c);                           /* power goes down */
    }
    MPPT_Status_t s = MPPT_GetStatus();
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, MPPT_MIN_DUTY, s.duty_cycle);
}

void test_mppt_power_increase_with_voltage_increase(void)
{
    setUp();
    /* Two updates: first establishes baseline, second increases both
     * voltage and power -> perturb_direction must go positive. */
    MPPT_Update(4.0f, 0.5f);           /* power = 2.0  */
    float duty_before = MPPT_GetDutyCycle();
    MPPT_Update(4.2f, 0.55f);          /* power = 2.31, both up */
    float duty_after  = MPPT_GetDutyCycle();
    TEST_ASSERT_TRUE(duty_after > duty_before);
}

void test_mppt_power_decrease_reverses_direction(void)
{
    setUp();
    MPPT_Update(4.0f, 0.5f);           /* power 2.0, prev_power set */
    MPPT_Update(4.2f, 0.55f);          /* power 2.31 up             */
    float duty_at_peak = MPPT_GetDutyCycle();
    MPPT_Update(4.3f, 0.4f);           /* power 1.72 DOWN           */
    float duty_after  = MPPT_GetDutyCycle();
    /* When power drops with voltage still rising, P&O reverses
     * direction; duty should step down from the peak. */
    TEST_ASSERT_TRUE(duty_after < duty_at_peak);
}

void test_mppt_efficiency_reported(void)
{
    setUp();
    MPPT_Update(4.0f, 0.5f);
    MPPT_Status_t s = MPPT_GetStatus();
    /* efficiency is power/theoretical which defaults to 1.0 on this
     * simple model — the point of the test is coverage of the
     * branch where theoretical_max > 0.01. */
    TEST_ASSERT_TRUE(s.efficiency > 0.0f);
}


/* =================================================================
 *  Battery manager — every BATT_STATE reachable from inputs
 * ================================================================= */

void test_battery_init_default_state(void)
{
    setUp();
    BatteryStatus_t b = BatteryManager_GetStatus();
    TEST_ASSERT_EQUAL(BATT_STATE_IDLE, b.state);
    TEST_ASSERT_TRUE(b.charge_enabled);
    TEST_ASSERT_TRUE(b.discharge_enabled);
    TEST_ASSERT_FLOAT_WITHIN(0.1f, 50.0f, b.soc_percent);
}

void test_battery_full_state_triggers_charge_lockout(void)
{
    setUp();
    BatteryManager_Update(BATT_CHARGE_CUTOFF_V + 0.1f, 0.2f, 25.0f);
    BatteryStatus_t b = BatteryManager_GetStatus();
    TEST_ASSERT_EQUAL(BATT_STATE_FULL, b.state);
    TEST_ASSERT_FALSE(b.charge_enabled);
    TEST_ASSERT_FALSE(BatteryManager_IsChargeAllowed());
}

void test_battery_critical_state_locks_discharge(void)
{
    setUp();
    BatteryManager_Update(BATT_DISCHARGE_CUTOFF_V - 0.1f, -0.2f, 25.0f);
    BatteryStatus_t b = BatteryManager_GetStatus();
    TEST_ASSERT_EQUAL(BATT_STATE_CRITICAL, b.state);
    TEST_ASSERT_FALSE(b.discharge_enabled);
    TEST_ASSERT_FALSE(BatteryManager_IsDischargeAllowed());
}

void test_battery_over_temp_triggers_fault(void)
{
    setUp();
    /* Nominal voltage but thermal out of range. */
    BatteryManager_Update(14.0f, 0.0f, BATT_TEMP_MAX_C + 1.0f);
    BatteryStatus_t b = BatteryManager_GetStatus();
    TEST_ASSERT_EQUAL(BATT_STATE_FAULT, b.state);
    TEST_ASSERT_FALSE(b.charge_enabled);
}

void test_battery_under_temp_triggers_fault(void)
{
    setUp();
    BatteryManager_Update(14.0f, 0.0f, BATT_TEMP_MIN_C - 1.0f);
    BatteryStatus_t b = BatteryManager_GetStatus();
    TEST_ASSERT_EQUAL(BATT_STATE_FAULT, b.state);
}

void test_battery_charging_state(void)
{
    setUp();
    /* Voltage inside safe range, current positive (charging). */
    BatteryManager_Update(14.0f, 0.5f, 25.0f);
    TEST_ASSERT_EQUAL(BATT_STATE_CHARGING, BatteryManager_GetStatus().state);
}

void test_battery_discharging_state(void)
{
    setUp();
    BatteryManager_Update(14.0f, -0.5f, 25.0f);
    TEST_ASSERT_EQUAL(BATT_STATE_DISCHARGING, BatteryManager_GetStatus().state);
}

void test_battery_idle_state(void)
{
    setUp();
    /* |current| < 0.05 A -> idle. */
    BatteryManager_Update(14.0f, 0.02f, 25.0f);
    TEST_ASSERT_EQUAL(BATT_STATE_IDLE, BatteryManager_GetStatus().state);
}

void test_battery_low_soc_drives_low_state(void)
{
    setUp();
    /* Pick a voltage giving SOC < 20 % per the lookup — cell_v in
     * the 3.50..3.30 band gives 5..20 %. Pack = 4 × 3.40 = 13.6 V. */
    BatteryManager_Update(13.6f, 0.0f, 25.0f);
    BatteryStatus_t b = BatteryManager_GetStatus();
    TEST_ASSERT_TRUE(b.soc_percent < 20.0f);
    TEST_ASSERT_EQUAL(BATT_STATE_LOW, b.state);
}

void test_battery_soc_lookup_edges(void)
{
    setUp();
    /* >= 4.20 V/cell -> 100 % */
    BatteryManager_Update(4.20f * BATT_CELLS, 0.0f, 25.0f);
    TEST_ASSERT_FLOAT_WITHIN(0.1f, 100.0f, BatteryManager_GetSOC());

    /* <= 3.00 V/cell -> 0 % (edge of the lookup) */
    BatteryManager_Update(2.99f * BATT_CELLS, 0.0f, 25.0f);
    TEST_ASSERT_FLOAT_WITHIN(0.1f, 0.0f, BatteryManager_GetSOC());

    /* Middle band: 3.70 V/cell -> 40 % */
    BatteryManager_Update(3.70f * BATT_CELLS, 0.0f, 25.0f);
    TEST_ASSERT_FLOAT_WITHIN(0.5f, 40.0f, BatteryManager_GetSOC());
}

void test_battery_fault_is_sticky(void)
{
    setUp();
    /* Fault latches permanently — a thermal excursion leaves the
     * pack in FAULT even after temperature returns to range. This
     * is the correct behaviour for Li-ion: an over-temperature
     * event may have damaged cells and requires ground clearance
     * (via a wipe / manual command) rather than auto-recovery. */
    BatteryManager_Update(14.0f, 0.0f, BATT_TEMP_MAX_C + 5.0f);
    TEST_ASSERT_EQUAL(BATT_STATE_FAULT, BatteryManager_GetStatus().state);

    BatteryManager_Update(14.0f, 0.5f, 25.0f);     /* all-nominal */
    TEST_ASSERT_EQUAL(BATT_STATE_FAULT,
                       BatteryManager_GetStatus().state);

    /* Explicit BatteryManager_Init is the only way back to a clean
     * state — confirms the latching contract. */
    BatteryManager_Init();
    TEST_ASSERT_EQUAL(BATT_STATE_IDLE, BatteryManager_GetStatus().state);
}


int main(void) {
    UNITY_BEGIN();

    /* MPPT */
    RUN_TEST(test_mppt_init_defaults);
    RUN_TEST(test_mppt_duty_clamps_at_upper_bound);
    RUN_TEST(test_mppt_duty_clamps_at_lower_bound);
    RUN_TEST(test_mppt_power_increase_with_voltage_increase);
    RUN_TEST(test_mppt_power_decrease_reverses_direction);
    RUN_TEST(test_mppt_efficiency_reported);

    /* Battery */
    RUN_TEST(test_battery_init_default_state);
    RUN_TEST(test_battery_full_state_triggers_charge_lockout);
    RUN_TEST(test_battery_critical_state_locks_discharge);
    RUN_TEST(test_battery_over_temp_triggers_fault);
    RUN_TEST(test_battery_under_temp_triggers_fault);
    RUN_TEST(test_battery_charging_state);
    RUN_TEST(test_battery_discharging_state);
    RUN_TEST(test_battery_idle_state);
    RUN_TEST(test_battery_low_soc_drives_low_state);
    RUN_TEST(test_battery_soc_lookup_edges);
    RUN_TEST(test_battery_fault_is_sticky);

    return UNITY_END();
}
