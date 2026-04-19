# Link Budget

Reference: CCSDS 401.0-B-30 (RF and Modulation), ITU Radio Regulations, ECSS-E-ST-50-05C

## 1. Link Budget Methodology

### 1.1 Friis Transmission Equation

The received power at the ground station is derived from the Friis equation:

```
P_rx = P_tx + G_tx + G_rx - L_fs - L_atm - L_point - L_pol - L_imp

Where:
  P_rx    = Received power (dBm)
  P_tx    = Transmitter output power (dBm)
  G_tx    = Transmit antenna gain (dBi)
  G_rx    = Receive antenna gain (dBi)
  L_fs    = Free space path loss (dB)
  L_atm   = Atmospheric attenuation (dB)
  L_point = Pointing loss (dB)
  L_pol   = Polarization mismatch loss (dB)
  L_imp   = Implementation loss (cable, connector, filter) (dB)
```

### 1.2 Free Space Path Loss Derivation

```
L_fs = 20*log10(4*pi*d/lambda)  [dB]
     = 20*log10(4*pi*d*f/c)
     = 32.45 + 20*log10(f_MHz) + 20*log10(d_km)

For UHF (437 MHz) at slant range 2000 km:
  L_fs = 32.45 + 20*log10(437) + 20*log10(2000)
       = 32.45 + 52.81 + 66.02 = 151.28 dB

For S-band (2.4 GHz) at slant range 2000 km:
  L_fs = 32.45 + 20*log10(2400) + 20*log10(2000)
       = 32.45 + 67.60 + 66.02 = 166.07 dB
```

### 1.3 Slant Range Geometry

```
                        * Satellite (h = 550 km)
                       /|
                      / |
         Slant      /   | h = 550 km
         Range d   /    |
                  /     |
                 / El.  |
    GS  *------/--------*  Subsatellite point
         Earth surface (R_E = 6371 km)

d = sqrt((R_E + h)^2 - R_E^2 * cos^2(El)) - R_E * sin(El)
```

| Elevation (deg) | Slant Range (km) | UHF FSPL (dB) | S-band FSPL (dB) |
|-----------------|-------------------|---------------|-------------------|
| 5 (minimum) | 1932 | 151.0 | 165.8 |
| 10 | 1510 | 148.8 | 163.6 |
| 20 | 1023 | 145.4 | 160.2 |
| 45 | 620 | 141.1 | 155.9 |
| 90 (zenith) | 550 | 140.0 | 154.8 |

## 2. Atmospheric and Propagation Effects

### 2.1 Atmospheric Attenuation

| Effect | UHF (437 MHz) | S-band (2.4 GHz) | Notes |
|--------|--------------|-------------------|-------|
| Tropospheric (dry air) | 0.05 dB | 0.10 dB | At 10 deg elevation |
| Rain attenuation (99.9%) | 0.0 dB | 0.3 dB | ITU-R P.838, moderate climate |
| Cloud/fog | 0.0 dB | 0.05 dB | Negligible at both bands |
| Ionospheric scintillation | 0.5 dB | 0.1 dB | Worst case, high solar activity |
| **Total atmospheric** | **0.55 dB** | **0.55 dB** | |

### 2.2 Faraday Rotation

Faraday rotation of linearly polarized signals through the ionosphere:

```
theta_F = 2.36e4 * TEC / f^2  [radians]

Where:
  TEC = Total Electron Content = 50 TECU (daytime, moderate solar)
  f = frequency in Hz

For UHF (437 MHz):
  theta_F = 2.36e4 * 50e16 / (437e6)^2 = 6.18 rad = 354 deg  (SEVERE)

For S-band (2.4 GHz):
  theta_F = 2.36e4 * 50e16 / (2.4e9)^2 = 0.20 rad = 11.8 deg  (manageable)
```

**Impact:** UHF must use circular polarization to avoid Faraday rotation nulls.
The monopole on the satellite is linearly polarized; ground station Yagi should be
circularly polarized, incurring 3 dB axial ratio loss in worst case.

### 2.3 Polarization Loss

| Configuration | Loss (dB) |
|---------------|-----------|
| Circular TX -- Circular RX (co-pol) | 0.0 |
| Linear TX -- Circular RX | 3.0 |
| Circular TX -- Linear RX | 3.0 |
| Cross-polarized (worst case) | > 20.0 |

For UHF: Linear (sat) to Circular (GS) = 3.0 dB loss (accounted in budget)
For S-band: Circular patch (sat) to Circular dish (GS) = 0.5 dB (axial ratio imperfection)

## 3. UHF Link Budget (437 MHz Downlink)

### 3.1 Detailed Budget

| # | Parameter | Symbol | Value | Unit |
|---|-----------|--------|-------|------|
| 1 | TX Power | P_tx | 30.0 | dBm |
| 2 | TX Cable + Connector Loss | L_tx | -0.5 | dB |
| 3 | TX Antenna Gain (monopole) | G_tx | 0.0 | dBi |
| 4 | TX Pointing Loss | L_point_tx | -1.0 | dB |
| 5 | **EIRP** | | **28.5** | **dBm** |
| 6 | Free Space Path Loss (5 deg el.) | L_fs | -151.0 | dB |
| 7 | Atmospheric Loss | L_atm | -0.55 | dB |
| 8 | Polarization Loss | L_pol | -3.0 | dB |
| 9 | **Total Path Loss** | | **-154.55** | **dB** |
| 10 | RX Antenna Gain (9-el Yagi) | G_rx | 14.0 | dBi |
| 11 | RX Cable + Connector Loss | L_rx | -1.0 | dB |
| 12 | RX Pointing Loss | L_point_rx | -0.5 | dB |
| 13 | **Received Power** | P_rx | **-113.55** | **dBm** |
| 14 | System Noise Temperature | T_sys | 500 | K |
| 15 | Boltzmann Constant | k | -228.6 | dBW/K/Hz |
| 16 | Noise Spectral Density | N_0 | -201.6 | dBW/Hz |
| 17 | Data Rate (9600 bps) | R | 39.8 | dB-Hz |
| 18 | **Eb/N0 (received)** | | **18.2** | **dB** |
| 19 | Required Eb/N0 (GMSK, BER=1e-5) | | 9.6 | dB |
| 20 | Coding Gain (conv. r=1/2, K=7) | G_code | 5.2 | dB |
| 21 | **Required Eb/N0 (with coding)** | | **4.4** | **dB** |
| 22 | **Link Margin** | | **13.8** | **dB** |

### 3.2 UHF Uplink (437 MHz)

| Parameter | Value | Unit |
|-----------|-------|------|
| GS TX Power | 36.0 | dBm (4 W) |
| GS Antenna Gain | 14.0 | dBi |
| GS Cable Loss | -1.0 | dB |
| EIRP | 49.0 | dBm |
| Path Loss (total) | -154.55 | dB |
| Sat RX Antenna Gain | 0.0 | dBi |
| Sat RX Cable Loss | -0.5 | dB |
| Received Power | -106.05 | dBm |
| Noise Temp (800 K, Earth-facing) | 800 | K |
| Eb/N0 (received) | 12.1 | dB |
| Required Eb/N0 (with coding) | 4.4 | dB |
| **Link Margin** | **7.7** | **dB** |

## 4. S-band Link Budget (2.4 GHz Downlink)

### 4.1 Detailed Budget

| # | Parameter | Symbol | Value | Unit |
|---|-----------|--------|-------|------|
| 1 | TX Power | P_tx | 33.0 | dBm |
| 2 | TX Cable + Connector Loss | L_tx | -1.0 | dB |
| 3 | TX Antenna Gain (patch) | G_tx | 6.0 | dBi |
| 4 | TX Pointing Loss (5 deg error) | L_point_tx | -1.5 | dB |
| 5 | **EIRP** | | **36.5** | **dBm** |
| 6 | Free Space Path Loss (10 deg el.) | L_fs | -163.6 | dB |
| 7 | Atmospheric Loss | L_atm | -0.55 | dB |
| 8 | Polarization Loss | L_pol | -0.5 | dB |
| 9 | **Total Path Loss** | | **-164.65** | **dB** |
| 10 | RX Antenna Gain (2.4m dish) | G_rx | 30.0 | dBi |
| 11 | RX Cable + Connector Loss | L_rx | -1.5 | dB |
| 12 | RX Pointing Loss | L_point_rx | -0.3 | dB |
| 13 | **Received Power** | P_rx | **-99.95** | **dBm** |
| 14 | System Noise Temperature | T_sys | 200 | K |
| 15 | Noise Spectral Density | N_0 | -205.6 | dBW/Hz |
| 16 | Data Rate (256 kbps) | R | 54.1 | dB-Hz |
| 17 | **Eb/N0 (received)** | | **21.5** | **dB** |
| 18 | Required Eb/N0 (QPSK, BER=1e-5) | | 9.6 | dB |
| 19 | Coding Gain (LDPC r=1/2) | G_code | 7.5 | dB |
| 20 | **Required Eb/N0 (with coding)** | | **2.1** | **dB** |
| 21 | **Link Margin** | | **19.4** | **dB** |

Note: The original S-band budget showed ~1 dB margin using a 20 dBi ground antenna. Upgrading to a
2.4m dish (30 dBi) and adding LDPC coding resolves the margin issue with substantial reserve.

## 5. Modulation and Coding Comparison

### 5.1 Modulation Schemes

| Modulation | Spectral Eff. (bps/Hz) | Req. Eb/N0 @ BER=1e-5 | Complexity | Selected For |
|------------|----------------------|----------------------|------------|-------------|
| BPSK | 1.0 | 9.6 dB | Low | - |
| GMSK (BT=0.5) | 1.0 | 9.6 dB | Low | UHF |
| QPSK | 2.0 | 9.6 dB | Medium | S-band |
| 8PSK | 3.0 | 13.0 dB | High | - |
| 16QAM | 4.0 | 13.4 dB | High | - |
| MSK | 1.0 | 9.6 dB | Low | - |

### 5.2 Forward Error Correction (FEC)

| Code | Rate | Coding Gain (dB) | Complexity | Standard |
|------|------|------------------|------------|----------|
| None (uncoded) | 1.0 | 0.0 | None | - |
| Conv. r=1/2, K=7 | 0.5 | 5.2 | Low | CCSDS 131.0-B-3 |
| Reed-Solomon (255,223) | 0.87 | 3.0 | Medium | CCSDS 131.0-B-3 |
| Conv + RS (concatenated) | 0.44 | 7.4 | Medium | CCSDS 131.0-B-3 |
| Turbo r=1/2 | 0.5 | 8.5 | High | CCSDS 131.0-B-3 |
| LDPC r=1/2 | 0.5 | 7.5 | Medium | CCSDS 131.1-O-2 |
| LDPC r=7/8 | 0.875 | 4.5 | Medium | CCSDS 131.1-O-2 |

**Selected:** Convolutional r=1/2, K=7 for UHF (low complexity); LDPC r=1/2 for S-band (best gain-to-complexity ratio)

## 6. Link Margin Sensitivity Analysis

### 6.1 Sensitivity to Elevation Angle

| Elevation | UHF Margin (dB) | S-band Margin (dB) | Contact Fraction |
|-----------|-----------------|---------------------|-----------------|
| 5 deg | 13.8 | 19.4 | 100% of passes |
| 10 deg | 16.0 | 21.6 | 85% of pass time |
| 20 deg | 19.4 | 25.0 | 60% of pass time |
| 45 deg | 23.7 | 29.3 | 25% of pass time |
| 90 deg | 24.8 | 30.4 | < 5% of pass time |

### 6.2 Sensitivity to Key Parameters

Impact of +/- 3 dB change in each parameter on UHF link margin:

| Parameter | Nominal | -3 dB effect | +3 dB effect |
|-----------|---------|-------------|-------------|
| TX Power | 30 dBm | Margin = 10.8 dB | Margin = 16.8 dB |
| TX Antenna Gain | 0 dBi | Margin = 10.8 dB | Margin = 16.8 dB |
| RX Antenna Gain | 14 dBi | Margin = 10.8 dB | Margin = 16.8 dB |
| System Noise Temp | 500 K | Margin = 16.8 dB | Margin = 10.8 dB |
| Data Rate | 9.6 kbps | Margin = 16.8 dB | Margin = 10.8 dB |

### 6.3 Rain Fade Analysis (S-band)

Per ITU-R P.618, rain attenuation at 2.4 GHz for Tashkent (climate zone K):

| Availability | Rain Rate (mm/hr) | Attenuation (dB) | S-band Margin Remaining |
|--------------|-------------------|-------------------|------------------------|
| 99.0% | 12 | 0.15 | 19.3 dB |
| 99.9% | 32 | 0.30 | 19.1 dB |
| 99.99% | 65 | 0.55 | 18.9 dB |

Rain fade is not a significant concern at 2.4 GHz. Impact becomes meaningful only above 10 GHz.

## 7. Data Throughput Analysis

### 7.1 Effective Data Rate

| Parameter | UHF | S-band |
|-----------|-----|--------|
| Raw bit rate | 9,600 bps | 256,000 bps |
| FEC overhead (rate) | 0.5 | 0.5 |
| AX.25/CCSDS framing overhead | 15% | 8% |
| Effective data rate | 4,080 bps | 117,760 bps |
| Per pass (8 min avg) | 240 KB | 6.9 MB |
| Per pass (12 min best) | 360 KB | 10.4 MB |
| Daily (6 passes, UHF+S) | 1.44 MB UHF + 41.4 MB S | 42.8 MB total |

### 7.2 Image Downlink Time

| Image Type | Size | S-band Passes Needed | UHF Passes Needed |
|------------|------|---------------------|-------------------|
| Thumbnail (320x240, JPEG) | 50 KB | < 1 | < 1 |
| Preview (1280x960, JPEG) | 500 KB | < 1 | 2 |
| Full frame (2592x1944, JPEG) | 3 MB | < 1 | 8 |
| Full frame (RAW) | 10 MB | 1-2 | 28 |
| Multispectral set (3 bands) | 30 MB | 3-5 | 83 |

## 8. Ground Station Configuration

### 8.1 Tashkent Primary Station

| Parameter | UHF System | S-band System |
|-----------|-----------|--------------|
| Antenna | 9-element cross Yagi | 2.4m parabolic dish |
| Gain | 14.0 dBi | 30.0 dBi |
| Polarization | RHCP | RHCP |
| Feed | Crossed dipole | Scalar horn |
| LNA | NF = 0.5 dB, Gain = 20 dB | NF = 0.7 dB, Gain = 25 dB |
| Tracking | Az/El rotator, auto-track | Az/El rotator, program track |
| TX Power | 4 W (uplink) | N/A (downlink only) |
| T_sys | 500 K | 200 K |

## 9. References

- CCSDS 401.0-B-30: Radio Frequency and Modulation Systems, 2020
- CCSDS 131.0-B-3: TM Synchronization and Channel Coding, 2017
- CCSDS 131.1-O-2: LDPC Coding for Near-Earth Applications, 2015
- ITU-R P.618-13: Propagation Data for Design of Earth-Space Systems
- ITU-R P.838-3: Specific Attenuation Model for Rain
- Wertz, "Space Mission Engineering: The New SMAD", Chapter 16
- ECSS-E-ST-50-05C: Radio Frequency and Modulation, 2008
