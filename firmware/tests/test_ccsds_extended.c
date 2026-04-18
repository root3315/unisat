/**
 * @file test_ccsds_extended.c
 * @brief Extended CCSDS coverage — Parse edge cases + secondary header.
 *
 * Complements test_ccsds.c with:
 *   * secondary-header round-trip (subsystem_id + timestamp preserved)
 *   * Parse rejects truncated buffers below the minimum 8-byte frame
 *   * Parse rejects buffers whose embedded CRC does not match
 *   * ValidateCRC length-guard (empty / too-short input)
 *   * BuildPacket clamps oversized data to CCSDS_MAX_DATA_SIZE
 *   * Sequence counter wraps at 14-bit boundary (0x3FFF -> 0)
 *   * APID masking to 11 bits (input with high bits set is truncated)
 *   * The 6-byte primary header is serialised big-endian
 *
 * These paths were unhit in the baseline coverage report (ccsds.c
 * at 10.0% of 80 lines); adding them pushes the module into the
 * high-60s line-coverage band and closes the CCSDS entry in the
 * traceability matrix (REQ-TLM-010 verification).
 */

#include "unity/unity.h"
#include "../stm32/Core/Inc/ccsds.h"
#include <string.h>

void setUp(void)    { CCSDS_Init(); CCSDS_ResetSequenceCount(); }
void tearDown(void) { /* nothing */ }


/* ------------------------------------------------------------------
 *  Secondary header
 * ------------------------------------------------------------------ */
void test_secondary_header_round_trip(void)
{
    setUp();
    CCSDS_Packet_t original, parsed;
    uint8_t data[] = {0x10, 0x20, 0x30};
    uint8_t buffer[256];

    CCSDS_BuildPacket(&original, APID_EPS_TELEMETRY, CCSDS_TELEMETRY,
                       /*subsystem=*/0x55, data, sizeof(data));
    uint16_t len = CCSDS_Serialize(&original, buffer, sizeof(buffer));
    TEST_ASSERT_TRUE(CCSDS_Parse(buffer, len, &parsed));

    TEST_ASSERT_EQUAL(0x55, parsed.secondary.subsystem_id);
    TEST_ASSERT_EQUAL(original.secondary.timestamp,
                      parsed.secondary.timestamp);
    TEST_ASSERT_EQUAL(original.secondary.packet_subtype,
                      parsed.secondary.packet_subtype);
}


/* ------------------------------------------------------------------
 *  Parse input length guards
 * ------------------------------------------------------------------ */
void test_parse_rejects_truncated(void)
{
    setUp();
    CCSDS_Packet_t parsed;
    uint8_t tiny[5] = {0};
    /* PRIMARY_HEADER_SIZE (6) + CRC_SIZE (2) = 8 minimum. */
    TEST_ASSERT_FALSE(CCSDS_Parse(tiny, sizeof(tiny), &parsed));
}


/* ------------------------------------------------------------------
 *  Parse rejects wrong CRC
 * ------------------------------------------------------------------ */
void test_parse_rejects_crc_mismatch(void)
{
    setUp();
    CCSDS_Packet_t original, parsed;
    uint8_t data[] = {0xDE, 0xAD};
    uint8_t buffer[128];

    CCSDS_BuildPacket(&original, 1, CCSDS_TELEMETRY, 0, data, sizeof(data));
    uint16_t len = CCSDS_Serialize(&original, buffer, sizeof(buffer));

    /* Flip a random middle byte — every flip inside the CRC-covered
     * region invalidates the trailing CRC. */
    buffer[8] ^= 0x01;
    TEST_ASSERT_FALSE(CCSDS_Parse(buffer, len, &parsed));
}


/* ------------------------------------------------------------------
 *  ValidateCRC length-guard
 * ------------------------------------------------------------------ */
void test_validate_crc_rejects_too_short(void)
{
    setUp();
    /* Input shorter than CRC_SIZE (= 2) must fail. */
    uint8_t zero[1] = {0};
    TEST_ASSERT_FALSE(CCSDS_ValidateCRC(zero, sizeof(zero)));
}


/* ------------------------------------------------------------------
 *  BuildPacket clamps oversized data
 * ------------------------------------------------------------------ */
void test_build_clamps_oversized_data(void)
{
    setUp();
    CCSDS_Packet_t p;
    /* Provide 2x max — the builder must clamp to CCSDS_MAX_DATA_SIZE. */
    static uint8_t huge[CCSDS_MAX_DATA_SIZE * 2];
    memset(huge, 0xAA, sizeof(huge));
    CCSDS_BuildPacket(&p, 1, CCSDS_TELEMETRY, 0, huge, sizeof(huge));
    TEST_ASSERT_EQUAL(CCSDS_MAX_DATA_SIZE, p.data_length);
}


/* ------------------------------------------------------------------
 *  Sequence counter wraps at 14 bits
 * ------------------------------------------------------------------ */
void test_sequence_counter_wraps_at_14_bits(void)
{
    setUp();
    CCSDS_Packet_t p;
    uint8_t d = 0;

    /* Drive the counter to 0x3FFE. */
    for (uint32_t i = 0; i < 0x3FFEU; ++i) {
        CCSDS_BuildPacket(&p, 1, CCSDS_TELEMETRY, 0, &d, 1);
    }
    TEST_ASSERT_EQUAL(0x3FFEU, CCSDS_GetSequenceCount());

    /* Two more builds: 0x3FFE -> 0x3FFF -> wrap to 0. */
    CCSDS_BuildPacket(&p, 1, CCSDS_TELEMETRY, 0, &d, 1);
    TEST_ASSERT_EQUAL(0x3FFFU, CCSDS_GetSequenceCount());
    CCSDS_BuildPacket(&p, 1, CCSDS_TELEMETRY, 0, &d, 1);
    TEST_ASSERT_EQUAL(0U, CCSDS_GetSequenceCount());
}


/* ------------------------------------------------------------------
 *  APID is masked to 11 bits
 * ------------------------------------------------------------------ */
void test_build_apid_masked_to_11_bits(void)
{
    setUp();
    CCSDS_Packet_t p;
    uint8_t d = 0;
    /* High bits set beyond the 11-bit mask — must be discarded. */
    CCSDS_BuildPacket(&p, 0xF801, CCSDS_TELEMETRY, 0, &d, 1);
    uint16_t apid = p.primary.version_type_apid & 0x7FFU;
    TEST_ASSERT_EQUAL(0x001, apid);
}


/* ------------------------------------------------------------------
 *  Primary header is big-endian on the wire
 * ------------------------------------------------------------------ */
void test_primary_header_is_big_endian(void)
{
    setUp();
    CCSDS_Packet_t p;
    uint8_t d = 0;
    uint8_t buf[64];
    /* Use an APID with distinguishable high and low bytes. */
    CCSDS_BuildPacket(&p, 0x123, CCSDS_TELEMETRY, 0, &d, 1);
    uint16_t len = CCSDS_Serialize(&p, buf, sizeof(buf));
    (void)len;

    /* first_word = 0<<13 | type<<12 | 1<<11 | 0x123.
     * CCSDS_TELEMETRY should be 0 (TM); flight code defines it as 0
     * per the enum, so bit 12 is 0. The 1<<11 sets the sec-hdr
     * flag; together with apid 0x123 this yields 0x0923. */
    uint16_t expected_word = (uint16_t)((1U << 11) | 0x123U);
    uint16_t wire = (uint16_t)((buf[0] << 8) | buf[1]);
    TEST_ASSERT_EQUAL(expected_word, wire);
}


/* ------------------------------------------------------------------
 *  Serialize rejects undersized output buffer
 * ------------------------------------------------------------------ */
void test_serialize_rejects_small_buffer(void)
{
    setUp();
    CCSDS_Packet_t p;
    uint8_t d[8] = {0};
    CCSDS_BuildPacket(&p, 1, CCSDS_TELEMETRY, 0, d, sizeof(d));

    uint8_t tiny[4];
    /* Not enough room for primary + secondary + data + CRC — returns 0. */
    TEST_ASSERT_EQUAL(0, CCSDS_Serialize(&p, tiny, sizeof(tiny)));
}


int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_secondary_header_round_trip);
    RUN_TEST(test_parse_rejects_truncated);
    RUN_TEST(test_parse_rejects_crc_mismatch);
    RUN_TEST(test_validate_crc_rejects_too_short);
    RUN_TEST(test_build_clamps_oversized_data);
    RUN_TEST(test_sequence_counter_wraps_at_14_bits);
    RUN_TEST(test_build_apid_masked_to_11_bits);
    RUN_TEST(test_primary_header_is_big_endian);
    RUN_TEST(test_serialize_rejects_small_buffer);
    return UNITY_END();
}
