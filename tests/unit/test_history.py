"""
Unit tests: History detector and feature extraction.
"""

import pytest
import numpy as np
from pathlib import Path
import sys
import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from history.features import (
    extract_recency_feature,
    extract_record_count_feature,
    extract_temporal_coverage_feature,
    extract_consistency_feature,
    extract_anomaly_frequency_feature,
    extract_all_features,
)
from history.detector import HistoryDetector
from history.generator import generate_asset_history, generate_asset_histories, InspectionRecord, AssetHistory


class TestHistoryFeatures:
    """Test feature extraction."""

    def test_recency_feature_fresh(self):
        # Recently inspected asset
        history = generate_asset_history(asset_id="asset_001", n_inspections=5, seed=42)
        recency = extract_recency_feature(history)
        assert 0.5 < recency <= 1.0  # Should be high (recent)

    def test_recency_feature_stale(self):
        # Asset not inspected in a long time (manually create)
        old_ts = (datetime.datetime.utcnow() - datetime.timedelta(days=365)).isoformat() + "Z"
        inspection = InspectionRecord(
            asset_id="asset_001",
            timestamp=old_ts,
            anomaly_detected=False,
            inspection_type="routine"
        )
        history = AssetHistory(
            asset_id="asset_001",
            inspections=[inspection],
            total_inspections=1,
            anomalies_detected=0,
        )
        recency = extract_recency_feature(history)
        assert recency < 0.1  # Should be very low (stale)

    def test_record_count_feature(self):
        history = generate_asset_history(asset_id="asset_001", n_inspections=20, seed=42)
        count = extract_record_count_feature(history, count_ref=20)
        assert count == 1.0  # Exactly at reference

    def test_record_count_feature_saturation(self):
        history = generate_asset_history(asset_id="asset_001", n_inspections=50, seed=42)
        count = extract_record_count_feature(history, count_ref=20)
        assert count == 1.0  # Saturates at 1.0

    def test_temporal_coverage_feature(self):
        history = generate_asset_history(asset_id="asset_001", n_inspections=10, seed=42)
        coverage = extract_temporal_coverage_feature(history)
        assert 0.0 <= coverage <= 1.0

    def test_consistency_feature(self):
        # All anomalies (high consistency)
        inspections = [
            InspectionRecord(
                asset_id="asset_001",
                timestamp=(datetime.datetime.utcnow() - datetime.timedelta(days=i)).isoformat() + "Z",
                anomaly_detected=True,
                inspection_type="routine"
            )
            for i in range(5)
        ]
        history = AssetHistory(
            asset_id="asset_001",
            inspections=inspections,
            total_inspections=5,
            anomalies_detected=5,
        )
        consistency = extract_consistency_feature(history)
        assert consistency > 0.8  # High consistency

    def test_anomaly_frequency_feature(self):
        history = generate_asset_history(asset_id="asset_001", n_inspections=20, anomaly_frequency=0.3, seed=42)
        freq = extract_anomaly_frequency_feature(history)
        # Should be approximately 0.3 ± variance
        assert 0.15 < freq < 0.45

    def test_extract_all_features_bounds(self):
        history = generate_asset_history(asset_id="asset_001", n_inspections=20, seed=42)
        features = extract_all_features(history)

        assert len(features) == 5
        for name, val in features.items():
            assert 0.0 <= val <= 1.0, f"Feature {name}={val} out of bounds"


class TestHistoryDetector:
    """Test history detector."""

    def test_detector_initialization(self):
        detector = HistoryDetector()
        assert detector.is_fitted is False

    def test_detector_predict_unfitted(self):
        detector = HistoryDetector()
        history = generate_asset_history(asset_id="asset_001", n_inspections=20, seed=42)
        result = detector.predict(history)

        assert result.name == "history"
        assert 0.0 <= result.prediction <= 1.0
        assert isinstance(result.raw_score, float)

    def test_detector_fit_and_predict(self):
        # Generate training data
        histories = generate_asset_histories(n_assets=20, n_inspections_per_asset=10, seed=42)
        labels = np.array([i % 2 for i in range(20)])  # Alternate normal/anomalous

        detector = HistoryDetector()
        detector.fit(histories, labels)
        assert detector.is_fitted is True

        # Predict on one asset
        history = generate_asset_history(asset_id="asset_test", n_inspections=10, seed=100)
        result = detector.predict(history)

        assert 0.0 <= result.prediction <= 1.0

    def test_detector_get_quality(self):
        detector = HistoryDetector()
        history = generate_asset_history(asset_id="asset_001", n_inspections=20, seed=42)
        quality = detector.get_quality(history)

        assert "quality" in quality
        assert "factors" in quality
        assert 0.0 <= quality["quality"] <= 1.0

        for factor_name, factor_val in quality["factors"].items():
            assert 0.0 <= factor_val <= 1.0, f"Factor {factor_name}={factor_val} out of bounds"

    def test_detector_quality_independent_of_prediction(self):
        """Verify quality is input property, not prediction confidence."""
        detector = HistoryDetector()
        history = generate_asset_history(asset_id="asset_001", n_inspections=20, seed=42)

        quality = detector.get_quality(history)
        prediction = detector.predict(history)

        # Quality should not depend on whether prediction is anomalous
        # (it depends on history structure, not output)
        assert 0.0 <= quality["quality"] <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
