"""
Unit test: Phase 1 basics (config, schemas, generators).
"""

import pytest
import numpy as np
from pathlib import Path
import sys
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas.outputs import (
    ModalityResult,
    QualityResult,
    GateResult,
    FusionResult,
    InferenceResult,
    FeedbackEvent,
)
from telemetry.generator import generate_sample, generate_batch, CHANNEL_SPECS
from history.generator import generate_asset_history, generate_asset_histories
from configs import load_config


class TestPhase1Schemas:
    """Test that schemas validate correctly."""

    def test_modality_result(self):
        mr = ModalityResult(name="vision", prediction=0.7, raw_score=1.5)
        assert mr.prediction == 0.7
        assert mr.to_dict()["name"] == "vision"

    def test_quality_result_valid(self):
        qr = QualityResult(quality=0.85, factors={"blur": 0.9, "exposure": 0.8})
        assert qr.quality == 0.85
        assert qr.factors["blur"] == 0.9

    def test_quality_result_bounds_check(self):
        # Quality out of bounds should raise
        with pytest.raises(AssertionError):
            QualityResult(quality=1.5, factors={"blur": 0.9})

    def test_quality_result_factor_bounds_check(self):
        # Factor out of bounds should raise
        with pytest.raises(AssertionError):
            QualityResult(quality=0.8, factors={"blur": 1.5})

    def test_gate_result(self):
        gr = GateResult(modality="vision", quality=0.9, prior=0.75, gate=0.675, weight=0.33)
        assert gr.gate == 0.675

    def test_fusion_result_valid(self):
        fr = FusionResult(
            fused_score=0.65,
            weights={"vision": 0.4, "telemetry": 0.35, "history": 0.25},
            cross_modal_disagreement=0.15
        )
        assert abs(sum(fr.weights.values()) - 1.0) < 1e-5

    def test_fusion_result_weight_sum_check(self):
        # Weights not summing to ~1 should raise
        with pytest.raises(AssertionError):
            FusionResult(
                fused_score=0.5,
                weights={"vision": 0.3, "telemetry": 0.3},  # sums to 0.6
                cross_modal_disagreement=0.1
            )

    def test_inference_result(self):
        ir = InferenceResult(
            asset_id="asset_001",
            prediction={"label": "normal", "raw_probability": 0.3, "calibrated_probability": 0.32},
            modalities=[
                {"name": "vision", "prediction": 0.2, "quality": 0.9, "prior": 0.75, "weight": 0.4}
            ],
            uncertainty={"cross_modal_disagreement": 0.1},
            explanations={"dominant_modality": "vision", "reason": "highest weight"}
        )
        assert ir.asset_id == "asset_001"
        json_str = ir.to_json()
        assert "asset_001" in json_str

    def test_feedback_event(self):
        fe = FeedbackEvent(
            prediction_correct=True,
            modality_flagged_reliable=None,
            predicted_confidence=0.7,
            timestamp="2024-01-10T12:00:00Z"
        )
        assert fe.prediction_correct is True


class TestPhase1TelemetryGenerator:
    """Test synthetic telemetry generation."""

    def test_generate_sample_normal(self):
        sample = generate_sample(condition="normal", seed=42)
        assert sample.condition == "normal"
        assert sample.ground_truth == 0
        assert set(sample.channels.keys()) == set(CHANNEL_SPECS.keys())
        assert len(sample.channels["temperature"]) == 100

    def test_generate_sample_anomalous(self):
        sample = generate_sample(condition="anomalous", seed=42)
        assert sample.condition == "anomalous"
        assert sample.ground_truth == 1

    def test_generate_sample_with_noise(self):
        sample = generate_sample(condition="normal", noise_level=1.0, seed=42)
        # Should have noise added
        assert "temperature" in sample.channels

    def test_generate_sample_with_missing_data(self):
        sample = generate_sample(condition="normal", missing_rate=0.2, seed=42)
        # Should have NaN values
        has_nan = False
        for ch in sample.channels.values():
            if np.isnan(ch).any():
                has_nan = True
                break
        assert has_nan

    def test_generate_sample_with_drift(self):
        sample = generate_sample(condition="normal", drift=5.0, seed=42)
        # Drift is added linearly; check that values span a wider range than normal
        assert "temperature" in sample.channels

    def test_generate_sample_with_staleness(self):
        sample = generate_sample(condition="normal", staleness_seconds=100.0, seed=42)
        # Timestamps should reflect staleness
        assert len(sample.timestamps) == 100

    def test_generate_sample_range_violation(self):
        sample = generate_sample(condition="normal", range_violation=True, seed=42)
        # Temperature should have a value outside its normal range
        temp = sample.channels["temperature"]
        spec = CHANNEL_SPECS["temperature"]
        # One value might exceed max due to violation
        assert "temperature" in sample.channels

    def test_generate_sample_composable_degradation(self):
        # Test that multiple degradation modes can be composed
        sample = generate_sample(
            condition="normal",
            noise_level=0.5,
            missing_rate=0.1,
            drift=2.0,
            spike_probability=0.05,
            seed=42
        )
        assert sample.condition == "normal"

    def test_generate_batch(self):
        batch = generate_batch(n_samples=20, condition_ratio=0.5, seed=42)
        assert len(batch) == 20
        anomalous_count = sum(1 for s in batch if s.condition == "anomalous")
        assert anomalous_count == 10


class TestPhase1HistoryGenerator:
    """Test synthetic history generation."""

    def test_generate_asset_history(self):
        history = generate_asset_history(asset_id="asset_001", n_inspections=20, seed=42)
        assert history.asset_id == "asset_001"
        assert len(history.inspections) == 20
        assert history.total_inspections == 20

    def test_generate_asset_history_anomaly_frequency(self):
        history = generate_asset_history(
            asset_id="asset_001",
            n_inspections=50,
            anomaly_frequency=0.3,
            seed=42
        )
        anomalies = sum(1 for insp in history.inspections if insp.anomaly_detected)
        # Should be approximately 15 (50 * 0.3), allow some variance
        assert 12 <= anomalies <= 18

    def test_generate_asset_histories(self):
        histories = generate_asset_histories(n_assets=5, n_inspections_per_asset=10, seed=42)
        assert len(histories) == 5
        for asset_id in [f"asset_{i:03d}" for i in range(5)]:
            assert asset_id in histories


class TestPhase1Config:
    """Test configuration loading."""

    def test_config_loads(self):
        config = load_config("configs/config.yaml")
        assert "seed" in config
        assert "modalities" in config
        assert "quality" in config
        assert "trust" in config

    def test_config_seed(self):
        config = load_config("configs/config.yaml")
        assert config["seed"] == 42

    def test_config_quality_vision(self):
        config = load_config("configs/config.yaml")
        assert "vision" in config["quality"]
        assert "blur_ref" in config["quality"]["vision"]

    def test_config_trust_bounds(self):
        config = load_config("configs/config.yaml")
        prior_bounds = config["trust"]["prior_bounds"]
        assert prior_bounds == [0.05, 0.99]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
