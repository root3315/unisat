# Key-data packet — <Mission name>

The "key data" packet is the smallest possible payload that, on its own, lets
recovery teams reconstruct the mission outcome even if no other artefact
survives the flight. It is transmitted at landing and should fit in a single
beacon frame.

## Format

```c
struct mission_beacon_t {
    uint32_t mission_id;
    uint32_t timestamp_unix;
    int32_t  lat_e7;          // degrees * 1e7
    int32_t  lon_e7;
    int16_t  alt_m;
    // mission-specific fields below this line
} __attribute__((packed));
```

Fill in the mission-specific fields. Keep the packet ≤ 64 bytes so that any
downlink budget can carry it.

## Triple redundancy

The packet should be transmitted at least three times by independent paths:

1. **In-flight beacon** — broadcast on the platform's primary RF link as soon
   as the science phase ends.
2. **Landing beacon** — broadcast for at least 60 seconds after touchdown
   detection, with a duty cycle that survives a low-battery scenario.
3. **Persistent storage** — written to the SD card and to internal flash so
   that physical recovery of either survives.

## Fallback plan

Document what happens if the primary downlink fails:

- Which subsystem owns the fallback transmission.
- Which fields can be reconstructed from raw telemetry on the SD card.
- Which fields are unrecoverable and why.

## Checksum

Specify the checksum or signature scheme the recovery team uses to validate
the packet (CRC-16, CMAC, HMAC-SHA256-truncated, …) and where the verification
key lives.
