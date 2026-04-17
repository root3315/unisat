/**
 * @file test_virtual_uart_build.c
 * @brief Compile-only smoke test for VirtualUART.
 *
 * Verifies the SITL TCP shim builds cleanly on the host target
 * (Linux/macOS/Windows). Does NOT attempt a real connection — the
 * full end-to-end test happens in the demo orchestration (Phase 9).
 */

#include "unity/unity.h"
#include "virtual_uart.h"

void setUp(void) {}
void tearDown(void) {}

void test_shutdown_without_init_is_safe(void) {
  /* Idempotent: calling Shutdown before Init must not crash. */
  VirtualUART_Shutdown();
  VirtualUART_Shutdown();
  TEST_ASSERT_TRUE(1);
}

void test_recv_on_uninit_returns_zero(void) {
  uint8_t buf[16];
  int n = VirtualUART_Recv(buf, sizeof(buf));
  TEST_ASSERT_EQUAL(0, n);
}

void test_send_on_uninit_returns_false(void) {
  const uint8_t b = 0x55;
  TEST_ASSERT_FALSE(VirtualUART_Send(&b, 1));
}

void test_init_to_closed_port_returns_false(void) {
  /* Connection to a port that is almost certainly not listening. */
  bool ok = VirtualUART_Init(1);  /* root-reserved, should refuse */
  TEST_ASSERT_FALSE(ok);
  VirtualUART_Shutdown();
}

int main(void) {
  UNITY_BEGIN();
  RUN_TEST(test_shutdown_without_init_is_safe);
  RUN_TEST(test_recv_on_uninit_returns_zero);
  RUN_TEST(test_send_on_uninit_returns_false);
  RUN_TEST(test_init_to_closed_port_returns_false);
  return UNITY_END();
}
