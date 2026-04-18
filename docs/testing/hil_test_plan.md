# Hardware-in-the-Loop (HIL) test plan

**Version:** 1.0 (Phase 6 baseline).
**Owner:** root3315.
**Status:** draft — bench BOM listed, firmware hooks pending.

## Purpose

HIL testing closes the gap between the host `ctest` green pipeline
(which proves the code is *correct*) and the TRL-5 claim (which
requires proof the code *runs on target hardware in a relevant
environment*). This plan specifies the minimal bench that turns
"the firmware compiles for STM32F446RE" into "the firmware
executes, reads real sensors, transmits real beacons, and keeps
going across a 48 h run."

Cost target: ≤ $150. Everything on the BOM is off-the-shelf and
shipped to a student team within one week.

## Bill of materials

| Item | Vendor / P/N | Qty | Unit $ | Purpose |
|------|--------------|----:|-------:|---------|
| Nucleo-F446RE dev board | STMicro / NUCLEO-F446RE | 1 | 14 | Target MCU with integrated ST-Link |
| BME280 breakout | Adafruit 2652 | 1 | 15 | I²C sensor under test |
| MPU-9250 breakout | generic eBay | 1 | 8 | SPI sensor under test |
| TMP117 breakout | SparkFun SEN-16416 | 1 | 15 | Precision temp sensor (Tboard) |
| u-blox NEO-M8N breakout | generic | 1 | 25 | GNSS receiver (I²C/DDC path) |
| Logic analyser | Saleae Logic 8 / Kingst LA1010 | 1 | 25 | Bus tracing, WCET probe |
| USB inline ammeter | USB charger-doctor | 1 | 8 | Power profile measurements |
| RTL-SDR dongle | generic RTL2832U | 1 | 25 | RF decode for AX.25 beacon over air |
| HopeRF RFM98W breakout | generic | 1 | 10 | 437 MHz TX for RF loop |
| Breadboard + jumpers | any | 1 | 10 | Wiring |
| **Total** | | | **155** | |

## Bench wiring

```
                          ┌──────────────────┐
                          │  Host PC (Linux) │
                          │  - pytest        │
                          │  - openocd       │
                          │  - gqrx          │
                          └──┬──────┬────────┘
                             │USB-A │USB-A
          ┌─── ST-Link ──────┘      └─────── RTL-SDR ─── antenna ─┐
          │                                                       │
          │   ┌─── I²C (PB6/PB7) ── BME280 / TMP117 / u-blox      │
          │   │                                                   │
          ▼   ▼    ┌── SPI (PA5/6/7) ── MPU-9250                  │
   ┌──────────────┐│                                              │
   │ Nucleo       ├┤  ┌── USART1 TX (PA9)  ── RFM98W ─ antenna ─┘
   │ F446RE       ├┘  │
   │              ├───┘
   │              ├──── USART2 (PA2/3)   ── FTDI USB-UART ── host VCP
   └──────────────┘
```

## Test matrix

The HIL test targets in the repo are defined as pytest tests that
talk to the bench over two channels:

* **UART VCP** — the OBC's USART2 debug channel, used for
  telemetry decoding and text-command injection.
* **RTL-SDR** — off-air capture of the RFM98W AX.25 beacon,
  decoded with direwolf or a Python FM demodulator.

The tests live under `tests/hil/` (directory created by this
plan; files added in the Phase 6 follow-up). Each test ID maps
1:1 to an SRS REQ:

| Test ID | SRS ref | Scenario | Pass criterion |
|---------|---------|----------|----------------|
| HIL-01 | REQ-BLD-001 | `make flash` + reset | OBC emits "UniSat v1.2 boot OK" on UART VCP within 3 s |
| HIL-02 | REQ-TLM-001 | Collect 5 beacons | 4 consecutive intervals within 30 s ± 500 ms |
| HIL-03 | REQ-TLM-003 | Tboard value vs TMP117 direct read | |ΔT| < 0.2 °C between beacon byte 14-15 and reference |
| HIL-04 | REQ-CMD-001 | Transmit authenticated cmd via RFM98W | OBC increments `accepted` stat; handler executes |
| HIL-05 | REQ-CMD-002 | Transmit tampered cmd | OBC increments `rejected_bad_tag`; no handler fire |
| HIL-06 | REQ-CMD-003 | Replay previous valid cmd | OBC increments `rejected_replay` |
| HIL-07 | REQ-FDIR-001 | Unplug BME280 mid-run | FDIR I²C bus counter ≥ 5 within 60 s, beacon shows FAULT stats |
| HIL-08 | REQ-EPS-003 | Drop bus voltage via bench PSU to 3.0 V | OBC enters safe mode within 30 s |
| HIL-09 | REQ-SAFE-002 | While in safe mode, attempt an imaging command | Handler refuses + FDIR logs |
| HIL-10 | REQ-BLD-002 | After 48 h soak | `arm-none-eabi-size firmware.elf` section totals unchanged; HWM stable |

## Soak-run procedure

```
# 0. Flash the image you want to soak.
make flash

# 1. Start ground-station collector.
python3 ground-station/cli/ax25_listen.py --serial /dev/ttyACM0 \
    --out soak_log.jsonl &

# 2. Start telemetry consistency checker (counts beacons, asserts
#    monotonic uptime, logs missed intervals).
python3 tests/hil/soak_sentinel.py \
    --duration 172800 \
    --log soak_log.jsonl \
    --report soak_report.md

# 3. Let it run. 48 h.

# 4. After completion, `soak_report.md` contains pass/fail.
```

The sentinel script is the same shape as
`flight-software/tests/test_long_soak.py` except the clock is real
wall time and the state machine under test is the actual OBC, not
the simulated Python flight-controller.

## Exit criteria (TRL-5 evidence package)

After a clean soak, the operator files a TRL-5 characterisation
packet containing:

1. `docs/characterization/*.md` populated (not TBD).
2. `soak_report.md` showing ≥ 48 h continuous operation.
3. `cppcheck` clean, `coverage` ≥ 80 %, `sanitizers` clean
   (already true at Phase 5 baseline for host tests; HIL adds
   the ARM-target flash/RAM numbers).
4. Three HIL-01..HIL-10 passes on three independent units (to
   rule out a lucky single-board run).

That packet is the *software* deliverable of TRL 5. The hardware
deliverable (vibration, TVAC, radiation) remains out of scope
per `docs/GAPS_AND_ROADMAP.md`.

## Current status

| Test | Status |
|------|:------:|
| Bench BOM defined | ✅ (this document) |
| Wiring diagram | ✅ (this document) |
| Test matrix | ✅ (this document) |
| Firmware HIL hooks (mode command, wcet probe) | ⏳ Phase 6 follow-up |
| `tests/hil/` pytest runner | ⏳ Phase 6 follow-up |
| `scripts/parse_wcet_tlm.py` | ⏳ Phase 6 follow-up |
| Soak sentinel script | ⏳ Phase 6 follow-up |
| First HIL pass on hardware | ⏳ depends on bench BOM purchase |
