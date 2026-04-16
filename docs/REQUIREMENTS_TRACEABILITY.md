# UniSat-1 Requirements Traceability Matrix

This document tracks all mission, system, and subsystem requirements for the UniSat-1 CubeSat platform.
Each requirement is linked to its parent, verification method, test ID, and current status.

## Verification Methods

| Code | Method |
|------|--------|
| A | Analysis |
| D | Demonstration |
| I | Inspection |
| T | Test |

## Status Legend

| Status | Meaning |
|--------|---------|
| VERIFIED | Requirement verified through designated method |
| IN PROGRESS | Verification underway |
| PLANNED | Verification not yet started |
| N/A | Not applicable for current mission phase |

---

## Mission-Level Requirements (REQ-MIS)

| ID | Description | Parent | Verification | Test ID | Status |
|----|-------------|--------|-------------|---------|--------|
| REQ-MIS-001 | The satellite shall operate in a Sun-Synchronous Orbit at 550 km altitude with 97.6 deg inclination | - | A | TST-ORB-001 | VERIFIED |
| REQ-MIS-002 | The mission shall have a minimum operational lifetime of 2 years | - | A | TST-LIF-001 | IN PROGRESS |
| REQ-MIS-003 | The satellite shall capture multispectral Earth imagery (R, G, B, NIR bands) with GSD <= 30 m | - | T | TST-IMG-001 | PLANNED |
| REQ-MIS-004 | The ground station shall maintain communication with the satellite during each visible pass | - | D | TST-COM-001 | IN PROGRESS |
| REQ-MIS-005 | The satellite shall comply with the CubeSat Design Specification (CDS) for 3U form factor | - | I | TST-CDS-001 | VERIFIED |

---

## System-Level Requirements (REQ-SYS)

| ID | Description | Parent | Verification | Test ID | Status |
|----|-------------|--------|-------------|---------|--------|
| REQ-SYS-001 | Total satellite mass shall not exceed 4.0 kg (3U limit) including 20% margin | REQ-MIS-005 | I | TST-MAS-001 | VERIFIED |
| REQ-SYS-002 | The EPS shall provide positive average power balance across each orbit | REQ-MIS-002 | A | TST-PWR-001 | VERIFIED |
| REQ-SYS-003 | The communication subsystem shall support UHF uplink/downlink at 437 MHz with 9600 bps data rate | REQ-MIS-004 | T | TST-UHF-001 | IN PROGRESS |
| REQ-SYS-004 | The ADCS shall achieve nadir pointing accuracy of <= 1.0 deg (3-sigma) | REQ-MIS-003 | T | TST-ADC-001 | PLANNED |
| REQ-SYS-005 | The OBC shall process and store at least 32 GB of payload data | REQ-MIS-003 | T | TST-OBC-001 | PLANNED |
| REQ-SYS-006 | Total component volume shall not exceed the 3U envelope (100 x 100 x 340.5 mm) | REQ-MIS-005 | I | TST-VOL-001 | VERIFIED |
| REQ-SYS-007 | The satellite shall survive thermal extremes of -40 C to +85 C (component rated range) | REQ-MIS-002 | A, T | TST-THR-001 | IN PROGRESS |
| REQ-SYS-008 | The battery subsystem shall provide at least 30 Wh capacity using Li-ion 18650 cells | REQ-SYS-002 | T | TST-BAT-001 | VERIFIED |
| REQ-SYS-009 | The satellite shall support S-band downlink at 2.4 GHz with >= 256 kbps for payload data transfer | REQ-MIS-003 | T | TST-SBD-001 | PLANNED |
| REQ-SYS-010 | The GNSS receiver shall provide orbital position with <= 10 m accuracy | REQ-MIS-001 | T | TST-GPS-001 | PLANNED |

---

## Subsystem-Level Requirements (REQ-SUB)

| ID | Description | Parent | Verification | Test ID | Status |
|----|-------------|--------|-------------|---------|--------|
| REQ-SUB-001 | Solar panels (GaAs triple-junction, 29.5% efficiency) shall generate >= 4.3 W average power with 6 deployed faces | REQ-SYS-002 | A, T | TST-SOL-001 | VERIFIED |
| REQ-SUB-002 | The magnetorquer system (3-axis) shall provide >= 0.2 Am^2 magnetic dipole for detumbling | REQ-SYS-004 | T | TST-MTQ-001 | PLANNED |
| REQ-SUB-003 | The camera module shall capture images at 8 MP resolution with on-board SVD compression | REQ-SYS-005 | T | TST-CAM-001 | PLANNED |
| REQ-SUB-004 | The ground station Yagi antenna (14 dBi gain) shall close the UHF link with >= 10 dB margin at 550 km altitude | REQ-SYS-003 | A | TST-LNK-001 | VERIFIED |
| REQ-SUB-005 | The radiation monitor (SBM-20 sensor) shall measure dose rate in the range 0.01 - 100 mR/hr | REQ-MIS-003 | T | TST-RAD-001 | PLANNED |

---

## Traceability Summary

### Coverage by Subsystem

| Subsystem | Requirements | Verified | In Progress | Planned |
|-----------|-------------|----------|-------------|---------|
| Orbit / Mission | 2 | 1 | 1 | 0 |
| Payload / Imaging | 3 | 0 | 0 | 3 |
| Communication | 3 | 1 | 1 | 1 |
| ADCS | 2 | 0 | 0 | 2 |
| Power / EPS | 3 | 3 | 0 | 0 |
| Structure / Mass | 2 | 2 | 0 | 0 |
| Thermal | 1 | 0 | 1 | 0 |
| OBC / Data | 1 | 0 | 0 | 1 |
| GNSS | 1 | 0 | 0 | 1 |
| Radiation | 1 | 0 | 0 | 1 |
| Ground Station | 1 | 1 | 0 | 0 |
| **Total** | **20** | **8** | **3** | **9** |

### Verification Method Distribution

| Method | Count |
|--------|-------|
| Analysis (A) | 5 |
| Test (T) | 13 |
| Inspection (I) | 3 |
| Demonstration (D) | 1 |

> Note: Some requirements use multiple verification methods (e.g., REQ-SYS-007 uses both Analysis and Test).

---

## Test Reference Index

| Test ID | Description | Requirement |
|---------|-------------|-------------|
| TST-ORB-001 | Orbit propagation analysis (J2 perturbation model) | REQ-MIS-001 |
| TST-LIF-001 | Atmospheric drag lifetime estimation | REQ-MIS-002 |
| TST-IMG-001 | Camera resolution and GSD verification on ground | REQ-MIS-003 |
| TST-COM-001 | End-to-end communication demonstration with ground station | REQ-MIS-004 |
| TST-CDS-001 | Physical inspection against CubeSat Design Specification | REQ-MIS-005 |
| TST-MAS-001 | Mass measurement of integrated satellite | REQ-SYS-001 |
| TST-PWR-001 | Power budget analysis and simulation across orbits | REQ-SYS-002 |
| TST-UHF-001 | UHF transceiver data rate and BER test | REQ-SYS-003 |
| TST-ADC-001 | ADCS pointing accuracy test on air-bearing table | REQ-SYS-004 |
| TST-OBC-001 | OBC data storage and processing throughput test | REQ-SYS-005 |
| TST-VOL-001 | Fit-check in 3U deployer mockup | REQ-SYS-006 |
| TST-THR-001 | Thermal vacuum chamber cycling test | REQ-SYS-007 |
| TST-BAT-001 | Battery capacity and cycle life test | REQ-SYS-008 |
| TST-SBD-001 | S-band transmitter data rate and power test | REQ-SYS-009 |
| TST-GPS-001 | GNSS position accuracy validation in orbit simulator | REQ-SYS-010 |
| TST-SOL-001 | Solar panel IV curve measurement under AM0 spectrum | REQ-SUB-001 |
| TST-MTQ-001 | Magnetorquer dipole moment measurement | REQ-SUB-002 |
| TST-CAM-001 | Camera module image capture and compression test | REQ-SUB-003 |
| TST-LNK-001 | Link budget analysis for UHF at max slant range | REQ-SUB-004 |
| TST-RAD-001 | Radiation sensor calibration with known source | REQ-SUB-005 |

---

*Document version: 1.0 | Last updated: 2026-04-15*
