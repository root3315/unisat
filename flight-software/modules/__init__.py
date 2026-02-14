"""UniSat flight software modules.

Provides the base module interface and exports for all subsystem modules.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Any


class ModuleStatus(Enum):
    """Lifecycle status of a flight software module."""

    UNINITIALIZED = auto()
    INITIALIZING = auto()
    READY = auto()
    RUNNING = auto()
    PAUSED = auto()
    ERROR = auto()
    STOPPED = auto()


class BaseModule(ABC):
    """Abstract base class for all flight software modules.

    Every subsystem module must inherit from this class and implement
    the initialize, start, stop, and get_status methods.

    Attributes:
        name: Human-readable module name.
        config: Configuration dictionary loaded from mission_config.json.
        status: Current lifecycle status.
        logger: Module-scoped logger instance.
    """

    def __init__(self, name: str, config: dict[str, Any] | None = None) -> None:
        """Initialize base module.

        Args:
            name: Human-readable module name.
            config: Optional configuration dictionary.
        """
        self.name = name
        self.config = config or {}
        self.status = ModuleStatus.UNINITIALIZED
        self.logger = logging.getLogger(f"unisat.{name}")
        self._error_count: int = 0
        self._max_errors: int = self.config.get("max_errors", 10)

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the module hardware and software resources.

        Returns:
            True if initialization succeeded, False otherwise.
        """
        ...

    @abstractmethod
    async def start(self) -> None:
        """Start the module's main operation loop."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Gracefully stop the module and release resources."""
        ...

    @abstractmethod
    async def get_status(self) -> dict[str, Any]:
        """Return current module status and health metrics.

        Returns:
            Dictionary with at least 'status' and 'error_count' keys.
        """
        ...

    async def reset(self) -> bool:
        """Reset the module after an error.

        Returns:
            True if the reset succeeded and module is ready again.
        """
        self.logger.info("Resetting module %s", self.name)
        await self.stop()
        self._error_count = 0
        self.status = ModuleStatus.UNINITIALIZED
        success = await self.initialize()
        if success:
            self.status = ModuleStatus.READY
        return success

    def record_error(self, message: str) -> bool:
        """Record an error and check if threshold is exceeded.

        Args:
            message: Description of the error.

        Returns:
            True if the module should be disabled (too many errors).
        """
        self._error_count += 1
        self.logger.error("[%s] Error #%d: %s", self.name, self._error_count, message)
        if self._error_count >= self._max_errors:
            self.status = ModuleStatus.ERROR
            self.logger.critical("Module %s exceeded error threshold (%d)", self.name, self._max_errors)
            return True
        return False

    async def health_check(self) -> bool:
        """Run a quick health check.

        Returns:
            True if the module appears healthy.
        """
        return self.status in (ModuleStatus.READY, ModuleStatus.RUNNING)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} status={self.status.name}>"


__all__ = [
    "BaseModule",
    "ModuleStatus",
]
