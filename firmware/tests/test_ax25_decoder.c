/**
 * @file test_ax25_decoder.c
 * @brief Streaming decoder tests (REQ-AX25-017/021/023/024).
 */

#include "unity/unity.h"
#include "ax25.h"
#include "ax25_decoder.h"
#include <string.h>

/* This repo's minimal Unity does NOT invoke setUp between RUN_TEST
 * calls — each test that uses `d` must init it explicitly. */
static ax25_decoder_t d;

void setUp(void) {}
void tearDown(void) {}

void test_init_zeros_state(void) {
  /* Poison before init. */
  memset(&d, 0xAA, sizeof(d));
  ax25_decoder_init(&d);
  TEST_ASSERT_EQUAL(AX25_STATE_HUNT, d.state);
  TEST_ASSERT_EQUAL(0, (int)d.frames_ok);
  TEST_ASSERT_EQUAL(0, (int)d.len);
  TEST_ASSERT_EQUAL(0, (int)d.bit_count);
}

/* REQ-AX25-017: streaming feed of a valid frame yields exactly one
 * frame_ready with identical contents to the batch decoder. */
void test_push_byte_single_frame(void) {
  ax25_decoder_init(&d);
  ax25_address_t dst = { .callsign = "CQ", .ssid = 0 };
  ax25_address_t src = { .callsign = "UN8SAT", .ssid = 1 };
  uint8_t frame[128];
  size_t n = 0;
  ax25_encode_ui_frame(&dst, &src, 0xF0, (const uint8_t *)"Hi", 2,
                         frame, sizeof(frame), &n);

  ax25_ui_frame_t out;
  bool ready;
  int ready_count = 0;
  for (size_t i = 0; i < n; i++) {
    ax25_decoder_push_byte(&d, frame[i], &out, &ready);
    if (ready) ready_count++;
  }
  TEST_ASSERT_EQUAL(1, ready_count);
  TEST_ASSERT_EQUAL(1, (int)d.frames_ok);
  TEST_ASSERT_EQUAL_MEMORY("Hi", out.info, 2);
  TEST_ASSERT_EQUAL(2, out.info_len);
  TEST_ASSERT_EQUAL_MEMORY("CQ", out.dst.callsign, 2);
  TEST_ASSERT_EQUAL_MEMORY("UN8SAT", out.src.callsign, 6);
  TEST_ASSERT_TRUE(out.fcs_valid);
}

/* REQ-AX25-023: idle flags between frames silently ignored. */
void test_push_byte_idle_flags_ignored(void) {
  ax25_decoder_init(&d);
  ax25_ui_frame_t out; bool ready;
  for (int i = 0; i < 10; i++) {
    ax25_decoder_push_byte(&d, 0x7E, &out, &ready);
    TEST_ASSERT_FALSE(ready);
  }
  TEST_ASSERT_EQUAL(0, (int)d.frames_ok);
  TEST_ASSERT_EQUAL(0, (int)d.frames_other_err);
}

/* REQ-AX25-023: back-to-back frames sharing a flag byte. */
void test_push_byte_back_to_back_frames(void) {
  ax25_decoder_init(&d);
  ax25_address_t dst = { .callsign = "CQ", .ssid = 0 };
  ax25_address_t src = { .callsign = "UN8SAT", .ssid = 1 };
  uint8_t a[64], b[64];
  size_t na = 0, nb = 0;
  ax25_encode_ui_frame(&dst, &src, 0xF0, (const uint8_t *)"A", 1, a, sizeof(a), &na);
  ax25_encode_ui_frame(&dst, &src, 0xF0, (const uint8_t *)"B", 1, b, sizeof(b), &nb);

  ax25_ui_frame_t out; bool ready;
  int seen = 0;
  uint8_t first_info = 0, second_info = 0;
  for (size_t i = 0; i < na; i++) {
    ax25_decoder_push_byte(&d, a[i], &out, &ready);
    if (ready) { seen++; first_info = out.info[0]; }
  }
  for (size_t i = 0; i < nb; i++) {
    ax25_decoder_push_byte(&d, b[i], &out, &ready);
    if (ready) { seen++; second_info = out.info[0]; }
  }
  TEST_ASSERT_EQUAL(2, seen);
  TEST_ASSERT_EQUAL('A', first_info);
  TEST_ASSERT_EQUAL('B', second_info);
  TEST_ASSERT_EQUAL(2, (int)d.frames_ok);
}

/* REQ-AX25-024: on error inside FRAME, decoder resets, does not
 * corrupt state for subsequent frames. */
void test_push_byte_recovers_after_garbage(void) {
  ax25_decoder_init(&d);
  ax25_ui_frame_t out; bool ready;

  /* Inject garbage with a leading flag. */
  ax25_decoder_push_byte(&d, 0x7E, &out, &ready);
  for (int i = 0; i < 50; i++) {
    ax25_decoder_push_byte(&d, 0xFF, &out, &ready);
  }
  TEST_ASSERT_EQUAL(AX25_STATE_HUNT, d.state);
  TEST_ASSERT_TRUE(d.frames_stuffing_err > 0);

  /* Now feed a real frame — it MUST decode. */
  ax25_address_t dst = { .callsign = "CQ", .ssid = 0 };
  ax25_address_t src = { .callsign = "UN8SAT", .ssid = 1 };
  uint8_t frame[64]; size_t n = 0;
  ax25_encode_ui_frame(&dst, &src, 0xF0, (const uint8_t *)"X", 1, frame, sizeof(frame), &n);

  int good = 0;
  for (size_t i = 0; i < n; i++) {
    ax25_decoder_push_byte(&d, frame[i], &out, &ready);
    if (ready) good++;
  }
  TEST_ASSERT_EQUAL(1, good);
  TEST_ASSERT_EQUAL('X', out.info[0]);
}

/* REQ-AX25-014: decoder never crashes on arbitrary garbage. */
void test_push_byte_fuzz_never_crashes(void) {
  ax25_decoder_init(&d);
  ax25_ui_frame_t out; bool ready;
  /* Deterministic LCG so the test is reproducible. */
  uint32_t seed = 0xDEADBEEF;
  for (int i = 0; i < 10000; i++) {
    seed = seed * 1103515245u + 12345u;
    ax25_decoder_push_byte(&d, (uint8_t)(seed >> 16), &out, &ready);
  }
  /* No crash = pass. No specific assertion on frames_ok. */
  TEST_ASSERT_TRUE(d.state == AX25_STATE_HUNT ||
                    d.state == AX25_STATE_FRAME);
}

int main(void) {
  UNITY_BEGIN();
  RUN_TEST(test_init_zeros_state);
  RUN_TEST(test_push_byte_single_frame);
  RUN_TEST(test_push_byte_idle_flags_ignored);
  RUN_TEST(test_push_byte_back_to_back_frames);
  RUN_TEST(test_push_byte_recovers_after_garbage);
  RUN_TEST(test_push_byte_fuzz_never_crashes);
  return UNITY_END();
}
