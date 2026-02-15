"""Telemetry Decoder — Parse and decode CCSDS telemetry packets."""

import struct
from dataclasses import dataclass
from typing import Any


# APID to subsystem mapping
APID_MAP = {
    0x001: "OBC", 0x002: "EPS", 0x003: "COMM", 0x004: "ADCS",
    0x005: "GNSS", 0x006: "Camera", 0x007: "Payload",
    0x010: "Error", 0x0FF: "Beacon",
}


@dataclass
class DecodedTelemetry:
    """Decoded telemetry packet."""
    apid: int
    subsystem: str
    sequence: int
    timestamp: int
    fields: dict[str, Any]


def decode_obc(data: bytes) -> dict[str, Any]:
    """Decode OBC housekeeping telemetry."""
    if len(data) < 18:
        return {}
    uptime, resets, cpu_temp, free_heap = struct.unpack_from("<IIfI", data, 0)
    state = data[16]
    errors = struct.unpack_from("<H", data, 17)[0] if len(data) >= 19 else 0
    return {
        "uptime_s": uptime, "reset_count": resets,
        "cpu_temp_c": round(cpu_temp, 2), "free_heap_bytes": free_heap,
        "state": state, "error_count": errors,
    }


def decode_eps(data: bytes) -> dict[str, Any]:
    """Decode EPS telemetry."""
    if len(data) < 32:
        return {}
    values = struct.unpack_from("<8f", data, 0)
    names = ["battery_v", "battery_a", "battery_soc", "solar_v",
             "solar_a", "solar_w", "bus_v", "total_w"]
    return {k: round(v, 3) for k, v in zip(names, values)}


def decode_adcs(data: bytes) -> dict[str, Any]:
    """Decode ADCS attitude telemetry."""
    if len(data) < 34:
        return {}
    mode = data[0]
    quat = struct.unpack_from("<4f", data, 1)
    rates = struct.unpack_from("<3f", data, 17)
    error = struct.unpack_from("<f", data, 29)[0]
    return {
        "mode": mode, "quaternion": [round(q, 4) for q in quat],
        "angular_rate_dps": [round(r, 4) for r in rates],
        "pointing_error_deg": round(error, 2),
    }


def decode_gnss(data: bytes) -> dict[str, Any]:
    """Decode GNSS position telemetry."""
    if len(data) < 38:
        return {}
    lat, lon, alt = struct.unpack_from("<3d", data, 0)
    vx, vy, vz = struct.unpack_from("<3f", data, 24)
    sats, fix = data[36], data[37]
    return {
        "latitude": round(lat, 6), "longitude": round(lon, 6),
        "altitude_m": round(alt, 1),
        "velocity": [round(vx, 2), round(vy, 2), round(vz, 2)],
        "satellites": sats, "fix_type": fix,
    }


def decode_beacon(data: bytes) -> dict[str, Any]:
    """Decode beacon packet."""
    if len(data) < 14:
        return {}
    state = data[0]
    uptime = struct.unpack_from("<I", data, 1)[0]
    batt_v = struct.unpack_from("<f", data, 5)[0]
    soc = struct.unpack_from("<f", data, 9)[0]
    return {
        "state": state, "uptime_s": uptime,
        "battery_v": round(batt_v, 2), "battery_soc": round(soc, 1),
    }


DECODERS = {
    0x001: decode_obc, 0x002: decode_eps, 0x004: decode_adcs,
    0x005: decode_gnss, 0x0FF: decode_beacon,
}


def decode_packet(apid: int, timestamp: int, sequence: int,
                  data: bytes) -> DecodedTelemetry:
    """Decode a telemetry packet by APID."""
    decoder = DECODERS.get(apid)
    fields = decoder(data) if decoder else {"raw": data.hex()}
    return DecodedTelemetry(
        apid=apid, subsystem=APID_MAP.get(apid, "Unknown"),
        sequence=sequence, timestamp=timestamp, fields=fields,
    )
