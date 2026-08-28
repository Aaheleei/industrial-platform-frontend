"""
Unit tests: Calibration (temperature scaling, metrics).
"""

import pytest
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from calibration.temperature_scaling import TemperatureScaler
from calibration.metrics import compute_ece, compute_brier_score, compute_reliability_diagram


class TestTemperatureScaler:
    """Test temperature scaling."""

    def test_scaler_initialization(self):
        scaler = TemperatureScaler(temperature=1.5)
        assert scaler.temperature == 1.5
        assert scaler.is_fitted is False

    def test_logit_to_probs_identity(self):
        """Logit 0 should give probability 0.5."""
        logits = np.array([0.0])
        probs = TemperatureScaler._logits_to_probs(logits)
        assert abs(probs[0] - 0.5) < 1e-5

    def test_logit_to_probs_bounds(self):
        """Probs should always be in [0, 1]."""
        logits = np.array([-10.0, -5.0, 0.0, 5.0, 10.0])
        probs = TemperatureScaler._logits_to_probs(logits)
        assert np.all(probs >= 0.0)
        assert np.all(probs <= 1.0)

    def test_logit_probs_roundtrip(self):
        """Convert probs -> logits -> probs should be close."""
        original_probs = np.array([0.1, 0.5, 0.9])
        logits = TemperatureScaler.logit(original_probs)
        recovered_probs = TemperatureScaler._logits_to_probs(logits)
        assert np.allclose(original_probs, recovered_probs)

    def test_temperature_scaling_effect(self):
        """Higher temperature should soften probabilities."""
        logits = np.array([2.0, -1.0])

        scaler1 = TemperatureScaler(temperature=1.0)
        probs1 = scaler1.transform(logits)

        scaler2 = TemperatureScaler(temperature=2.0)
        probs2 = scaler2.transform(logits)

        # Higher temp should push probs closer to 0.5
        assert abs(probs1[0] - 0.5) > abs(probs2[0] - 0.5)
        assert abs(probs1[1] - 0.5) > abs(probs2[1] - 0.5)

    def test_scaler_fit(self):
        """Fit temperature on validation set."""
        # Generate synthetic validation data
        np.random.seed(42)
        val_logits = np.random.randn(100) * 2.0
        val_labels = (TemperatureScaler._logits_to_probs(val_logits) > 0.5).astype(int)

        scaler = TemperatureScaler()
        scaler.fit(val_logits, val_labels)

        assert scaler.is_fitted is True
        assert 0.1 <= scaler.temperature <= 10.0


class TestCalibrationMetrics:
    """Test calibration metrics."""

    def test_ece_perfect_calibration(self):
        """ECE should be low for perfectly calibrated predictions."""
        # If probs match labels exactly, ECE should be ~0
        probs = np.array([0.0, 0.0, 1.0, 1.0])
        labels = np.array([0, 0, 1, 1])
        ece = compute_ece(probs, labels)
        assert ece < 0.1

    def test_ece_poor_calibration(self):
        """ECE should be high for poorly calibrated predictions."""
        # If probs are opposite labels, ECE should be high
        probs = np.array([0.9, 0.9, 0.1, 0.1])
        labels = np.array([0, 0, 1, 1])
        ece = compute_ece(probs, labels)
        assert ece > 0.7

    def test_ece_bounds(self):
        """ECE always in [0, 1]."""
        for _ in range(10):
            probs = np.random.rand(50)
            labels = np.random.randint(0, 2, 50)
            ece = compute_ece(probs, labels)
            assert 0.0 <= ece <= 1.0

    def test_brier_score_perfect(self):
        """Brier score should be 0 for perfect predictions."""
        probs = np.array([0.0, 0.0, 1.0, 1.0])
        labels = np.array([0, 0, 1, 1])
        bs = compute_brier_score(probs, labels)
        assert abs(bs - 0.0) < 1e-5

    def test_brier_score_worst(self):
        """Brier score should be 1 for worst predictions."""
        probs = np.array([1.0, 1.0, 0.0, 0.0])
        labels = np.array([0, 0, 1, 1])
        bs = compute_brier_score(probs, labels)
        assert abs(bs - 1.0) < 1e-5

    def test_brier_score_bounds(self):
        """Brier score always in [0, 1]."""
        for _ in range(10):
            probs = np.random.rand(50)
            labels = np.random.randint(0, 2, 50)
            bs = compute_brier_score(probs, labels)
            assert 0.0 <= bs <= 1.0

    def test_reliability_diagram_structure(self):
        """Reliability diagram should have correct structure."""
        probs = np.random.rand(100)
        labels = np.random.randint(0, 2, 100)

        diag = compute_reliability_diagram(probs, labels, n_bins=5)

        assert 'bin_centers' in diag
        assert 'accuracies' in diag
        assert 'confidences' in diag
        assert 'bin_sizes' in diag

        assert len(diag['bin_centers']) == 5
        assert len(diag['accuracies']) == 5
        assert len(diag['confidences']) == 5


class TestCalibrationPipeline:
    """Test full calibration pipeline."""

    def test_calibration_improves_ece(self):
        """Calibration should reduce ECE (or at least not worsen it much)."""
        np.random.seed(42)

        # Generate synthetic data: poorly calibrated predictions
        logits = np.random.randn(200) * 3.0  # Wide spread
        probs_raw = TemperatureScaler._logits_to_probs(logits)
        labels = (probs_raw > 0.5).astype(int) ^ np.random.randint(0, 2, 200)  # Flip some labels

        # Split into train/val
        train_idx = np.arange(100)
        val_idx = np.arange(100, 200)

        train_logits = logits[train_idx]
        train_labels = labels[train_idx]
        val_logits = logits[val_idx]
        val_labels = labels[val_idx]

        # Compute ECE before calibration
        probs_uncalibrated = TemperatureScaler._logits_to_probs(val_logits)
        ece_before = compute_ece(probs_uncalibrated, val_labels)

        # Calibrate
        scaler = TemperatureScaler()
        scaler.fit(train_logits, train_labels)

        # Compute ECE after calibration
        probs_calibrated = scaler.transform(val_logits)
        ece_after = compute_ece(probs_calibrated, val_labels)

        # Should improve or be close
        assert ece_after <= ece_before + 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
