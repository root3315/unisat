# UniSat — Software Requirements Specification

**Version:** 1.2 (TRL-5 hardening baseline)
**Status:** LIVE — amended with every feature commit.
**Scope:** On-board software for the UniSat CubeSat OBC (STM32F446RE
+ FreeRTOS) and the supporting ground-station stack.

## Document conventions

* Requirements are prefixed by subsystem and numbered densely — new
  REQs append; numbers are never reused.
* Every REQ carries a *priority* (MUST / SHOULD / MAY), a
  *verification method* (Test / Analysis / Inspection / Demo) and,
  where already closed, a pointer to the implementing commit or
  file and to the test proving compliance.
* Traceability is maintained in `docs/requirements/traceability.csv`
  and regenerated from this SRS + source grep by
  `scripts/gen_trace_matrix.py`.

## 1. Command & Telecommand (CMD)

| ID | Priority | Statement | Verification | Implemented in | Tested by |
|----|:-:|---|:-:|---|---|
| REQ-CMD-001 | MUST | Every uplink telecommand shall be authenticated with HMAC-SHA256 over the payload and replay counter. | Test | `command_dispatcher.c` | `test_command_dispatcher.c::test_valid_counter_and_tag_dispatches` |
| REQ-CMD-002 | MUST | Unauthenticated or tampered telecommands shall be dropped silently with no downlink response. | Test | `command_dispatcher.c` | `test_tampered_tag_rejected` |
| REQ-CMD-003 | MUST | The dispatcher shall reject replayed telecommands via a 32-bit counter + 64-bit sliding window. | Test | `command_dispatcher.c` | `test_duplicate_counter_is_replay`, `test_counter_older_than_window_dropped` |
| REQ-CMD-004 | MUST | Counter value 0 shall be reserved and rejected. | Test | `command_dispatcher.c` | `test_counter_zero_rejected` |
| REQ-CMD-005 | MUST | HMAC keys shall be stored in a CRC-protected A/B flash layout with strictly monotonic generation numbers. | Test | `key_store.c` | `test_key_store.c` |
| REQ-CMD-006 | SHOULD | Key rotation shall require new_gen > current active generation. | Test | `key_store.c` | `test_stale_generation_rejected` |
| REQ-CMD-007 | MUST | A torn write during rotation shall leave the previously-active key intact at the next boot. | Test | `key_store.c` | `test_corrupt_crc_falls_back_to_other_slot` |
| REQ-CMD-008 | MUST | On boot with no valid key in either slot the dispatcher shall refuse every frame (fail-closed) and FDIR shall report `FAULT_KEYSTORE_EMPTY`. | Test | `command_dispatcher.c`, `fdir.c` | `test_no_key_rejects_everything` |

## 2. Communication (COMM / AX.25)

| ID | Priority | Statement | Verification | Implemented in | Tested by |
|----|:-:|---|:-:|---|---|
| REQ-AX25-001 | MUST | The link layer shall encode AX.25 v2.2 UI frames with bit-stuffing, CRC-16/X.25 FCS, and 0x7E flag framing. | Test | `ax25.c` | `test_ax25_frame` |
| REQ-AX25-006 | MUST | FCS computation shall match ITU-T X.25 `fcs(b"123456789") == 0x906E` on both C and Python sides. | Test | `ax25.c`, `ground-station/utils/ax25.py` | `test_ax25_fcs` |
| REQ-AX25-012 | MUST | The decoder shall hard-reject any frame exceeding 400 bytes post-unstuffing. | Test | `ax25_decoder.c` | `test_ax25_decoder::test_oversize_rejected` |
| REQ-AX25-014 | MUST | The decoder shall never crash or leak state on arbitrary byte streams. | Test (fuzz) | `ax25_decoder.c` | fuzz harness, 10 000 cases |
| REQ-AX25-015 | MUST | C and Python decoders shall produce byte-identical output against 28 shared golden vectors. | Test | both | `test_ax25_golden` + `ground-station/tests/test_ax25.py` |
| REQ-AX25-019 | MUST | Decoder shall run in a dedicated FreeRTOS task, not in interrupt context. | Inspection | `comm.c` | design review |
| REQ-AX25-024 | MUST | Error recovery shall be O(1) per byte (reset to HUNT state, drop offending byte). | Analysis | `ax25_decoder.c` | design review |

## 3. Telemetry (TLM)

| ID | Priority | Statement | Verification | Implemented in | Tested by |
|----|:-:|---|:-:|---|---|
| REQ-TLM-001 | MUST | Housekeeping beacons shall be emitted every 30 s on the UHF channel. | Inspection | `main.c::CommTask`, `BEACON_PERIOD_MS` | operator verification |
| REQ-TLM-002 | MUST | Beacon packet shall be exactly 48 bytes (raw layout spec §7.2). | Test | `telemetry.c::Telemetry_PackBeacon` | `test_beacon_returns_48_bytes` |
| REQ-TLM-003 | MUST | Beacon byte 14-15 (Tboard) shall carry the board-temperature in signed 0.1 °C units. | Test | `board_temp.c`, `telemetry.c:154` | `test_board_temp.c` |
| REQ-TLM-004 | MUST | Tboard value 0 shall be used only while the TMP117 has not yet produced a valid reading. | Test | `board_temp.c` | `test_uninitialised_returns_zero_and_invalid` |
| REQ-TLM-005 | SHOULD | Out-of-range sensor readings (< −60 °C or > +130 °C) shall be rejected and FDIR shall report `FAULT_SENSOR_OUT_OF_RANGE`. | Test | `board_temp.c`, `fdir.c` | `test_out_of_range_rejected` |
| REQ-TLM-010 | MUST | Every housekeeping downlink shall be wrapped in a CCSDS Space Packet with APID 0x07D (beacon) or 0x010-0x014 (per-subsystem). | Inspection | `ccsds.c`, `telemetry.c` | design review |

## 4. Attitude Determination & Control (ADCS)

| ID | Priority | Statement | Verification | Implemented in | Tested by |
|----|:-:|---|:-:|---|---|
| REQ-ADCS-001 | MUST | B-dot controller shall reduce angular rate to below 0.5 °/s within 90 min of deployment. | Analysis | `adcs.c`, `bdot.c` | `test_adcs_algorithms` + on-orbit TBD |
| REQ-ADCS-002 | MUST | Quaternion arithmetic shall preserve unit norm to within 1e-5 after 10 000 iterations. | Test | `quaternion.c` | `test_adcs_algorithms::test_quat_norm_preserved` |
| REQ-ADCS-003 | SHOULD | Magnetometer saturation shall not crash the attitude filter (clamp + propagate last known attitude). | Test | `adcs.c` | `test_adcs_algorithms::test_saturation_handled` |
| REQ-ADCS-004 | MAY | Pointing-mode accuracy target: ≤ 5° (sun), ≤ 2° (nadir), ≤ 10° (target). | Analysis | `sun_pointing.c`, `target_pointing.c` | design review |

## 5. Electrical Power (EPS)

| ID | Priority | Statement | Verification | Implemented in | Tested by |
|----|:-:|---|:-:|---|---|
| REQ-EPS-001 | MUST | MPPT controller shall converge to the solar-panel maximum-power point within 10 iterations across ±20 % irradiance steps. | Test | `mppt.c` | `test_eps::test_mppt_convergence` |
| REQ-EPS-002 | MUST | Battery manager shall trigger `FAULT_BATTERY_UNDERVOLT` at ≤ 3.2 V pack voltage. | Test | `battery_manager.c`, `fdir.c` | `test_eps::test_undervolt_threshold` |
| REQ-EPS-003 | MUST | Bus-voltage brown-out shall force a safe-mode entry. | Analysis | `eps.c`, `fdir.c` (FAULT_BATTERY_UNDERVOLT → SAFE_MODE) | `test_fdir::test_aggregate_stats` |
| REQ-EPS-004 | SHOULD | Load-shedding priority: payload → camera → ADCS actuators → comm TX → OBC. | Inspection | `power_distribution.c` | design review |

## 6. Fault Detection, Isolation, Recovery (FDIR)

| ID | Priority | Statement | Verification | Implemented in | Tested by |
|----|:-:|---|:-:|---|---|
| REQ-FDIR-001 | MUST | The FDIR module shall maintain per-fault occurrence counters and aggregate statistics. | Test | `fdir.c` | `test_fdir::test_empty_state_after_init`, `test_aggregate_stats` |
| REQ-FDIR-002 | MUST | Escalation shall trigger once the recent-window counter reaches the per-fault threshold. | Test | `fdir.c` | `test_escalation_after_threshold` |
| REQ-FDIR-003 | MUST | Per-fault state shall be isolated — reporting fault A shall not affect fault B's counters. | Test | `fdir.c` | `test_cross_fault_isolation` |
| REQ-FDIR-004 | MUST | The recent-window shall slide forward — stale events shall NOT accumulate into escalation. | Test | `fdir.c` | `test_recent_window_slides` |
| REQ-FDIR-005 | MUST | A missed task-feed shall raise `FAULT_WATCHDOG_TASK_MISS`. | Test (integration) | `watchdog.c` → `fdir.c` | manual trace |
| REQ-FDIR-006 | SHOULD | FDIR recovery actions shall follow the severity ladder LOG_ONLY → RETRY → RESET_BUS → DISABLE_SUBSYS → SAFE_MODE → REBOOT. | Inspection | `fdir.c` g_table, `docs/reliability/fdir.md` | design review |

## 7. Safe Mode (SAFE)

| ID | Priority | Statement | Verification | Implemented in | Tested by |
|----|:-:|---|:-:|---|---|
| REQ-SAFE-001 | MUST | Safe mode shall be entered on any of: comm loss > 24 h, battery under-volt, repeated FDIR escalations. | Test | `modules/safe_mode.py`, `fdir.c` | `test_safe_mode.py`, `test_mission_e2e.py` |
| REQ-SAFE-002 | MUST | In safe mode only telemetry + comm + health tasks shall remain active. | Inspection | `modules/safe_mode.py`, profile `disabled_modules` | `test_required_modules_resolve_for_cubesat_leo` |
| REQ-SAFE-003 | MUST | Safe mode entry shall be idempotent — a second entry call while already active shall not overwrite the original reason. | Test | `modules/safe_mode.py` | `test_safe_mode.py::test_double_enter_does_not_overwrite` |
| REQ-SAFE-004 | SHOULD | Safe mode exit shall be explicit (ground command or automatic recovery check) — no time-based auto-exit. | Inspection | `modules/safe_mode.py` | design review |

## 8. Ground Segment (GS)

| ID | Priority | Statement | Verification | Implemented in | Tested by |
|----|:-:|---|:-:|---|---|
| REQ-GS-001 | MUST | The Python AX.25 library shall produce output byte-identical to the C implementation against 28 shared golden vectors. | Test | `ground-station/utils/ax25.py` | `test_ax25.py::test_golden_vectors` |
| REQ-GS-002 | MUST | The Streamlit dashboard shall decode every beacon field defined in `docs/communication_protocol.md` §7.2. | Inspection | `ground-station/pages/*` | manual demo |
| REQ-GS-003 | SHOULD | The ground-side HMAC helper shall mirror RFC 4231 test vectors on the exact same bytes as the firmware library. | Test | `ground-station/utils/hmac_auth.py` | `test_hmac.py` |

## 9. Build & Quality (BLD)

| ID | Priority | Statement | Verification | Implemented in | Tested by |
|----|:-:|---|:-:|---|---|
| REQ-BLD-001 | MUST | The firmware shall cross-compile for STM32F446RE with `arm-none-eabi-gcc` out of the box (LD, startup, clock config in the repo). | Demo | `firmware/stm32/Target/` | `scripts/verify.sh` target step |
| REQ-BLD-002 | MUST | Flash + RAM usage shall stay below 90 % of STM32F446RE capacity. | Analysis | `scripts/verify.sh` | 90 % budget gate |
| REQ-BLD-003 | MUST | Host ctest + pytest shall pass 100 % on every push. | Test | CI | `make ci` |
| REQ-BLD-004 | SHOULD | `cppcheck --enable=warning,portability` shall report zero issues. | Test | `scripts/run_cppcheck.sh` | `make cppcheck` |
| REQ-BLD-005 | SHOULD | Host coverage (lcov) shall be ≥ 80 % lines / ≥ 85 % functions. | Test | `firmware/CMakeLists.txt` coverage target | `make coverage` |
| REQ-BLD-006 | SHOULD | ASAN + UBSAN shall run clean over the full ctest suite. | Test | `-DSANITIZERS=ON` | `make sanitizers` |

## 10. Out-of-scope

Explicitly not covered by this SRS:

* Radiation hardening of silicon (SEL immunity, TID > 30 krad).
* Formal mission-assurance documentation to NASA-STD-8739.x or
  ECSS-Q-ST-80C class-1 levels.
* Hardware-qualified flight heritage.
* RF front-end licensing (IARU coordination) — operator task.

See `docs/GAPS_AND_ROADMAP.md` §"Out of scope" for the full list.

---

*Document owner: root3315. Review cadence: updated with every
feature commit on `feat/trl5-hardening`. Traceability regeneration:
`scripts/gen_trace_matrix.py` (Phase 6 follow-up, currently manual).*
