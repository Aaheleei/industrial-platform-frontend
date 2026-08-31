"""
Unit tests: Fusion engine (all 5 edge cases + integration).
"""

import pytest
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from fusion.fusion import FusionEngine
from schemas.outputs import ModalityResult, FusionResult


class TestFusionBasic:
    """Test basic fusion operations."""

    def test_fusion_initialization(self):
        engine = FusionEngine()
        assert engine is not None

    def test_fuse_two_modalities(self):
        engine = FusionEngine()

        results = [
            ModalityResult(name="vision", prediction=0.7, raw_score=1.5),
            ModalityResult(name="telemetry", prediction=0.3, raw_score=-0.5),
        ]
        weights = {"vision": 0.6, "telemetry": 0.4}

        fused = engine.combine(results, weights)

        # Expected: 0.6*0.7 + 0.4*0.3 = 0.42 + 0.12 = 0.54
        assert abs(fused.fused_score - 0.54) < 0.01
        assert 0.0 <= fused.fused_score <= 1.0

    def test_fuse_three_modalities(self):
        engine = FusionEngine()

        results = [
            ModalityResult(name="vision", prediction=0.9, raw_score=2.0),
            ModalityResult(name="telemetry", prediction=0.5, raw_score=0.0),
            ModalityResult(name="history", prediction=0.7, raw_score=1.0),
        ]
        weights = {"vision": 0.5, "telemetry": 0.3, "history": 0.2}

        fused = engine.combine(results, weights)

        # Expected: 0.5*0.9 + 0.3*0.5 + 0.2*0.7 = 0.45 + 0.15 + 0.14 = 0.74
        assert abs(fused.fused_score - 0.74) < 0.01


class TestFusionEdgeCases:
    """Test all 5 required edge cases."""

    def test_edge_case_all_modalities_present(self):
        """Edge case 1: All modalities present."""
        engine = FusionEngine()

        results = [
            ModalityResult(name="vision", prediction=0.8, raw_score=1.5),
            ModalityResult(name="telemetry", prediction=0.2, raw_score=-1.0),
            ModalityResult(name="history", prediction=0.5, raw_score=0.0),
        ]
        weights = {"vision": 0.5, "telemetry": 0.25, "history": 0.25}

        fused = engine.combine(results, weights)

        assert 0.0 <= fused.fused_score <= 1.0
        assert abs(sum(fused.weights.values()) - 1.0) < 1e-5

    def test_edge_case_one_missing(self):
        """Edge case 2: One modality missing (weight = 0)."""
        engine = FusionEngine()

        results = [
            ModalityResult(name="vision", prediction=0.8, raw_score=1.5),
            ModalityResult(name="telemetry", prediction=0.2, raw_score=-1.0),
        ]
        weights = {"vision": 0.6, "telemetry": 0.4, "history": 0.0}

        fused = engine.combine(results, weights)

        # History weight is 0, so only vision and telemetry contribute
        # Renormalize: vision=0.6/1.0, telemetry=0.4/1.0
        expected = 0.6 * 0.8 + 0.4 * 0.2
        assert abs(fused.fused_score - expected) < 0.01
        assert fused.weights["history"] == 0.0

    def test_edge_case_one_heavily_degraded(self):
        """Edge case 3: One modality heavily degraded (low weight)."""
        engine = FusionEngine()

        results = [
            ModalityResult(name="vision", prediction=0.9, raw_score=2.0),
            ModalityResult(name="telemetry", prediction=0.1, raw_score=-2.0),  # Degraded
            ModalityResult(name="history", prediction=0.8, raw_score=1.5),
        ]
        weights = {"vision": 0.45, "telemetry": 0.05, "history": 0.5}  # Telemetry down-weighted

        fused = engine.combine(results, weights)

        # Telemetry has low weight, shouldn't dominate
        assert fused.fused_score > 0.7  # Should be closer to vision/history

    def test_edge_case_two_contradictory(self):
        """Edge case 4: Two modalities contradictory (disagreement)."""
        engine = FusionEngine()

        results = [
            ModalityResult(name="vision", prediction=0.9, raw_score=2.0),  # Anomaly
            ModalityResult(name="telemetry", prediction=0.1, raw_score=-2.0),  # Normal
            ModalityResult(name="history", prediction=0.5, raw_score=0.0),  # Neutral
        ]
        weights = {"vision": 0.4, "telemetry": 0.3, "history": 0.3}

        fused = engine.combine(results, weights)

        # Cross-modal disagreement should be high
        disagreement = fused.cross_modal_disagreement
        expected_disagreement = 0.9 - 0.1  # max - min
        assert abs(disagreement - expected_disagreement) < 0.01

    def test_edge_case_multiple_degraded(self):
        """Edge case 5: Multiple modalities degraded simultaneously."""
        engine = FusionEngine()

        results = [
            ModalityResult(name="vision", prediction=0.2, raw_score=-1.5),  # Degraded
            ModalityResult(name="telemetry", prediction=0.15, raw_score=-2.0),  # Degraded
            ModalityResult(name="history", prediction=0.8, raw_score=1.5),  # Good
        ]
        weights = {"vision": 0.1, "telemetry": 0.1, "history": 0.8}  # History dominates

        fused = engine.combine(results, weights)

        # Should be close to history's prediction
        assert fused.fused_score > 0.65


class TestFusionCrossModalDisagreement:
    """Test cross-modal disagreement computation."""

    def test_disagreement_all_agree(self):
        """All modalities agree -> low disagreement."""
        engine = FusionEngine()

        results = [
            ModalityResult(name="vision", prediction=0.7, raw_score=1.0),
            ModalityResult(name="telemetry", prediction=0.7, raw_score=1.0),
            ModalityResult(name="history", prediction=0.7, raw_score=1.0),
        ]
        weights = {"vision": 0.33, "telemetry": 0.33, "history": 0.34}

        fused = engine.combine(results, weights)

        assert fused.cross_modal_disagreement < 0.01  # ~0 for perfect agreement

    def test_disagreement_high(self):
        """Modalities disagree -> high disagreement."""
        engine = FusionEngine()

        results = [
            ModalityResult(name="vision", prediction=0.95, raw_score=3.0),  # Strong anomaly
            ModalityResult(name="telemetry", prediction=0.05, raw_score=-3.0),  # Strong normal
        ]
        weights = {"vision": 0.5, "telemetry": 0.5}

        fused = engine.combine(results, weights)

        expected_disagreement = 0.95 - 0.05
        assert abs(fused.cross_modal_disagreement - expected_disagreement) < 0.01


class TestFusionWeightHandling:
    """Test fusion weight handling."""

    def test_fusion_weights_returned(self):
        """Fusion should return weights used."""
        engine = FusionEngine()

        results = [
            ModalityResult(name="vision", prediction=0.7, raw_score=1.0),
            ModalityResult(name="telemetry", prediction=0.3, raw_score=-1.0),
        ]
        weights = {"vision": 0.6, "telemetry": 0.4}

        fused = engine.combine(results, weights)

        assert fused.weights == weights

    def test_fusion_zero_weight_no_contribution(self):
        """Zero-weight modality shouldn't affect fusion."""
        engine = FusionEngine()

        # Two modalities with zero weight one
        results = [
            ModalityResult(name="vision", prediction=0.5, raw_score=0.0),
            ModalityResult(name="telemetry", prediction=0.95, raw_score=3.0),  # Outlier
        ]
        weights_with_zero = {"vision": 1.0, "telemetry": 0.0}
        weights_normal = {"vision": 1.0, "telemetry": 0.0}

        fused_zero = engine.combine(results, weights_with_zero)
        fused_normal = engine.combine(results, weights_normal)

        assert abs(fused_zero.fused_score - 0.5) < 0.01  # Only vision contributes


class TestFusionBounds:
    """Test that fusion output stays in [0, 1]."""

    def test_fusion_score_in_bounds(self):
        """Fused score always in [0, 1]."""
        engine = FusionEngine()

        for _ in range(10):
            predictions = np.random.rand(3)
            weights = np.random.rand(3)
            weights = weights / weights.sum()

            results = [
                ModalityResult(name="vision", prediction=float(predictions[0]), raw_score=0.0),
                ModalityResult(name="telemetry", prediction=float(predictions[1]), raw_score=0.0),
                ModalityResult(name="history", prediction=float(predictions[2]), raw_score=0.0),
            ]
            weight_dict = {
                "vision": float(weights[0]),
                "telemetry": float(weights[1]),
                "history": float(weights[2]),
            }

            fused = engine.combine(results, weight_dict)
            assert 0.0 <= fused.fused_score <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
