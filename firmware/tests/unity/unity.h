/* Unity Test Framework — Minimal header for UniSat tests */
/* Full framework: https://github.com/ThrowTheSwitch/Unity */

#ifndef UNITY_H
#define UNITY_H

#include <stdio.h>
#include <math.h>

static int unity_tests_run = 0;
static int unity_tests_failed = 0;
static const char *unity_current_test = "";

#define UNITY_BEGIN() (unity_tests_run = 0, unity_tests_failed = 0, 0)
#define UNITY_END() (printf("\n%d Tests, %d Failures\n", \
    unity_tests_run, unity_tests_failed), unity_tests_failed)

#define RUN_TEST(func) do { \
    unity_current_test = #func; \
    unity_tests_run++; \
    func(); \
    printf("."); \
} while(0)

#define TEST_ASSERT_TRUE(cond) do { \
    if (!(cond)) { \
        printf("\nFAIL: %s (line %d): expected TRUE\n", unity_current_test, __LINE__); \
        unity_tests_failed++; return; \
    } \
} while(0)

#define TEST_ASSERT_FALSE(cond) TEST_ASSERT_TRUE(!(cond))

#define TEST_ASSERT_EQUAL(expected, actual) do { \
    if ((expected) != (actual)) { \
        printf("\nFAIL: %s (line %d): expected %d, got %d\n", \
            unity_current_test, __LINE__, (int)(expected), (int)(actual)); \
        unity_tests_failed++; return; \
    } \
} while(0)

#define TEST_ASSERT_NOT_EQUAL(expected, actual) \
    TEST_ASSERT_TRUE((expected) != (actual))

#define TEST_ASSERT_FLOAT_WITHIN(delta, expected, actual) do { \
    if (fabs((double)(expected) - (double)(actual)) > (double)(delta)) { \
        printf("\nFAIL: %s (line %d): expected %.6f ± %.6f, got %.6f\n", \
            unity_current_test, __LINE__, (double)(expected), \
            (double)(delta), (double)(actual)); \
        unity_tests_failed++; return; \
    } \
} while(0)

#define TEST_ASSERT_GREATER_THAN(threshold, actual) \
    TEST_ASSERT_TRUE((actual) > (threshold))

#define TEST_ASSERT_EQUAL_MEMORY(expected, actual, len) do { \
    const unsigned char *e = (const unsigned char *)(expected); \
    const unsigned char *a = (const unsigned char *)(actual); \
    for (int _i = 0; _i < (int)(len); _i++) { \
        if (e[_i] != a[_i]) { \
            printf("\nFAIL: %s (line %d): memory differs at byte %d\n", \
                unity_current_test, __LINE__, _i); \
            unity_tests_failed++; return; \
        } \
    } \
} while(0)

#define TEST_ASSERT_NULL(ptr) do { \
    if ((ptr) != NULL) { \
        printf("\nFAIL: %s (line %d): expected NULL pointer\n", \
            unity_current_test, __LINE__); \
        unity_tests_failed++; return; \
    } \
} while(0)

#define TEST_ASSERT_NOT_NULL(ptr) do { \
    if ((ptr) == NULL) { \
        printf("\nFAIL: %s (line %d): expected non-NULL pointer\n", \
            unity_current_test, __LINE__); \
        unity_tests_failed++; return; \
    } \
} while(0)

#endif /* UNITY_H */
