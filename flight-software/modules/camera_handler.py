"""Camera Handler for UniSat CubeSat.

Manages scheduled and on-demand image capture. In hardware mode this would
interface with the camera sensor; here it simulates capture using Pillow
for testing and development.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from modules import BaseModule, ModuleStatus


@dataclass
class ImageMetadata:
    """Metadata associated with a captured image.

    Attributes:
        filename: Name of the image file.
        timestamp: Unix timestamp of capture.
        latitude: GPS latitude in degrees (WGS84).
        longitude: GPS longitude in degrees (WGS84).
        altitude_km: Altitude above sea level in kilometers.
        exposure_ms: Exposure duration in milliseconds.
        width: Image width in pixels.
        height: Image height in pixels.
        size_bytes: File size in bytes.
        orbit_number: Orbit number at time of capture.
    """

    filename: str
    timestamp: float
    latitude: float
    longitude: float
    altitude_km: float
    exposure_ms: float
    width: int
    height: int
    size_bytes: int = 0
    orbit_number: int = 0


class CameraHandler(BaseModule):
    """Handles image capture, storage, and metadata management.

    Attributes:
        storage_dir: Directory for captured images.
        max_storage_mb: Maximum storage allocation in megabytes.
        resolution: Tuple of (width, height) in pixels.
        capture_count: Total number of images captured this session.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the camera handler.

        Args:
            config: Configuration with 'storage_dir', 'max_storage_mb',
                    'resolution_width', 'resolution_height'.
        """
        super().__init__("camera", config)
        self.storage_dir = Path(self.config.get("storage_dir", "./images"))
        self.max_storage_mb: int = self.config.get("max_storage_mb", 512)
        width = self.config.get("resolution_width", 3264)
        height = self.config.get("resolution_height", 2448)
        self.resolution: tuple[int, int] = (width, height)
        self.capture_count: int = 0
        self._metadata_log: list[ImageMetadata] = []

    async def initialize(self) -> bool:
        """Create storage directory and verify disk space.

        Returns:
            True if initialization succeeded.
        """
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            self.status = ModuleStatus.READY
            self.logger.info("Camera ready, resolution=%dx%d, storage=%s",
                             self.resolution[0], self.resolution[1], self.storage_dir)
            return True
        except OSError as exc:
            self.record_error(f"Storage init failed: {exc}")
            self.status = ModuleStatus.ERROR
            return False

    async def start(self) -> None:
        """Start camera handler."""
        self.status = ModuleStatus.RUNNING
        self.logger.info("Camera handler started")

    async def stop(self) -> None:
        """Stop camera handler and save metadata index."""
        await self._save_metadata_index()
        self.status = ModuleStatus.STOPPED
        self.logger.info("Camera stopped, %d images captured", self.capture_count)

    async def get_status(self) -> dict[str, Any]:
        """Return camera status and storage usage.

        Returns:
            Dict with capture count, storage usage, and resolution info.
        """
        used_mb = self._get_storage_used_mb()
        return {
            "status": self.status.name,
            "capture_count": self.capture_count,
            "storage_used_mb": round(used_mb, 2),
            "storage_max_mb": self.max_storage_mb,
            "storage_pct": round(used_mb / self.max_storage_mb * 100, 1) if self.max_storage_mb else 0.0,
            "resolution": f"{self.resolution[0]}x{self.resolution[1]}",
            "error_count": self._error_count,
        }

    async def capture_image(self, latitude: float = 0.0, longitude: float = 0.0,
                            altitude_km: float = 550.0, exposure_ms: float = 10.0,
                            orbit_number: int = 0) -> ImageMetadata | None:
        """Capture a simulated Earth-observation image.

        Generates a synthetic image with noise patterns representing terrain.
        In production this would trigger the real camera sensor.

        Args:
            latitude: Current satellite latitude.
            longitude: Current satellite longitude.
            altitude_km: Current altitude in km.
            exposure_ms: Exposure time in ms.
            orbit_number: Current orbit number.

        Returns:
            ImageMetadata on success, None on failure.
        """
        if self._get_storage_used_mb() >= self.max_storage_mb:
            self.record_error("Storage full, cannot capture")
            return None
        try:
            ts = time.time()
            filename = f"IMG_{int(ts)}_{self.capture_count:04d}.png"
            filepath = self.storage_dir / filename
            w, h = self.resolution
            rng = np.random.default_rng(seed=int(ts) & 0xFFFFFFFF)
            base = rng.integers(30, 180, size=(h, w, 3), dtype=np.uint8)
            gradient = np.linspace(0, 50, h, dtype=np.float32).reshape(h, 1, 1)
            combined = np.clip(base.astype(np.float32) + gradient, 0, 255).astype(np.uint8)
            img = Image.fromarray(combined, "RGB")
            img.save(str(filepath), "PNG")
            size_bytes = filepath.stat().st_size
            meta = ImageMetadata(
                filename=filename, timestamp=ts, latitude=latitude,
                longitude=longitude, altitude_km=altitude_km,
                exposure_ms=exposure_ms, width=w, height=h,
                size_bytes=size_bytes, orbit_number=orbit_number,
            )
            self._metadata_log.append(meta)
            self.capture_count += 1
            self.logger.info("Captured %s (%.1f KB)", filename, size_bytes / 1024)
            return meta
        except Exception as exc:
            self.record_error(f"Capture failed: {exc}")
            return None

    def get_latest_metadata(self, count: int = 1) -> list[ImageMetadata]:
        """Return metadata for the most recent captures.

        Args:
            count: Number of recent entries to return.

        Returns:
            List of ImageMetadata, newest first.
        """
        return list(reversed(self._metadata_log[-count:]))

    def _get_storage_used_mb(self) -> float:
        """Calculate total storage used by captured images.

        Returns:
            Storage used in megabytes.
        """
        if not self.storage_dir.exists():
            return 0.0
        total = sum(f.stat().st_size for f in self.storage_dir.iterdir() if f.is_file())
        return total / (1024 * 1024)

    async def _save_metadata_index(self) -> None:
        """Save the metadata index to a JSON file."""
        index_path = self.storage_dir / "index.json"
        entries = [asdict(m) for m in self._metadata_log]
        index_path.write_text(json.dumps(entries, indent=2))
        self.logger.info("Saved metadata index with %d entries", len(entries))

    async def cleanup_oldest(self, keep_count: int = 100) -> int:
        """Delete oldest images to free storage, keeping the newest.

        Args:
            keep_count: Number of newest images to keep.

        Returns:
            Number of images deleted.
        """
        if len(self._metadata_log) <= keep_count:
            return 0
        to_delete = self._metadata_log[:-keep_count]
        deleted = 0
        for meta in to_delete:
            filepath = self.storage_dir / meta.filename
            if filepath.exists():
                filepath.unlink()
                deleted += 1
        self._metadata_log = self._metadata_log[-keep_count:]
        self.logger.info("Cleaned up %d images, keeping %d", deleted, keep_count)
        return deleted
