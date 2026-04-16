# Communication Protocol

Reference: CCSDS 133.0-B-2 (Space Packet Protocol), CCSDS 132.0-B-2 (TM Space Data Link), AX.25 Link Access Procedure v2.2

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
       |       Timestamp (8 bytes, UNIX epoch ms)        |
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

Total packet size: 18 + N + 2 bytes (min 20 bytes with empty payload)
Maximum packet size: 4096 bytes (implementation limit)

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
| 6 | 0x006 | Camera | 0x02 | On request | 4096 | Image data chunk |
| 7 | 0x007 | Payload | 0x01 | 0.01 Hz | 32 | Radiation dose rate and cumulative dose |
| 7 | 0x007 | Payload | 0x02 | On event | 64 | IoT relay message |
| 16 | 0x010 | Error | 0x01 | On event | 48 | Error report (code, severity, context) |
| 255 | 0x0FF | Beacon | 0x01 | 0.1 Hz | 64 | Beacon (callsign, status, position) |

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
| 0x0201 | CMD_LOAD_ON | channel: u8 | ACK + channel state | Elevated |
| 0x0202 | CMD_LOAD_OFF | channel: u8 | ACK + channel state | Elevated |
| 0x0203 | CMD_SET_HEATER | mode: u8, setpoint: i8 | ACK | Elevated |
| 0x0204 | CMD_BATTERY_TEST | None | Battery TM sequence | Elevated |
| 0x0205 | CMD_SET_POWER_MODE | mode: u8 | ACK + mode change | Critical |

### 4.3 ADCS Commands (Opcode 0x04xx)

| Opcode | Name | Parameters | Response | Auth Level |
|--------|------|------------|----------|------------|
| 0x0400 | CMD_ADCS_STATUS | None | ADCS TM packet | Basic |
| 0x0401 | CMD_SET_ADCS_MODE | mode: u8 | ACK + mode | Elevated |
| 0x0402 | CMD_SET_TARGET | quat: [f32; 4] | ACK | Elevated |
| 0x0403 | CMD_DETUMBLE | None | ACK + start detumble | Elevated |
| 0x0404 | CMD_MTQ_TEST | axis: u8, duty: f32 | ACK + MTQ state | Critical |
| 0x0405 | CMD_RW_TEST | axis: u8, speed: f32 | ACK + RW state | Critical |
| 0x0406 | CMD_CALIBRATE_MAG | None | ACK + cal data TM | Elevated |

### 4.4 COMM Commands (Opcode 0x03xx)

| Opcode | Name | Parameters | Response | Auth Level |
|--------|------|------------|----------|------------|
| 0x0300 | CMD_COMM_STATUS | None | COMM TM packet | Basic |
| 0x0301 | CMD_SET_TX_POWER | power_dbm: u8 | ACK | Elevated |
| 0x0302 | CMD_SET_DATA_RATE | rate: u16 | ACK | Elevated |
| 0x0303 | CMD_BEACON_ON | interval_ms: u32 | ACK | Elevated |
| 0x0304 | CMD_BEACON_OFF | None | ACK | Elevated |
| 0x0305 | CMD_S_BAND_ON | None | ACK | Elevated |
| 0x0306 | CMD_S_BAND_OFF | None | ACK | Elevated |

### 4.5 Payload Commands (Opcode 0x06xx - 0x07xx)

| Opcode | Name | Parameters | Response | Auth Level |
|--------|------|------------|----------|------------|
| 0x0600 | CMD_CAPTURE_IMAGE | resolution: u8, compression: u8 | ACK + image ID | Elevated |
| 0x0601 | CMD_DOWNLOAD_IMAGE | image_id: u16, offset: u32 | Image data TM sequence | Basic |
| 0x0602 | CMD_LIST_IMAGES | None | Image catalog TM | Basic |
| 0x0603 | CMD_DELETE_IMAGE | image_id: u16 | ACK | Elevated |
| 0x0700 | CMD_RAD_START | None | ACK | Basic |
| 0x0701 | CMD_RAD_STOP | None | ACK | Basic |
| 0x0702 | CMD_RAD_DOWNLOAD | None | Radiation data TM | Basic |

## 5. Response Format and Error Codes

### 5.1 Acknowledgment Packet

Every command receives an ACK/NAK response:

```
ACK Packet (APID 0x100, Subtype 0x00):
  +--------+--------+--------+--------+--------+--------+
  | Opcode (2B)     | Status | SeqNum (2B)     | Spare  |
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
| 0x02 | ERR_INVALID_PARAM | Parameter out of range |
| 0x03 | ERR_AUTH_FAILED | HMAC verification failed |
| 0x04 | ERR_SEQ_INVALID | Sequence number out of window |
| 0x05 | ERR_TIME_STALE | Timestamp outside freshness window |
| 0x06 | ERR_BUSY | Subsystem busy, try later |
| 0x07 | ERR_NOT_READY | Subsystem not initialized |
| 0x08 | ERR_DISABLED | Subsystem or channel disabled |
| 0x09 | ERR_HARDWARE | Hardware fault detected |
| 0x0A | ERR_CRC_FAIL | Packet CRC mismatch |
| 0x0B | ERR_OVERFLOW | Buffer or storage full |
| 0x0C | ERR_TIMEOUT | Operation timed out |
| 0x0D | ERR_PERMISSION | Insufficient auth level for command |
| 0x0E | ERR_SAFE_MODE | Command rejected in safe mode |
| 0xFF | ERR_UNKNOWN | Unclassified error |

### 5.3 Severity Levels (for Error Report TM, APID 0x010)

| Level | Value | Action |
|-------|-------|--------|
| DEBUG | 0 | Log only |
| INFO | 1 | Log + include in next HK packet |
| WARNING | 2 | Log + immediate TM if link active |
| ERROR | 3 | Log + trigger anomaly counter |
| CRITICAL | 4 | Log + enter safe mode |

## 6. Command Authentication (HMAC-SHA256)

### 6.1 Authentication Fields

```
Command packet with authentication:

+--CCSDS Header--+--Cmd Payload--+--Auth Block (36 bytes)---+--CRC--+
|  (16 bytes)     |  (variable)   | SeqNum(4B) | Timestamp(4B) |      |
|                 |               | HMAC-SHA256(32B)        |      |
+-----------------+---------------+-------------------------+------+

HMAC input = CCSDS_Header + Cmd_Payload + SeqNum + Timestamp
HMAC key   = 256-bit pre-shared key (loaded during integration)
```

### 6.2 Authentication Levels

| Level | Commands | Requirements |
|-------|----------|-------------|
| Basic | Status queries, data download | No HMAC required |
| Elevated | Mode changes, config updates | HMAC + valid sequence + timestamp |
| Critical | Reboot, memory write, SW update | HMAC + sequence + timestamp + confirm byte |

### 6.3 Replay Protection

- **Sequence number**: Monotonically increasing, window of 16 (reject if < last - 16)
- **Timestamp**: Must be within +/- 60 seconds of satellite clock
- **Key management**: Single pre-shared key, no in-orbit key rotation (mission simplicity)

## 7. AX.25 Frame Format (UHF Link Layer)

### 7.1 AX.25 UI Frame Structure

```
+-------+----------+--------+--------+-------+----------+-------+
| Flag  | Address  | Ctrl   | PID    | Info  | FCS      | Flag  |
| 0x7E  | (14B)    | (1B)   | (1B)   | (var) | (2B)     | 0x7E  |
+-------+----------+--------+--------+-------+----------+-------+

Flag:     0x7E (HDLC flag, bit-stuffed)
Address:  Destination (7B) + Source (7B) = 14 bytes
          Destination: GS callsign (e.g., UN7xxx-0)
          Source: Satellite callsign (e.g., UN8SAT-1)
Control:  0x03 (UI frame, unnumbered information)
PID:      0xF0 (no layer 3 protocol)
Info:     CCSDS Space Packet (up to 256 bytes for UHF)
FCS:      CRC-16/AX.25 (X^16 + X^12 + X^5 + 1)
```

### 7.2 Beacon Frame (Periodic, 10s interval)

```
AX.25 UI Frame:
  Destination: CQ-0 (broadcast)
  Source: UN8SAT-1
  Info field (64 bytes):
    +------+------+------+------+------+------+------+------+
    | Call | Mode | Vbat | Ibat | SOC  | Temp | Lat  | Lon  |
    | sign |  (1B)| (2B) | (2B) | (1B) | (2B) | (4B) | (4B) |
    +------+------+------+------+------+------+------+------+
    | Alt  | Quat (16B)          | Errors| Uptime| Padding  |
    | (4B) | w, x, y, z          | (2B)  | (4B)  | (to 64B) |
    +------+---------------------+-------+-------+----------+
```

## 8. Protocol State Machine

### 8.1 UHF Communication State Machine

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
              |      |  TX         |
              +------+ RESPONSE   |
                     +------+------+
                            |
                     Pass ends (LOS) OR idle timeout (120s)
                            |
                     +------v------+
                     |   IDLE      |
                     | (beacon TX) |
                     +-------------+
```

### 8.2 S-band Downlink State Machine

```
                     +-------------+
                     |  S-BAND OFF |
                     +------+------+
                            |
                     CMD_S_BAND_ON received (via UHF)
                            |
                     +------v------+
                     |  WARM-UP    | (PA stabilization, 5s)
                     +------+------+
                            |
                     +------v------+
                     |  SYNC TX    | (send sync pattern 1s)
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
     |                                      |  (parse, authenticate, execute)
     |                                      |  ~50ms processing
     |<-- AX.25[ACK_OK] -------------------|  t=50ms
     |                                      |
     |<-- AX.25[OBC_HK TM] ----------------|  t=100ms
     |                                      |
     |--- AX.25[CMD_CAPTURE_IMAGE] -------->|  t=500ms
     |                                      |  (camera init, capture)
     |<-- AX.25[ACK_QUEUED] ----------------|  t=550ms
     |                                      |  ~2s capture time
     |<-- AX.25[CAMERA_STATUS TM] ----------|  t=2.5s (capture complete)
     |                                      |
     |--- AX.25[CMD_DOWNLOAD_IMAGE] ------->|  t=3.0s
     |<-- AX.25[ACK_OK] -------------------|  t=3.05s
     |<-- AX.25[IMAGE_DATA chunk 1] --------|  t=3.1s
     |<-- AX.25[IMAGE_DATA chunk 2] --------|  t=3.4s
     |    ...                               |
     |<-- AX.25[IMAGE_DATA chunk N] --------|  t=N*0.3s
     |                                      |
```

### 9.2 Beacon Timing

```
Time (s):  0    10   20   30   40   50   60   70   80   90
           |    |    |    |    |    |    |    |    |    |
Beacon TX: *----*----*----*----*----*----*----*----*----*
                                    ^
                                    | GS sends command
                                    | Beacon suspended during cmd processing
                                    | Resumes after TX response
```

## 10. Data Integrity and Reliability

### 10.1 Error Detection Layers

| Layer | Mechanism | Coverage |
|-------|-----------|----------|
| Physical | GMSK/QPSK demodulation with BER tracking | Bit-level |
| Data Link | AX.25 FCS (CRC-16) | Frame-level |
| Network | CCSDS CRC-16/CCITT | Packet-level |
| Application | HMAC-SHA256 (commands) | Command integrity |
| File Transfer | CRC-32 per image chunk + sequence numbers | File-level |

### 10.2 Retransmission Policy

- **Beacon**: No retransmission (periodic, best-effort)
- **Command ACK**: Retransmit command if no ACK within 5 seconds (GS-initiated)
- **TM packets**: No automatic retransmit; GS can request specific data
- **Image chunks**: GS tracks received chunks, requests missing chunks by offset
- **Maximum retries**: 3 per command, then abort and log error

## 11. References

- CCSDS 133.0-B-2: Space Packet Protocol, 2020
- CCSDS 132.0-B-2: TM Space Data Link Protocol, 2015
- CCSDS 131.0-B-3: TM Synchronization and Channel Coding, 2017
- CCSDS 231.0-B-3: TC Synchronization and Channel Coding, 2017
- AX.25 Link Access Protocol for Amateur Packet Radio, v2.2, 1998
- IARU Satellite Frequency Coordination Guidelines
- ITU Radio Regulations, Article 25 (Amateur Service)
