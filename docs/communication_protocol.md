# Communication Protocol

## CCSDS Space Packet Format

All telemetry and telecommand packets follow CCSDS 133.0-B-2.

### Packet Structure

| Field | Size | Description |
|-------|------|-------------|
| Primary Header | 6 bytes | Version, Type, APID, Sequence, Length |
| Secondary Header | 10 bytes | Timestamp (8B), Subsystem ID, Subtype |
| Data Field | variable | Payload data |
| CRC-16 | 2 bytes | CRC-16/CCITT over entire packet |

### APID Assignments

| APID | Subsystem | Direction |
|------|-----------|-----------|
| 0x001 | OBC Housekeeping | TM |
| 0x002 | EPS Telemetry | TM |
| 0x003 | COMM Status | TM |
| 0x004 | ADCS Attitude | TM |
| 0x005 | GNSS Position | TM |
| 0x006 | Camera Status | TM |
| 0x007 | Payload Data | TM |
| 0x010 | Error Report | TM |
| 0x0FF | Beacon | TM |
| 0x100 | Telecommand | TC |

### Command Authentication

All telecommands are authenticated using HMAC-SHA256:
- Shared secret key pre-loaded on satellite
- Sequence number prevents replay attacks
- Timestamp within ±60s window for freshness

### Link Parameters

| Parameter | UHF | S-band |
|-----------|-----|--------|
| Frequency | 437 MHz | 2.4 GHz |
| Data Rate | 9600 bps | 256 kbps |
| Modulation | GMSK | QPSK |
| Protocol | AX.25 | CCSDS |
| TX Power | 1 W | 2 W |
