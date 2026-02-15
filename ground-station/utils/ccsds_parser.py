"""CCSDS Parser — Parse raw bytes into structured CCSDS packets."""

import struct
from dataclasses import dataclass

PRIMARY_HEADER_SIZE = 6
SECONDARY_HEADER_SIZE = 10
CRC_SIZE = 2


@dataclass
class CCSDSPacket:
    """Parsed CCSDS space packet."""
    version: int
    packet_type: int
    apid: int
    sequence_flags: int
    sequence_count: int
    data_length: int
    timestamp: int
    subsystem_id: int
    packet_subtype: int
    payload: bytes
    crc: int
    crc_valid: bool


def crc16_ccitt(data: bytes) -> int:
    """Calculate CRC-16/CCITT checksum."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc


def parse_packet(raw: bytes) -> CCSDSPacket | None:
    """Parse raw bytes into a CCSDS packet structure."""
    min_size = PRIMARY_HEADER_SIZE + SECONDARY_HEADER_SIZE + CRC_SIZE
    if len(raw) < min_size:
        return None

    # Primary header (big-endian)
    word0, word1, word2 = struct.unpack_from(">HHH", raw, 0)

    version = (word0 >> 13) & 0x07
    packet_type = (word0 >> 12) & 0x01
    apid = word0 & 0x7FF
    seq_flags = (word1 >> 14) & 0x03
    seq_count = word1 & 0x3FFF
    data_length = word2

    # Secondary header
    offset = PRIMARY_HEADER_SIZE
    timestamp = struct.unpack_from(">Q", raw, offset)[0]
    offset += 8
    subsystem_id = raw[offset]
    packet_subtype = raw[offset + 1]
    offset += 2

    # Payload
    payload_size = len(raw) - offset - CRC_SIZE
    if payload_size < 0:
        return None
    payload = raw[offset:offset + payload_size]

    # CRC
    received_crc = struct.unpack_from(">H", raw, len(raw) - CRC_SIZE)[0]
    calculated_crc = crc16_ccitt(raw[:-CRC_SIZE])
    crc_valid = received_crc == calculated_crc

    return CCSDSPacket(
        version=version, packet_type=packet_type, apid=apid,
        sequence_flags=seq_flags, sequence_count=seq_count,
        data_length=data_length, timestamp=timestamp,
        subsystem_id=subsystem_id, packet_subtype=packet_subtype,
        payload=payload, crc=received_crc, crc_valid=crc_valid,
    )


def build_packet(apid: int, subsystem: int, data: bytes,
                 packet_type: int = 0) -> bytes:
    """Build a CCSDS packet from components."""
    seq_count = 0  # Would be tracked globally
    word0 = (0 << 13) | (packet_type << 12) | (1 << 11) | (apid & 0x7FF)
    word1 = (3 << 14) | (seq_count & 0x3FFF)

    secondary = struct.pack(">Q", 0) + bytes([subsystem, 0])
    total_data_len = SECONDARY_HEADER_SIZE + len(data) + CRC_SIZE - 1
    word2 = total_data_len

    header = struct.pack(">HHH", word0, word1, word2)
    body = header + secondary + data
    crc = crc16_ccitt(body)
    return body + struct.pack(">H", crc)
