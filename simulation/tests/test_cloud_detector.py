"""Tests for the cloud detector module."""

import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from cloud_detector import CloudDetector, generate_sample_scene


class TestBrightPixelDetection:
    """Test that brightness thresholding works correctly."""

    def test_bright_pixels_detected_as_cloud(self):
        """Uniformly bright pixels (cloud-like) should be classified as cloud."""
        detector = CloudDetector(brightness_threshold=0.4, ndsi_threshold=0.2)
        bright = np.full((10, 10), 0.8)
        result = detector.detect(bright, bright, bright, bright)
        assert result.cloud_percentage > 95.0

    def test_dark_pixels_not_detected_as_cloud(self):
        """Dark pixels (clear land/ocean) should not be clouds."""
        detector = CloudDetector(brightness_threshold=0.4, ndsi_threshold=0.2)
        dark = np.full((10, 10), 0.1)
        result = detector.detect(dark, dark, dark, dark)
        assert result.cloud_percentage < 5.0

    def test_mixed_scene_partial_coverage(self):
        """Half bright, half dark scene should yield ~50% cloud."""
        detector = CloudDetector(brightness_threshold=0.4, ndsi_threshold=0.2)
        top = np.full((5, 10), 0.8)   # cloud
        bot = np.full((5, 10), 0.1)   # clear
        red = np.vstack([top, bot])
        result = detector.detect(red, red, red, red)
        assert 40.0 < result.cloud_percentage < 60.0


class TestNDSIFiltering:
    """Test that snow pixels are filtered out by NDSI."""

    def test_snow_not_classified_as_cloud(self):
        """High-NDSI (snow-like) bright pixels should be filtered out."""
        detector = CloudDetector(brightness_threshold=0.3, ndsi_threshold=0.2)
        # Snow: bright green, dimmer NIR => high NDSI
        green = np.full((10, 10), 0.85)
        nir = np.full((10, 10), 0.20)
        red = np.full((10, 10), 0.60)
        blue = np.full((10, 10), 0.55)
        result = detector.detect(red, green, blue, nir)
        # NDSI ~ (0.85 - 0.20)/(0.85 + 0.20) ~ 0.62 > 0.2 threshold
        assert result.cloud_percentage < 10.0


class TestCloudPercentage:
    """Test cloud coverage percentage calculation."""

    def test_all_cloud_gives_100_percent(self):
        detector = CloudDetector(brightness_threshold=0.3)
        bright = np.full((20, 20), 0.9)
        result = detector.detect(bright, bright, bright, bright)
        assert result.cloud_percentage > 99.0

    def test_no_cloud_gives_0_percent(self):
        detector = CloudDetector(brightness_threshold=0.4)
        dark = np.full((20, 20), 0.05)
        result = detector.detect(dark, dark, dark, dark)
        assert result.cloud_percentage < 1.0

    def test_pixel_counts_consistent(self):
        detector = CloudDetector()
        scene = generate_sample_scene(50, 50)
        result = detector.detect(**scene)
        assert result.num_total_pixels == 50 * 50
        expected_pct = 100.0 * result.num_cloud_pixels / result.num_total_pixels
        assert abs(result.cloud_percentage - expected_pct) < 0.01


class TestSampleScene:
    """Test with the synthetic sample scene generator."""

    def test_sample_scene_has_clouds(self):
        """Sample scene should detect the cloud patch."""
        scene = generate_sample_scene(100, 100)
        detector = CloudDetector()
        result = detector.detect(**scene)
        # Cloud patch is 50x50 out of 100x100 = 25%
        assert 15.0 < result.cloud_percentage < 40.0

    def test_sample_scene_snow_region_mostly_clear(self):
        """Snow region in sample scene should not be flagged as cloud."""
        scene = generate_sample_scene(100, 100)
        detector = CloudDetector()
        result = detector.detect(**scene)
        snow_region = result.cloud_mask[70:, 70:]
        snow_false_positives = 100.0 * np.sum(snow_region) / snow_region.size
        assert snow_false_positives < 15.0
