# System Architecture

Reference: ECSS-E-ST-40C (Software Engineering), CCSDS 133.0-B-2, CubeSat Design Specification Rev. 14

## 1. Overview

UniSat follows a layered architecture with clear separation between hardware abstraction, subsystem logic, and mission management. The system is split across two processors: an STM32F446RE microcontroller running FreeRTOS for real-time control, and a Raspberry Pi Zero 2 W running Python 3.11+ asyncio for high-level mission management, image processing, and ground station communication.

## 2. System Block Diagram

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

## 3. Software Architecture Layers

### 3.1 Layer Diagram

```
┌──────────────────────────────────────────────────┐
│  Layer 4: APPLICATION (Mission Management)       │
│  flight_controller.py, scheduler.py, safe_mode   │
├──────────────────────────────────────────────────┤
│  Layer 3: SUBSYSTEM (Domain Logic)               │
│  obc.c, eps.c, adcs.c, comm.c, telemetry.c      │
├──────────────────────────────────────────────────┤
│  Layer 2: DRIVER (Device Abstraction)            │
│  lis3mdl.c, bme280.c, mpu9250.c, ublox.c        │
│  tmp117.c, sbm20.c, mcp3008.c, sun_sensor.c     │
├──────────────────────────────────────────────────┤
│  Layer 1: HAL (Hardware Abstraction Layer)        │
│  stm32f4xx_hal_i2c, _spi, _uart, _adc, _gpio   │
├──────────────────────────────────────────────────┤
│  Layer 0: HARDWARE                               │
│  STM32F446RE, CC1125, SPV1040, sensors, radios   │
└──────────────────────────────────────────────────┘
```

### 3.2 Layer Descriptions

| Layer | Name | Responsibility | Allowed Dependencies |
|-------|------|----------------|----------------------|
| 4 | Application | Mission scheduling, orbit prediction, image processing, safe mode logic | Layer 3 (via UART) |
| 3 | Subsystem | Sensor fusion, ADCS control, EPS management, CCSDS packetization | Layer 2, FreeRTOS API |
| 2 | Driver | Register-level I/O for each IC, data parsing, calibration | Layer 1 only |
| 1 | HAL | STM32 CubeMX-generated peripheral initialization and low-level I/O | Hardware registers |
| 0 | Hardware | Physical ICs, buses, connectors | N/A |

**Strict rule:** No layer may call into a layer more than one level below it. The Application layer (RPi) communicates with the Subsystem layer (STM32) exclusively through UART CCSDS packets.

## 4. Communication Buses

| Bus | Protocol | Speed | Connected Devices |
|-----|----------|-------|-------------------|
| I2C1 | I2C FM | 400 kHz | LIS3MDL (0x1C), BME280 (0x76), TMP117 (0x48), u-blox (0x42) |
| SPI1 | SPI Mode 0 | 5 MHz | MPU9250 (PA4 CS), MCP3008 (PA5 CS) |
| USART1 | UART | 9600 baud | UHF transceiver (CC1125) |
| USART2 | UART | 115200 baud | S-band / Flight controller (RPi) |
| ADC1 | Internal ADC | 12-bit | Battery V/I, Solar V/I, CPU temp |
| GPIO | Digital I/O | -- | SBM-20 (pulse), deploy switches, LEDs |

### 4.1 I/O Retry Policy

All bus operations follow a uniform retry policy (defined in `config.h`):
- Max retries: 3 (`IO_MAX_RETRIES`)
- Retry delay: 10 ms (`IO_RETRY_DELAY_MS`)
- Timeout per transaction: 100 ms (`IO_TIMEOUT_MS`)
- Failure action: Log `ERR_SENSOR_TIMEOUT`, continue with stale data

## 5. Inter-Process Communication (FreeRTOS)

### 5.1 Message Queues

| Queue | Depth | Item Size | Producer | Consumer |
|-------|-------|-----------|----------|----------|
| `telemetryQueue` | 16 | sizeof(SensorData_t) = 96 B | SensorTask | TelemetryTask |
| `commandQueue` | 8 | 64 bytes | CommTask | CommandProcessor |
| `adcsQueue` | 8 | sizeof(SensorData_t) = 96 B | SensorTask | ADCSTask |

### 5.2 Synchronization Primitives

| Primitive | Type | Purpose |
|-----------|------|---------|
| UART TX Mutex | osMutexId_t | Prevents interleaving of CCSDS packets on USART1/2 |
| EPS Data Mutex | osMutexId_t | Protects battery SOC and power rail state |
| Beacon Timer | osSemaphoreId_t | Signals CommTask to transmit beacon every 30 s |
| Error Log Mutex | osMutexId_t | Serializes writes to error_handler EEPROM log |

### 5.3 Task Table

| Task | Priority | Stack (words) | Period | Watchdog Fed |
|------|----------|---------------|--------|--------------|
| WatchdogTask | 5 (highest) | 256 | 1000 ms | Hardware IWDG |
| CommTask | 4 | 1024 | 100 ms poll | TASK_COMM |
| SensorTask | 3 | 512 | 1000 ms | TASK_SENSOR |
| ADCSTask | 3 | 1024 | On queue event | TASK_ADCS |
| TelemetryTask | 2 | 512 | On queue event | TASK_TELEMETRY |
| PayloadTask | 1 (lowest) | 512 | 5000 ms | TASK_PAYLOAD |

## 6. Memory Architecture

### 6.1 STM32F446RE Memory Map

| Region | Address | Size | Usage |
|--------|---------|------|-------|
| Flash (code) | 0x0800_0000 | 512 KB | Firmware image, constants, ISR vectors |
| SRAM1 | 0x2000_0000 | 112 KB | FreeRTOS heap, task stacks, globals |
| SRAM2 | 0x2001_C000 | 16 KB | DMA buffers (UART RX/TX, SPI) |
| Backup SRAM | 0x4002_4000 | 4 KB | Reset count, last error, persistent config |
| CCM RAM | 0x1000_0000 | 64 KB | ADCS matrices, quaternion workspace |

### 6.2 External Storage

| Device | Interface | Capacity | Purpose |
|--------|-----------|----------|---------|
| FRAM (FM25V20A) x2 | SPI | 2 x 256 KB | Error log, telemetry ring buffer, calibration data |
| NOR Flash (W25Q128JV) x2 | SPI | 2 x 16 MB | Firmware golden image (A/B), science data staging |
| SD Card | SDIO | 32 GB | Image storage, long-term telemetry archive |

### 6.3 Memory Budget (SRAM)

```
Total SRAM: 128 KB (112 + 16)

FreeRTOS Heap:          32 KB  (configTOTAL_HEAP_SIZE)
Task Stacks:
  WatchdogTask           1 KB  (256 words)
  CommTask               4 KB  (1024 words)
  SensorTask             2 KB  (512 words)
  ADCSTask               4 KB  (1024 words)
  TelemetryTask          2 KB  (512 words)
  PayloadTask            2 KB  (512 words)
Message Queues:
  telemetryQueue        1.5 KB (16 x 96 B)
  commandQueue          0.5 KB (8 x 64 B)
  adcsQueue             0.75 KB (8 x 96 B)
Global Data:             8 KB  (config, status structs, buffers)
DMA Buffers:            16 KB  (SRAM2, UART RX/TX rings)
─────────────────────────────────
Total Allocated:        ~74 KB
Remaining:              ~54 KB  (42% margin)
```

## 7. Software State Machine

### 7.1 State Diagram

```
                ┌──────────────────────────────────┐
                │           STARTUP                │
                │  HAL_Init, peripheral init,       │
                │  sensor self-test, queue create   │
                └──────────┬───────────────────────┘
                           │ All init OK
                           ▼
                ┌──────────────────────────────────┐
                │         DEPLOYMENT               │
                │  Wait 30 min (CDS requirement),   │
                │  deploy antennas, confirm release │
                └──────────┬───────────────────────┘
                           │ Antenna deployed
                           ▼
                ┌──────────────────────────────────┐
                │         DETUMBLING               │
                │  B-dot control via magnetorquers  │
                │  Target: omega < 2 deg/s          │
                └──────────┬───────────────────────┘
                           │ omega < 2 deg/s for 60 s
                           ▼
              ┌────────────────────────────────────┐
              │            NOMINAL                  │
              │  Full operations, all subsystems ON │
              ├──────────────┬─────────────────────┤
              │              │                      │
     ┌────────▼───┐    ┌────▼──────┐               │
     │ LOW_POWER  │    │ SAFE_MODE │               │
     │ V_bat<12.4V│    │ Comm loss │               │
     │ Non-essen. │    │ >24h, or  │               │
     │ loads OFF  │    │ critical  │               │
     └─────┬──────┘    │ error     │               │
           │           └─────┬─────┘               │
           │  V_bat>14V      │ Comm restored OR    │
           │  & sun detected │ auto-recovery OK    │
           └─────────────────┴─────────────────────┘
                             │
                             ▼
                          NOMINAL
```

### 7.2 Transition Guard Conditions

| From | To | Guard Condition | Action on Entry |
|------|----|-----------------|-----------------|
| STARTUP | DEPLOYMENT | All peripherals init OK, sensor self-test pass | Start 30-min timer |
| DEPLOYMENT | DETUMBLING | Deploy timer expired, antenna confirm | Enable magnetorquers, ADCS B-dot mode |
| DETUMBLING | NOMINAL | Angular rate < 2 deg/s sustained 60 s | Enable all subsystems, start beacon |
| NOMINAL | LOW_POWER | V_bat < 12.4 V (SOC < 15%) | Disable CAMERA, PAYLOAD, S-BAND, HEATER |
| NOMINAL | SAFE_MODE | Comm loss > 24 h OR ERR_CRITICAL_BATTERY OR ERR_WATCHDOG_TIMEOUT | Disable all non-essential, beacon only |
| LOW_POWER | NOMINAL | V_bat > 14.0 V AND sun detected | Sequential re-enable with 5 s delays |
| SAFE_MODE | NOMINAL | Valid TC received OR auto-recovery pass (max 5 attempts, 1 h apart) | Full subsystem re-init sequence |

## 8. Interface Control Document (ICD) Summary

| Interface | From | To | Physical | Protocol | Data Rate | Packet Format |
|-----------|------|----|----------|----------|-----------|---------------|
| IF-01 | OBC | EPS | Internal bus | I2C registers | On demand | Raw register R/W |
| IF-02 | OBC | ADCS Sensors | I2C1, SPI1 | Driver API | 1 Hz poll | SensorData_t struct |
| IF-03 | OBC | UHF Radio | USART1, 9600 | AX.25 + CCSDS | 9600 bps | CCSDS_Packet_t |
| IF-04 | OBC | S-band Radio | USART2, 115200 | CCSDS | 256 kbps | CCSDS_Packet_t |
| IF-05 | OBC | Flight Ctrl | USART2, 115200 | CCSDS | 115200 bps | CCSDS_Packet_t |
| IF-06 | OBC | GNSS | I2C1 | UBX binary | On demand | UBX-NAV-PVT |
| IF-07 | OBC | Payload | GPIO + SPI | Custom | On demand | Payload_ReadData() |
| IF-08 | GS | Satellite | RF 437 MHz | AX.25 + CCSDS | 9600 bps | TC/TM packets |
| IF-09 | GS | Satellite | RF 2.4 GHz | CCSDS | 256 kbps | TM bulk data |

## 9. Fault Detection, Isolation and Recovery (FDIR)

### 9.1 FDIR Strategy Overview

FDIR follows a three-level hierarchy per ECSS-Q-ST-30C:

| Level | Scope | Response Time | Actor |
|-------|-------|---------------|-------|
| L0 - Hardware | Peripheral level | < 1 ms | Watchdog IC, voltage supervisor |
| L1 - Software autonomous | Subsystem level | < 10 s | `Error_Handler`, `Watchdog_CheckAll`, `fdir.c` advisor |
| L1.5 - System supervisor | Mode level | < 1 s (watchdog tick) | `mode_manager.c` drives SAFE/DEGRADED/REBOOT from FDIR aggregate |
| L1.6 - Persistent log | Ring buffer | across warm reboots | `fdir_persistent.c` — .noinit SRAM + CRC |
| L2 - Ground commanded | System level | Next pass (~90 min) | Ground operator TC |

> **TRL-5 hardening (branch `feat/trl5-hardening`):** the firmware now
> carries a full software-side FDIR stack under
> `firmware/stm32/Core/{Inc,Src}/`:
> * `fdir.c/.h` — table-driven fault advisor, 12 fault IDs, 60 s escalation
>   window (details in [docs/reliability/fdir.md](reliability/fdir.md))
> * `mode_manager.c/.h` — polls FDIR at 1 Hz in WatchdogTask and drives
>   the satellite-level mode transition
> * `fdir_persistent.c/.h` — warm-reboot-survivable fault ring in .noinit
> * `key_store.c/.h` — A/B persistent HMAC key with monotonic generation
> * `command_dispatcher.c/.h` — HMAC + 32-bit replay counter for uplink
>
> See [docs/requirements/SRS.md](requirements/SRS.md) for the
> requirement-level contract and the per-REQ test coverage.

### 9.2 Fault Table

| Fault ID | Detection Method | Isolation | Recovery |
|----------|------------------|-----------|----------|
| ERR_SENSOR_TIMEOUT | I/O timeout > 100 ms, 3 retries | Mark sensor STALE, use last-known | Re-init sensor driver, continue |
| ERR_COMM_FAILURE | TX fail 3x, no RX > 60 s | Increment error counter | Reset UART peripheral, re-init CC1125 |
| ERR_LOW_BATTERY | V_bat < 12.4 V (ADC read) | Transition to LOW_POWER | Shed loads: Camera, Payload, S-band |
| ERR_CRITICAL_BATTERY | V_bat < 12.0 V | Transition to SAFE_MODE | Emergency shutdown non-essential loads |
| ERR_ADCS_FAILURE | Pointing error > 30 deg sustained | Disable reaction wheels | Fall back to B-dot magnetorquer control |
| ERR_WATCHDOG_TIMEOUT | Task missed Watchdog_Feed > 10 s | Identify stalled task | Restart stalled task; if 3x fail, reboot OBC |
| ERR_MEMORY_CORRUPT | CRC mismatch on FRAM read | Isolate corrupted region | Switch to backup FRAM, log event |
| ERR_TEMPERATURE_HIGH | CPU temp > 85 C or sensor > 60 C | Reduce duty cycle | Disable high-power loads, wait for cooling |
| ERR_TEMPERATURE_LOW | Battery temp < -10 C | Enable heater | PWM heater ON until T > 0 C |

### 9.3 Error Severity and Response

```
ERROR_DEBUG     → Log only (FRAM ring buffer)
ERROR_INFO      → Log + increment counter
ERROR_WARNING   → Log + telemetry alert flag
ERROR_ERROR     → Log + attempt autonomous recovery
ERROR_CRITICAL  → Log + enter SAFE_MODE immediately
```

## 10. Boot Sequence

```
Time (ms)   Action
────────────────────────────────────────────────────────
   0        Power-on reset / IWDG reset detected
   1        HAL_Init() — SysTick, NVIC priority grouping
   3        SystemClock_Config() — HSE 8 MHz → PLL 180 MHz
   5        MX_GPIO_Init() — Deploy switches, LEDs, CS pins
   8        MX_I2C1_Init() — 400 kHz, 7-bit addressing
  10        MX_SPI1_Init() — 5 MHz, Mode 0, MSB first
  12        MX_USART1_UART_Init() — 9600, 8N1 (UHF)
  14        MX_USART2_UART_Init() — 115200, 8N1 (S-band/RPi)
  16        MX_ADC1_Init() — 12-bit, scan mode
  18        MX_TIM2_Init() — 1 ms tick for SBM-20 pulse count
  20        Config_Init() — Load compile-time config into RAM
  25        OBC_Init() — Read reset count from backup SRAM
  30        EPS_Init() — Read battery voltage, start MPPT
  35        COMM_Init() — Configure CC1125, enable RX interrupt
  40        ADCS_Init() — Zero bias estimates, set IDLE mode
  45        GNSS_Init() — Send UBX-CFG-PRT, set navigation rate
  50        Sensors_Init() — WHO_AM_I checks for all I2C/SPI ICs
  55        CCSDS_Init() — Reset sequence counter
  60        Telemetry_Init() — Clear buffer pointers
  65        Watchdog_Init() — Clear all feed timestamps
  70        Error_Init() — Read last error from EEPROM
  80        Payload_Init(RADIATION_MONITOR) — Configure SBM-20
  90        Create message queues (telemetry, command, adcs)
 100        Create FreeRTOS tasks (6 tasks)
 105        system_state = NOMINAL
 110        osKernelStart() — Scheduler takes over
────────────────────────────────────────────────────────
Total boot: ~110 ms to scheduler start
```

## 11. Watchdog Architecture (Multi-Level)

### 11.1 Level Diagram

```
┌─────────────────────────────────────────────┐
│  Level 3: GROUND WATCHDOG                    │
│  If no telemetry received for 24 hours,     │
│  ground station sends hard reset TC          │
├─────────────────────────────────────────────┤
│  Level 2: RPi FLIGHT CONTROLLER WATCHDOG     │
│  health_monitor.py checks heartbeat from     │
│  STM32 (UART keepalive every 5 s).          │
│  On timeout: toggle STM32 nRST GPIO line     │
├─────────────────────────────────────────────┤
│  Level 1: SOFTWARE WATCHDOG (WatchdogTask)   │
│  Checks Watchdog_IsTaskAlive() for all 5     │
│  tasks. If any task last_feed > 10 s:       │
│  → Log ERR_WATCHDOG_TIMEOUT                  │
│  → Attempt task restart (osThreadTerminate)  │
│  → After 3 failures: OBC_SoftwareReset()    │
├─────────────────────────────────────────────┤
│  Level 0: HARDWARE WATCHDOG (IWDG)           │
│  STM32 Independent Watchdog, 10 s timeout   │
│  (LSI 32 kHz, prescaler /256, reload 1250)  │
│  Fed by WatchdogTask every 1000 ms.         │
│  If WatchdogTask itself hangs → HW reset     │
├─────────────────────────────────────────────┤
│  External: MAX6369 WATCHDOG IC               │
│  Independent IC on OBC board. 60 s timeout.  │
│  If STM32 does not toggle WDI pin → hard     │
│  power cycle via EPS reset line.             │
└─────────────────────────────────────────────┘
```

### 11.2 Watchdog Timing Summary

| Level | Timeout | Feed Source | Reset Action |
|-------|---------|-------------|--------------|
| L0 - IWDG | 10 s | WatchdogTask (1 Hz) | STM32 CPU reset |
| L0 - MAX6369 | 60 s | GPIO toggle from WatchdogTask | EPS power-cycle OBC |
| L1 - SW per-task | 10 s per task | Each task calls Watchdog_Feed() | Task restart, then OBC reset |
| L2 - RPi heartbeat | 30 s | STM32 UART keepalive | RPi toggles nRST GPIO |
| L3 - Ground | 24 h | Telemetry reception at GS | Ground sends TC reboot |

## 12. Data Flow

1. **Sensors** → SensorTask → telemetryQueue (16 deep) + adcsQueue (8 deep)
2. **telemetryQueue** → TelemetryTask → CCSDS packets → CommTask
3. **adcsQueue** → ADCSTask → magnetorquer/reaction wheel commands
4. **CommTask** → UART → UHF/S-band radio → Ground Station
5. **Ground Station** → Command → CommTask → commandQueue → Processing
6. **Flight Controller** (RPi) → UART → OBC for scheduling, image downlink, orbit prediction

## 13. References

- ECSS-E-ST-40C: Software Engineering (2009)
- ECSS-Q-ST-30C: Dependability (2009)
- CCSDS 133.0-B-2: Space Packet Protocol (2020)
- CubeSat Design Specification Rev. 14, Cal Poly SLO
- FreeRTOS V10.4.6 Reference Manual
