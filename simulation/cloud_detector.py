"""Cloud Detector — Simple cloud detection for Earth observation payload.

Implements a brightness + spectral index approach for identifying
cloud pixels in multispectral satellite imagery. Designed for the
UniSat CubeSat Earth observation mission with RGB + NIR bands.

The algorithm is inspired by the Fmask (Function of mask) approach:
    Zhu, Z. & Woodcock, C.E. (2012). Object-based cloud and cloud
    shadow detection in Landsat imagery. Remote Sensing of Environment,
    118, 83-94. https://doi.org/10.1016/j.rse.2011.10.028

Simplified for CubeSat use: combines brightness thresholding with
the Normalized Difference Snow Index (NDSI) to separate bright clouds
from bright snow/ice.
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class CloudResult:
    """Cloud detection result."""
    cloud_mask: np.ndarray       # Binary mask (True = cloud)
    cloud_percentage: float      # Fraction of image covered by clouds (0-100)
    num_cloud_pixels: int        # Total cloud pixel count
    num_total_pixels: int        # Total pixel count
    mean_brightness: float       # Mean scene brightness (0-1)
    ndsi_map: np.ndarray         # NDSI values for the scene


class CloudDetector:
    """Detect clouds in multispectral satellite imagery.

    Uses a two-stage approach:
    1. Brightness test: pixels brighter than a threshold in visible
       bands are cloud candidates.
    2. NDSI test: among bright candidates, filter out snow/ice using
       the Normalized Difference Snow Index. Snow has high NDSI
       (green reflects, SWIR absorbs), while clouds have low NDSI
       since they reflect both bands similarly. When no SWIR band
       is available, NIR is used as a proxy (less accurate but
       sufficient for initial screening).

    Args:
        brightness_threshold: Minimum brightness (0-1) for cloud
            candidates. Default 0.4 works for 8-bit imagery
            normalized to [0, 1].
        ndsi_threshold: Maximum NDSI for a pixel to be classified as
            cloud (not snow). Default 0.2.
    """

    def __init__(self, brightness_threshold: float = 0.4,
                 ndsi_threshold: float = 0.2) -> None:
        self.brightness_threshold = brightness_threshold
        self.ndsi_threshold = ndsi_threshold

    def _compute_brightness(self, red: np.ndarray, green: np.ndarray,
                            blue: np.ndarray) -> np.ndarray:
        """Compute per-pixel brightness as mean of visible bands."""
        return (red.astype(np.float64)
                + green.astype(np.float64)
                + blue.astype(np.float64)) / 3.0

    def _compute_ndsi(self, green: np.ndarray,
                      nir: np.ndarray) -> np.ndarray:
        """Compute Normalized Difference Snow Index.

        NDSI = (Green - NIR) / (Green + NIR)

        True NDSI uses SWIR instead of NIR, but for a 4-band CubeSat
        payload NIR serves as a reasonable proxy. Snow reflects green
        more than NIR, so NDSI > 0.4 typically indicates snow. Clouds
        reflect both similarly, yielding NDSI near 0.
        """
        g = green.astype(np.float64)
        n = nir.astype(np.float64)
        denom = g + n
        ndsi = np.where(denom > 0, (g - n) / denom, 0.0)
        return ndsi

    def detect(self, red: np.ndarray, green: np.ndarray,
               blue: np.ndarray, nir: np.ndarray) -> CloudResult:
        """Detect clouds in a multispectral image.

        All input arrays must have the same shape and contain values
        normalized to [0, 1] (float) or [0, 255] (uint8).

        Args:
            red: Red band array.
            green: Green band array.
            blue: Blue band array.
            nir: Near-infrared band array.

        Returns:
            CloudResult with binary mask and statistics.
        """
        # Normalize uint8 to float if needed
        bands = []
        for band in [red, green, blue, nir]:
            arr = np.asarray(band, dtype=np.float64)
            if arr.max() > 1.0:
                arr = arr / 255.0
            bands.append(arr)
        red_f, green_f, blue_f, nir_f = bands

        brightness = self._compute_brightness(red_f, green_f, blue_f)
        ndsi = self._compute_ndsi(green_f, nir_f)

        # Stage 1: brightness test
        bright_mask = brightness >= self.brightness_threshold

        # Stage 2: NDSI test — exclude snow (high NDSI)
        not_snow = ndsi <= self.ndsi_threshold

        cloud_mask = bright_mask & not_snow

        total = cloud_mask.size
        cloud_count = int(np.sum(cloud_mask))
        pct = 100.0 * cloud_count / total if total > 0 else 0.0

        return CloudResult(
            cloud_mask=cloud_mask,
            cloud_percentage=pct,
            num_cloud_pixels=cloud_count,
            num_total_pixels=total,
            mean_brightness=float(np.mean(brightness)),
            ndsi_map=ndsi,
        )


def generate_sample_scene(height: int = 100, width: int = 100,
                          seed: int = 42) -> dict[str, np.ndarray]:
    """Generate a synthetic multispectral scene for testing.

    Creates a scene with three regions:
    - Clear land (dark, low reflectance)
    - Cloud (bright in all bands, NDSI near 0)
    - Snow (bright in green, dimmer in NIR, high NDSI)

    Returns dict with 'red', 'green', 'blue', 'nir' arrays (float 0-1).
    """
    rng = np.random.default_rng(seed)

    red = np.full((height, width), 0.15)
    green = np.full((height, width), 0.18)
    blue = np.full((height, width), 0.12)
    nir = np.full((height, width), 0.35)

    # Cloud patch (top-left quadrant)
    red[:50, :50] = 0.75 + rng.normal(0, 0.03, (50, 50))
    green[:50, :50] = 0.78 + rng.normal(0, 0.03, (50, 50))
    blue[:50, :50] = 0.80 + rng.normal(0, 0.03, (50, 50))
    nir[:50, :50] = 0.72 + rng.normal(0, 0.03, (50, 50))

    # Snow patch (bottom-right quadrant)
    h_start = min(70, height)
    w_start = min(70, width)
    h_size = height - h_start
    w_size = width - w_start
    if h_size > 0 and w_size > 0:
        red[h_start:, w_start:] = 0.60 + rng.normal(0, 0.02, (h_size, w_size))
        green[h_start:, w_start:] = 0.85 + rng.normal(0, 0.02, (h_size, w_size))
        blue[h_start:, w_start:] = 0.55 + rng.normal(0, 0.02, (h_size, w_size))
        nir[h_start:, w_start:] = 0.20 + rng.normal(0, 0.02, (h_size, w_size))

    # Clip to valid range
    for arr in [red, green, blue, nir]:
        np.clip(arr, 0.0, 1.0, out=arr)

    return {"red": red, "green": green, "blue": blue, "nir": nir}


def main() -> None:
    """Demonstrate cloud detection on a synthetic scene."""
    print("=" * 60)
    print("UniSat Cloud Detector Demo")
    print("=" * 60)

    scene = generate_sample_scene()
    detector = CloudDetector()
    result = detector.detect(**scene)

    print(f"Scene size:       {result.num_total_pixels} pixels")
    print(f"Mean brightness:  {result.mean_brightness:.3f}")
    print(f"Cloud pixels:     {result.num_cloud_pixels}")
    print(f"Cloud coverage:   {result.cloud_percentage:.1f}%")
    print(f"NDSI range:       [{result.ndsi_map.min():.3f}, "
          f"{result.ndsi_map.max():.3f}]")

    # Expected: ~25% cloud (top-left 50x50 out of 100x100)
    # Snow patch should NOT be classified as cloud
    snow_region = result.cloud_mask[70:, 70:]
    snow_cloud_pct = 100.0 * np.sum(snow_region) / snow_region.size
    print(f"\nSnow region cloud false-positives: {snow_cloud_pct:.1f}%")
    print("(Should be near 0% — snow filtered by NDSI)")


if __name__ == "__main__":
    main()
