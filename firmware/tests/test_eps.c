/**
 * @file test_eps.c
 * @brief Unit tests for EPS subsystem
 */

#include "unity/unity.h"
#include "../stm32/EPS/mppt.h"
#include "../stm32/EPS/battery_manager.h"

void setUp(void) {}
void tearDown(void) {}

void test_mppt_init_duty_cycle(void) {
    MPPT_Init();
    MPPT_Status_t s = MPPT_GetStatus();
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.5f, s.duty_cycle);
}

void test_mppt_duty_cycle_clamped(void) {
    MPPT_Init();
    for (int i = 0; i < 100; i++) {
        MPPT_Update(5.0f, 1.0f);
    }
    float dc = MPPT_GetDutyCycle();
    TEST_ASSERT_TRUE(dc >= MPPT_MIN_DUTY && dc <= MPPT_MAX_DUTY);
}

void test_battery_soc_full(void) {
    BatteryManager_Init();
    BatteryManager_Update(16.8f, 0.0f, 25.0f);
    BatteryStatus_t s = BatteryManager_GetStatus();
    TEST_ASSERT_FLOAT_WITHIN(5.0f, 100.0f, s.soc_percent);
}

void test_battery_overcharge_protection(void) {
    BatteryManager_Init();
    BatteryManager_Update(17.0f, 0.5f, 25.0f);
    TEST_ASSERT_FALSE(BatteryManager_IsChargeAllowed());
}

void test_battery_overdischarge_protection(void) {
    BatteryManager_Init();
    BatteryManager_Update(11.5f, -0.5f, 25.0f);
    TEST_ASSERT_FALSE(BatteryManager_IsDischargeAllowed());
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_mppt_init_duty_cycle);
    RUN_TEST(test_mppt_duty_cycle_clamped);
    RUN_TEST(test_battery_soc_full);
    RUN_TEST(test_battery_overcharge_protection);
    RUN_TEST(test_battery_overdischarge_protection);
    return UNITY_END();
}
