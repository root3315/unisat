/**
 * @file test_hmac.c
 * @brief RFC 4231 HMAC-SHA256 test vectors + SHA-256 sanity.
 */

#include "unity/unity.h"
#include "sha256.h"
#include "hmac_sha256.h"
#include <string.h>

void setUp(void) {}
void tearDown(void) {}

/* FIPS 180-4 Appendix B.1: "abc" -> ba7816bf 8f01cfea 4141... */
void test_sha256_abc(void) {
    uint8_t d[32];
    sha256((const uint8_t *)"abc", 3, d);
    static const uint8_t expected[32] = {
        0xba,0x78,0x16,0xbf,0x8f,0x01,0xcf,0xea,
        0x41,0x41,0x40,0xde,0x5d,0xae,0x22,0x23,
        0xb0,0x03,0x61,0xa3,0x96,0x17,0x7a,0x9c,
        0xb4,0x10,0xff,0x61,0xf2,0x00,0x15,0xad,
    };
    TEST_ASSERT_EQUAL_MEMORY(expected, d, 32);
}

/* FIPS 180-4 Appendix B.2: "" -> e3b0c442...b855. */
void test_sha256_empty(void) {
    uint8_t d[32];
    sha256(NULL, 0, d);
    static const uint8_t expected[32] = {
        0xe3,0xb0,0xc4,0x42,0x98,0xfc,0x1c,0x14,
        0x9a,0xfb,0xf4,0xc8,0x99,0x6f,0xb9,0x24,
        0x27,0xae,0x41,0xe4,0x64,0x9b,0x93,0x4c,
        0xa4,0x95,0x99,0x1b,0x78,0x52,0xb8,0x55,
    };
    TEST_ASSERT_EQUAL_MEMORY(expected, d, 32);
}

/* RFC 4231 §4.2: Test Case 1.
 * key = 20 x 0x0b, data = "Hi There"
 * expected = b0344c61d8db38535ca8afceaf0bf12b
 *            881dc200c9833da726e9376c2e32cff7 */
void test_hmac_sha256_rfc4231_case1(void) {
    uint8_t key[20];
    memset(key, 0x0b, sizeof(key));
    uint8_t tag[32];
    hmac_sha256(key, sizeof(key), (const uint8_t *)"Hi There", 8, tag);
    static const uint8_t expected[32] = {
        0xb0,0x34,0x4c,0x61,0xd8,0xdb,0x38,0x53,
        0x5c,0xa8,0xaf,0xce,0xaf,0x0b,0xf1,0x2b,
        0x88,0x1d,0xc2,0x00,0xc9,0x83,0x3d,0xa7,
        0x26,0xe9,0x37,0x6c,0x2e,0x32,0xcf,0xf7,
    };
    TEST_ASSERT_EQUAL_MEMORY(expected, tag, 32);
}

/* RFC 4231 §4.3: Test Case 2.
 * key = "Jefe", data = "what do ya want for nothing?"
 * expected = 5bdcc146bf60754e6a042426089575c7
 *            5a003f089d2739839dec58b964ec3843 */
void test_hmac_sha256_rfc4231_case2(void) {
    uint8_t tag[32];
    hmac_sha256((const uint8_t *)"Jefe", 4,
                (const uint8_t *)"what do ya want for nothing?", 28, tag);
    static const uint8_t expected[32] = {
        0x5b,0xdc,0xc1,0x46,0xbf,0x60,0x75,0x4e,
        0x6a,0x04,0x24,0x26,0x08,0x95,0x75,0xc7,
        0x5a,0x00,0x3f,0x08,0x9d,0x27,0x39,0x83,
        0x9d,0xec,0x58,0xb9,0x64,0xec,0x38,0x43,
    };
    TEST_ASSERT_EQUAL_MEMORY(expected, tag, 32);
}

void test_hmac_verify_constant_time(void) {
    uint8_t a[32] = { 0 };
    uint8_t b[32] = { 0 };
    TEST_ASSERT_EQUAL(1, hmac_sha256_verify(a, b));
    b[31] = 0x01;
    TEST_ASSERT_EQUAL(0, hmac_sha256_verify(a, b));
    b[31] = 0x00;
    b[0]  = 0x80;
    TEST_ASSERT_EQUAL(0, hmac_sha256_verify(a, b));
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_sha256_abc);
    RUN_TEST(test_sha256_empty);
    RUN_TEST(test_hmac_sha256_rfc4231_case1);
    RUN_TEST(test_hmac_sha256_rfc4231_case2);
    RUN_TEST(test_hmac_verify_constant_time);
    return UNITY_END();
}
