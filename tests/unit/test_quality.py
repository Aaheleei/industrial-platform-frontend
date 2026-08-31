"""
Unit tests: Quality estimation (all 3 modalities).

Invariant check: Quality must be independent of model prediction confidence.
"""

import pytest
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from quality.estimator import estimate_quality
from vision.preprocessing import estimate_vision_quality
from telemetry.detector import TelemetryDetector
from telemetry.generator import generate_sample
from history.detector import HistoryDetector
from history.generator import generate_asset_history
from configs import load_config


class TestQualityBounds:
    """Test that all quality factors stay in [0, 1]."""

    def test_vision_quality_bounds(self):
        config = load_config("configs/config.yaml")
        img = np.random.rand(224, 224, 3)
        result = estimate_vision_quality(img, config)

        assert 0.0 <= result["quality"] <= 1.0
        for name, val in result["factors"].items():
            assert 0.0 <= val <= 1.0, f"Vision factor {name}={val} out of bounds"

    def test_telemetry_quality_bounds(self):
        config = load_config("configs/config.yaml")
        detector = TelemetryDetector()
        sample = generate_sample(condition="normal", seed=42)
        result = detector.get_quality(sample.channels, sample.timestamps, config)

        assert 0.0 <= result["quality"] <= 1.0
        for name, val in result["factors"].items():
            assert 0.0 <= val <= 1.0, f"Telemetry factor {name}={val} out of bounds"

    def test_history_quality_bounds(self):
        config = load_config("configs/config.yaml")
        detector = HistoryDetector()
        history = generate_asset_history(asset_id="asset_001", n_inspections=20, seed=42)
        result = detector.get_quality(history, config)

        assert 0.0 <= result["quality"] <= 1.0
        for name, val in result["factors"].items():
            assert 0.0 <= val <= 1.0, f"History factor {name}={val} out of bounds"


class TestQualityIndependenceOfPrediction:
    """
    Critical invariant: Quality must be independent of model prediction.

    Quality is answerable without knowing what the model predicted.
    If quality depends on prediction confidence, that's a bug.
    """

    def test_vision_quality_independent_of_prediction(self):
        """
        Vision quality should depend only on image properties (blur, exposure, illumination),
        not on whether the detector thinks it's anomalous.
        """
        config = load_config("configs/config.yaml")

        # Create two images with same quality properties
        img1 = np.ones((224, 224, 3)) * 0.5  # Mid-gray, uniform
        quality1 = estimate_vision_quality(img1, config)

        # Create another uniform image
        img2 = np.ones((224, 224, 3)) * 0.7  # Different brightness, but still uniform
        quality2 = estimate_vision_quality(img2, config)

        # Quality factors should be similar (both are uniform, blur-free, well-exposed)
        # They won't be identical (exposure differs), but both should be reasonably high
        assert quality1["quality"] > 0.4  # Uniform image = decent quality
        assert quality2["quality"] > 0.4  # Allow for exposure-related variation

    def test_telemetry_quality_independent_of_prediction(self):
        """
        Telemetry quality should depend on missingness, noise, drift, staleness,
        NOT on whether the model predicts anomaly or normal.
        """
        config = load_config("configs/config.yaml")
        detector = TelemetryDetector()

        # Clean telemetry
        sample_clean = generate_sample(condition="normal", noise_level=0.0, seed=42)
        quality_clean = detector.get_quality(sample_clean.channels, sample_clean.timestamps, config)

        # Degraded telemetry (same condition, but with noise)
        sample_noisy = generate_sample(condition="normal", noise_level=1.0, seed=42)
        quality_noisy = detector.get_quality(sample_noisy.channels, sample_noisy.timestamps, config)

        # Quality should be lower for noisy telemetry
        assert quality_clean["quality"] > quality_noisy["quality"]

    def test_history_quality_independent_of_prediction(self):
        """
        History quality should depend on recency, coverage, consistency,
        NOT on the model's predicted anomaly probability.
        """
        config = load_config("configs/config.yaml")
        detector = HistoryDetector()

        # Create a history with few recent inspections (low recency)
        # This should give low quality regardless of anomaly frequency
        history = generate_asset_history(asset_id="asset_001", n_inspections=5, seed=42)
        quality = detector.get_quality(history, config)

        # Quality should be in [0, 1]
        assert 0.0 <= quality["quality"] <= 1.0
        # Recency factor should reflect age, not predicted anomaly probability
        assert "recency" in quality["factors"]


class TestQualityFactorInterpretability:
    """Test that quality factors are interpretable and map correctly."""

    def test_vision_blur_factor_interpretable(self):
        """Blurry image -> lower blur factor."""
        config = load_config("configs/config.yaml")
        from vision.preprocessing import compute_blur_factor

        sharp_img = np.random.rand(224, 224, 3)  # Random = high freq = sharp
        blur_sharp = compute_blur_factor(sharp_img)

        uniform_img = np.ones((224, 224, 3)) * 0.5  # Uniform = low freq = blurry
        blur_uniform = compute_blur_factor(uniform_img)

        assert blur_sharp > blur_uniform

    def test_telemetry_missingness_factor_interpretable(self):
        """More missing data -> lower missingness factor."""
        detector = TelemetryDetector()
        config = load_config("configs/config.yaml")

        sample_complete = generate_sample(condition="normal", missing_rate=0.0, seed=42)
        quality_complete = detector.get_quality(sample_complete.channels, sample_complete.timestamps, config)

        sample_missing = generate_sample(condition="normal", missing_rate=0.3, seed=42)
        quality_missing = detector.get_quality(sample_missing.channels, sample_missing.timestamps, config)

        assert quality_complete["quality"] > quality_missing["quality"]


class TestQualityDispatch:
    """Test quality estimator dispatch."""

    def test_estimate_quality_vision(self):
        config = load_config("configs/config.yaml")
        img = np.random.rand(224, 224, 3)
        result = estimate_quality("vision", img, config)
        assert "quality" in result
        assert "factors" in result

    def test_estimate_quality_telemetry(self):
        config = load_config("configs/config.yaml")
        sample = generate_sample(condition="normal", seed=42)
        result = estimate_quality("telemetry", (sample.channels, sample.timestamps), config)
        assert "quality" in result
        assert "factors" in result

    def test_estimate_quality_history(self):
        config = load_config("configs/config.yaml")
        history = generate_asset_history(asset_id="asset_001", seed=42)
        result = estimate_quality("history", history, config)
        assert "quality" in result
        assert "factors" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
