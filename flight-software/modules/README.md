# Flight Software Modules

Quick reference for all modules in the UniSat flight software stack.

## Module Overview

| Module | File | Purpose | Key Dependencies |
|--------|------|---------|-----------------|
| **BaseModule** | `__init__.py` | Abstract base class with lifecycle, error tracking, health checks | -- |
| **TelemetryManager** | `telemetry_manager.py` | CCSDS packet build/parse, sequence counters, mission time | `struct` |
| **CommunicationManager** | `communication.py` | UART serial I/O, HMAC-SHA256 auth, TX/RX queues | `pyserial`, TelemetryManager |
| **DataLogger** | `data_logger.py` | SQLite telemetry storage, CSV export, DB rotation | `sqlite3`, `aiofiles` |
| **CameraHandler** | `camera_handler.py` | Image capture, storage management, metadata index | `Pillow`, `numpy` |
| **ImageProcessor** | `image_processor.py` | SVD compression, JPEG conversion, geotagging, thumbnails | `Pillow`, `numpy` |
| **OrbitPredictor** | `orbit_predictor.py` | SGP4 propagation, pass prediction, eclipse detection | `sgp4` |
| **TaskScheduler** | `scheduler.py` | Priority queue with time/periodic/orbit/event triggers | `heapq` |
| **HealthMonitor** | `health_monitor.py` | CPU temp, RAM, disk monitoring with threshold alerts | `shutil`, `pathlib` |
| **PowerManager** | `power_manager.py` | Power budget tracking, automatic load shedding | -- |
| **SafeModeHandler** | `safe_mode.py` | Emergency autonomous operation, beacon mode | -- |
| **PayloadInterface** | `payload_interface.py` | Abstract payload API + RadiationPayload, NullPayload | -- |

## Data Flow

```
Sensors / Hardware
       |
       v
+------------------+     +------------------+
| TelemetryManager | --> | DataLogger       |
| (build packets)  |     | (SQLite storage) |
+------------------+     +------------------+
       |
       v
+------------------+     +------------------+
| CommunicationMgr | <-- | SafeModeHandler  |
| (UART TX/RX)     |     | (beacon mode)    |
+------------------+     +------------------+
       |
       v
  Ground Station

+------------------+     +------------------+
| HealthMonitor    | --> | PowerManager     |
| (CPU/RAM/disk)   |     | (load shedding)  |
+------------------+     +------------------+

+------------------+     +------------------+
| CameraHandler    | --> | ImageProcessor   |
| (capture)        |     | (compress/geo)   |
+------------------+     +------------------+

+------------------+
| OrbitPredictor   | --> pass windows, eclipse state
+------------------+

+------------------+
| TaskScheduler    | --> orchestrates all timed/periodic/orbit tasks
+------------------+

+------------------+
| PayloadInterface | --> collect_sample() from any payload type
+------------------+
```

## BaseModule Lifecycle

Every module inherits from `BaseModule` and follows this lifecycle:

```
UNINITIALIZED -> INITIALIZING -> READY -> RUNNING -> STOPPED
                                   |
                                   +--> ERROR (on threshold exceeded)
                                          |
                                          +--> reset() -> READY
```

Key inherited methods:
- `initialize()` -- set up hardware/software resources
- `start()` -- begin main operation
- `stop()` -- gracefully shut down
- `get_status()` -- return health metrics dict
- `reset()` -- stop, clear errors, re-initialize
- `record_error(msg)` -- increment error counter; returns `True` if threshold exceeded
- `health_check()` -- returns `True` if status is READY or RUNNING

## How to Add a New Module

1. **Create the file** in `flight-software/modules/`, e.g. `my_sensor.py`.

2. **Inherit from BaseModule:**
   ```python
   from modules import BaseModule, ModuleStatus

   class MySensor(BaseModule):
       def __init__(self, config=None):
           super().__init__("my_sensor", config)

       async def initialize(self) -> bool:
           # Set up hardware, return True on success
           self.status = ModuleStatus.READY
           return True

       async def start(self) -> None:
           self.status = ModuleStatus.RUNNING

       async def stop(self) -> None:
           self.status = ModuleStatus.STOPPED

       async def get_status(self) -> dict:
           return {"status": self.status.name, "error_count": self._error_count}
   ```

3. **Register in FlightController.MODULE_MAP** (`flight_controller.py`):
   ```python
   MODULE_MAP = {
       ...
       "my_sensor": "modules.my_sensor",
   }
   ```

4. **Enable in mission_config.json:**
   ```json
   "subsystems": {
       "my_sensor": {"enabled": true}
   }
   ```

5. **Add a telemetry APID** (if the module produces telemetry) in `telemetry_manager.py`:
   ```python
   class APID(IntEnum):
       ...
       MY_SENSOR = 0x08
   ```

6. **Write tests** in `flight-software/tests/test_my_sensor.py`.

## Configuration Reference

All modules accept an optional `config` dictionary. The FlightController loads `mission_config.json` and passes relevant sections to each module.

| Config Key | Used By | Default | Description |
|------------|---------|---------|-------------|
| `mission_epoch_unix` | TelemetryManager | `time.time()` | Mission start epoch as Unix timestamp |
| `port` | CommunicationManager | `/dev/ttyS0` | Serial device path |
| `baud_rate` | CommunicationManager | `9600` | UART baud rate |
| `hmac_key` | CommunicationManager | `unisat_default_key` | HMAC-SHA256 shared secret |
| `db_dir` | DataLogger | `./data` | SQLite database directory |
| `max_db_size_gb` | DataLogger | `1.0` | Max DB size before rotation |
| `storage_dir` | CameraHandler | `./images` | Image storage directory |
| `max_storage_mb` | CameraHandler | `512` | Max image storage allocation |
| `resolution_width` | CameraHandler | `3264` | Capture width in pixels |
| `resolution_height` | CameraHandler | `2448` | Capture height in pixels |
| `output_dir` | ImageProcessor | `./processed` | Processed image output directory |
| `svd_rank` | ImageProcessor | `50` | Default SVD rank for compression |
| `jpeg_quality` | ImageProcessor | `75` | JPEG quality (1-95) |
| `thumbnail_size` | ImageProcessor | `256` | Max thumbnail dimension in pixels |
| `tle_line1` | OrbitPredictor | `""` | TLE line 1 (falls back to default SSO) |
| `tle_line2` | OrbitPredictor | `""` | TLE line 2 |
| `ground_station` | OrbitPredictor | Tashkent | Ground station lat/lon/alt |
| `thresholds` | HealthMonitor | See defaults | `{metric: [warn, crit]}` |
| `disk_path` | HealthMonitor | `/` | Path to monitor for disk usage |
| `max_errors` | BaseModule | `10` | Error count before module enters ERROR state |
