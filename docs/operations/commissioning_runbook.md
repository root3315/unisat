# Commissioning Runbook — Day 0 to Day 72

**Purpose.** Step-by-step checklist for the first three days in
orbit (LEOP — Launch and Early Orbit Phase). Written from the
ground-operator's seat: what to do, in what order, and what
"good" looks like at each checkpoint.

**Applies to:** UniSat-1 or any derivative mission sharing the
firmware stack in this repo.

---

## Pre-launch — T-24 h through T-0

The point of this section is to make sure the ground station is
ready *before* the launch vehicle lifts off. Every hour spent
here saves two hours of panic later.

### GS-1. Ground-station cold start (T-24 h)

```bash
# From a clean checkout, on the operations laptop:
git clone https://github.com/root3315/unisat.git
cd unisat
./scripts/verify.sh           # ctest + pytest + SITL beacon demo
```

**Pass criterion:** final line `✓ UniSat green. Ready to submit.`

### GS-2. Antenna + transceiver readiness (T-12 h)

1. Point the UHF yagi at the predicted AOS azimuth.
2. Connect the SDR (or TNC) to `ground-station/cli/ax25_listen.py`
   through a piped demodulator.
3. Transmit a known beacon from `ax25_send.py` at low power into
   a dummy load; confirm `ax25_listen` prints the same JSON bytes.

### GS-3. Orbit prediction (T-6 h)

1. Ingest the launch vehicle's pre-release TLE into
   `simulation/orbit_simulator.py`.
2. Compute first three ground-station passes:
   - AOS, TCA (time of closest approach), LOS.
   - Max elevation.
   - Doppler shift.
3. Record in `ops_log.md` — each pass gets a row.

### GS-4. Operator roster (T-2 h)

Two operators minimum per pass for the first 48 h. Sheet with
shifts + callsigns + phone numbers. One operator runs the radio,
the other monitors telemetry + tweets status for the team.

---

## Phase 1 — Acquire first signal (Day 0, first pass)

### Checkpoint A — AOS confirmation

**When:** first pass over the ground station after deployment.
Deployment usually happens ~30 min after separation from the
launch vehicle. Satellite initially tumbles; the initial signal
will be weak and fade-modulated.

**Action:**
1. Start the listener 5 min before predicted AOS:
   ```bash
   python -m cli.ax25_listen --port 52100 --count 0 | tee logs/pass_001.json
   ```
2. Track the yagi manually or via rotator.
3. Watch for any JSON output from the listener.

**Pass criterion:** at least one beacon frame decoded with
`fcs_valid: true` within the predicted pass window.

**Fail handling:**
- Re-check polarization (circular vs linear) on the yagi.
- Step the local oscillator ±5 kHz — the satellite's TCXO may
  have drifted after launch vibration.
- If the next pass is also silent, escalate to Phase 6 (recovery).

### Checkpoint B — Beacon content sanity

Open the decoded JSON and verify:

| Field | Expected first-pass value |
|---|---|
| `src.callsign` | Your mission callsign (e.g. `UN8SAT`) |
| `fcs_valid` | `true` |
| `info_hex` (bytes 0-3) | Small uptime, < 3600 s |
| `info_hex` (byte 4) | OBC mode = 0 (IDLE) or 1 (DETUMBLE) |
| `info_hex` (bytes 5-6) | Battery voltage 3.3-4.1 V converted (raw mV little-endian) |

If uptime is already hours, the satellite has been alive longer
than you expected — check deployment timestamp vs TLE.

---

## Phase 2 — Detumble verification (Days 0-2)

Post-deployment every CubeSat tumbles; the ADCS B-dot controller
spends the first 1-12 h damping the rotation rate. Monitoring this
is the single most important early-mission task.

### Checkpoint C — Angular-rate telemetry

Beacon bytes 32-33 carry `omega` in 0.01 deg/s units (magnitude).

**Expected trajectory:**

| Time since deploy | Typical omega |
|---|---|
| 0 h | 5-15 °/s (post-separation tumble) |
| 1 h | 3-8 °/s (B-dot engaged) |
| 6 h | < 2 °/s |
| 12 h | < 0.5 °/s |

Plot omega vs time — you want a monotonic decay.

**Fail handling:**
- If omega is flat or growing: magnetorquer driver has failed.
  Send the diagnostic command `0x04` (FDIR report) to pull fault
  codes from the dispatcher.
- If ADCS mode is stuck at 0 (IDLE): OBC task scheduler not
  dispatching ADCS_Update. Escalate.

### Checkpoint D — Quaternion stability

Once omega < 0.5 °/s, beacon bytes 16-31 carry the quaternion.
Watch for:
- `|q| == 1.0 ± 0.001` — normalised, good.
- Quaternion slowly drifting under magnetic control — nominal.
- NaN / inf — IMU driver returned garbage, escalate.

---

## Phase 3 — Deploy appendages (Day 2)

Solar panels and antennas stay stowed until:
- omega < 0.5 °/s for 6 consecutive hours.
- Battery SOC ≥ 75 %.
- Two consecutive passes with valid beacon.

### Checkpoint E — Authenticated deploy command

This is the first *uplink* command the mission will send. Every
byte is authenticated with HMAC-SHA256, counter-fresh. See
[`docs/security/ax25_threat_model.md`](../security/ax25_threat_model.md)
for the wire format.

```bash
python scripts/send_command.py \
    --counter $(cat state/last_counter.txt | awk '{print $1+1}') \
    --cmd DEPLOY_PANELS \
    --callsign <YOUR_CALL> \
    --key-file state/mission_key.bin
```

The ground-side script:
1. Reads the last sent counter, increments by 1.
2. Serialises `[counter BE][CCSDS cmd packet]`.
3. Appends HMAC-SHA256 tag.
4. Transmits through the TNC.
5. Persists the new counter to `state/last_counter.txt`.

**Pass criterion:** next beacon shows `mode = 2` (NOMINAL) and
solar power > 1 W.

**Fail handling:**
- Beacon mode still 1 (DETUMBLE): deploy command not acknowledged.
  Verify counter value — it must be strictly greater than the
  last accepted. Dispatcher stats (downlinked in the beacon
  extended housekeeping) will show `rejected_replay` or
  `rejected_bad_tag` if the frame was refused.

---

## Phase 4 — Nominal operations (Days 3-14)

### Checkpoint F — Pass schedule

From Day 3 the satellite should beacon every 30 s. You get 4-6
passes per day over a mid-latitude ground station. Routine:

1. Run `ax25_listen` 5 min before each predicted AOS.
2. After LOS, push the JSON log to the archive:
   ```bash
   cp logs/pass_*.json archive/$(date +%Y-%m-%d)/
   ```
3. If an authenticated command is needed, batch them for the pass
   with highest elevation.
4. Update dashboard in the Streamlit UI.

### Checkpoint G — Anomaly triage

For every pass, check the beacon's error counter (byte 45):

| error_count | Meaning | Action |
|---|---|---|
| 0 | Clean. | Continue. |
| 1-5 | Transient I²C glitches. | Monitor. |
| 6-20 | Sensor flapping. | Log, plan downlink of full error log next pass. |
| 21-255 | Serious fault. | Escalate to Phase 6. |

Saturated errors (byte=0xFF) mean the telemetry counter maxed out —
indicative, not diagnostic. Downlink the full FDIR log.

---

## Phase 5 — First payload activity (Day 14+)

Once you have two weeks of clean telemetry, you can point the
payload. Specifics depend on the mission:

- **Earth observation:** send `ACTIVATE_CAMERA` + `TAKE_IMAGE`
  with TLE-derived ground-point scheduler.
- **Radiation monitor:** already counting passively, downlink
  accumulated dose.
- **IoT relay:** schedule transponder windows.

See the payload's own `README.md` in `payloads/<type>/` for the
command set.

---

## Phase 6 — Recovery procedures

### Safe mode entry

The satellite enters SAFE_MODE autonomously if any of:
- Battery SOC < 20 %.
- 24 h without ground contact.
- Watchdog triggered > 3 times in an hour.
- FDIR severity ≥ SAFE_MODE.

In SAFE_MODE the only active subsystems are:
- Beacon (30 s cadence, reduced payload).
- Battery monitor.
- Command receiver (still HMAC-authenticated).

### Recovery actions (in escalation order)

1. **Wait.** If the trigger was ground contact loss, next
   successful beacon receive will itself clear the flag on
   subsequent ack.
2. **Send `RESET_FDIR`** with an authenticated command; this
   clears the fault log (`.noinit` SRAM) and re-enters
   NOMINAL if no fault is currently tripping.
3. **Send `SOFT_REBOOT`** — OBC restarts, re-runs selftest.
   Counter window is preserved through the A/B key store.
4. **Send `HARD_REBOOT`** — same but includes a deeper init
   (re-calibrate sensors, re-acquire TLE, etc.).
5. **Last-resort:** if nothing responds for 72 h, file a
   collision-conjunction check with 18th SPCS and prepare
   the team for end-of-mission.

Each of these commands is defined in the command dispatcher
and tested in `firmware/tests/test_command_dispatcher.c`.

---

## Appendix A — `ops_log.md` template

Use one log file per mission week. Fill in every pass.

```markdown
# Week of 2026-MM-DD

## Pass 2026-MM-DDThh:mm UTC (AOS) — operator @call
- Max elevation: XX°
- Frames received: N
- fcs_valid: true on all
- mode: 2 (NOMINAL)
- omega:   0.3 °/s
- SOC:     87 %
- errors:  0
- Commands sent: none
- Anomalies: none
```

## Appendix B — Counter tracking

The authenticated-uplink counter persists locally in
`state/last_counter.txt`. Never decrement it. If you lose
the file, the first uplink after re-initialisation will fail
with `rejected_replay`; recover by re-syncing to the
satellite's current highest counter (downlinked in the
extended housekeeping beacon).

## Appendix C — Escalation contacts

Fill this in before launch. Include amateur-radio elmers, IARU
reps, and your national radio regulator emergency contact.
Hard-coded names get stale; keep this appendix a living document.

---

*This runbook is a template. Tailor it to your ground station,
callsign, and mission-specific commands before launch day.*
