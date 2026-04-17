# ADR-001: No CSP — CCSDS-only Network Layer

**Status:** Accepted — 2026-04-17
**Track:** 1 (AX.25 Link Layer)
**Context doc:** [`../superpowers/specs/2026-04-17-track1-ax25-design.md`](../superpowers/specs/2026-04-17-track1-ax25-design.md)

## Context

An external review flagged the absence of CSP (CubeSat Space Protocol) as a
project deficiency, comparing UniSat to `libcsp`-based flight software. CSP
provides port-based addressing, packet routing between internal nodes, and
a light authentication layer over arbitrary data links.

## Decision

UniSat-1 does **not** implement CSP. The network-layer role is filled by
CCSDS Space Packet Protocol (CCSDS 133.0-B-2) carried inside AX.25 UI frames
on the UHF link, and directly over CCSDS ASM framing on the S-band link.

## Rationale

1. **Topology**. UniSat-1 is a point-to-point satellite ↔ ground system.
   CSP is valuable when multiple internal nodes share a bus — typically
   OBC ↔ EPS ↔ COMMS ↔ payload on CAN or RS-485 with independent MCUs.
   UniSat packages all subsystems in a single STM32F446 OBC; there is no
   internal bus for CSP to route on.
2. **Addressing**. CCSDS APID is an 11-bit subsystem/packet-type tag that
   covers every dispatch decision we need today (OBC housekeeping, EPS
   telemetry, ADCS attitude, GNSS, payload data, commands). Adding CSP
   ports would duplicate this with no operational benefit.
3. **Flash footprint**. `libcsp` adds ~4 KB of flash plus a routing table
   that would never contain more than two entries.
4. **Ground-station interop**. Amateur-radio ground tools (GNU Radio
   Companion, SatNOGS, gpredict-based tracking software) ingest AX.25 +
   CCSDS natively. CSP frames are uncommon on amateur UHF and would
   require custom receiving software.
5. **Testability**. Every byte on the wire is explainable with existing
   open specs (AX.25 v2.2, CCSDS 133.0-B-2). Adding CSP adds an
   independent framing layer a student must learn before touching the
   link.

## Consequences

- No built-in CMP (CSP Management Protocol) — we duplicate health telemetry
  via CCSDS APID `OBC_HOUSEKEEPING`.
- No RDP (Reliable Datagram Protocol) — reliability is managed at the
  application layer via sequence numbers + ground-side retransmit. This is
  acceptable because beacon frames are idempotent and commands carry their
  own sequence + HMAC (planned for Track 1b).
- If UniSat-2 adds an EPS daughterboard with its own MCU over CAN, CSP
  should be reconsidered at that mission boundary.

## Alternatives considered

- **Port `libcsp` wholesale**: rejected (rationale above, ~20 hours work,
  zero operational benefit on current hardware).
- **Thin CSP-compatible adapter on top of CCSDS APID**: rejected as a
  "checkbox" solution that adds maintenance burden without real value.
