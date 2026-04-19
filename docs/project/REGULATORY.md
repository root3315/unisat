# Regulatory and Licensing Guide

**Audience:** teams who intend to fly UniSat on real hardware, not
just submit the software as a competition deliverable.

Software on its own needs no licence. The moment you emit RF
energy or attempt an orbital launch, regulators enter the picture.
This guide maps the pieces you will actually hit; it is not legal
advice.

---

## Decision tree

```
Do you transmit RF from a ground station or payload?
├── No  → no radio licence required, skip to §5 (launch).
└── Yes → §1 (amateur) → §2 (IARU coordination) → §3 (national).

Do you launch the object?
├── No  (simulation only, CanSat indoors)
│     → only §4 (export control) if publishing to international teams.
└── Yes
    ├── Sub-orbital (rocket ≤ 100 km)   → §5.A
    ├── High-altitude balloon            → §5.B
    └── Orbital                          → §5.C  (serious paperwork)
```

---

## 1. Amateur radio licence

UniSat's UHF link at 437 MHz lives inside the amateur-satellite
band — free to use, but only by licensed operators. The path to a
callsign is the same wherever you are:

1. Pick the national amateur-radio authority:
   - **US:** FCC — Technician / General / Extra exams. 35 USD.
   - **UK:** Ofcom — Foundation / Intermediate / Full.
   - **RU:** Roskomnadzor / SRR — categories 1-4.
   - **DE:** BNetzA — Klasse A / E.
   - **EU general:** CEPT T/R 61-01 / 61-02 for cross-border
     recognition.
2. Pass the Technician-class (or equivalent) exam — basic RF,
   operating rules, safety. ~2 weeks of study for a motivated
   student.
3. Receive a callsign (the `UN8SAT-1` example throughout UniSat
   docs is illustrative; **replace it with your real callsign
   before first transmission**).

**Budget:** 30–70 USD, 2-6 weeks wall time.

---

## 2. IARU frequency coordination

For any satellite using the amateur-satellite service, IARU
(International Amateur Radio Union) runs the global frequency
coordination to prevent two sats from stepping on each other.

1. Fill in the online form at
   <https://www.amsat.org/frequency-coordination/>.
2. Supply: mission description, orbit, launch date, uplink and
   downlink frequencies, modulation, TX power, callsign.
3. Lead time: **3 months** minimum before launch; coordinators
   like it earlier. Fee: free.
4. IARU assigns (or confirms) your frequency, typically within
   the 435.000 – 438.000 MHz amateur sub-band.

**Gatekeeper for: ITU filings, launch-provider acceptance,
CSLI / RSpace, orbital insurance.** Skipping IARU is a red
flag to every launch broker.

---

## 3. National radio regulator

Your country's telecom regulator signs off on the satellite as a
radio station:

- **US:** FCC Form 312 (Experimental Licence) or Part 25 for
  commercial. CubeSat-specific guidance at
  <https://www.fcc.gov/space-station-licensing-filings>.
- **EU:** national authority + ECC report 88 for small satellites.
- **RU:** GKRCh (State Commission on Radio Frequencies) approval
  via the operator. Use of 435–438 MHz inside amateur service is
  permitted without a commercial licence.

Expect paperwork: radio diagram, emission masks, EIRP calculations,
launch schedule. Provide the link-budget and threat-model docs
already in this repo — they cover most of what regulators want.

---

## 4. Export control

Space-related software can be dual-use. Before publishing or
collaborating across borders:

- **US:** EAR (Export Administration Regulations) — CubeSat
  software is usually ECCN 9E001/9D001, controlled for NS,
  RS, AT. Open-source release on public GitHub is exempt
  under the TSU publicly-available exception, but adding an
  export-control notice to NOTICE or README is prudent.
- **EU:** Dual-Use Regulation 2021/821 — category 9 (aerospace).
- **RU:** FSTEC and Minpromtorg oversee the same territory.

If your team has members from multiple jurisdictions, do a one-page
legal check before release. The MIT→Apache 2.0 licence migration
already made in v1.2.0 does not change export control status.

---

## 5. Launch-specific filings

### 5.A  Sub-orbital rocket / CanSat dropped from a balloon

- **US:** FAA / AST — Sub-Orbital Reusable Launch Vehicle rules
  if > 100 km apogee. Below that, university ranges (Spaceport
  America, Hanksville) handle waivers locally.
- **EU / RU:** university ranges typically cover regulatory via
  institutional agreement.

### 5.B  High-altitude balloon

- **US:** FAA Part 101 — weight/size limits drive the
  notification level. Unmanned balloons under 4 pounds are
  largely unregulated but still need NOTAM coordination.
- **Many countries:** civil aviation authority notification, no
  licence if under the weight / altitude thresholds.

### 5.C  Orbital CubeSat (the real deal)

1. **Launch provider contract** — commercial (SpaceX Rideshare,
   NanoRacks, Exolaunch) or government (NASA CSLI). CSLI is free
   for US educational teams but selective.
2. **ITU filing** — the national spectrum regulator files with
   ITU on your behalf (API stage, C/D coordination, notification).
   12-18 months lead time.
3. **IARU coordination** (§2) — feeds ITU.
4. **National space-agency licence** — Space Act Title 51 in the
   US, Russian Space Act Chapter 2, German Space Activities Act,
   etc. Demonstrates liability insurance (typically 60 M USD
   TPL) and de-orbit plan under 25 years.
5. **Deployment safety review** — launch provider's P-POD test
   plan, random vibration profile, thermal-vacuum qualification
   records. UniSat's `docs/testing/hil_test_plan.md` and mass
   budget feed into this review.
6. **De-orbit plan** — most authorities require < 25 years
   post-mission. Our 550 km SSO template decays in ~5 years
   naturally (see `docs/budgets/orbit_analysis.md`).

**Total wall time:** 18-36 months from first regulator contact
to launch vehicle handover for a typical university CubeSat.

---

## 6. What UniSat already provides for regulators

| Reviewer asks for… | UniSat doc |
|---|---|
| Emission description | `docs/design/communication_protocol.md` + `docs/hardware/CC1125_configuration.md` |
| Link budget | `docs/budgets/link_budget.md` |
| Power budget | `docs/budgets/power_budget.md` |
| Mass budget | `docs/budgets/mass_budget.md` |
| Orbit / de-orbit | `docs/budgets/orbit_analysis.md` |
| Thermal margins | `docs/budgets/thermal_analysis.md` |
| FDIR / safe-mode behaviour | `docs/reliability/fdir.md` |
| Command authentication | `docs/security/ax25_threat_model.md` |
| Software requirements | `docs/requirements/SRS.md` + traceability.csv |
| Testing evidence | `docs/testing/hil_test_plan.md` |

You still supply the physical artefacts — antenna pattern, launch
environment tests, operations centre procedures — but the software
story is already assembled.

---

## 7. Shortcuts for students

If you only need **to run a competition**, you typically do not
need anything in §§2-5. Competition organizers run the range
under an umbrella licence. Check the specific rulebook:

- **CanSat championship:** no radio licence needed by the team,
  organizer's range covers it.
- **CubeSat Design challenge:** simulation-only; no RF transmitted.
- **NASA Space Apps:** software-only, no regulatory exposure.
- **Spaceport America Cup:** range users must obtain an FAA COA;
  the organizer helps with the paperwork.

In those contexts, treat this document as background knowledge
useful for the "how would you deploy for real" question during
the defence.

---

*This document is informational, not legal advice. Regulations
change. Contact your national regulator before you transmit.*
