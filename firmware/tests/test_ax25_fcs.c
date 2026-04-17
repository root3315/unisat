/**
 * @file test_ax25_fcs.c
 * @brief FCS CRC-16/X.25 oracle tests (REQ-AX25-022).
 */

#include "unity/unity.h"
#include "ax25.h"
#include <string.h>

void setUp(void) {}
void tearDown(void) {}

/* REQ-AX25-022: canonical reference vector. */
void test_fcs_reference_vector_123456789(void) {
  const char *s = "123456789";
  uint16_t fcs = ax25_fcs_crc16((const uint8_t *)s, 9);
  TEST_ASSERT_EQUAL(0x906E, fcs);
}

void test_fcs_empty_input_returns_zero(void) {
  /* init 0xFFFF, no data, xorout 0xFFFF -> 0x0000 */
  uint16_t fcs = ax25_fcs_crc16(NULL, 0);
  TEST_ASSERT_EQUAL(0x0000, fcs);
}

void test_fcs_single_zero_byte(void) {
  /* CRC-16/X.25 of a single 0x00 byte. Hand-computed reference
   * (also verifiable via `python -c "import crcmod; print(hex(
   * crcmod.predefined.mkPredefinedCrcFun('x-25')(b'\\x00')))"`). */
  const uint8_t zero = 0;
  uint16_t fcs = ax25_fcs_crc16(&zero, 1);
  TEST_ASSERT_EQUAL(0xF078, fcs);
}

int main(void) {
  UNITY_BEGIN();
  RUN_TEST(test_fcs_reference_vector_123456789);
  RUN_TEST(test_fcs_empty_input_returns_zero);
  RUN_TEST(test_fcs_single_zero_byte);
  return UNITY_END();
}
