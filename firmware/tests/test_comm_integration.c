/**
 * @file test_comm_integration.c
 * @brief End-to-end COMM <-> AX.25 decoder integration test.
 *
 * Feeds encoded frame bytes through COMM_UART_RxCallback (as if the
 * UART IRQ had delivered them one by one), then calls
 * COMM_ProcessRxBuffer() and asserts that the AX.25 decoder saw a
 * valid frame.
 */

#include "unity/unity.h"
#include "comm.h"
#include "ax25_api.h"

void setUp(void) {}
void tearDown(void) {}

/* Capture decoded payload from a strong CCSDS_Dispatcher_Submit
 * override (replaces the weak sink in comm.c). */
static uint8_t  last_payload[256];
static uint16_t last_payload_len = 0;

void CCSDS_Dispatcher_Submit(const uint8_t *data, uint16_t n) {
    last_payload_len = n > sizeof(last_payload) ? (uint16_t)sizeof(last_payload) : n;
    memcpy(last_payload, data, last_payload_len);
}

void test_rx_ring_drained_through_decoder(void) {
    COMM_Init();
    last_payload_len = 0;

    /* Build an AX.25 frame using the project-style facade. */
    AX25_Address_t dst = { .callsign = "CQ", .ssid = 0 };
    AX25_Address_t src = { .callsign = "UN8SAT", .ssid = 1 };
    uint8_t frame[128];
    uint16_t n = 0;
    TEST_ASSERT_TRUE(AX25_EncodeUiFrame(&dst, &src, 0xF0,
        (const uint8_t *)"hello", 5, frame, sizeof(frame), &n));

    /* Simulate ISR pushing each byte into the ring buffer. */
    for (uint16_t i = 0; i < n; i++) {
        COMM_UART_RxCallback(COMM_CHANNEL_UHF, frame[i]);
    }

    /* Task wakes up and drains. */
    COMM_ProcessRxBuffer();

    COMM_Status_t st = COMM_GetStatus();
    TEST_ASSERT_EQUAL(1, (int)st.ax25_frames_ok);
    TEST_ASSERT_EQUAL(0, (int)st.ax25_fcs_errors);
    TEST_ASSERT_EQUAL(0, (int)st.ax25_frame_errors);
    TEST_ASSERT_EQUAL(5, (int)last_payload_len);
    TEST_ASSERT_EQUAL_MEMORY("hello", last_payload, 5);
}

void test_comm_send_ax25_wraps_info_correctly(void) {
    COMM_Init();

    uint8_t info[3] = { 'A', 'B', 'C' };
    TEST_ASSERT_TRUE(COMM_SendAX25(COMM_CHANNEL_UHF,
        "CQ", 0, "UN8SAT", 1, info, 3));

    /* Under SIMULATION_MODE COMM_Send just bumps packets_sent. */
    COMM_Status_t st = COMM_GetStatus();
    TEST_ASSERT_EQUAL(1, (int)st.packets_sent);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_rx_ring_drained_through_decoder);
    RUN_TEST(test_comm_send_ax25_wraps_info_correctly);
    return UNITY_END();
}
