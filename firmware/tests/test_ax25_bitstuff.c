/**
 * @file test_ax25_bitstuff.c
 * @brief Bit-level stuffing tests (REQ-AX25-007 / REQ-AX25-016).
 */

#include "unity/unity.h"
#include "ax25.h"
#include <string.h>

void setUp(void) {}
void tearDown(void) {}

/* 0xFF LSB-first bits: 1,1,1,1,1,1,1,1.
 * After 5 ones, insert 0 -> 1,1,1,1,1,0,1,1,1 (9 bits).
 * Packed LSB-first into bytes:
 *   byte 0 (bits 0..7): 1,1,1,1,1,0,1,1 = 0xDF
 *   byte 1 (bit 8):     1               = 0x01 */
void test_stuff_all_ones_byte_inserts_one_zero(void) {
  const uint8_t in[1] = { 0xFF };
  uint8_t out[4] = { 0 };
  size_t n = ax25_bit_stuff(in, 1, out, sizeof(out));
  TEST_ASSERT_EQUAL(2, (int)n);
  TEST_ASSERT_EQUAL(0xDF, out[0]);
  TEST_ASSERT_EQUAL(0x01, out[1]);
}

void test_stuff_no_ones_unchanged(void) {
  const uint8_t in[2] = { 0x00, 0x00 };
  uint8_t out[4] = { 0 };
  size_t n = ax25_bit_stuff(in, 2, out, sizeof(out));
  TEST_ASSERT_EQUAL(2, (int)n);
  TEST_ASSERT_EQUAL(0x00, out[0]);
  TEST_ASSERT_EQUAL(0x00, out[1]);
}

/* REQ-AX25-016: byte-boundary stuffing.
 * Input 0x1F, 0xF8 LSB-first bits:
 *   byte 0: 1,1,1,1,1,0,0,0
 *   byte 1: 0,0,0,1,1,1,1,1
 * After stuff (two runs of five 1s each):
 *   1,1,1,1,1,0,0,0,0,0,0,0,1,1,1,1,1,0 (18 bits)
 * Packed LSB-first into 3 bytes:
 *   byte 0 (bits 0..7):  1,1,1,1,1,0,0,0 = 0x1F
 *   byte 1 (bits 8..15): 0,0,0,0,1,1,1,1 = 0xF0
 *   byte 2 (bits 16..17): 1,0 + padding  = 0x01 */
void test_stuff_across_byte_boundary(void) {
  const uint8_t in[2] = { 0x1F, 0xF8 };
  uint8_t out[8] = { 0 };
  size_t n = ax25_bit_stuff(in, 2, out, sizeof(out));
  TEST_ASSERT_EQUAL(3, (int)n);
  TEST_ASSERT_EQUAL(0x1F, out[0]);
  TEST_ASSERT_EQUAL(0xF0, out[1]);
  TEST_ASSERT_EQUAL(0x01, out[2]);
}

void test_unstuff_recovers_original_prefix(void) {
  /* Byte-level roundtrip loses exact length because the stuffed bit
   * stream may not be byte-aligned — trailing bits are zero padding.
   * The first len(original) bytes MUST match; the unstuff length may
   * be len(original) or len(original)+1 depending on padding. Frame
   * boundaries (0x7E flags) resolve this ambiguity in the streaming
   * decoder (Task 4.2). */
  const uint8_t original[3] = { 0x12, 0xFF, 0x34 };
  uint8_t stuffed[8] = { 0 };
  size_t ns = ax25_bit_stuff(original, 3, stuffed, sizeof(stuffed));
  TEST_ASSERT_TRUE(ns > 0);

  uint8_t recovered[8] = { 0 };
  ax25_status_t st = AX25_OK;
  size_t nr = ax25_bit_unstuff(stuffed, ns, recovered, sizeof(recovered), &st);
  TEST_ASSERT_EQUAL(AX25_OK, st);
  TEST_ASSERT_TRUE(nr >= 3);
  TEST_ASSERT_EQUAL_MEMORY(original, recovered, 3);
}

/* 0x3F = 00111111 LSB-first = 1,1,1,1,1,1,0,0 — six 1s is a violation. */
void test_unstuff_rejects_six_ones(void) {
  const uint8_t bad[1] = { 0x3F };
  uint8_t out[4] = { 0 };
  ax25_status_t st = AX25_OK;
  size_t n = ax25_bit_unstuff(bad, 1, out, sizeof(out), &st);
  TEST_ASSERT_EQUAL(0, (int)n);
  TEST_ASSERT_EQUAL(AX25_ERR_STUFFING_VIOLATION, st);
}

int main(void) {
  UNITY_BEGIN();
  RUN_TEST(test_stuff_all_ones_byte_inserts_one_zero);
  RUN_TEST(test_stuff_no_ones_unchanged);
  RUN_TEST(test_stuff_across_byte_boundary);
  RUN_TEST(test_unstuff_recovers_original_prefix);
  RUN_TEST(test_unstuff_rejects_six_ones);
  return UNITY_END();
}
