/**
 * @file test_ccsds.c
 * @brief Unit tests for CCSDS packet module
 */

#include "unity/unity.h"
#include "../stm32/Core/Inc/ccsds.h"
#include <string.h>

void setUp(void) { CCSDS_Init(); }
void tearDown(void) {}

void test_crc16_known_value(void) {
    uint8_t data[] = {0x01, 0x02, 0x03, 0x04};
    uint16_t crc = CCSDS_CalculateCRC16(data, 4);
    TEST_ASSERT_NOT_EQUAL(0, crc);
}

void test_build_packet_sets_apid(void) {
    CCSDS_Packet_t packet;
    uint8_t data[] = {0xAA, 0xBB};
    CCSDS_BuildPacket(&packet, APID_OBC_HOUSEKEEPING, CCSDS_TELEMETRY, 0, data, 2);
    uint16_t apid = packet.primary.version_type_apid & 0x7FF;
    TEST_ASSERT_EQUAL(APID_OBC_HOUSEKEEPING, apid);
}

void test_sequence_counter_increments(void) {
    CCSDS_ResetSequenceCount();
    TEST_ASSERT_EQUAL(0, CCSDS_GetSequenceCount());
    CCSDS_Packet_t p;
    uint8_t d = 0;
    CCSDS_BuildPacket(&p, 1, CCSDS_TELEMETRY, 0, &d, 1);
    TEST_ASSERT_EQUAL(1, CCSDS_GetSequenceCount());
    CCSDS_BuildPacket(&p, 1, CCSDS_TELEMETRY, 0, &d, 1);
    TEST_ASSERT_EQUAL(2, CCSDS_GetSequenceCount());
}

void test_serialize_and_parse_roundtrip(void) {
    CCSDS_Packet_t original, parsed;
    uint8_t data[] = {0x01, 0x02, 0x03, 0x04, 0x05};
    uint8_t buffer[256];

    CCSDS_BuildPacket(&original, APID_EPS_TELEMETRY, CCSDS_TELEMETRY, 1, data, 5);
    uint16_t len = CCSDS_Serialize(&original, buffer, sizeof(buffer));
    TEST_ASSERT_GREATER_THAN(0, len);

    bool ok = CCSDS_Parse(buffer, len, &parsed);
    TEST_ASSERT_TRUE(ok);
    TEST_ASSERT_EQUAL(5, parsed.data_length);
    TEST_ASSERT_EQUAL_MEMORY(data, parsed.data, 5);
}

void test_crc_validation_detects_corruption(void) {
    CCSDS_Packet_t packet;
    uint8_t data[] = {0xFF};
    uint8_t buffer[256];

    CCSDS_BuildPacket(&packet, 1, CCSDS_TELEMETRY, 0, data, 1);
    uint16_t len = CCSDS_Serialize(&packet, buffer, sizeof(buffer));

    /* Corrupt one byte */
    buffer[len / 2] ^= 0xFF;
    TEST_ASSERT_FALSE(CCSDS_ValidateCRC(buffer, len));
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_crc16_known_value);
    RUN_TEST(test_build_packet_sets_apid);
    RUN_TEST(test_sequence_counter_increments);
    RUN_TEST(test_serialize_and_parse_roundtrip);
    RUN_TEST(test_crc_validation_detects_corruption);
    return UNITY_END();
}
