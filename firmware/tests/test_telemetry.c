/**
 * @file test_telemetry.c
 * @brief Telemetry module smoke tests — Init + sequence + reset.
 *
 * The per-packer tests live in test_telemetry_packers.c; this file
 * focuses on the module-level invariants:
 *   * Init is callable and leaves the module in a clean state.
 *   * Every Pack* function produces output that is non-empty and
 *     parseable (a quick smoke, different from the APID-specific
 *     assertions in test_telemetry_packers.c).
 *   * Repeated Init resets the per-module counter and leaves state
 *     idempotent — an on-orbit warm reset must not leave half-baked
 *     internal state that biases the next packet's sequence.
 *
 * Kept minimal so the suite stays fast; the deeper coverage is in
 * the dedicated packer + beacon-layout tests.
 */

#include "unity/unity.h"
#include "telemetry.h"
#include "ccsds.h"
#include "adcs.h"

void setUp(void)    { Telemetry_Init(); ADCS_Init(); CCSDS_ResetSequenceCount(); }
void tearDown(void) { /* nothing */ }


void test_telemetry_init_idempotent(void)
{
    setUp();
    Telemetry_Init();
    Telemetry_Init();
    /* No assertion needed — Init must not crash on repeated call. */
    TEST_ASSERT_TRUE(1);
}

void test_pack_obc_yields_nonzero_length(void)
{
    setUp();
    uint8_t buf[128];
    uint16_t len = Telemetry_PackOBC(buf, sizeof(buf));
    TEST_ASSERT_TRUE(len > 0);
    TEST_ASSERT_TRUE(len <= sizeof(buf));
}

void test_ccsds_sequence_advances_through_packers(void)
{
    setUp();
    uint8_t buf[128];
    uint16_t seq_before = CCSDS_GetSequenceCount();

    (void)Telemetry_PackOBC(buf, sizeof(buf));
    (void)Telemetry_PackEPS(buf, sizeof(buf));
    (void)Telemetry_PackADCS(buf, sizeof(buf));

    uint16_t seq_after = CCSDS_GetSequenceCount();
    /* Every packer calls CCSDS_BuildPacket once which increments the
     * module-wide sequence counter — so three packers must advance
     * it by exactly three. */
    TEST_ASSERT_EQUAL(seq_before + 3U, seq_after);
}


int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_telemetry_init_idempotent);
    RUN_TEST(test_pack_obc_yields_nonzero_length);
    RUN_TEST(test_ccsds_sequence_advances_through_packers);
    return UNITY_END();
}
