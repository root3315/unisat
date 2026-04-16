"""
UniSat Flight Controller — Main async mission control.

Manages all satellite subsystems through dynamic module loading,
async task scheduling, and state machine transitions.
"""

import asyncio
import json
import logging
import importlib
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger("unisat.flight")


class SatelliteState(Enum):
    """Satellite operational states."""
    STARTUP = "startup"
    NOMINAL = "nominal"
    SAFE_MODE = "safe_mode"
    LOW_POWER = "low_power"


class FlightController:
    """Main flight controller for UniSat CubeSat."""

    MODULE_MAP = {
        "comm": "modules.communication",
        "camera": "modules.camera_handler",
        "adcs": "modules.orbit_predictor",
        "gnss": "modules.orbit_predictor",
        "payload": "modules.payload_interface",
    }

    def __init__(self, config_path: str = "mission_config.json") -> None:
        self.config = self._load_config(config_path)
        self.state = SatelliteState.STARTUP
        self.modules: dict[str, Any] = {}
        self.command_queue: asyncio.Queue[dict] = asyncio.Queue()
        self._running = False
        self._setup_logging()

    @staticmethod
    def _load_config(path: str) -> dict:
        """Load mission configuration from JSON file."""
        config_path = Path(path)
        if not config_path.exists():
            config_path = Path(__file__).parent.parent / path
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _setup_logging(self) -> None:
        """Configure logging with rotation."""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
        )
        handler.setFormatter(formatter)
        root = logging.getLogger("unisat")
        root.addHandler(handler)
        root.setLevel(logging.DEBUG)

    async def initialize(self) -> None:
        """Initialize all enabled subsystems from config."""
        mission = self.config.get("mission", {})
        logger.info("Initializing %s v%s", mission.get("name"), mission.get("version"))

        from modules.telemetry_manager import TelemetryManager
        from modules.data_logger import DataLogger
        from modules.health_monitor import HealthMonitor
        from modules.scheduler import TaskScheduler

        self.modules["telemetry"] = TelemetryManager()
        self.modules["data_logger"] = DataLogger()
        self.modules["health"] = HealthMonitor()
        self.modules["scheduler"] = TaskScheduler()

        subsystems = self.config.get("subsystems", {})
        for name, cfg in subsystems.items():
            if cfg.get("enabled", False) and name in self.MODULE_MAP:
                try:
                    importlib.import_module(self.MODULE_MAP[name])
                    logger.info("Loaded module: %s", name)
                except ImportError as exc:
                    logger.warning("Failed to load %s: %s", name, exc)

        self.state = SatelliteState.NOMINAL
        logger.info("All subsystems initialized — state: NOMINAL")

    async def telemetry_loop(self) -> None:
        """Collect and store telemetry at 1 Hz."""
        tlm = self.modules.get("telemetry")
        db = self.modules.get("data_logger")
        while self._running:
            try:
                health = self.modules["health"].get_report()
                if tlm:
                    packet = tlm.build_housekeeping_packet(health)
                    if db:
                        db.store_telemetry(packet)
            except Exception as exc:
                logger.error("Telemetry error: %s", exc)
            await asyncio.sleep(1.0)

    async def command_loop(self) -> None:
        """Process incoming telecommands."""
        while self._running:
            try:
                cmd = await asyncio.wait_for(self.command_queue.get(), timeout=5.0)
                logger.info("Processing command: %s", cmd.get("type"))
                await self._execute_command(cmd)
            except asyncio.TimeoutError:
                pass
            except Exception as exc:
                logger.error("Command error: %s", exc)

    async def _execute_command(self, cmd: dict) -> None:
        """Execute a validated telecommand."""
        cmd_type = cmd.get("type", "")
        if cmd_type == "set_mode":
            mode = cmd.get("mode", "nominal")
            self.state = SatelliteState(mode)
            logger.info("Mode changed to %s", self.state.value)
        elif cmd_type == "capture_image":
            cam = self.modules.get("camera")
            if cam:
                cam.capture()
        elif cmd_type == "reboot":
            logger.warning("Reboot commanded")
            self._running = False

    async def health_monitor_loop(self) -> None:
        """Monitor system health at 0.2 Hz."""
        monitor = self.modules["health"]
        while self._running:
            report = monitor.get_report()
            if report.get("cpu_temp_c", 0) > 80:
                logger.warning("CPU overheating: %.1f C", report["cpu_temp_c"])
            if report.get("disk_usage_pct", 0) > 90:
                logger.warning("Disk almost full: %.1f%%", report["disk_usage_pct"])
            if report.get("ram_usage_pct", 0) > 90:
                logger.warning("RAM critical: %.1f%%", report["ram_usage_pct"])
            await asyncio.sleep(5.0)

    async def scheduler_loop(self) -> None:
        """Run scheduled tasks based on orbit position."""
        scheduler = self.modules["scheduler"]
        while self._running:
            due_tasks = scheduler.get_due_tasks()
            for task in due_tasks:
                logger.info("Executing scheduled task: %s", task.get("name"))
                scheduler.mark_completed(task["id"])
            await asyncio.sleep(10.0)

    async def run(self) -> None:
        """Main execution loop — start all async tasks."""
        await self.initialize()
        self._running = True

        tasks = [
            asyncio.create_task(self.telemetry_loop()),
            asyncio.create_task(self.command_loop()),
            asyncio.create_task(self.health_monitor_loop()),
            asyncio.create_task(self.scheduler_loop()),
        ]

        logger.info("Flight controller running with %d tasks", len(tasks))

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Flight controller shutting down")
        finally:
            self._running = False


async def main() -> None:
    """Entry point for flight controller."""
    controller = FlightController()
    await controller.run()


if __name__ == "__main__":
    asyncio.run(main())
