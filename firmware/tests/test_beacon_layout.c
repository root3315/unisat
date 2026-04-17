/**
 * @file test_beacon_layout.c
 * @brief Unit tests: Telemetry_PackBeacon emits 48-byte raw layout per spec §7.2
 */

#include "unity/unity.h"
#include "../stm32/Core/Inc/telemetry.h"
#include "../stm32/Core/Inc/adcs.h"
#include <string.h>
#include <stdint.h>

void setUp(void) {
    /* Initialise ADCS so quaternion = identity (1,0,0,0), making bytes 16-31 non-zero */
    ADCS_Init();
}
void tearDown(void) {}

/* (a) Telemetry_PackBeacon must return exactly 48 */
void test_beacon_returns_48_bytes(void) {
    uint8_t buf[64];
    memset(buf, 0xAA, sizeof(buf));
    uint16_t len = Telemetry_PackBeacon(buf, sizeof(buf));
    TEST_ASSERT_EQUAL(48, len);
}

/* (b) Byte 4 is the ADCS mode enum, which must be in 0..7 */
void test_beacon_mode_byte_in_range(void) {
    uint8_t buf[48];
    memset(buf, 0, sizeof(buf));
    Telemetry_PackBeacon(buf, sizeof(buf));
    TEST_ASSERT_TRUE(buf[4] <= 7);
}

/* (c) Bytes 16..31 (quaternion: Qw, Qx, Qy, Qz as f32) must not all be zero */
void test_beacon_quaternion_not_all_zero(void) {
    uint8_t buf[48];
    memset(buf, 0, sizeof(buf));
    Telemetry_PackBeacon(buf, sizeof(buf));

    int all_zero = 1;
    for (int i = 16; i <= 31; i++) {
        if (buf[i] != 0) {
            all_zero = 0;
            break;
        }
    }
    TEST_ASSERT_FALSE(all_zero);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_beacon_returns_48_bytes);
    RUN_TEST(test_beacon_mode_byte_in_range);
    RUN_TEST(test_beacon_quaternion_not_all_zero);
    return UNITY_END();
}
