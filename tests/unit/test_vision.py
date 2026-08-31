"""
Unit test: Vision detector and preprocessing.
"""

import pytest
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from vision.preprocessing import (
    resize_and_normalize,
    compute_blur_factor,
    compute_exposure_factor,
    compute_illumination_uniformity,
    estimate_vision_quality,
)
from vision.detector import VisionDetector
from vision.localization import compute_anomaly_heatmap


class TestVisionPreprocessing:
    """Test image preprocessing and quality factor extraction."""

    def test_resize_and_normalize_rgb(self):
        # Create a random RGB image
        img = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
        resized = resize_and_normalize(img, target_size=224)
        assert resized.shape == (224, 224, 3)
        assert resized.dtype == np.float32
        assert resized.min() >= 0.0 and resized.max() <= 1.0

    def test_resize_and_normalize_grayscale(self):
        # Grayscale image
        img = np.random.randint(0, 256, (480, 640), dtype=np.uint8)
        resized = resize_and_normalize(img, target_size=224)
        assert resized.shape == (224, 224, 3)
        assert resized.dtype == np.float32

    def test_compute_blur_factor(self):
        # Create a sharp image (high Laplacian variance)
        sharp_img = np.random.rand(224, 224, 3)
        blur_factor_sharp = compute_blur_factor(sharp_img)
        assert 0.0 <= blur_factor_sharp <= 1.0

        # Create a blurry image (low Laplacian variance)
        blurry_img = np.ones((224, 224, 3)) * 0.5
        blur_factor_blurry = compute_blur_factor(blurry_img)
        assert blur_factor_blurry <= blur_factor_sharp

    def test_compute_exposure_factor(self):
        # Well-exposed image (mean around midpoint)
        img = np.ones((224, 224, 3)) * 0.5  # 127.5 in 8-bit
        exposure = compute_exposure_factor(img, exposure_range=(50, 200))
        assert 0.0 <= exposure <= 1.0
        assert exposure > 0.8  # Should be close to 1

        # Over-exposed image (mean near 255)
        img_bright = np.ones((224, 224, 3)) * 0.99
        exposure_bright = compute_exposure_factor(img_bright, exposure_range=(50, 200))
        assert exposure_bright < exposure  # Should be lower

    def test_compute_illumination_uniformity(self):
        # Uniform illumination (low std)
        uniform = np.ones((224, 224, 3)) * 0.5
        illum_uniform = compute_illumination_uniformity(uniform)
        assert illum_uniform > 0.8

        # Non-uniform illumination (high std)
        non_uniform = np.random.rand(224, 224, 3)
        illum_non_uniform = compute_illumination_uniformity(non_uniform)
        assert illum_non_uniform < illum_uniform

    def test_estimate_vision_quality_bounds(self):
        img = np.random.rand(224, 224, 3)
        config = {
            "vision": {
                "blur_ref": 100.0,
                "exposure_range": [50, 200],
                "illumination_threshold": 30.0,
            }
        }
        result = estimate_vision_quality(img, config)

        assert "quality" in result
        assert "factors" in result
        assert 0.0 <= result["quality"] <= 1.0

        for factor_name, factor_val in result["factors"].items():
            assert 0.0 <= factor_val <= 1.0, f"Factor {factor_name}={factor_val} out of bounds"


class TestVisionDetector:
    """Test vision detector."""

    def test_detector_initialization(self):
        detector = VisionDetector(device="cpu")
        assert detector.model is not None
        assert detector.device == "cpu"

    def test_detector_predict(self):
        detector = VisionDetector(device="cpu")

        # Create a random image
        img = np.random.rand(480, 640, 3)
        result = detector.predict(img)

        assert result.name == "vision"
        assert 0.0 <= result.prediction <= 1.0
        assert isinstance(result.raw_score, float)

    def test_detector_predict_uint8(self):
        detector = VisionDetector(device="cpu")

        # Create a uint8 image
        img = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
        result = detector.predict(img)

        assert 0.0 <= result.prediction <= 1.0

    def test_detector_get_quality(self):
        detector = VisionDetector(device="cpu")
        img = np.random.rand(480, 640, 3)

        quality_result = detector.get_quality(img)

        assert "quality" in quality_result
        assert "factors" in quality_result
        assert 0.0 <= quality_result["quality"] <= 1.0


class TestVisionLocalization:
    """Test localization stub."""

    def test_heatmap_returns_none(self):
        img = np.random.rand(224, 224, 3)
        heatmap = compute_anomaly_heatmap(img)
        assert heatmap is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
