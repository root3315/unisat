/**
 * @file test_adcs_algorithms.c
 * @brief Unit tests for ADCS algorithms (quaternion, B-dot)
 */

#include "unity/unity.h"
#include "../stm32/ADCS/quaternion.h"
#include "../stm32/ADCS/bdot.h"
#include <math.h>

void setUp(void) {}
void tearDown(void) {}

void test_quaternion_identity(void) {
    Quaternion_t q = Quat_Identity();
    TEST_ASSERT_FLOAT_WITHIN(1e-6, 1.0f, q.w);
    TEST_ASSERT_FLOAT_WITHIN(1e-6, 0.0f, q.x);
}

void test_quaternion_norm(void) {
    Quaternion_t q = {0.5f, 0.5f, 0.5f, 0.5f};
    float n = Quat_Norm(q);
    TEST_ASSERT_FLOAT_WITHIN(1e-5, 1.0f, n);
}

void test_quaternion_normalize(void) {
    Quaternion_t q = {2.0f, 0.0f, 0.0f, 0.0f};
    Quaternion_t n = Quat_Normalize(q);
    TEST_ASSERT_FLOAT_WITHIN(1e-5, 1.0f, Quat_Norm(n));
}

void test_quaternion_multiply_identity(void) {
    Quaternion_t id = Quat_Identity();
    Quaternion_t q = {0.707f, 0.707f, 0.0f, 0.0f};
    Quaternion_t r = Quat_Multiply(id, q);
    TEST_ASSERT_FLOAT_WITHIN(1e-3, q.w, r.w);
    TEST_ASSERT_FLOAT_WITHIN(1e-3, q.x, r.x);
}

void test_quaternion_inverse(void) {
    Quaternion_t q = Quat_Normalize((Quaternion_t){1.0f, 1.0f, 0.0f, 0.0f});
    Quaternion_t qi = Quat_Inverse(q);
    Quaternion_t r = Quat_Multiply(q, qi);
    TEST_ASSERT_FLOAT_WITHIN(1e-4, 1.0f, r.w);
    TEST_ASSERT_FLOAT_WITHIN(1e-4, 0.0f, r.x);
}

void test_euler_quaternion_roundtrip(void) {
    EulerAngles_t e = {0.1f, 0.2f, 0.3f};
    Quaternion_t q = Quat_FromEuler(e);
    EulerAngles_t e2 = Quat_ToEuler(q);
    TEST_ASSERT_FLOAT_WITHIN(1e-3, e.roll, e2.roll);
    TEST_ASSERT_FLOAT_WITHIN(1e-3, e.pitch, e2.pitch);
    TEST_ASSERT_FLOAT_WITHIN(1e-3, e.yaw, e2.yaw);
}

void test_bdot_output_opposes_field_change(void) {
    BDot_Init();
    float mag1[3] = {100.0f, 0.0f, 0.0f};
    float mag2[3] = {110.0f, 0.0f, 0.0f};
    float moment[3];

    BDot_Update(mag1, 1.0f, moment);  /* first sample */
    BDot_Update(mag2, 1.0f, moment);

    /* B increased in X, so moment should be negative in X */
    TEST_ASSERT_TRUE(moment[0] < 0.0f);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_quaternion_identity);
    RUN_TEST(test_quaternion_norm);
    RUN_TEST(test_quaternion_normalize);
    RUN_TEST(test_quaternion_multiply_identity);
    RUN_TEST(test_quaternion_inverse);
    RUN_TEST(test_euler_quaternion_roundtrip);
    RUN_TEST(test_bdot_output_opposes_field_change);
    return UNITY_END();
}
