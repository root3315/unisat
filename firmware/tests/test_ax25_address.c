/**
 * @file test_ax25_address.c
 * @brief Address encode/decode tests (REQ-AX25-002, AX.25 v2.2 §3.12).
 */

#include "unity/unity.h"
#include "ax25.h"
#include <string.h>

void setUp(void) {}
void tearDown(void) {}

void test_encode_address_simple(void) {
  ax25_address_t a = { .callsign = "UN8SAT", .ssid = 1 };
  uint8_t out[7] = { 0 };
  TEST_ASSERT_EQUAL(AX25_OK, ax25_encode_address(&a, false, out));
  TEST_ASSERT_EQUAL('U' << 1, out[0]);
  TEST_ASSERT_EQUAL('N' << 1, out[1]);
  TEST_ASSERT_EQUAL('8' << 1, out[2]);
  TEST_ASSERT_EQUAL('S' << 1, out[3]);
  TEST_ASSERT_EQUAL('A' << 1, out[4]);
  TEST_ASSERT_EQUAL('T' << 1, out[5]);
  /* CRRSSIDH: 0 | 11 | 0001 | 0 = 0x62 */
  TEST_ASSERT_EQUAL(0x62, out[6]);
}

void test_encode_address_padded_short_callsign(void) {
  ax25_address_t a = { .callsign = "CQ", .ssid = 0 };
  uint8_t out[7] = { 0 };
  TEST_ASSERT_EQUAL(AX25_OK, ax25_encode_address(&a, false, out));
  TEST_ASSERT_EQUAL('C' << 1, out[0]);
  TEST_ASSERT_EQUAL('Q' << 1, out[1]);
  TEST_ASSERT_EQUAL(' ' << 1, out[2]);
  TEST_ASSERT_EQUAL(' ' << 1, out[3]);
  TEST_ASSERT_EQUAL(' ' << 1, out[4]);
  TEST_ASSERT_EQUAL(' ' << 1, out[5]);
  TEST_ASSERT_EQUAL(0x60, out[6]);
}

void test_encode_address_last_sets_h_bit(void) {
  ax25_address_t a = { .callsign = "UN8SAT", .ssid = 1 };
  uint8_t out[7] = { 0 };
  ax25_encode_address(&a, true, out);
  TEST_ASSERT_EQUAL(0x63, out[6]);  /* H-bit set */
}

void test_decode_address_round_trip(void) {
  ax25_address_t in = { .callsign = "UN8SAT", .ssid = 1 };
  uint8_t enc[7];
  ax25_encode_address(&in, true, enc);

  ax25_address_t out;
  bool is_last = false;
  TEST_ASSERT_EQUAL(AX25_OK, ax25_decode_address(enc, &is_last, &out));
  TEST_ASSERT_TRUE(is_last);
  TEST_ASSERT_EQUAL_MEMORY("UN8SAT", out.callsign, 6);
  TEST_ASSERT_EQUAL(1, out.ssid);
}

void test_decode_address_trims_padding(void) {
  ax25_address_t in = { .callsign = "CQ", .ssid = 0 };
  uint8_t enc[7];
  ax25_encode_address(&in, false, enc);

  ax25_address_t out;
  bool is_last = true;
  TEST_ASSERT_EQUAL(AX25_OK, ax25_decode_address(enc, &is_last, &out));
  TEST_ASSERT_FALSE(is_last);
  TEST_ASSERT_EQUAL_MEMORY("CQ\0\0\0\0", out.callsign, 6);
  TEST_ASSERT_EQUAL(0, out.ssid);
}

void test_decode_rejects_lowercase_char(void) {
  /* 0xC2 = 'a' << 1 — lowercase is not valid in AX.25 callsigns. */
  uint8_t bad[7] = { 0xC2, 0x40, 0x40, 0x40, 0x40, 0x40, 0x63 };
  ax25_address_t out;
  bool is_last = false;
  TEST_ASSERT_EQUAL(AX25_ERR_ADDRESS_INVALID,
                    ax25_decode_address(bad, &is_last, &out));
}

void test_encode_rejects_bad_ssid(void) {
  ax25_address_t a = { .callsign = "UN8SAT", .ssid = 16 };  /* > 15 */
  uint8_t out[7];
  TEST_ASSERT_EQUAL(AX25_ERR_ADDRESS_INVALID,
                    ax25_encode_address(&a, false, out));
}

int main(void) {
  UNITY_BEGIN();
  RUN_TEST(test_encode_address_simple);
  RUN_TEST(test_encode_address_padded_short_callsign);
  RUN_TEST(test_encode_address_last_sets_h_bit);
  RUN_TEST(test_decode_address_round_trip);
  RUN_TEST(test_decode_address_trims_padding);
  RUN_TEST(test_decode_rejects_lowercase_char);
  RUN_TEST(test_encode_rejects_bad_ssid);
  return UNITY_END();
}
