"""Image Processor for UniSat CubeSat.

Provides SVD-based image compression, JPEG conversion, geotagging with GPS
coordinates in EXIF, and thumbnail generation for downlink optimization.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ExifTags

from modules import BaseModule, ModuleStatus


def _decimal_to_dms(decimal_degrees: float) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    """Convert decimal degrees to DMS (degrees, minutes, seconds) rational tuples.

    Args:
        decimal_degrees: Coordinate in decimal degrees.

    Returns:
        Tuple of three (numerator, denominator) pairs for degrees, minutes, seconds.
    """
    d = abs(decimal_degrees)
    degrees = int(d)
    minutes_float = (d - degrees) * 60
    minutes = int(minutes_float)
    seconds_float = (minutes_float - minutes) * 60
    seconds_x1000 = int(seconds_float * 1000)
    return (degrees, 1), (minutes, 1), (seconds_x1000, 1000)


class ImageProcessor(BaseModule):
    """Processes satellite imagery with compression, conversion, and geotagging.

    Attributes:
        output_dir: Directory for processed images.
        default_svd_rank: Default SVD rank k for compression.
        jpeg_quality: JPEG compression quality (1-95).
        thumbnail_size: Maximum thumbnail dimension in pixels.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the image processor.

        Args:
            config: Configuration with 'output_dir', 'svd_rank', 'jpeg_quality',
                    'thumbnail_size'.
        """
        super().__init__("image_processor", config)
        self.output_dir = Path(self.config.get("output_dir", "./processed"))
        self.default_svd_rank: int = self.config.get("svd_rank", 50)
        self.jpeg_quality: int = self.config.get("jpeg_quality", 75)
        self.thumbnail_size: int = self.config.get("thumbnail_size", 256)
        self._processed_count: int = 0

    async def initialize(self) -> bool:
        """Create output directory.

        Returns:
            True if initialization succeeded.
        """
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.status = ModuleStatus.READY
            self.logger.info("Image processor ready, SVD rank=%d", self.default_svd_rank)
            return True
        except OSError as exc:
            self.record_error(f"Init failed: {exc}")
            return False

    async def start(self) -> None:
        """Start the image processor."""
        self.status = ModuleStatus.RUNNING

    async def stop(self) -> None:
        """Stop the image processor."""
        self.status = ModuleStatus.STOPPED
        self.logger.info("Image processor stopped, %d images processed", self._processed_count)

    async def get_status(self) -> dict[str, Any]:
        """Return processor status.

        Returns:
            Dict with processed count and configuration.
        """
        return {
            "status": self.status.name,
            "processed_count": self._processed_count,
            "svd_rank": self.default_svd_rank,
            "jpeg_quality": self.jpeg_quality,
            "error_count": self._error_count,
        }

    def compress_svd(self, image_path: str, rank: int | None = None) -> tuple[np.ndarray, float]:
        """Compress an image using truncated SVD.

        Each color channel is decomposed independently. The rank-k
        approximation retains the k largest singular values.

        Args:
            image_path: Path to the input image.
            rank: SVD rank (number of singular values to keep).
                  Defaults to self.default_svd_rank.

        Returns:
            Tuple of (reconstructed image array uint8, compression ratio).
        """
        k = rank or self.default_svd_rank
        img = Image.open(image_path).convert("RGB")
        arr = np.array(img, dtype=np.float64)
        h, w, channels = arr.shape
        original_size = h * w * channels
        compressed_size = 0
        result = np.zeros_like(arr)
        for c in range(channels):
            channel = arr[:, :, c]
            u, s, vt = np.linalg.svd(channel, full_matrices=False)
            actual_k = min(k, len(s))
            u_k = u[:, :actual_k]
            s_k = s[:actual_k]
            vt_k = vt[:actual_k, :]
            result[:, :, c] = np.clip(u_k @ np.diag(s_k) @ vt_k, 0, 255)
            compressed_size += actual_k * (h + w + 1)
        ratio = original_size / max(compressed_size, 1)
        self.logger.info("SVD rank-%d: ratio=%.2fx (%dx%d)", k, ratio, w, h)
        return result.astype(np.uint8), ratio

    async def compress_and_save(self, input_path: str, rank: int | None = None) -> str:
        """Compress an image with SVD and save the result.

        Args:
            input_path: Path to the source image.
            rank: SVD rank override.

        Returns:
            Path to the compressed output image.
        """
        arr, ratio = self.compress_svd(input_path, rank)
        stem = Path(input_path).stem
        out_path = self.output_dir / f"{stem}_svd.png"
        Image.fromarray(arr, "RGB").save(str(out_path), "PNG")
        self._processed_count += 1
        self.logger.info("Saved compressed image: %s (ratio=%.2fx)", out_path.name, ratio)
        return str(out_path)

    async def convert_to_jpeg(self, input_path: str, quality: int | None = None) -> str:
        """Convert an image to JPEG format.

        Args:
            input_path: Path to the source image.
            quality: JPEG quality (1-95). Defaults to self.jpeg_quality.

        Returns:
            Path to the JPEG output.
        """
        q = quality or self.jpeg_quality
        img = Image.open(input_path).convert("RGB")
        stem = Path(input_path).stem
        out_path = self.output_dir / f"{stem}.jpg"
        img.save(str(out_path), "JPEG", quality=q, optimize=True)
        self._processed_count += 1
        self.logger.info("JPEG converted: %s (quality=%d)", out_path.name, q)
        return str(out_path)

    async def geotag(self, input_path: str, latitude: float, longitude: float,
                     altitude_km: float) -> str:
        """Add GPS EXIF tags to an image.

        Args:
            input_path: Path to the image file.
            latitude: GPS latitude in decimal degrees.
            longitude: GPS longitude in decimal degrees.
            altitude_km: Altitude in kilometers.

        Returns:
            Path to the geotagged output image.
        """
        img = Image.open(input_path)
        exif = img.getexif()
        ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
        lat_dms = _decimal_to_dms(latitude)
        lon_dms = _decimal_to_dms(longitude)
        ifd[1] = "N" if latitude >= 0 else "S"
        ifd[2] = lat_dms
        ifd[3] = "E" if longitude >= 0 else "W"
        ifd[4] = lon_dms
        ifd[5] = b"\x00"
        ifd[6] = (int(altitude_km * 1000), 1)
        stem = Path(input_path).stem
        out_path = self.output_dir / f"{stem}_geo.jpg"
        img.save(str(out_path), exif=exif.tobytes())
        self.logger.info("Geotagged: %s (%.4f, %.4f, %.1f km)", out_path.name,
                         latitude, longitude, altitude_km)
        return str(out_path)

    async def generate_thumbnail(self, input_path: str, size: int | None = None) -> str:
        """Generate a thumbnail of an image.

        Args:
            input_path: Path to the source image.
            size: Maximum dimension in pixels. Defaults to self.thumbnail_size.

        Returns:
            Path to the thumbnail image.
        """
        max_dim = size or self.thumbnail_size
        img = Image.open(input_path)
        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        stem = Path(input_path).stem
        out_path = self.output_dir / f"{stem}_thumb.jpg"
        img.convert("RGB").save(str(out_path), "JPEG", quality=60, optimize=True)
        self.logger.info("Thumbnail: %s (%dx%d)", out_path.name, img.width, img.height)
        return str(out_path)
