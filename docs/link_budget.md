# Link Budget

## UHF Downlink (437 MHz)

| Parameter | Value |
|-----------|-------|
| TX Power | 1 W (30 dBm) |
| TX Antenna Gain | 0 dBi (monopole) |
| EIRP | 30 dBm |
| Free Space Loss (2000 km) | -152.3 dB |
| Atmospheric Loss | -1.0 dB |
| RX Antenna Gain | 14 dBi (Yagi) |
| Implementation Loss | -2.0 dB |
| Received Power | -111.3 dBm |
| System Noise Temp | 500 K |
| Noise Floor (9600 Hz BW) | -129.8 dBm |
| **SNR** | **18.5 dB** |
| Required Eb/No (BER 10⁻⁵) | 10 dB |
| **Link Margin** | **8.5 dB** |

## S-band Downlink (2.4 GHz)

| Parameter | Value |
|-----------|-------|
| TX Power | 2 W (33 dBm) |
| TX Antenna Gain | 6 dBi (patch) |
| EIRP | 39 dBm |
| Free Space Loss (2000 km) | -167.1 dB |
| Atmospheric Loss | -1.5 dB |
| RX Antenna Gain | 20 dBi (dish) |
| Implementation Loss | -2.0 dB |
| Received Power | -111.6 dBm |
| Noise Floor (256 kHz BW) | -115.5 dBm |
| **SNR** | **3.9 dB** |
| **Link Margin** | **~1 dB** (marginal) |

## Notes
- S-band margin is tight; consider higher gain ground antenna or lower data rate
- UHF link is robust with 8.5 dB margin
