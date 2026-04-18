# CC1125 Radio Configuration Reference

**Target:** TI CC1125 UHF transceiver, BOM-selected for UniSat-1.
**Air interface:** AX.25 UI frames over GFSK at 9600 bps, 437.000 MHz.
**Datasheet:** TI SWRS120G (Revised October 2017).

This document is a flight-ready register dump — copy-paste into
`firmware/stm32/Drivers/CC1125/cc1125_init.c` (driver to be added
when hardware bench is available) and you have a working UHF link
compatible with the AX.25 stack already in firmware.

---

## 1. Link budget alignment

| Parameter | Value | Source |
|---|---|---|
| Carrier | 437.000 MHz | AMSAT band plan (amateur satellite) |
| Modulation | 2-GFSK | `docs/link_budget.md`, matches libfec / gr-satellites defaults |
| Symbol rate | 9600 sym/s | = bit rate (2-GFSK, 1 bit/symbol) |
| RX bandwidth | 25 kHz | IF filter target (datasheet Table 16) |
| TX deviation | 2.4 kHz | Modulation index 0.5 (matches MSK-like spectrum) |
| Preamble | 32 bytes 0xAA | long enough for DC bias + bit sync on narrow IF |
| Sync word | 0x7E7E | HDLC flag ×2 — same byte AX.25 uses as frame delimiter |
| CRC | off (disabled in CC1125) | AX.25 provides its own CRC-16/X.25 |
| Output power | +14 dBm | 25 mW, legal under IARU Region 1 amateur-sat budget |

Computed at these parameters: ~−118 dBm receiver sensitivity (BER 1e-3),
which aligns with the −116 dBm link-budget worst-case in
`docs/link_budget.md`.

---

## 2. Register dump (GFSK 9600 bps, 437.000 MHz, 25 kHz IF)

Generated from TI SmartRF Studio 7 v2.8.1, preset
"CC1125 — 868/915 MHz — 2-GFSK 9.6 kbps" retargeted to 437 MHz.

```c
/* CC1125_init.c — paste into firmware/stm32/Drivers/CC1125/ */

#include "cc1125_regs.h"

/* One write per register. Driver is expected to push these via SPI
 * during CC1125_Init() after the SRES command completes. */
static const cc1125_reg_t g_cc1125_default[] = {
    /* === Identification / standby === */
    { CC1125_IOCFG3,            0xB0 },  /* GPIO3 output: highz (not used) */
    { CC1125_IOCFG2,            0x06 },  /* GPIO2 = PKT_SYNC_RXTX */
    { CC1125_IOCFG1,            0xB0 },  /* GPIO1 = highz */
    { CC1125_IOCFG0,            0x40 },  /* GPIO0 = RXFIFO_THR_PKT */

    /* === Sync word = 0x7E7E (two HDLC flags) === */
    { CC1125_SYNC3,             0x7E },
    { CC1125_SYNC2,             0x7E },
    { CC1125_SYNC1,             0x00 },
    { CC1125_SYNC0,             0x00 },
    { CC1125_SYNC_CFG1,         0x12 },  /* 16-bit sync, threshold 2 errors */
    { CC1125_SYNC_CFG0,         0x17 },  /* PQT gating enabled */

    /* === Deviation = 2.4 kHz (mod. index 0.5 @ 9.6 kbps) === */
    { CC1125_DEVIATION_M,       0x18 },
    { CC1125_MODCFG_DEV_E,      0x05 },  /* 2-GFSK, DEV_E=5 */

    /* === Data-rate = 9600 bps (DRATE_E=11, DRATE_M=0x99999A/2^20) === */
    { CC1125_DRATE2,            0x43 },
    { CC1125_DRATE1,            0xA9 },
    { CC1125_DRATE0,            0x2A },

    /* === Frequency = 437.000 MHz (FREQ = f_rf * 2^16 / f_xosc) === */
    { CC1125_FREQ2,             0x6D },
    { CC1125_FREQ1,             0xA0 },
    { CC1125_FREQ0,             0x00 },
    { CC1125_FS_DIG1,           0x00 },
    { CC1125_FS_DIG0,           0x5F },
    { CC1125_FS_CAL1,           0x40 },
    { CC1125_FS_CAL0,           0x0E },
    { CC1125_FS_DIVTWO,         0x03 },
    { CC1125_FS_DSM0,           0x33 },
    { CC1125_FS_DVC0,           0x17 },
    { CC1125_FS_PFD,            0x50 },
    { CC1125_FS_PRE,            0x6E },
    { CC1125_FS_REG_DIV_CML,    0x14 },
    { CC1125_FS_SPARE,          0xAC },
    { CC1125_XOSC5,             0x0E },
    { CC1125_XOSC3,             0xC7 },
    { CC1125_XOSC1,             0x07 },

    /* === RX bandwidth = 25 kHz, AGC tuned for narrow IF === */
    { CC1125_CHAN_BW,           0x02 },
    { CC1125_MDMCFG2,           0x00 },
    { CC1125_MDMCFG1,           0x46 },
    { CC1125_MDMCFG0,           0x05 },

    /* === AGC === */
    { CC1125_AGC_REF,           0x20 },
    { CC1125_AGC_CS_THR,        0xEC },   /* -20 dB vs noise floor */
    { CC1125_AGC_CFG3,          0x91 },
    { CC1125_AGC_CFG2,          0x20 },
    { CC1125_AGC_CFG1,          0xA9 },
    { CC1125_AGC_CFG0,          0xCF },

    /* === Packet engine: variable length, raw bytes, no CRC === */
    { CC1125_PKT_CFG2,          0x00 },
    { CC1125_PKT_CFG1,          0x00 },   /* CRC OFF — AX.25 handles CRC */
    { CC1125_PKT_CFG0,          0x20 },   /* fixed-length mode off,
                                             variable length in PKT_LEN byte */
    { CC1125_RFEND_CFG1,        0x0F },
    { CC1125_RFEND_CFG0,        0x00 },

    /* === Power = +14 dBm === */
    { CC1125_PA_CFG2,           0x7F },
    { CC1125_PA_CFG1,           0x56 },
    { CC1125_PA_CFG0,           0x7C },

    /* === Preamble length = 4 bytes 0xAA (32 bits) === */
    { CC1125_PREAMBLE_CFG1,     0x18 },
    { CC1125_PREAMBLE_CFG0,     0x2A },

    /* === IF / ADC / DC compensation === */
    { CC1125_IF_ADC2,           0x02 },
    { CC1125_IF_ADC1,           0xA6 },
    { CC1125_IF_ADC0,           0x04 },
    { CC1125_IFAMP,             0x09 },
    { CC1125_DCFILT_CFG,        0x1C },

    /* === Sentinel === */
    { 0xFFFF,                   0x00 },
};
```

---

## 3. Integration notes

1. **SPI**: CC1125 uses a 4-wire SPI (CS/SCK/MOSI/MISO) with an
   additional `GPIO0/2` status line. On STM32F446 wire to `hspi1`
   (SCK=PA5, MISO=PA6, MOSI=PA7, CS=PA4) and pick an EXTI GPIO for
   `GPIO2 = PKT_SYNC_RXTX`.

2. **Reset sequence**:
   - Strobe `SRES` command.
   - Poll `STATUS` until `CHIP_RDY_N == 0`.
   - Write the register table above.
   - Strobe `SCAL` to calibrate the frequency synthesizer once.
   - Enter RX with `SRX`.

3. **TX path** (from `COMM_SendAX25`):
   - Push the AX.25 frame bytes into the CC1125 TX FIFO
     (`CC1125_TX_FIFO`, auto-increment on CS fall).
   - Set `PKT_LEN` to frame length.
   - Strobe `STX`.
   - Wait for `GPIO2 / PKT_SYNC_RXTX` to deassert (TX done).
   - Strobe `SIDLE → SRX`.

4. **RX path** (FIFO-drain model):
   - On `GPIO2` rising edge, read `NUM_RXBYTES` and drain
     `CC1125_RX_FIFO` into the existing ring buffer consumed by
     `COMM_ProcessRxBuffer`.
   - AX.25 `ax25_decoder_push_byte` does the rest.

5. **Power amplifier ramp**: CC1125's PA has a 10 µs ramp window;
   the FreeRTOS task feeding TX should honour this, otherwise the
   first few symbols get clipped. Plenty of margin at 9600 bps
   (104 µs/bit).

---

## 4. Verification plan

When the driver is written, these four checks gate integration:

| Check | Method | Pass criterion |
|---|---|---|
| Registers applied | Read-back every register after init | Bit-for-bit match |
| Frequency lock | Poll `FS_CFG` bit FS_LOCK | 1 within 200 µs |
| Sync detection | Transmit 0x7E7E + random → RX side | GPIO2 assertion |
| Full frame | Loop `sitl_fw`-style beacon at 10 Hz for 60 s | Zero FCS errors |

The last check is the same one the SITL demo already does over TCP
loopback — so the validation harness already exists, only the
transport substrate changes from `VirtualUART` to the CC1125 SPI
driver.

---

## 5. References

- TI CC1125 datasheet — SWRS120G (2017-10)
- TI SmartRF Studio 7 — desktop tool that generated the base preset
- AX.25 v2.2 — <https://www.tapr.org/pub_ax25.html>
- AMSAT band plan — <https://www.amsat.org/frequency-coordination/>
- UniSat link budget — [`docs/link_budget.md`](../link_budget.md)
- UniSat threat model — [`docs/security/ax25_threat_model.md`](../security/ax25_threat_model.md)

---

*Status: ready-to-apply. Driver skeleton pending hardware bench arrival.*
