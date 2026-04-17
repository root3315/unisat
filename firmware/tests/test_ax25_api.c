/**
 * @file test_ax25_api.c
 * @brief Facade smoke test — consumers using ONLY AX25_Xxx() names
 * must get the same end-to-end behaviour as the snake_case core.
 */

#include "unity/unity.h"
#include "ax25_api.h"
#include <string.h>

void setUp(void) {}
void tearDown(void) {}

void test_facade_encode_decode_round_trip(void) {
  AX25_Address_t dst = { .callsign = "CQ", .ssid = 0 };
  AX25_Address_t src = { .callsign = "UN8SAT", .ssid = 1 };

  uint8_t buf[128];
  uint16_t n = 0;
  TEST_ASSERT_TRUE(AX25_EncodeUiFrame(&dst, &src, 0xF0,
      (const uint8_t *)"Hi", 2, buf, sizeof(buf), &n));
  TEST_ASSERT_TRUE(n > 20);

  AX25_Decoder_t dec;
  AX25_DecoderInit(&dec);

  AX25_UiFrame_t out;
  bool ready;
  int got = 0;
  for (uint16_t i = 0; i < n; i++) {
    AX25_DecoderPushByte(&dec, buf[i], &out, &ready);
    if (ready) got++;
  }
  TEST_ASSERT_EQUAL(1, got);
  TEST_ASSERT_EQUAL_MEMORY("Hi", out.info, 2);
  TEST_ASSERT_EQUAL(2, out.info_len);
}

int main(void) {
  UNITY_BEGIN();
  RUN_TEST(test_facade_encode_decode_round_trip);
  return UNITY_END();
}
