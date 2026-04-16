"""
UniSat Flight Controller — Multi-mission async mission control.

Manages all subsystems through dynamic module loading, configurable state
machine, event-driven architecture, and async task scheduling. Supports
CubeSat, CanSat, rocket, HAB, drone, and custom mission profiles.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from core.event_bus import EventBus, Event
from core.state_machine import StateMachine
from core.module_registry import ModuleRegistry
from core.mission_types import (
    MissionProfile,
    build_profile_from_config,
)

logger = logging.getLogger("unisat.flight")


class FlightController:
    """Main flight controller for UniSat multi-mission platform.

    Orchestrates the event bus, state machine, module registry, and async
    task loops. Configuration is loaded from mission_config.json and the
    appropriate mission profile is selected automatically.

    Attributes:
        config: Raw mission configuration dict.
        profile: Resolved mission profile with phases and module lists.
        event_bus: Shared event bus for inter-module communication.
        state_machine: Configurable phase-based state machine.
        registry: Dynamic module registry.
    """

    def __init__(self, config_path: str = "mission_config.json") -> None:
        self.config = self._load_config(config_path)
        self.profile: MissionProfile = build_profile_from_config(self.config)
        self.event_bus = EventBus()
        self.state_machine = StateMachine(self.profile)
        self.registry = ModuleRegistry(self.event_bus)
        self.command_queue: asyncio.Queue[dict] = asyncio.Queue()
        self._running = False
        self._setup_logging()

    @staticmethod
    def _load_config(path: str) -> dict:
        """Load mission configuration from JSON file."""
        config_path = Path(path)
        if not config_path.exists():
            config_path = Path(__file__).parent.parent / path
        if not config_path.exists():
            config_path = Path(__file__).parent / path
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
        if not root.handlers:
            root.addHandler(handler)
        root.setLevel(logging.DEBUG)

    async def initialize(self) -> None:
        """Initialize all subsystems based on mission profile and config."""
        mission = self.config.get("mission", {})
        logger.info(
            "Initializing %s v%s [%s / %s]",
            mission.get("name", "UniSat"),
            mission.get("version", "?"),
            self.profile.mission_type.value,
            self.profile.platform.value,
        )

        # Register event handlers for state transitions
        self.event_bus.subscribe("phase.*", self._on_phase_event)
        self.event_bus.subscribe("module.*", self._on_module_event)

        # Load modules from profile + config
        self.registry.load_modules_from_config(
            self.config,
            core_modules=self.profile.core_modules,
            optional_modules=self.profile.optional_modules,
        )

        # Initialize all loaded modules
        results = await self.registry.initialize_all()
        failed = [name for name, ok in results.items() if not ok]
        if failed:
            logger.warning("Modules failed to initialize: %s", failed)

        # Start all initialized modules
        await self.registry.start_all()

        # Emit startup event
        await self.event_bus.emit(
            "system.initialized",
            data={
                "mission_type": self.profile.mission_type.value,
                "platform": self.profile.platform.value,
                "modules_loaded": list(self.registry.modules.keys()),
                "initial_phase": self.state_machine.phase_name,
            },
            source="flight_controller",
        )

        logger.info(
            "Initialization complete — %d modules loaded, phase: %s",
            len(self.registry.modules),
            self.state_machine.phase_name,
        )

    async def _on_phase_event(self, event: Event) -> None:
        """Handle phase transition events."""
        logger.debug("Phase event: %s -> %s", event.name, event.data)

    async def _on_module_event(self, event: Event) -> None:
        """Handle module lifecycle events."""
        logger.debug("Module event: %s -> %s", event.name, event.data)

    # ------------------------------------------------------------------
    # Main loops
    # ------------------------------------------------------------------

    async def telemetry_loop(self) -> None:
        """Collect and store telemetry at the mission-configured rate."""
        interval = 1.0 / max(self.profile.default_telemetry_hz, 0.1)
        tlm = self.registry.get_module("telemetry")
        db = self.registry.get_module("data_logger")

        while self._running:
            try:
                # Build telemetry from all available sources
                health_mod = self.registry.get_module("health")
                if health_mod and tlm:
                    report = await health_mod.check_health()
                    packet = tlm.build_packet(
                        tlm.APID.HOUSEKEEPING if hasattr(tlm, "APID") else 0x01,
                        tlm.pack_housekeeping(
                            battery_v=3.7,
                            battery_soc=0.85,
                            cpu_temp=report.cpu_temp_c,
                            solar_current_ma=0.0,
                            uptime_s=int(report.uptime_s),
                        ),
                    )
                    if db:
                        await db.log_telemetry(
                            timestamp=report.timestamp,
                            apid=0x01,
                            sequence_count=0,
                            mission_time=report.uptime_s,
                            payload=packet,
                        )
            except Exception as exc:
                logger.error("Telemetry error: %s", exc)
            await asyncio.sleep(interval)

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

    async def state_machine_loop(self) -> None:
        """Monitor state machine timeouts and trigger auto-transitions."""
        while self._running:
            try:
                # Check for phase timeout
                auto_next = self.state_machine.check_timeout()
                if auto_next:
                    old = self.state_machine.phase_name
                    ok = await self.state_machine.transition_to(
                        auto_next, reason="timeout"
                    )
                    if ok:
                        await self.event_bus.emit(
                            self.state_machine.current.definition.entry_event,
                            data={"from": old, "to": auto_next, "reason": "timeout"},
                            source="state_machine",
                        )
            except Exception as exc:
                logger.error("State machine error: %s", exc)
            await asyncio.sleep(1.0)

    async def scheduler_loop(self) -> None:
        """Run scheduled tasks via the task scheduler."""
        scheduler = self.registry.get_module("scheduler")
        if not scheduler:
            logger.warning("No scheduler module loaded, skipping scheduler loop")
            return

        while self._running:
            try:
                executed = await scheduler.tick()
                if executed:
                    logger.debug("Scheduler executed %d tasks", executed)
            except Exception as exc:
                logger.error("Scheduler error: %s", exc)
            await asyncio.sleep(1.0)

    async def _execute_command(self, cmd: dict) -> None:
        """Execute a validated telecommand."""
        cmd_type = cmd.get("type", "")

        if cmd_type == "set_phase":
            target = cmd.get("phase", "")
            reason = cmd.get("reason", "telecommand")
            ok = await self.state_machine.transition_to(target, reason=reason)
            if ok:
                await self.event_bus.emit(
                    f"phase.{target}.enter",
                    data={"reason": reason},
                    source="command",
                )

        elif cmd_type == "set_mode":
            # Legacy compatibility
            mode = cmd.get("mode", "nominal")
            await self.state_machine.transition_to(mode, reason="legacy_command")

        elif cmd_type == "capture_image":
            cam = self.registry.get_module("camera")
            if cam and hasattr(cam, "capture"):
                cam.capture()

        elif cmd_type == "reboot":
            logger.warning("Reboot commanded")
            self._running = False

        elif cmd_type == "module_status":
            report = self.registry.get_status_report()
            logger.info("Module status: %s", report)

        else:
            # Publish as generic command event for modules to handle
            await self.event_bus.emit(
                f"command.{cmd_type}",
                data=cmd,
                source="command",
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def transition_phase(self, target: str, reason: str = "") -> bool:
        """Transition to a new mission phase.

        Args:
            target: Target phase name.
            reason: Human-readable reason.

        Returns:
            True if the transition succeeded.
        """
        old = self.state_machine.phase_name
        ok = await self.state_machine.transition_to(target, reason=reason)
        if ok:
            await self.event_bus.emit(
                self.state_machine.current.definition.entry_event,
                data={"from": old, "to": target, "reason": reason},
                source="flight_controller",
            )
        return ok

    def get_system_status(self) -> dict:
        """Return comprehensive system status for telemetry."""
        return {
            "mission_type": self.profile.mission_type.value,
            "platform": self.profile.platform.value,
            "phase": self.state_machine.get_phase_info(),
            "modules": self.registry.get_status_report(),
            "events": self.event_bus.get_stats(),
        }

    async def run(self) -> None:
        """Main execution loop — start all async tasks."""
        await self.initialize()
        self._running = True

        tasks = [
            asyncio.create_task(self.telemetry_loop()),
            asyncio.create_task(self.command_loop()),
            asyncio.create_task(self.state_machine_loop()),
            asyncio.create_task(self.scheduler_loop()),
        ]

        logger.info(
            "Flight controller running — %d tasks, phase: %s",
            len(tasks),
            self.state_machine.phase_name,
        )

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Flight controller shutting down")
        finally:
            self._running = False
            await self.registry.stop_all()
            await self.event_bus.emit(
                "system.shutdown",
                source="flight_controller",
            )

    async def shutdown(self) -> None:
        """Graceful shutdown."""
        self._running = False
        await self.registry.stop_all()


async def main() -> None:
    """Entry point for flight controller."""
    controller = FlightController()
    await controller.run()


if __name__ == "__main__":
    asyncio.run(main())
