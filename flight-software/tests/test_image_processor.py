"""Tests for ImageProcessor module."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.image_processor import ImageProcessor


def test_image_processor_init():
    ip = ImageProcessor()
    assert ip is not None


def test_svd_compress():
    ip = ImageProcessor()
    import numpy as np
    img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    compressed = ip.svd_compress(img, k=10)
    assert compressed.shape == img.shape
