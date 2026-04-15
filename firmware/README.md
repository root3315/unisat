# UniSat Firmware

STM32F446RE firmware with FreeRTOS for the UniSat On-Board Computer.

## Architecture

```
FreeRTOS Kernel
├── SensorTask     (Priority 3) — Read all sensors at 1 Hz
├── TelemetryTask  (Priority 2) — Pack CCSDS packets from sensor queue
├── CommTask       (Priority 4) — UART TX/RX, beacon every 30s
├── ADCSTask       (Priority 3) — Run attitude control algorithms
├── WatchdogTask   (Priority 5) — Monitor tasks, feed IWDG
└── PayloadTask    (Priority 1) — Collect payload data at 0.2 Hz
```

## Building

```bash
# ARM cross-compilation
sudo apt install gcc-arm-none-eabi cmake
cd firmware && mkdir build && cd build
cmake .. && make -j$(nproc)

# Host build (for testing, no hardware)
cmake -DSIMULATION_MODE=ON .. && make
```

## Flashing

```bash
# Via ST-Link
st-flash write build/unisat_firmware.bin 0x08000000

# Or use the script
../scripts/flash_stm32.sh
```

## Directory Structure

| Directory | Description |
|-----------|-------------|
| `stm32/Core/Inc/` | All header files (13 modules) |
| `stm32/Core/Src/` | Implementation files |
| `stm32/ADCS/` | Attitude algorithms (quaternion, B-dot, pointing) |
| `stm32/EPS/` | Power system (MPPT, battery, PDU) |
| `stm32/Drivers/` | HAL drivers for 8 sensors |
| `tests/` | Unity framework unit tests |

## Adding a New Sensor

1. Create `Drivers/NewSensor/new_sensor.h` and `.c`
2. Add I2C/SPI init in the driver
3. Add read function to `sensors.c`
4. Add data fields to `SensorData_t` in `main.h`
5. Read it in `SensorTask` in `main.c`
6. Pack telemetry in `telemetry.c`

## Memory Map (STM32F446RE)

| Region | Start | Size | Usage |
|--------|-------|------|-------|
| Flash | 0x08000000 | 512 KB | Code + constants |
| SRAM | 0x20000000 | 128 KB | Stack + heap + FreeRTOS |
| Backup SRAM | 0x40024000 | 4 KB | Error log persistence |

## Debug

- SWD via PA13/PA14 (ST-Link V2)
- UART debug printf via USART2 (115200 baud)
- LED indicators on PC13 (heartbeat)
