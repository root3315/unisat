"""Module Registry — Dynamic module loading with config injection.

Replaces the old hardcoded MODULE_MAP. Discovers and loads modules by name,
passes per-module config from mission_config.json, and manages lifecycle
(initialize -> start -> stop) for all registered modules.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any

from modules import BaseModule, ModuleStatus
from core.event_bus import EventBus

logger = logging.getLogger("unisat.registry")

# Maps short module names to their importable module paths and class names.
# New modules just add an entry here — no other code changes needed.
DEFAULT_MODULE_MAP: dict[str, tuple[str, str]] = {
    # Core modules
    "telemetry": ("modules.telemetry_manager", "TelemetryManager"),
    "data_logger": ("modules.data_logger", "DataLogger"),
    "health": ("modules.health_monitor", "HealthMonitor"),
    "scheduler": ("modules.scheduler", "TaskScheduler"),

    # Communication
    "comm": ("modules.communication", "CommunicationManager"),

    # Navigation & ADCS
    "orbit_predictor": ("modules.orbit_predictor", "OrbitPredictor"),

    # Imaging
    "camera": ("modules.camera_handler", "CameraHandler"),
    "image_processor": ("modules.image_processor", "ImageProcessor"),

    # Power & Safety
    "power_manager": ("modules.power_manager", "PowerManager"),
    "safe_mode": ("modules.safe_mode", "SafeModeHandler"),

    # Payload
    "payload": ("modules.payload_interface", "RadiationPayload"),

    # --- New modules for multi-mission support ---
    "imu": ("modules.imu_sensor", "IMUSensor"),
    "barometer": ("modules.barometric_altimeter", "BarometricAltimeter"),
    "descent_controller": ("modules.descent_controller", "DescentController"),
    "gnss": ("modules.gnss_receiver", "GNSSReceiver"),
}


class ModuleRegistry:
    """Manages dynamic loading, configuration, and lifecycle of flight modules.

    Attributes:
        modules: Dict of loaded module instances by name.
        event_bus: Shared event bus for inter-module communication.
    """

    def __init__(self, event_bus: EventBus,
                 module_map: dict[str, tuple[str, str]] | None = None) -> None:
        """Initialize the registry.

        Args:
            event_bus: The shared event bus instance.
            module_map: Optional override for the module mapping.
        """
        self.event_bus = event_bus
        self._module_map: dict[str, tuple[str, str]] = dict(
            module_map or DEFAULT_MODULE_MAP
        )
        self.modules: dict[str, BaseModule] = {}
        self._load_errors: dict[str, str] = {}

    def register_module(self, name: str, module_path: str, class_name: str) -> None:
        """Register a new module type.

        Args:
            name: Short name used in config (e.g. "imu").
            module_path: Python module path (e.g. "modules.imu_sensor").
            class_name: Class name to instantiate.
        """
        self._module_map[name] = (module_path, class_name)
        logger.info("Registered module type: %s -> %s.%s", name, module_path, class_name)

    def load_module(self, name: str, config: dict[str, Any] | None = None) -> BaseModule | None:
        """Load and instantiate a single module.

        Args:
            name: Module name (must be in the module map).
            config: Per-module configuration dict.

        Returns:
            The instantiated module, or None on failure.
        """
        if name in self.modules:
            logger.debug("Module '%s' already loaded", name)
            return self.modules[name]

        mapping = self._module_map.get(name)
        if not mapping:
            self._load_errors[name] = f"Unknown module: {name}"
            logger.warning("No mapping for module: %s", name)
            return None

        module_path, class_name = mapping
        try:
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            instance: BaseModule = cls(config=config or {})
            self.modules[name] = instance
            logger.info("Loaded module: %s (%s.%s)", name, module_path, class_name)
            return instance
        except ImportError as exc:
            self._load_errors[name] = f"Import error: {exc}"
            logger.warning("Failed to import %s: %s", module_path, exc)
        except AttributeError as exc:
            self._load_errors[name] = f"Class not found: {exc}"
            logger.warning("Class %s not found in %s: %s", class_name, module_path, exc)
        except TypeError:
            # Module constructor doesn't accept config — try without
            try:
                mod = importlib.import_module(module_path)
                cls = getattr(mod, class_name)
                instance_noconfig: BaseModule = cls()
                self.modules[name] = instance_noconfig
                logger.info("Loaded module (no-config): %s", name)
                return instance_noconfig
            except Exception as inner_exc:
                self._load_errors[name] = f"Instantiation error: {inner_exc}"
                logger.warning("Failed to instantiate %s: %s", name, inner_exc)
        except Exception as exc:
            self._load_errors[name] = f"Unexpected error: {exc}"
            logger.error("Unexpected error loading %s: %s", name, exc)

        return None

    def load_modules_from_config(self, config: dict[str, Any],
                                 core_modules: list[str],
                                 optional_modules: list[str]) -> dict[str, BaseModule]:
        """Load all modules specified by the mission profile and config.

        Core modules are always loaded. Optional modules are loaded only
        if their subsystem is enabled in ``config["subsystems"]``.

        Args:
            config: Full mission_config.json content.
            core_modules: Module names to always load.
            optional_modules: Module names to load if enabled.

        Returns:
            Dict of successfully loaded modules.
        """
        subsystems_cfg = config.get("subsystems", {})

        # Load core modules (always)
        for name in core_modules:
            module_cfg = subsystems_cfg.get(name, {})
            self.load_module(name, module_cfg)

        # Load optional modules (only if enabled)
        for name in optional_modules:
            sub_cfg = subsystems_cfg.get(name, {})
            if sub_cfg.get("enabled", False):
                self.load_module(name, sub_cfg)

        logger.info(
            "Module loading complete: %d loaded, %d failed",
            len(self.modules), len(self._load_errors),
        )
        return self.modules

    async def initialize_all(self) -> dict[str, bool]:
        """Initialize all loaded modules.

        Returns:
            Dict mapping module name to initialization success.
        """
        results: dict[str, bool] = {}
        for name, module in self.modules.items():
            try:
                ok = await module.initialize()
                results[name] = ok
                if ok:
                    logger.info("Initialized: %s", name)
                else:
                    logger.warning("Init returned False: %s", name)
            except Exception as exc:
                results[name] = False
                logger.error("Init failed for %s: %s", name, exc)
        return results

    async def start_all(self) -> None:
        """Start all initialized modules."""
        for name, module in self.modules.items():
            if module.status == ModuleStatus.READY:
                try:
                    await module.start()
                except Exception as exc:
                    logger.error("Start failed for %s: %s", name, exc)

    async def stop_all(self) -> None:
        """Stop all running modules."""
        for name, module in self.modules.items():
            if module.status in (ModuleStatus.RUNNING, ModuleStatus.READY):
                try:
                    await module.stop()
                except Exception as exc:
                    logger.error("Stop failed for %s: %s", name, exc)

    def get_module(self, name: str) -> BaseModule | None:
        """Get a loaded module by name."""
        return self.modules.get(name)

    def get_status_report(self) -> dict[str, Any]:
        """Return status of all modules and load errors."""
        return {
            "loaded": {
                name: {
                    "status": mod.status.name,
                    "type": type(mod).__name__,
                }
                for name, mod in self.modules.items()
            },
            "errors": dict(self._load_errors),
        }
