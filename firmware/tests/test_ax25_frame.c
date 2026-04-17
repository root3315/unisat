/**
 * @file test_ax25_frame.c
 * @brief UI-frame encode / pure decode tests (REQ-AX25-001..015, 018).
 */

#include "unity/unity.h"
#include "ax25.h"
#include <string.h>

void setUp(void) {}
void tearDown(void) {}

static size_t unwrap(const uint8_t *frame, size_t n,
                      uint8_t *body, size_t cap) {
  /* Strip leading/trailing 0x7E flags, then bit-unstuff the middle. */
  ax25_status_t st;
  return ax25_bit_unstuff(&frame[1], n - 2, body, cap, &st);
}

void test_encode_has_flags_at_both_ends(void) {
  ax25_address_t dst = { .callsign = "CQ", .ssid = 0 };
  ax25_address_t src = { .callsign = "UN8SAT", .ssid = 1 };
  uint8_t out[128] = { 0 };
  size_t n = 0;
  ax25_status_t st = ax25_encode_ui_frame(&dst, &src, 0xF0,
      (const uint8_t *)"Hi", 2, out, sizeof(out), &n);
  TEST_ASSERT_EQUAL(AX25_OK, st);
  TEST_ASSERT_TRUE(n > 20);
  TEST_ASSERT_EQUAL(0x7E, out[0]);
  TEST_ASSERT_EQUAL(0x7E, out[n - 1]);
}

void test_encode_rejects_info_too_long(void) {
  ax25_address_t dst = { .callsign = "CQ", .ssid = 0 };
  ax25_address_t src = { .callsign = "UN8SAT", .ssid = 1 };
  uint8_t info[AX25_MAX_INFO_LEN + 1] = { 0 };
  uint8_t out[512];
  size_t n = 0;
  TEST_ASSERT_EQUAL(AX25_ERR_INFO_TOO_LONG,
      ax25_encode_ui_frame(&dst, &src, 0xF0, info, sizeof(info),
          out, sizeof(out), &n));
}

void test_encode_rejects_buffer_overflow(void) {
  ax25_address_t dst = { .callsign = "CQ", .ssid = 0 };
  ax25_address_t src = { .callsign = "UN8SAT", .ssid = 1 };
  uint8_t info[2] = { 'H', 'i' };
  uint8_t out[8];  /* too small for a 20-byte minimum frame */
  size_t n = 0;
  TEST_ASSERT_EQUAL(AX25_ERR_BUFFER_OVERFLOW,
      ax25_encode_ui_frame(&dst, &src, 0xF0, info, 2,
          out, sizeof(out), &n));
}

void test_decode_round_trip(void) {
  ax25_address_t dst = { .callsign = "CQ", .ssid = 0 };
  ax25_address_t src = { .callsign = "UN8SAT", .ssid = 1 };
  uint8_t frame[128];
  size_t n = 0;
  TEST_ASSERT_EQUAL(AX25_OK, ax25_encode_ui_frame(&dst, &src, 0xF0,
      (const uint8_t *)"Hi", 2, frame, sizeof(frame), &n));

  uint8_t body[128];
  size_t body_n = unwrap(frame, n, body, sizeof(body));
  TEST_ASSERT_TRUE(body_n >= 18);

  ax25_ui_frame_t decoded;
  TEST_ASSERT_EQUAL(AX25_OK,
      ax25_decode_ui_frame(body, body_n, &decoded));
  TEST_ASSERT_EQUAL_MEMORY("CQ", decoded.dst.callsign, 2);
  TEST_ASSERT_EQUAL(0, decoded.dst.ssid);
  TEST_ASSERT_EQUAL_MEMORY("UN8SAT", decoded.src.callsign, 6);
  TEST_ASSERT_EQUAL(1, decoded.src.ssid);
  TEST_ASSERT_EQUAL(0x03, decoded.control);
  TEST_ASSERT_EQUAL(0xF0, decoded.pid);
  TEST_ASSERT_EQUAL(2, decoded.info_len);
  TEST_ASSERT_EQUAL_MEMORY("Hi", decoded.info, 2);
  TEST_ASSERT_TRUE(decoded.fcs_valid);
}

void test_decode_rejects_bad_fcs(void) {
  uint8_t body[32];
  ax25_address_t d = { .callsign = "CQ", .ssid = 0 };
  ax25_address_t s = { .callsign = "UN8SAT", .ssid = 1 };
  ax25_encode_address(&d, false, &body[0]);
  ax25_encode_address(&s, true, &body[7]);
  body[14] = 0x03; body[15] = 0xF0;
  body[16] = 'H'; body[17] = 'i';
  body[18] = 0xDE; body[19] = 0xAD;  /* bogus FCS */

  ax25_ui_frame_t out;
  TEST_ASSERT_EQUAL(AX25_ERR_FCS_MISMATCH,
      ax25_decode_ui_frame(body, 20, &out));
}

/* REQ-AX25-018: digipeater paths rejected. */
void test_decode_rejects_digipeater_path(void) {
  uint8_t body[64];
  ax25_address_t d = { .callsign = "CQ", .ssid = 0 };
  ax25_address_t s = { .callsign = "UN8SAT", .ssid = 1 };
  ax25_address_t r = { .callsign = "REPEAT", .ssid = 0 };
  ax25_encode_address(&d, false, &body[0]);
  ax25_encode_address(&s, false, &body[7]);   /* H=0 -> more follows */
  ax25_encode_address(&r, true,  &body[14]);
  body[21] = 0x03; body[22] = 0xF0; body[23] = 'X';
  uint16_t fcs = ax25_fcs_crc16(body, 24);
  body[24] = (uint8_t)fcs;
  body[25] = (uint8_t)(fcs >> 8);

  ax25_ui_frame_t out;
  TEST_ASSERT_EQUAL(AX25_ERR_ADDRESS_INVALID,
      ax25_decode_ui_frame(body, 26, &out));
}

void test_decode_rejects_bad_control(void) {
  uint8_t body[32];
  ax25_address_t d = { .callsign = "CQ", .ssid = 0 };
  ax25_address_t s = { .callsign = "UN8SAT", .ssid = 1 };
  ax25_encode_address(&d, false, &body[0]);
  ax25_encode_address(&s, true,  &body[7]);
  body[14] = 0x99;   /* not 0x03 */
  body[15] = 0xF0;
  uint16_t fcs = ax25_fcs_crc16(body, 16);
  body[16] = (uint8_t)fcs;
  body[17] = (uint8_t)(fcs >> 8);

  ax25_ui_frame_t out;
  TEST_ASSERT_EQUAL(AX25_ERR_CONTROL_INVALID,
      ax25_decode_ui_frame(body, 18, &out));
}

void test_decode_rejects_bad_pid(void) {
  uint8_t body[32];
  ax25_address_t d = { .callsign = "CQ", .ssid = 0 };
  ax25_address_t s = { .callsign = "UN8SAT", .ssid = 1 };
  ax25_encode_address(&d, false, &body[0]);
  ax25_encode_address(&s, true,  &body[7]);
  body[14] = 0x03;
  body[15] = 0xEE;   /* not 0xF0 */
  uint16_t fcs = ax25_fcs_crc16(body, 16);
  body[16] = (uint8_t)fcs;
  body[17] = (uint8_t)(fcs >> 8);

  ax25_ui_frame_t out;
  TEST_ASSERT_EQUAL(AX25_ERR_PID_INVALID,
      ax25_decode_ui_frame(body, 18, &out));
}

int main(void) {
  UNITY_BEGIN();
  RUN_TEST(test_encode_has_flags_at_both_ends);
  RUN_TEST(test_encode_rejects_info_too_long);
  RUN_TEST(test_encode_rejects_buffer_overflow);
  RUN_TEST(test_decode_round_trip);
  RUN_TEST(test_decode_rejects_bad_fcs);
  RUN_TEST(test_decode_rejects_digipeater_path);
  RUN_TEST(test_decode_rejects_bad_control);
  RUN_TEST(test_decode_rejects_bad_pid);
  return UNITY_END();
}
