# Power Budget

## Solar Generation

| Parameter | Value |
|-----------|-------|
| Solar Constant | 1361 W/m² |
| Panel Type | GaAs Triple Junction |
| Panel Efficiency | 29.5% |
| Panel Area (per face) | 60 cm² |
| Number of Panels (3U) | 6 |
| Average Illumination Factor | 0.35 |
| **Average Generation** | **~4.8 W** |

## Power Consumption by Mode

| Subsystem | Nominal (W) | Peak (W) | Safe Mode (W) |
|-----------|-------------|----------|----------------|
| OBC | 0.50 | 0.80 | 0.50 |
| COMM UHF | 1.00 | 1.50 | 1.00 |
| COMM S-band | 2.00 | 2.50 | OFF |
| ADCS | 0.80 | 1.20 | 0.30 |
| GNSS | 0.30 | 0.40 | OFF |
| Camera | 0.00 | 3.00 | OFF |
| Payload | 0.50 | 0.80 | OFF |
| Heater | 0.00 | 2.00 | OFF |
| **Total** | **5.10** | **12.20** | **1.80** |

## Battery Specifications

| Parameter | Value |
|-----------|-------|
| Cell Type | Panasonic NCR18650B |
| Configuration | 4S1P |
| Capacity | 30 Wh (3.4 Ah × 3.7V × 4) |
| Voltage Range | 12.0 – 16.8 V |
| Charge Cutoff | 4.2 V/cell |
| Discharge Cutoff | 3.0 V/cell |
| Operating Temp | -10°C to +45°C |

## Energy Balance (per orbit, ~92 min)

- Sunlight period: ~60 min → Generation: ~4.8 Wh
- Eclipse period: ~32 min → Generation: 0 Wh
- Nominal consumption per orbit: ~5.1 W × 1.53h = ~7.8 Wh
- **Net balance: ~4.8 - 7.8 = -3.0 Wh** (battery supplements during eclipse)
- SOC swing per orbit: ~10%
