"""Earth Observation Payload — Multispectral camera controller."""

import time
from dataclasses import dataclass


@dataclass
class ImageCapture:
    """Captured image metadata."""
    timestamp: float
    filename: str
    bands: list[str]
    resolution_mp: float
    gsd_m: float
    latitude: float
    longitude: float
    altitude_km: float
    size_bytes: int


class EarthObservationPayload:
    """Manages multispectral camera for Earth observation."""

    def __init__(self, resolution_mp: float = 8.0, gsd_m: float = 30.0) -> None:
        self.resolution_mp = resolution_mp
        self.gsd_m = gsd_m
        self.bands = ["R", "G", "B", "NIR"]
        self.captures: list[ImageCapture] = []
        self.active = False

    def initialize(self) -> bool:
        self.active = True
        return True

    def capture(self, lat: float = 0.0, lon: float = 0.0,
                alt_km: float = 550.0) -> ImageCapture:
        """Capture an image with all spectral bands."""
        seq = len(self.captures) + 1
        capture = ImageCapture(
            timestamp=time.time(),
            filename=f"IMG_{seq:04d}_{'_'.join(self.bands)}.raw",
            bands=self.bands, resolution_mp=self.resolution_mp,
            gsd_m=self.gsd_m, latitude=lat, longitude=lon,
            altitude_km=alt_km,
            size_bytes=int(self.resolution_mp * 1e6 * len(self.bands)),
        )
        self.captures.append(capture)
        return capture

    def shutdown(self) -> None:
        self.active = False
