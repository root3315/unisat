# System Architecture

## Overview

UniSat follows a layered architecture with clear separation between hardware abstraction, subsystem logic, and mission management.

## Block Diagram

```
┌─────────────────────────────────────────────────────┐
│                 GROUND STATION                       │
│    Streamlit Dashboard / Plotly / Command Center     │
└──────────────────────┬──────────────────────────────┘
                       │ UHF 437 MHz (AX.25/CCSDS)
                       │ S-band 2.4 GHz (CCSDS)
┌──────────────────────┴──────────────────────────────┐
│              FLIGHT CONTROLLER (RPi Zero 2 W)        │
│  Python 3.11+ / asyncio / SQLite / SGP4              │
│  ┌────────────────────────────────────────────────┐  │
│  │ Modules: Camera | Orbit | Health | Scheduler   │  │
│  │          Telemetry | Comm | SafeMode | Power   │  │
│  └────────────────────┬───────────────────────────┘  │
│                       │ UART (115200 baud)            │
│  ┌────────────────────┴───────────────────────────┐  │
│  │         OBC FIRMWARE (STM32F446RE)              │  │
│  │         FreeRTOS 6 Tasks / CCSDS Packets        │  │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐          │  │
│  │  │Sensor│ │  TLM │ │ COMM │ │ ADCS │          │  │
│  │  │ Task │ │ Task │ │ Task │ │ Task │          │  │
│  │  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘          │  │
│  │     │        │        │        │               │  │
│  │  ┌──┴────────┴────────┴────────┴──┐            │  │
│  │  │     Message Queues (FreeRTOS)   │            │  │
│  │  └────────────────────────────────┘            │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

## Communication Buses

| Bus | Protocol | Speed | Connected Devices |
|-----|----------|-------|-------------------|
| I2C1 | I2C FM | 400 kHz | LIS3MDL, BME280, TMP117, u-blox |
| SPI1 | SPI Mode 0 | 5 MHz | MPU9250, MCP3008 |
| USART1 | UART | 9600 baud | UHF transceiver |
| USART2 | UART | 115200 baud | S-band / Flight controller |
| ADC1 | Internal ADC | 12-bit | Battery V/I, Solar V/I, CPU temp |
| GPIO | Digital I/O | — | SBM-20, deploy switches, LEDs |

## State Machine

```
STARTUP ──→ DEPLOYMENT ──→ DETUMBLING ──→ NOMINAL
                                              │
                              ┌────────────────┤
                              ↓                ↓
                         LOW_POWER        SAFE_MODE
                              │                │
                              └────────────────┘
                                      ↓
                                   NOMINAL
```

## Data Flow

1. **Sensors** → SensorTask → telemetryQueue
2. **telemetryQueue** → TelemetryTask → CCSDS packets → CommTask
3. **CommTask** → UART → UHF/S-band radio → Ground Station
4. **Ground Station** → Command → CommTask → commandQueue → Processing
