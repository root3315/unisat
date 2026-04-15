"""Tests for NDVI analyzer."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from ndvi_analyzer import NDVIAnalyzer, generate_sample_scene


def test_ndvi_range():
    """NDVI should always be in [-1, 1]."""
    analyzer = NDVIAnalyzer()
    red = np.random.randint(0, 255, (50, 50), dtype=np.uint8)
    nir = np.random.randint(0, 255, (50, 50), dtype=np.uint8)
    ndvi = analyzer.compute_ndvi(red, nir)
    assert ndvi.min() >= -1.0
    assert ndvi.max() <= 1.0


def test_ndvi_vegetation():
    """High NIR + low Red should give high NDVI (vegetation)."""
    analyzer = NDVIAnalyzer()
    red = np.full((10, 10), 30, dtype=np.uint8)
    nir = np.full((10, 10), 200, dtype=np.uint8)
    ndvi = analyzer.compute_ndvi(red, nir)
    assert ndvi.mean() > 0.5


def test_ndvi_water():
    """Low NIR + moderate Red should give negative NDVI (water)."""
    analyzer = NDVIAnalyzer()
    red = np.full((10, 10), 50, dtype=np.uint8)
    nir = np.full((10, 10), 20, dtype=np.uint8)
    ndvi = analyzer.compute_ndvi(red, nir)
    assert ndvi.mean() < 0


def test_classification_classes():
    """Classification should produce valid class IDs (0-4)."""
    analyzer = NDVIAnalyzer()
    scene = generate_sample_scene(64, 64)
    result = analyzer.analyze(scene["red"], scene["nir"])
    assert set(np.unique(result.classification_map)).issubset({0, 1, 2, 3, 4})


def test_analysis_percentages_sum():
    """Vegetation + water + bare soil should not exceed 100%."""
    analyzer = NDVIAnalyzer()
    scene = generate_sample_scene()
    result = analyzer.analyze(scene["red"], scene["nir"])
    total = result.vegetation_pct + result.water_pct + result.bare_soil_pct
    assert total <= 100.0


def test_zero_division_safety():
    """NDVI should handle zero inputs without error."""
    analyzer = NDVIAnalyzer()
    red = np.zeros((10, 10), dtype=np.uint8)
    nir = np.zeros((10, 10), dtype=np.uint8)
    ndvi = analyzer.compute_ndvi(red, nir)
    assert not np.any(np.isnan(ndvi))
    assert not np.any(np.isinf(ndvi))
