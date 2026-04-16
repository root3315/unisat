"""Tests for ImageProcessor module."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.image_processor import ImageProcessor


def test_image_processor_init():
    ip = ImageProcessor()
    assert ip is not None


def test_image_processor_has_methods():
    ip = ImageProcessor()
    assert hasattr(ip, 'compress_svd')
    assert hasattr(ip, 'convert_to_jpeg')
    assert hasattr(ip, 'geotag')
    assert hasattr(ip, 'generate_thumbnail')
