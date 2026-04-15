"""NDVI Analyzer — Normalized Difference Vegetation Index for NASA Space Apps.

Implements vegetation analysis from multispectral satellite imagery
using Red and NIR bands captured by the Earth observation payload.
"""

import numpy as np
from dataclasses import dataclass
from typing import Any


@dataclass
class NDVIResult:
    """NDVI analysis result."""
    ndvi_map: np.ndarray
    mean_ndvi: float
    min_ndvi: float
    max_ndvi: float
    vegetation_pct: float  # % pixels with NDVI > 0.3
    water_pct: float  # % pixels with NDVI < -0.1
    bare_soil_pct: float  # % pixels with 0 < NDVI < 0.2
    classification_map: np.ndarray
    histogram: dict[str, Any]


class NDVIAnalyzer:
    """Compute and classify NDVI from multispectral imagery."""

    # Classification thresholds
    WATER_THRESHOLD = -0.1
    BARE_SOIL_LOW = 0.0
    BARE_SOIL_HIGH = 0.2
    SPARSE_VEG_HIGH = 0.4
    DENSE_VEG_THRESHOLD = 0.6

    CLASSES = {
        0: "Water",
        1: "Bare Soil / Urban",
        2: "Sparse Vegetation",
        3: "Moderate Vegetation",
        4: "Dense Vegetation",
    }

    def compute_ndvi(self, red: np.ndarray, nir: np.ndarray) -> np.ndarray:
        """Compute NDVI from Red and NIR bands.

        NDVI = (NIR - Red) / (NIR + Red)
        Range: [-1, 1] where higher values indicate more vegetation.
        """
        red = red.astype(np.float64)
        nir = nir.astype(np.float64)

        denominator = nir + red
        # Avoid division by zero
        ndvi = np.where(
            denominator > 0,
            (nir - red) / denominator,
            0.0
        )
        return np.clip(ndvi, -1.0, 1.0)

    def classify(self, ndvi: np.ndarray) -> np.ndarray:
        """Classify NDVI into land cover categories."""
        classes = np.zeros_like(ndvi, dtype=np.uint8)
        classes[ndvi < self.WATER_THRESHOLD] = 0  # Water
        classes[(ndvi >= self.BARE_SOIL_LOW) & (ndvi < self.BARE_SOIL_HIGH)] = 1
        classes[(ndvi >= self.BARE_SOIL_HIGH) & (ndvi < self.SPARSE_VEG_HIGH)] = 2
        classes[(ndvi >= self.SPARSE_VEG_HIGH) & (ndvi < self.DENSE_VEG_THRESHOLD)] = 3
        classes[ndvi >= self.DENSE_VEG_THRESHOLD] = 4
        return classes

    def analyze(self, red: np.ndarray, nir: np.ndarray) -> NDVIResult:
        """Perform complete NDVI analysis."""
        ndvi = self.compute_ndvi(red, nir)
        classification = self.classify(ndvi)
        total_pixels = ndvi.size

        # Histogram
        bins = np.linspace(-1, 1, 21)
        hist_counts, hist_edges = np.histogram(ndvi, bins=bins)

        return NDVIResult(
            ndvi_map=ndvi,
            mean_ndvi=float(np.mean(ndvi)),
            min_ndvi=float(np.min(ndvi)),
            max_ndvi=float(np.max(ndvi)),
            vegetation_pct=float(np.sum(ndvi > 0.3) / total_pixels * 100),
            water_pct=float(np.sum(ndvi < self.WATER_THRESHOLD) / total_pixels * 100),
            bare_soil_pct=float(np.sum(
                (ndvi >= self.BARE_SOIL_LOW) & (ndvi < self.BARE_SOIL_HIGH)
            ) / total_pixels * 100),
            classification_map=classification,
            histogram={"counts": hist_counts.tolist(),
                       "edges": hist_edges.tolist()},
        )

    def compute_evi(self, red: np.ndarray, nir: np.ndarray,
                    blue: np.ndarray) -> np.ndarray:
        """Compute Enhanced Vegetation Index (EVI).

        EVI = G * (NIR - Red) / (NIR + C1*Red - C2*Blue + L)
        More sensitive in high-biomass areas than NDVI.
        """
        red = red.astype(np.float64)
        nir = nir.astype(np.float64)
        blue = blue.astype(np.float64)

        g, c1, c2, l_coeff = 2.5, 6.0, 7.5, 1.0
        denominator = nir + c1 * red - c2 * blue + l_coeff
        evi = np.where(
            denominator > 0,
            g * (nir - red) / denominator,
            0.0
        )
        return np.clip(evi, -1.0, 1.0)


def generate_sample_scene(height: int = 256, width: int = 256) -> dict:
    """Generate a synthetic multispectral scene for testing."""
    np.random.seed(42)

    # Create terrain types
    terrain = np.zeros((height, width))
    # Water (bottom-left)
    terrain[:height//3, :width//3] = 0
    # Forest (center)
    terrain[height//4:3*height//4, width//4:3*width//4] = 1
    # Urban (top-right)
    terrain[2*height//3:, 2*width//3:] = 2
    # Agricultural (edges)
    terrain[terrain == 0] = 3  # Fill remaining

    # Generate spectral bands based on terrain
    red = np.zeros((height, width), dtype=np.float64)
    nir = np.zeros((height, width), dtype=np.float64)
    blue = np.zeros((height, width), dtype=np.float64)
    green = np.zeros((height, width), dtype=np.float64)

    # Water: high blue, low NIR
    mask = terrain == 0
    red[mask] = 30 + np.random.normal(0, 5, mask.sum())
    nir[mask] = 20 + np.random.normal(0, 3, mask.sum())
    blue[mask] = 80 + np.random.normal(0, 5, mask.sum())

    # Forest: low red, high NIR
    mask = terrain == 1
    red[mask] = 40 + np.random.normal(0, 5, mask.sum())
    nir[mask] = 200 + np.random.normal(0, 15, mask.sum())
    green[mask] = 80 + np.random.normal(0, 8, mask.sum())

    # Urban: moderate all bands
    mask = terrain == 2
    red[mask] = 120 + np.random.normal(0, 10, mask.sum())
    nir[mask] = 130 + np.random.normal(0, 10, mask.sum())
    blue[mask] = 100 + np.random.normal(0, 8, mask.sum())

    # Agriculture: moderate red, high NIR
    mask = terrain == 3
    red[mask] = 60 + np.random.normal(0, 8, mask.sum())
    nir[mask] = 160 + np.random.normal(0, 12, mask.sum())
    green[mask] = 70 + np.random.normal(0, 6, mask.sum())

    return {
        "red": np.clip(red, 0, 255).astype(np.uint8),
        "green": np.clip(green, 0, 255).astype(np.uint8),
        "blue": np.clip(blue, 0, 255).astype(np.uint8),
        "nir": np.clip(nir, 0, 255).astype(np.uint8),
        "terrain_truth": terrain,
    }


if __name__ == "__main__":
    scene = generate_sample_scene()
    analyzer = NDVIAnalyzer()
    result = analyzer.analyze(scene["red"], scene["nir"])

    print(f"NDVI Analysis:")
    print(f"  Mean NDVI: {result.mean_ndvi:.3f}")
    print(f"  Range: [{result.min_ndvi:.3f}, {result.max_ndvi:.3f}]")
    print(f"  Vegetation: {result.vegetation_pct:.1f}%")
    print(f"  Water: {result.water_pct:.1f}%")
    print(f"  Bare soil: {result.bare_soil_pct:.1f}%")
