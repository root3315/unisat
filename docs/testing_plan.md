# Testing Plan

## Test Levels

### Unit Tests
- **Firmware:** Unity test framework for C code
- **Python:** pytest with >70% coverage target
- **Scope:** Individual functions and classes

### Integration Tests
- Communication protocol (CCSDS encode/decode roundtrip)
- Sensor → Telemetry → CCSDS → Serial pipeline
- Flight controller module loading

### System Tests
- Full mission simulation (orbit + power + thermal + comm)
- Ground station end-to-end with simulated telemetry
- Safe mode entry and recovery

## Test Matrix

| Test ID | Module | Description | Criteria | Status |
|---------|--------|-------------|----------|--------|
| T-001 | CCSDS | Packet build/parse roundtrip | 100% data integrity | Pass |
| T-002 | CCSDS | CRC corruption detection | Detect all single-byte errors | Pass |
| T-003 | ADCS | Quaternion normalization | |q| = 1.0 ± 1e-5 | Pass |
| T-004 | ADCS | Euler-Quaternion roundtrip | Error < 0.001 rad | Pass |
| T-005 | ADCS | B-dot opposes field change | Negative correlation | Pass |
| T-006 | EPS | MPPT duty cycle clamping | 0.1 ≤ DC ≤ 0.95 | Pass |
| T-007 | EPS | Battery overcharge protection | Charge disabled > 4.2V/cell | Pass |
| T-008 | EPS | Battery overdischarge protection | Discharge disabled < 3.0V/cell | Pass |
| T-009 | Flight | Config loading | Valid JSON parsed | Pass |
| T-010 | Ground | Telemetry decode | Fields match encoded values | Pass |

## CI/CD Pipeline

1. **On push:** Run all unit tests, linting (ruff), type checking (mypy)
2. **On PR:** Full test suite + firmware build
3. **On release:** Generate documentation PDFs
