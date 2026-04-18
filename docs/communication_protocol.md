# Communication Protocol

Reference: CCSDS 133.0-B-2 (Space Packet Protocol), CCSDS 132.0-B-2 (TM Space Data Link), AX.25 Link Access Procedure v2.2

## Wire-format compatibility contract

Every byte layout described in this document — the beacon, the
authenticated command frame, the CCSDS header fields — is
**frozen within a major version** per [Semantic Versioning][sv].

[sv]: https://semver.org/spec/v2.0.0.html

- **Any additive change** (new field appended after the last one,
  new APID value, new flag bit in a reserved range) → minor bump
  (`1.2.x → 1.3.0`). Backwards-compatible receivers must ignore
  unknown trailing bytes / unknown APIDs.
- **Any breaking change** (reorder, resize, or remove an existing
  field; redefine a reserved bit; switch endianness) → **major
  bump** (`1.x → 2.0.0`).
- All multi-byte integer fields in this document are
  **big-endian** on the wire, matching CCSDS and ITU convention.
  This includes the 4-byte replay counter in the command frame
  (`command_dispatcher.h`).

Ground stations, flight firmware, and third-party decoders that
follow this contract can be mixed and matched across patch
releases without coordination.


## 1. Protocol Architecture

### 1.1 Protocol Stack

```
  Ground Station                                 Satellite
  +------------------+                          +------------------+
  | Application      |                          | Application      |
  | (GS Software)    |                          | (Flight SW)      |
  +--------+---------+                          +--------+---------+
           |                                             |
  +--------v---------+                          +--------v---------+
  | CCSDS Space      |  <-- Space Packet -->    | CCSDS Space      |
  | Packet Protocol  |     (TM/TC payload)      | Packet Protocol  |
  +--------+---------+                          +--------+---------+
           |                                             |
  +--------v---------+       UHF Link           +--------v---------+
  | AX.25 Data Link  |  <===================>  | AX.25 Data Link  |
  | (HDLC framing)   |                         | (HDLC framing)   |
  +--------+---------+                          +--------+---------+
           |                                             |
  +--------v---------+                          +--------v---------+
  | GMSK Modem       |  ~~~~~ 437 MHz ~~~~~>   | GMSK Modem       |
  | (9600 bps)       |                         | (9600 bps)       |
  +------------------+                          +------------------+

  +--------v---------+       S-band Link        +--------v---------+
  | CCSDS TM Frame   |  <===================>  | CCSDS TM Frame   |
  | (LDPC coded)     |                         | (LDPC coded)     |
  +--------+---------+                          +--------+---------+
           |                                             |
  +--------v---------+                          +--------v---------+
  | QPSK Modem       |  ~~~~~ 2.4 GHz ~~~~~>   | QPSK Modem       |
  | (256 kbps)       |                         | (256 kbps)       |
  +------------------+                          +------------------+
```

### 1.2 Link Parameters

| Parameter | UHF (Primary TT&C) | S-band (Payload Downlink) |
|-----------|---------------------|--------------------------|
| Frequency | 437.xxx MHz (amateur) | 2.4xx GHz (ISM) |
| Data Rate | 9600 bps | 256 kbps |
| Modulation | GMSK (BT=0.5) | QPSK |
| FEC | Conv. r=1/2, K=7 | LDPC r=1/2 |
| Data Link | AX.25 v2.2 | CCSDS TM Frame |
| TX Power | 1 W (30 dBm) | 2 W (33 dBm) |
| Duplex | Half-duplex | Simplex (downlink only) |
| Use | Commands, housekeeping TM, beacon | Image data, bulk science |
| Effective Data Rate | 4,080 bps (after FEC + framing) | 117,760 bps |
| Per-Pass Throughput (8 min) | ~240 KB | ~6.9 MB |
| Link Margin (5 deg el.) | 13.8 dB | 19.4 dB |

## 2. CCSDS Space Packet Format (CCSDS 133.0-B-2)

### 2.1 Primary Header (6 bytes)

```
Byte:  0         1         2         3         4         5
Bit:   7654 3210 7654 3210 7654 3210 7654 3210 7654 3210 7654 3210
       +---------+---------+---------+---------+---------+---------+
       |VVV|T|S|   APID    |FF| Sequence Count |  Data Length - 1  |
       +---------+---------+---------+---------+---------+---------+
       
VVV    = Version Number (3 bits) = 000 (always)
T      = Packet Type (1 bit): 0 = TM, 1 = TC
S      = Secondary Header Flag (1 bit): 1 = present
APID   = Application Process Identifier (11 bits)
FF     = Sequence Flags (2 bits): 11 = standalone packet
Seq    = Sequence Count (14 bits): 0-16383, wrapping counter
Length = Data Length - 1 (16 bits): bytes in data field minus one
```

### 2.2 Secondary Header (10 bytes)

```
Byte:  6    7    8    9   10   11   12   13   14   15
       +----+----+----+----+----+----+----+----+----+----+
       |       Timestamp (8 bytes, CCSDS epoch ms)       |
       +----+----+----+----+----+----+----+----+----+----+
       |SubsysID| Subtype |
       +---------+---------+

Timestamp: 64-bit unsigned, milliseconds since 2000-01-01T00:00:00 UTC (CCSDS epoch)
SubsysID:  8-bit subsystem identifier
Subtype:   8-bit message subtype within subsystem
```

### 2.3 Full Packet Layout

```
+---Primary Header (6B)---+--Secondary Header (10B)--+---Data Field (N B)---+--CRC (2B)--+
| Ver|T|S|APID|Flg|SeqCnt | Timestamp(8B)|SID|SubTyp |  Payload bytes ...   | CRC16-CCITT|
| Len                      |                          |                      |            |
+--------------------------+--------------------------+----------------------+------------+
```

- Minimum packet size: 6 + 10 + 0 + 2 = 18 bytes (empty payload)
- Maximum packet size: 6 + 10 + 240 + 2 = 258 bytes (CCSDS_MAX_PACKET_SIZE in firmware)
- CRC polynomial: 0x1021 (CRC-16/CCITT), initial value 0xFFFF

## 3. APID Assignments

### 3.1 Telemetry APIDs (0x001 - 0x0FF)

| APID | Hex | Subsystem | Subtype | Rate | Size (bytes) | Description |
|------|-----|-----------|---------|------|--------------|-------------|
| 1 | 0x001 | OBC | 0x01 | 1 Hz | 48 | Housekeeping (temps, uptime, mode, errors) |
| 1 | 0x001 | OBC | 0x02 | On event | 32 | Mode change notification |
| 1 | 0x001 | OBC | 0x03 | On event | 64 | Memory dump response |
| 2 | 0x002 | EPS | 0x01 | 1 Hz | 72 | Power telemetry (V, I, SOC, solar, loads) |
| 2 | 0x002 | EPS | 0x02 | On event | 24 | Power mode change |
| 2 | 0x002 | EPS | 0x03 | On event | 16 | Overprotection triggered |
| 3 | 0x003 | COMM | 0x01 | 0.1 Hz | 32 | COMM status (RSSI, packets TX/RX, errors) |
| 3 | 0x003 | COMM | 0x02 | On event | 16 | Link acquired/lost |
| 4 | 0x004 | ADCS | 0x01 | 1 Hz | 84 | Attitude (quaternion, rates, mag, sun) |
| 4 | 0x004 | ADCS | 0x02 | 0.1 Hz | 36 | ADCS mode and control torques |
| 5 | 0x005 | GNSS | 0x01 | 0.1 Hz | 48 | Position (lat, lon, alt, vel, PDOP, sats) |
| 6 | 0x006 | Camera | 0x01 | On event | 24 | Capture status (image ID, size, time) |
| 6 | 0x006 | Camera | 0x02 | On request | 240 | Image data chunk (max data field) |
| 7 | 0x007 | Payload | 0x01 | 0.2 Hz | 32 | Radiation dose rate and cumulative dose |
| 7 | 0x007 | Payload | 0x02 | On event | 64 | IoT relay message |
| 16 | 0x010 | Error | 0x01 | On event | 48 | Error report (code, severity, context) |
| 255 | 0x0FF | Beacon | 0x01 | 1/30 Hz | 48 | Beacon (callsign, status, position) |

### 3.2 Telecommand APIDs (0x100 - 0x1FF)

| APID | Hex | Description |
|------|-----|-------------|
| 256 | 0x100 | General telecommand (routed by opcode) |
| 257 | 0x101 | Time-tagged command (delayed execution) |
| 258 | 0x102 | Macro command (sequence of commands) |

## 4. Command Table

### 4.1 OBC Commands (Opcode 0x01xx)

| Opcode | Name | Parameters | Response | Auth Level |
|--------|------|------------|----------|------------|
| 0x0100 | CMD_NOP | None | ACK | Basic |
| 0x0101 | CMD_REBOOT | confirm: u8 (0xAA) | ACK, then reboot | Critical |
| 0x0102 | CMD_SET_MODE | mode: u8 | ACK + new mode | Elevated |
| 0x0103 | CMD_GET_STATUS | None | Status TM packet | Basic |
| 0x0104 | CMD_SET_TIME | epoch_ms: u64 | ACK + time sync TM | Elevated |
| 0x0105 | CMD_MEM_DUMP | addr: u32, len: u16 | Memory dump TM | Critical |
| 0x0106 | CMD_MEM_WRITE | addr: u32, data: [u8] | ACK | Critical |
| 0x0107 | CMD_SW_UPDATE | segment: u16, data: [u8] | ACK per segment | Critical |
| 0x0108 | CMD_CLEAR_ERRORS | None | ACK + error count = 0 | Elevated |
| 0x0109 | CMD_SET_TM_RATE | apid: u16, rate_hz: f32 | ACK | Elevated |

### 4.2 EPS Commands (Opcode 0x02xx)

| Opcode | Name | Parameters | Response | Auth Level |
|--------|------|------------|----------|------------|
| 0x0200 | CMD_EPS_STATUS | None | EPS TM packet | Basic |
| 0x0201 | CMD_LOAD_ON | channel: u8 (0-7) | ACK + channel state | Elevated |
| 0x0202 | CMD_LOAD_OFF | channel: u8 (0-7) | ACK + channel state | Elevated |
| 0x0203 | CMD_SET_HEATER | mode: u8, setpoint_C: i8 | ACK | Elevated |
| 0x0204 | CMD_BATTERY_TEST | None | Battery TM sequence | Elevated |
| 0x0205 | CMD_SET_POWER_MODE | mode: u8 | ACK + mode change | Critical |
| 0x0206 | CMD_EPS_EMERGENCY | None | ACK, shed loads | Critical |

### 4.3 COMM Commands (Opcode 0x03xx)

| Opcode | Name | Parameters | Response | Auth Level |
|--------|------|------------|----------|------------|
| 0x0300 | CMD_COMM_STATUS | None | COMM TM packet | Basic |
| 0x0301 | CMD_SET_TX_POWER | power_dbm: u8 | ACK | Elevated |
| 0x0302 | CMD_SET_DATA_RATE | rate_bps: u16 | ACK | Elevated |
| 0x0303 | CMD_BEACON_ON | interval_ms: u32 (min 10000) | ACK | Elevated |
| 0x0304 | CMD_BEACON_OFF | None | ACK | Elevated |
| 0x0305 | CMD_S_BAND_ON | None | ACK | Elevated |
| 0x0306 | CMD_S_BAND_OFF | None | ACK | Elevated |

### 4.4 ADCS Commands (Opcode 0x04xx)

| Opcode | Name | Parameters | Response | Auth Level |
|--------|------|------------|----------|------------|
| 0x0400 | CMD_ADCS_STATUS | None | ADCS TM packet | Basic |
| 0x0401 | CMD_SET_ADCS_MODE | mode: u8 (0-4) | ACK + mode | Elevated |
| 0x0402 | CMD_SET_TARGET | lat: f64, lon: f64, alt: f64 | ACK | Elevated |
| 0x0403 | CMD_DETUMBLE | None | ACK + start detumble | Elevated |
| 0x0404 | CMD_MTQ_TEST | axis: u8, duty: f32 | ACK + MTQ state | Critical |
| 0x0405 | CMD_RW_TEST | axis: u8, speed_rpm: f32 | ACK + RW state | Critical |
| 0x0406 | CMD_CALIBRATE_MAG | None | ACK + cal data TM | Elevated |
| 0x0407 | CMD_DESATURATE | None | ACK + start desaturation | Elevated |

### 4.5 Payload & Camera Commands (Opcode 0x06xx - 0x07xx)

| Opcode | Name | Parameters | Response | Auth Level |
|--------|------|------------|----------|------------|
| 0x0600 | CMD_CAPTURE_IMAGE | resolution: u8, compression: u8 | ACK + image ID | Elevated |
| 0x0601 | CMD_DOWNLOAD_IMAGE | image_id: u16, offset: u32 | Image data TM sequence | Basic |
| 0x0602 | CMD_LIST_IMAGES | None | Image catalog TM | Basic |
| 0x0603 | CMD_DELETE_IMAGE | image_id: u16 | ACK | Elevated |
| 0x0604 | CMD_LIST_FILES | dir: u8 | File catalog TM | Basic |
| 0x0605 | CMD_DELETE_FILE | file_id: u32 | ACK | Elevated |
| 0x0700 | CMD_RAD_START | None | ACK | Basic |
| 0x0701 | CMD_RAD_STOP | None | ACK | Basic |
| 0x0702 | CMD_RAD_DOWNLOAD | start_time: u64, end_time: u64 | Radiation data TM | Basic |
| 0x0703 | CMD_PAYLOAD_CMD | cmd_data: u8[64] | ACK + payload response | Elevated |

## 5. Response Format and Error Codes

### 5.1 Acknowledgment Packet

Every command receives an ACK/NAK response:

```
ACK Packet (APID 0x100, Subtype 0x00):
  +--------+--------+--------+--------+--------+--------+
  | Opcode (2B)     | Status | ErrCode| SeqNum (2B)     |
  +--------+--------+--------+--------+--------+--------+
  
Status byte:
  0x00 = ACK_OK       (command accepted and executed)
  0x01 = ACK_QUEUED   (command accepted, execution deferred)
  0x02 = ACK_PROGRESS (command in progress, partial result)
  0xFF = NAK          (command rejected, see error code)
```

### 5.2 Error Codes

| Code | Name | Description |
|------|------|-------------|
| 0x00 | ERR_NONE | No error |
| 0x01 | ERR_UNKNOWN_CMD | Unrecognized opcode |
| 0x02 | ERR_INVALID_PARAM | Parameter out of range or invalid type |
| 0x03 | ERR_AUTH_FAILED | HMAC-SHA256 verification failed |
| 0x04 | ERR_SEQ_INVALID | Sequence number out of acceptance window |
| 0x05 | ERR_TIME_STALE | Timestamp outside +/- 60 s freshness window |
| 0x06 | ERR_BUSY | Subsystem busy executing prior command |
| 0x07 | ERR_NOT_READY | Subsystem not initialized or in wrong mode |
| 0x08 | ERR_DISABLED | Target subsystem or channel disabled by EPS |
| 0x09 | ERR_HARDWARE | Hardware fault detected during execution |
| 0x0A | ERR_CRC_FAIL | Packet CRC-16/CCITT mismatch |
| 0x0B | ERR_OVERFLOW | Buffer, queue, or storage capacity exceeded |
| 0x0C | ERR_TIMEOUT | Operation timed out (I/O or processing) |
| 0x0D | ERR_PERMISSION | Auth level insufficient for requested command |
| 0x0E | ERR_SAFE_MODE | Command rejected because satellite is in safe mode |
| 0x0F | ERR_REPLAY | Replay attack detected (sequence reuse) |
| 0xFF | ERR_UNKNOWN | Unclassified internal error |

### 5.3 Severity Levels (for Error Report TM, APID 0x010)

| Level | Value | Action |
|-------|-------|--------|
| DEBUG | 0 | Log to FRAM ring buffer only |
| INFO | 1 | Log + include in next housekeeping packet |
| WARNING | 2 | Log + immediate TM if link active |
| ERROR | 3 | Log + trigger anomaly counter, attempt recovery |
| CRITICAL | 4 | Log + enter safe mode, beacon-only operation |

## 6. Command Authentication (HMAC-SHA256)

### 6.1 Authentication Fields

```
Command packet with authentication:

+--CCSDS Header--+--Cmd Payload--+---Auth Block (44 bytes)--------+--CRC--+
|  (16 bytes)     |  (variable)   | SeqNum(4B) | Timestamp(8B)    |       |
|                 |               | HMAC-SHA256 (32B)              |       |
+-----------------+---------------+--------------------------------+-------+

HMAC input = CCSDS_Header || Cmd_Payload || SeqNum || Timestamp
HMAC key   = 256-bit pre-shared key (loaded during integration, stored in FRAM)
```

### 6.2 Authentication Levels

| Level | Commands | Requirements |
|-------|----------|-------------|
| Basic | Status queries, data download | No HMAC required (read-only, no state change) |
| Elevated | Mode changes, config updates | HMAC + valid sequence number + timestamp |
| Critical | Reboot, memory write, SW update | HMAC + sequence + timestamp + confirm byte (0xAA) |

### 6.3 Replay Protection

- **Sequence window**: Accept if seq_num > last_accepted - 16 AND seq_num != previously used
- **Timestamp freshness**: |TC_timestamp - onboard_UTC| < 60 seconds
- **Time sync relaxation**: CMD_SET_TIME accepts +/- 300 s window (to allow clock correction)
- **Key management**: Single pre-shared 256-bit key, no in-orbit key rotation
- **Key storage**: Duplicated in two FRAM chips (FM25V20A) for redundancy

## 7. AX.25 Frame Format (UHF Link Layer)

### 7.1 AX.25 UI Frame Structure

```
+-------+----------+--------+--------+-------+----------+-------+
| Flag  | Address  | Ctrl   | PID    | Info  | FCS      | Flag  |
| 0x7E  | (14B)    | (1B)   | (1B)   | (var) | (2B)     | 0x7E  |
+-------+----------+--------+--------+-------+----------+-------+
  1 B     14 B       1 B      1 B    <=256 B    2 B       1 B

Total frame overhead: 20 bytes (excluding info field)
```

| Field | Value | Size | Description |
|-------|-------|------|-------------|
| Flag | 0x7E | 1 B | HDLC frame delimiter, bit-stuffed |
| Dest Address | e.g. GS callsign UN7xxx-0 | 7 B | 6 char callsign + SSID byte |
| Source Address | e.g. UN8SAT-1 | 7 B | Satellite callsign + SSID |
| Control | 0x03 | 1 B | UI frame (unnumbered information) |
| PID | 0xF0 | 1 B | No layer 3 protocol |
| Information | CCSDS Space Packet | <=256 B | Full CCSDS packet as payload |
| FCS | CRC-16/AX.25 | 2 B | Polynomial: x^16 + x^12 + x^5 + 1 |
| Flag | 0x7E | 1 B | End-of-frame delimiter |

Note: AX.25 is used only on the UHF link. The S-band link uses CCSDS Attached Sync Marker (ASM) framing directly over the synchronous serial stream.

### 7.2 Beacon Frame Content (Periodic, 30 s interval)

```
AX.25 UI Frame:
  Destination: CQ-0 (broadcast)
  Source: UN8SAT-1

  Info field — Beacon Data Layout (48 bytes):
  +--------+------+------+------+------+------+------+------+
  | Offset | 0-3  | 4    | 5-6  | 7-8  | 9    | 10-11| 12-13|
  | Field  | Upt  | Mode | Vbat | Ibat | SOC  | Psol | Tcpu |
  | Type   | u32  | u8   | u16  | i16  | u8   | u16  | i16  |
  | Unit   | sec  | enum | mV   | mA   | %    | mW   | 0.1C |
  +--------+------+------+------+------+------+------+------+
  | Offset | 14-15| 16-19| 20-23| 24-27| 28-31| 32-33| 34-37|
  | Field  | Tboard| Qw  | Qx   | Qy   | Qz   | Omega| Lat  |
  | Type   | i16  | f32  | f32  | f32  | f32  | u16  | i32  |
  | Unit   | 0.1C | --   | --   | --   | --   |.01d/s| 1e-7 |
  +--------+------+------+------+------+------+------+------+
  | Offset | 38-41| 42-43| 44   | 45   | 46-47|
  | Field  | Lon  | Alt  | Fix  | Errs | SeqCnt|
  | Type   | i32  | u16  | u8   | u8   | u16   |
  | Unit   | 1e-7 | m    | enum | count| count |
  +--------+------+------+------+------+-------+

Total beacon: 48 B data + 16 B CCSDS headers + 2 B CRC = 66 B packet
With AX.25: 66 + 20 = 86 B frame
TX duration: 86 * 8 / 9600 = 71.7 ms
Duty cycle: 71.7 ms / 30 s = 0.24%
```

## 8. Protocol State Machine

### 8.1 Receiver State Machine (Satellite)

```
                    ┌──────────┐
         ┌──────────│   IDLE   │◄──────────────────────┐
         │          └────┬─────┘                        │
         │               │ Byte received                │
         │               ▼                              │
         │          ┌──────────┐                        │
         │    ┌─────│   SYNC   │ Wait for AX.25 flag   │
         │    │     └────┬─────┘ (0x7E)                 │
         │    │ timeout   │ Flag matched                 │
         │    │ (500ms)   ▼                              │
         │    │     ┌──────────┐                        │
         │    │     │  HEADER  │ Collect address + ctrl  │
         │    │     └────┬─────┘ (16 bytes)             │
         │    │          │ Header complete               │
         │    │          ▼                              │
         │    │     ┌──────────┐                        │
         │    │     │   DATA   │ Collect info field      │
         │    │     └────┬─────┘ (until next 0x7E)      │
         │    │          │ End flag received             │
         │    │          ▼                              │
         │    │     ┌──────────┐                        │
         │    └────►│ VALIDATE │ Verify AX.25 FCS       │
         │          └──┬───┬───┘ then CCSDS CRC-16      │
         │     CRC OK  │   │ CRC FAIL                   │
         │             ▼   └────────────────────────────┘
         │   ┌────────────────┐    (increment error counter)
         │   │ AUTHENTICATE   │
         │   │ Verify HMAC if │
         │   │ auth required  │
         │   └──┬──────┬──────┘
         │ OK   │      │ FAIL → send NAK (ERR_AUTH_FAILED)
         │      ▼      └───────────────────────────────►│
         │   ┌────────────────┐                         │
         │   │ PROCESS PACKET │                         │
         │   │ Dispatch to    │                         │
         │   │ command queue  │                         │
         │   │ Send ACK       │                         │
         │   └───────┬────────┘                         │
         │           │                                  │
         └───────────┘◄─────────────────────────────────┘
```

### 8.2 UHF Communication State Machine

```
                     +-------------+
                     |   IDLE      |
                     | (beacon TX) |
                     +------+------+
                            |
                     GS detected (preamble + valid AX.25)
                            |
                     +------v------+
              +----->|   LINK      |<-----+
              |      | ESTABLISHED |      |
              |      +------+------+      |
              |             |             |
         No response   Valid CMD      Invalid CMD
         (timeout 30s)     |          (NAK sent)
              |      +------v------+      |
              |      |  COMMAND    |------+
              |      |  PROCESSING |
              |      +------+------+
              |             |
              |        Response ready
              |             |
              |      +------v------+
              +------+ TX          |
                     | RESPONSE   |
                     +------+------+
                            |
                     Pass ends (LOS) OR idle timeout (120s)
                            |
                     +------v------+
                     |   IDLE      |
                     | (beacon TX) |
                     +-------------+
```

### 8.3 S-band Downlink State Machine

```
                     +-------------+
                     |  S-BAND OFF |
                     +------+------+
                            |
                     CMD_S_BAND_ON received (via UHF)
                            |
                     +------v------+
                     |  WARM-UP    | (PA stabilization, 5 s)
                     +------+------+
                            |
                     +------v------+
                     |  SYNC TX    | (ASM pattern, 1 s)
                     +------+------+
                            |
                     +------v------+
                     |  DATA TX    | (CCSDS TM frames, continuous)
                     +------+------+
                            |
                     Buffer empty OR CMD_S_BAND_OFF OR timeout (15 min)
                            |
                     +------v------+
                     |  S-BAND OFF |
                     +-------------+
```

## 9. Timing Diagrams

### 9.1 Typical Command-Response Sequence

```
Ground Station                          Satellite
     |                                      |
     |--- AX.25[CMD_GET_STATUS] ----------->|  t=0
     |                                      |  t+5ms: Parse AX.25
     |                                      |  t+7ms: Extract CCSDS
     |                                      |  t+10ms: Verify CRC-16
     |                                      |  t+12ms: No auth (Basic)
     |                                      |  t+15ms: Execute command
     |                                      |  t+20ms: Build response
     |<-- AX.25[ACK_OK] -------------------|  t=50ms
     |                                      |
     |<-- AX.25[OBC_HK TM] ----------------|  t=100ms
     |                                      |
```

### 9.2 Authenticated Command Sequence

```
Ground Station                          Satellite
     |                                      |
     |--- AX.25[CMD_SET_MODE(SAFE)] ------->|  t=0
     |   (includes HMAC + seq + timestamp)   |
     |                                      |  t+5ms: Parse AX.25
     |                                      |  t+10ms: Verify CRC
     |                                      |  t+12ms: Extract HMAC
     |                                      |  t+15ms: Verify HMAC-SHA256
     |                                      |  t+18ms: Check seq > last
     |                                      |  t+20ms: Check timestamp window
     |                                      |  t+25ms: Execute mode change
     |<-- AX.25[ACK_OK] -------------------|  t=50ms
     |<-- AX.25[MODE_CHANGE TM] ------------|  t=80ms
     |                                      |
```

### 9.3 Image Downlink via S-band

```
Ground Station                          Satellite
     |                                      |
     |--- UHF: CMD_S_BAND_ON ------------->|  t=0
     |<-- UHF: ACK_OK ---------------------|  t=50ms
     |                                      |  t=5s: PA warm-up complete
     |                                      |  t=6s: ASM sync pattern
     |                                      |
     |--- UHF: CMD_DOWNLOAD_IMAGE --------->|  t=7s
     |   (image_id=42, offset=0)            |
     |<-- UHF: ACK_OK ---------------------|  t=7.05s
     |                                      |
     |<~~ S-band: Image chunk 0 (240B) ~~~~|  t=7.1s
     |<~~ S-band: Image chunk 1 (240B) ~~~~|  t=7.12s
     |<~~ S-band: Image chunk 2 (240B) ~~~~|  t=7.14s
     |    ...                               |
     |<~~ S-band: Image chunk N (last) ~~~~~|
     |                                      |
     |--- UHF: CMD_S_BAND_OFF ------------>|
     |<-- UHF: ACK_OK ---------------------|
     |                                      |

S-band chunk rate: 258 B * 8 / 256000 bps = 8.1 ms per chunk
3 MB image: ~12,500 chunks = ~102 s (~1.7 min)
```

## 10. Data Prioritization and Queue Management

### 10.1 TX Queue Priority

| Priority | Packet Type | Max Latency | Queue Depth |
|----------|-------------|-------------|-------------|
| 0 (highest) | Emergency TM (ERR_CRITICAL) | Immediate | 4 |
| 1 | TC Acknowledgement (ACK/NAK) | < 100 ms | 8 |
| 2 | Beacon | 30 s period | 1 (overwrite) |
| 3 | Housekeeping TM (OBC, EPS) | < 5 s | 16 |
| 4 | GNSS/ADCS TM | < 10 s | 8 |
| 5 (lowest) | Payload / Image data | Best effort | 32 |

### 10.2 Store-and-Forward

When no ground station contact is available, telemetry is stored to the SD card in a circular buffer. During the next pass, stored data is downlinked in chronological order after real-time housekeeping.

```
SD Card Layout:
  /tlm/YYYY-MM-DD/HH-MM-SS.ccsds    (raw CCSDS packets, ~4 MB/day)
  /img/NNNN.jpg                       (camera images, 50 KB - 10 MB each)
  /rad/YYYY-MM-DD.bin                 (radiation data, ~100 KB/day)
  /err/error_log.bin                  (error log mirror from FRAM)

Storage policy: Oldest telemetry deleted first when SD > 90% full.
Images and radiation data protected until explicitly deleted by TC.
```

## 11. Data Integrity and Reliability

### 11.1 Error Detection Layers

| Layer | Mechanism | Coverage | Standard |
|-------|-----------|----------|----------|
| Physical | FEC (Conv r=1/2 or LDPC r=1/2) | Bit-level correction | CCSDS 131.0-B-3 |
| Data Link | AX.25 FCS (CRC-16) | Frame-level | AX.25 v2.2 |
| Network | CCSDS CRC-16/CCITT | Packet-level | CCSDS 133.0-B-2 |
| Application | HMAC-SHA256 (commands) | Command integrity + auth | CCSDS 352.0-B-2 |
| File Transfer | CRC-32 per image + sequence numbers | File-level completeness | Custom |

### 11.2 Retransmission Policy

- **Beacon**: No retransmission (periodic, best-effort)
- **Command ACK**: GS retransmits command if no ACK within 5 seconds (max 3 retries)
- **TM packets**: No automatic retransmit; GS can request specific data via TC
- **Image chunks**: GS tracks received chunks, requests missing by offset using CMD_DOWNLOAD_IMAGE
- **Maximum retries**: 3 per command from GS side, then abort and log

## 12. References

- CCSDS 133.0-B-2: Space Packet Protocol, 2020
- CCSDS 132.0-B-2: TM Space Data Link Protocol, 2015
- CCSDS 131.0-B-3: TM Synchronization and Channel Coding, 2017
- CCSDS 231.0-B-3: TC Synchronization and Channel Coding, 2017
- CCSDS 352.0-B-2: CCSDS Cryptographic Algorithms, 2019
- AX.25 Link Access Protocol for Amateur Packet Radio, v2.2, 1998
- IARU Satellite Frequency Coordination Guidelines
- ITU Radio Regulations, Article 25 (Amateur Service)
