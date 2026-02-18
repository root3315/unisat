# Thermal Analysis

## Environment

| Source | Heat Flux |
|--------|-----------|
| Solar Radiation | 1361 W/m² (direct) |
| Earth Albedo | ~408 W/m² (30% reflection) |
| Earth IR | 237 W/m² (average) |
| Cosmic Background | 2.725 K (~0 W/m²) |

## Thermal Properties

| Parameter | Value |
|-----------|-------|
| Surface Treatment | Black anodized aluminum |
| Solar Absorptivity (α) | 0.88 |
| IR Emissivity (ε) | 0.85 |
| Internal Dissipation | 3.5 W (nominal) |

## Temperature Predictions

### Hot Case (full sun, max power)
- External faces: +45°C to +65°C
- Internal average: +40°C
- Battery: +35°C

### Cold Case (eclipse, minimum power)  
- External faces: -35°C to -15°C
- Internal average: -10°C
- Battery: +5°C (heater active)

### Operating Limits

| Component | Min (°C) | Max (°C) |
|-----------|----------|----------|
| STM32F4 MCU | -40 | +85 |
| Li-ion Battery | -10 | +45 |
| Camera Sensor | -20 | +60 |
| Solar Cells | -100 | +100 |
| General Electronics | -20 | +60 |

## Thermal Control Strategy
- **Passive:** MLI blanket, black anodized surfaces, thermal mass
- **Active:** Battery heater (1W) activated below 0°C
- **Software:** Duty cycle reduction in hot case
