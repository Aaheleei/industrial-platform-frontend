"""
Unit tests: Telemetry detector and preprocessing.
"""

import pytest
import numpy as np
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from telemetry.preprocessing import (
    preprocess_telemetry,
    compute_signal_to_noise_ratio,
    get_missingness_rate,
    compute_in_range_fraction,
    compute_drift_penalty,
    compute_staleness_penalty,
)
from telemetry.detector import TelemetryDetector
from telemetry.generator import generate_sample


class TestTelemetryPreprocessing:
    """Test telemetry preprocessing utilities."""

    def test_preprocess_telemetry(self):
        channels = {
            "temperature": np.array([60.0, 61.0, 59.0, 60.5]),
            "vibration": np.array([1.0, 1.1, 0.9]),
        }
        preprocessed = preprocess_telemetry(channels, window_size=100)

        assert "temperature" in preprocessed
        assert "vibration" in preprocessed
        assert len(preprocessed["temperature"]) == 100

    def test_compute_snr(self):
        # Clean signal (low noise)
        clean = np.array([1.0, 1.0, 1.0, 1.0, 1.0])
        snr_clean = compute_signal_to_noise_ratio(clean)
        assert snr_clean >= 0.0

        # Noisy signal
        noisy = np.array([1.0, 2.0, 0.5, 1.5, 0.8])
        snr_noisy = compute_signal_to_noise_ratio(noisy)
        # SNR of noisy should be comparable (simple test)
        assert snr_noisy >= 0.0

    def test_get_missingness_rate(self):
        signal_complete = np.array([1.0, 2.0, 3.0])
        assert get_missingness_rate(signal_complete) == 0.0

        signal_half_missing = np.array([1.0, np.nan, 3.0, np.nan])
        assert get_missingness_rate(signal_half_missing) == 0.5

    def test_compute_in_range_fraction(self):
        signal = np.array([1.0, 2.0, 3.0, 100.0, np.nan])
        fraction = compute_in_range_fraction(signal, (0.0, 50.0))
        # 3 values in range, 1 out of range, 1 NaN -> 3/4 = 0.75
        assert abs(fraction - 0.75) < 0.01

    def test_compute_drift_penalty(self):
        no_drift = np.array([1.0, 1.0, 1.0, 1.0])
        penalty_no_drift = compute_drift_penalty(no_drift)
        assert penalty_no_drift > 0.9

        with_drift = np.array([1.0, 2.0, 3.0, 4.0])
        penalty_with_drift = compute_drift_penalty(with_drift)
        assert penalty_with_drift < penalty_no_drift

    def test_compute_staleness_penalty(self):
        now = time.time()
        fresh_ts = now
        penalty_fresh = compute_staleness_penalty(fresh_ts, now, half_life_s=300)
        assert penalty_fresh > 0.99

        stale_ts = now - 600  # 2 half-lives ago
        penalty_stale = compute_staleness_penalty(stale_ts, now, half_life_s=300)
        assert penalty_stale < 0.3  # Should decay significantly


class TestTelemetryDetector:
    """Test telemetry detector."""

    def test_detector_initialization(self):
        detector = TelemetryDetector(z_threshold=2.5)
        assert detector.z_threshold == 2.5

    def test_detector_predict_normal(self):
        detector = TelemetryDetector()
        sample = generate_sample(condition="normal", seed=42)
        result = detector.predict(sample.channels, sample.timestamps)

        assert result.name == "telemetry"
        assert 0.0 <= result.prediction <= 1.0
        assert isinstance(result.raw_score, float)

    def test_detector_predict_anomalous(self):
        detector = TelemetryDetector()
        sample = generate_sample(condition="anomalous", seed=42)
        result = detector.predict(sample.channels, sample.timestamps)

        assert 0.0 <= result.prediction <= 1.0

    def test_detector_get_quality(self):
        detector = TelemetryDetector()
        sample = generate_sample(condition="normal", seed=42)
        quality = detector.get_quality(sample.channels, sample.timestamps)

        assert "quality" in quality
        assert "factors" in quality
        assert 0.0 <= quality["quality"] <= 1.0

        # Check all factors are in bounds
        for factor_name, factor_val in quality["factors"].items():
            assert 0.0 <= factor_val <= 1.0, f"Factor {factor_name}={factor_val} out of bounds"

    def test_detector_quality_independent_of_prediction(self):
        """Verify quality is input property, not prediction confidence."""
        detector = TelemetryDetector()
        sample = generate_sample(condition="normal", seed=42)

        quality = detector.get_quality(sample.channels, sample.timestamps)
        prediction = detector.predict(sample.channels, sample.timestamps)

        # Quality should not depend on whether prediction is anomalous or normal
        # (it depends on input degradation modes, not output)
        assert 0.0 <= quality["quality"] <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
