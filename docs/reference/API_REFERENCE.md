# UniSat API Reference

Complete API reference for all Python modules in the UniSat CubeSat platform.

---

## Flight Software Modules

All flight software modules inherit from `BaseModule` (defined in `flight-software/modules/__init__.py`), which provides lifecycle management (`initialize`, `start`, `stop`, `get_status`, `reset`), error tracking (`record_error`, `health_check`), and a per-module logger.

### FlightController

**Module:** `flight-software/flight_controller.py`

Main async mission controller. Manages subsystem loading, telemetry collection, command processing, and state machine transitions.

```python
class FlightController:
    def __init__(self, config_path: str = "mission_config.json") -> None
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `initialize` | `async initialize() -> None` | `None` | Load config, import enabled subsystem modules, set state to NOMINAL |
| `telemetry_loop` | `async telemetry_loop() -> None` | `None` | Collect health reports and build housekeeping packets at 1 Hz |
| `command_loop` | `async command_loop() -> None` | `None` | Dequeue and execute telecommands (5 s timeout per poll) |
| `health_monitor_loop` | `async health_monitor_loop() -> None` | `None` | Check CPU temp, disk, RAM every 5 s; log warnings on threshold breach |
| `scheduler_loop` | `async scheduler_loop() -> None` | `None` | Execute due scheduled tasks every 10 s |
| `run` | `async run() -> None` | `None` | Start all async loops via `asyncio.gather` |

**States** (`SatelliteState` enum): `STARTUP`, `NOMINAL`, `SAFE_MODE`, `LOW_POWER`

```python
# Example
import asyncio
from flight_controller import FlightController

controller = FlightController("mission_config.json")
asyncio.run(controller.run())
```

---

### TelemetryManager

**Module:** `flight-software/modules/telemetry_manager.py`

Builds and parses CCSDS-compatible telemetry packets. Manages per-APID sequence counters and mission elapsed time.

```python
class TelemetryManager(BaseModule):
    def __init__(self, config: dict | None = None) -> None
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get_mission_time` | `get_mission_time() -> float` | `float` | Seconds since mission epoch |
| `build_packet` | `build_packet(apid: APID, payload: bytes) -> bytes` | `bytes` | Build complete CCSDS packet (sync + primary header + secondary header + payload) |
| `parse_packet` | `parse_packet(raw: bytes) -> TelemetryFrame \| None` | `TelemetryFrame \| None` | Parse raw bytes into a `TelemetryFrame` dataclass |
| `pack_housekeeping` | `pack_housekeeping(battery_v, battery_soc, cpu_temp, solar_current_ma, uptime_s) -> bytes` | `bytes` | Pack 5 HK fields into 20 bytes (big-endian `>ffffI`) |
| `unpack_housekeeping` | `unpack_housekeeping(data: bytes) -> dict[str, float \| int]` | `dict` | Unpack 20-byte HK payload into named dictionary |

**APID Constants** (`APID` IntEnum): `HOUSEKEEPING=0x01`, `ADCS=0x02`, `EPS=0x03`, `CAMERA=0x04`, `PAYLOAD=0x05`, `GPS=0x06`, `THERMAL=0x07`, `COMMAND_ACK=0x10`, `EVENT=0x20`

```python
from modules.telemetry_manager import TelemetryManager, APID

tlm = TelemetryManager()
payload = tlm.pack_housekeeping(3.7, 0.85, 42.0, 350.0, 86400)
packet = tlm.build_packet(APID.HOUSEKEEPING, payload)
frame = tlm.parse_packet(packet)
```

---

### CommunicationManager

**Module:** `flight-software/modules/communication.py`

UART serial communication with HMAC-SHA256 command authentication and packet queuing.

```python
class CommunicationManager(BaseModule):
    def __init__(self, config: dict | None = None,
                 telemetry: TelemetryManager | None = None) -> None
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `sign_command` | `sign_command(command_bytes: bytes) -> bytes` | `bytes` | Compute 32-byte HMAC-SHA256 digest |
| `verify_command` | `verify_command(command_bytes: bytes, signature: bytes) -> bool` | `bool` | Verify command signature with constant-time comparison |
| `send_packet` | `async send_packet(packet: bytes) -> bool` | `bool` | Write packet to UART; queues on failure |
| `receive_packet` | `async receive_packet() -> bytes \| None` | `bytes \| None` | Read one CCSDS packet from serial (sync word search) |
| `send_authenticated_command` | `async send_authenticated_command(command_id: int, payload: bytes) -> bool` | `bool` | Build `[2B cmd_id][payload][32B HMAC]` and send |
| `flush_tx_queue` | `async flush_tx_queue() -> int` | `int` | Attempt to send all queued packets; returns count sent |
| `is_connected` | `is_connected() -> bool` | `bool` | True if link active and last RX within 120 s |
| `seconds_since_last_rx` | `seconds_since_last_rx() -> float` | `float` | Elapsed time since last successful reception |

**Config keys:** `port` (default `/dev/ttyS0`), `baud_rate` (default `9600`), `hmac_key` (default `unisat_default_key`)

---

### DataLogger

**Module:** `flight-software/modules/data_logger.py`

SQLite-backed telemetry storage with automatic database rotation and CSV export.

```python
class DataLogger(BaseModule):
    def __init__(self, config: dict | None = None) -> None
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `log_telemetry` | `async log_telemetry(timestamp, apid, sequence_count, mission_time, payload) -> bool` | `bool` | Insert one telemetry record |
| `query_by_time_range` | `async query_by_time_range(start_time, end_time, apid=None) -> list[dict]` | `list[dict]` | Query records within time window, optional APID filter |
| `export_csv` | `async export_csv(output_path, start_time=None, end_time=None) -> int` | `int` | Export records to CSV; returns record count |

**Config keys:** `db_dir` (default `./data`), `max_db_size_gb` (default `1.0`)

Database auto-rotates when it exceeds `max_db_size_gb`, archiving the old file with a Unix timestamp suffix.

---

### CameraHandler

**Module:** `flight-software/modules/camera_handler.py`

Image capture, storage management, and metadata logging. Generates synthetic images in simulation mode.

```python
class CameraHandler(BaseModule):
    def __init__(self, config: dict | None = None) -> None
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `capture_image` | `async capture_image(latitude=0.0, longitude=0.0, altitude_km=550.0, exposure_ms=10.0, orbit_number=0) -> ImageMetadata \| None` | `ImageMetadata \| None` | Capture image, save PNG, return metadata |
| `get_latest_metadata` | `get_latest_metadata(count=1) -> list[ImageMetadata]` | `list[ImageMetadata]` | Most recent capture metadata, newest first |
| `cleanup_oldest` | `async cleanup_oldest(keep_count=100) -> int` | `int` | Delete oldest images; returns deletion count |

**Config keys:** `storage_dir` (default `./images`), `max_storage_mb` (default `512`), `resolution_width` (default `3264`), `resolution_height` (default `2448`)

---

### ImageProcessor

**Module:** `flight-software/modules/image_processor.py`

SVD compression, JPEG conversion, GPS EXIF geotagging, and thumbnail generation.

```python
class ImageProcessor(BaseModule):
    def __init__(self, config: dict | None = None) -> None
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `compress_svd` | `compress_svd(image_path: str, rank: int \| None = None) -> tuple[np.ndarray, float]` | `(array, ratio)` | Per-channel SVD compression; returns reconstructed image and compression ratio |
| `compress_and_save` | `async compress_and_save(input_path: str, rank=None) -> str` | `str` | Compress with SVD and save as `*_svd.png`; returns output path |
| `convert_to_jpeg` | `async convert_to_jpeg(input_path: str, quality=None) -> str` | `str` | Convert to optimized JPEG |
| `geotag` | `async geotag(input_path: str, latitude: float, longitude: float, altitude_km: float) -> str` | `str` | Add GPS EXIF tags and save as `*_geo.jpg` |
| `generate_thumbnail` | `async generate_thumbnail(input_path: str, size=None) -> str` | `str` | Generate thumbnail using Lanczos resampling |

**Config keys:** `output_dir` (default `./processed`), `svd_rank` (default `50`), `jpeg_quality` (default `75`), `thumbnail_size` (default `256`)

---

### OrbitPredictor

**Module:** `flight-software/modules/orbit_predictor.py`

SGP4-based orbit propagation with ground station pass prediction and eclipse computation.

```python
class OrbitPredictor(BaseModule):
    def __init__(self, config: dict | None = None) -> None
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get_position` | `get_position(dt: datetime \| None = None) -> SatellitePosition \| None` | `SatellitePosition \| None` | ECI position + geodetic lat/lon/alt at given time |
| `predict_passes` | `predict_passes(hours=24.0, min_elevation=5.0, step_s=30.0) -> list[PassPrediction]` | `list[PassPrediction]` | Ground station pass windows with AOS/LOS/max elevation |
| `is_in_sunlight` | `is_in_sunlight(dt: datetime \| None = None) -> bool` | `bool` | Cylindrical shadow model eclipse check |

**Config keys:** `tle_line1`, `tle_line2`, `ground_station.latitude`, `ground_station.longitude`, `ground_station.altitude_m`

Falls back to a default 550 km SSO orbit if no TLE is provided.

---

### TaskScheduler

**Module:** `flight-software/modules/scheduler.py`

Priority-queue task scheduler with time-based, periodic, orbit-triggered, and event-triggered execution.

```python
class TaskScheduler(BaseModule):
    def __init__(self, config: dict | None = None) -> None
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `add_time_task` | `add_time_task(task_id, name, callback, trigger_time, priority=NORMAL)` | `None` | Schedule one-shot task at a Unix timestamp |
| `add_periodic_task` | `add_periodic_task(task_id, name, callback, interval_s, priority=NORMAL)` | `None` | Schedule repeating task |
| `add_orbit_task` | `add_orbit_task(task_id, name, callback, orbit_number, priority=NORMAL)` | `None` | Trigger at specific orbit number |
| `add_event_task` | `add_event_task(task_id, name, callback, event_name, priority=HIGH)` | `None` | Trigger on named event |
| `fire_event` | `async fire_event(event_name: str) -> int` | `int` | Fire event and execute all listeners; returns count |
| `tick` | `async tick() -> int` | `int` | Process all due tasks; returns executed count |
| `remove_task` | `remove_task(task_id: str) -> bool` | `bool` | Remove task by ID |

**Priority levels** (`TaskPriority`): `CRITICAL=0`, `HIGH=1`, `NORMAL=2`, `LOW=3`, `BACKGROUND=4`

---

### HealthMonitor

**Module:** `flight-software/modules/health_monitor.py`

System health monitoring with configurable warning/critical thresholds.

```python
class HealthMonitor(BaseModule):
    def __init__(self, config: dict | None = None) -> None
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `read_cpu_temperature` | `read_cpu_temperature() -> float` | `float` | Read CPU temp (Linux: `/sys/class/thermal`; other: simulated) |
| `read_ram_usage` | `read_ram_usage() -> float` | `float` | RAM usage percentage (Linux: `/proc/meminfo`; Windows: `GlobalMemoryStatusEx`) |
| `read_disk_usage` | `read_disk_usage() -> tuple[float, float]` | `(pct, free_mb)` | Disk usage for configured path |
| `check_health` | `async check_health() -> HealthReport` | `HealthReport` | Full health check with alert generation |
| `get_recent_alerts` | `get_recent_alerts(count=10) -> list[HealthAlert]` | `list[HealthAlert]` | Most recent alerts, newest first |

**Default thresholds:** `cpu_temp_c: (70, 85)`, `ram_used_pct: (80, 95)`, `disk_used_pct: (85, 95)` -- each pair is (warning, critical).

---

### PowerManager

**Module:** `flight-software/modules/power_manager.py`

Power budget tracking and automatic load shedding.

```python
class PowerManager:
    def __init__(self) -> None
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `update` | `update(solar_w: float, battery_soc: float) -> PowerBudget` | `PowerBudget` | Update budget, trigger load shedding if SOC < thresholds |
| `enable_subsystem` | `enable_subsystem(name: str) -> bool` | `bool` | Re-enable a subsystem after shedding |
| `disable_subsystem` | `disable_subsystem(name: str) -> bool` | `bool` | Manually disable (OBC cannot be disabled) |
| `get_consumption` | `get_consumption() -> float` | `float` | Total current consumption in watts |

**Thresholds:** `SOC_LOW_THRESHOLD = 30%` (shed camera, S-band), `SOC_CRITICAL_THRESHOLD = 15%` (keep only OBC + UHF COMM).

**Subsystem priorities** (`PowerPriority`): OBC(10) > COMM(9) > ADCS(7) > GNSS(6) > HEATER(5) > PAYLOAD(4) > CAMERA(3) > SBAND(2)

---

### SafeModeHandler

**Module:** `flight-software/modules/safe_mode.py`

Autonomous emergency operation when communication is lost or critical failures occur.

```python
class SafeModeHandler:
    def __init__(self) -> None
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `enter_safe_mode` | `enter_safe_mode(reason: SafeModeReason) -> None` | `None` | Disable non-essential subsystems, enter beacon mode |
| `exit_safe_mode` | `exit_safe_mode() -> bool` | `bool` | Re-enable all subsystems and return to nominal |
| `update_comm_timestamp` | `update_comm_timestamp() -> None` | `None` | Call on valid RX; triggers recovery if in COMM_LOSS safe mode |
| `check_comm_timeout` | `check_comm_timeout() -> bool` | `bool` | Enter safe mode if no comm for 24 hours |
| `should_send_beacon` | `should_send_beacon() -> bool` | `bool` | True every 30 s while in safe mode |
| `update` | `update() -> SafeModeState` | `SafeModeState` | Periodic tick: check timeouts, manage beacon timing |
| `is_active` | `is_active() -> bool` | `bool` | Whether safe mode is currently active |
| `get_disabled_subsystems` | `get_disabled_subsystems() -> list[str]` | `list[str]` | Subsystems disabled by safe mode |

**Reasons** (`SafeModeReason`): `COMM_LOSS`, `LOW_BATTERY`, `THERMAL_LIMIT`, `WATCHDOG`, `MANUAL`

---

### PayloadInterface

**Module:** `flight-software/modules/payload_interface.py`

Abstract base class for swappable payload modules. Includes `RadiationPayload` (SBM-20 Geiger counter) and `NullPayload` (test stub).

```python
class PayloadInterface(ABC):
    def __init__(self, payload_type: str, config_path: str | None = None) -> None
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `initialize` | `initialize() -> bool` | `bool` | (abstract) Initialize payload hardware |
| `collect_sample` | `collect_sample() -> PayloadSample \| None` | `PayloadSample \| None` | (abstract) Collect one measurement |
| `shutdown` | `shutdown() -> None` | `None` | (abstract) Power down payload |
| `start` | `start() -> bool` | `bool` | Activate payload (calls `initialize`) |
| `stop` | `stop() -> None` | `None` | Deactivate payload (calls `shutdown`) |
| `collect` | `collect() -> PayloadSample \| None` | `PayloadSample \| None` | Collect sample with sequence numbering and bookkeeping |
| `get_status` | `get_status() -> PayloadStatus` | `PayloadStatus` | Current status including sample count and health |

---

## Ground Station Utilities

### telemetry_decoder

**Module:** `ground-station/utils/telemetry_decoder.py`

Decodes telemetry payloads by APID into human-readable dictionaries.

| Function | Signature | Returns | Description |
|----------|-----------|---------|-------------|
| `decode_obc` | `decode_obc(data: bytes) -> dict` | `dict` | Decode OBC housekeeping (uptime, resets, cpu_temp, heap, state, errors) |
| `decode_eps` | `decode_eps(data: bytes) -> dict` | `dict` | Decode EPS (battery V/A/SOC, solar V/A/W, bus V, total W) |
| `decode_adcs` | `decode_adcs(data: bytes) -> dict` | `dict` | Decode ADCS (mode, quaternion, angular rates, pointing error) |
| `decode_gnss` | `decode_gnss(data: bytes) -> dict` | `dict` | Decode GNSS (lat, lon, alt, velocity, satellites, fix type) |
| `decode_beacon` | `decode_beacon(data: bytes) -> dict` | `dict` | Decode beacon (state, uptime, battery V, SOC) |
| `decode_packet` | `decode_packet(apid, timestamp, sequence, data) -> DecodedTelemetry` | `DecodedTelemetry` | Auto-dispatch to correct decoder by APID |

### ccsds_parser

**Module:** `ground-station/utils/ccsds_parser.py`

Low-level CCSDS space packet parser and builder with CRC-16/CCITT validation.

| Function | Signature | Returns | Description |
|----------|-----------|---------|-------------|
| `parse_packet` | `parse_packet(raw: bytes) -> CCSDSPacket \| None` | `CCSDSPacket \| None` | Parse raw bytes into `CCSDSPacket` with CRC validation |
| `build_packet` | `build_packet(apid, subsystem, data, packet_type=0) -> bytes` | `bytes` | Build CCSDS packet with primary/secondary headers and CRC |
| `crc16_ccitt` | `crc16_ccitt(data: bytes) -> int` | `int` | Calculate CRC-16/CCITT (poly 0x1021, init 0xFFFF) |

### orbit_visualizer

**Module:** `ground-station/utils/orbit_visualizer.py`

Simplified Keplerian ground track propagation and pass prediction for the dashboard.

| Function | Signature | Returns | Description |
|----------|-----------|---------|-------------|
| `propagate_ground_track` | `propagate_ground_track(n_points=200, hours=2.5) -> list[SatPosition]` | `list[SatPosition]` | Generate ground track lat/lon/alt points |
| `predict_passes` | `predict_passes(gs_lat, gs_lon, min_elevation=5.0, hours=48.0) -> list[dict]` | `list[dict]` | Predict passes with AOS/LOS/duration/max elevation |
| `is_in_eclipse` | `is_in_eclipse(lat, lon, timestamp) -> bool` | `bool` | Simplified solar elevation eclipse check |

### map_renderer

**Module:** `ground-station/utils/map_renderer.py`

Plotly figure builders for the ground station dashboard.

| Function | Signature | Returns | Description |
|----------|-----------|---------|-------------|
| `create_ground_track_figure` | `create_ground_track_figure(track_lats, track_lons, sat_lat, sat_lon, gs_lat=41.2995, gs_lon=69.2401, gs_name="Tashkent GS") -> go.Figure` | `go.Figure` | 3D orthographic globe with ground track, satellite marker, and GS marker |
| `create_2d_map` | `create_2d_map(track_lats, track_lons, markers=None) -> go.Figure` | `go.Figure` | 2D natural earth projection with track and optional markers |
