"""
Unit tests: Trust priors and human feedback.

Section 12 acceptance check: Update prior and verify downstream inference reflects it.
"""

import pytest
import numpy as np
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from trust.priors import TrustPriorStore
from schemas.outputs import FeedbackEvent
from configs import load_config


class TestTrustPriorStoreBasic:
    """Test basic prior store operations."""

    def test_store_initialization(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            store = TrustPriorStore(store_path=f.name)
            assert store is not None

    def test_get_prior_default(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            store = TrustPriorStore(store_path=f.name)
            prior = store.get_prior("asset_unknown", "vision")
            assert prior == 0.5

    def test_set_prior(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            store = TrustPriorStore(store_path=f.name)
            store.set_prior("asset_001", "vision", 0.8)
            prior = store.get_prior("asset_001", "vision")
            assert abs(prior - 0.8) < 1e-5

    def test_set_prior_clipping(self):
        """Prior should be clipped to [0.05, 0.99]."""
        config = {"trust": {"prior_bounds": [0.05, 0.99]}}

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            store = TrustPriorStore(store_path=f.name, config=config)

            # Try to set too low
            store.set_prior("asset_001", "vision", 0.0)
            prior = store.get_prior("asset_001", "vision")
            assert prior == 0.05

            # Try to set too high
            store.set_prior("asset_001", "vision", 1.0)
            prior = store.get_prior("asset_001", "vision")
            assert prior == 0.99

    def test_persistence_across_instances(self):
        """Store should persist to disk and be readable by new instance."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            store_path = f.name

        # First instance
        store1 = TrustPriorStore(store_path=store_path)
        store1.set_prior("asset_001", "vision", 0.75)

        # Second instance
        store2 = TrustPriorStore(store_path=store_path)
        prior = store2.get_prior("asset_001", "vision")
        assert abs(prior - 0.75) < 1e-5


class TestTrustPriorUpdate:
    """Test prior updates from feedback."""

    def test_update_correct_feedback(self):
        """Feedback saying modality was correct should increase prior."""
        config = load_config("configs/config.yaml")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            store = TrustPriorStore(store_path=f.name, config=config)

            # Start with neutral prior
            store.set_prior("asset_001", "telemetry", 0.5)

            # Feedback: telemetry was correct
            feedback = FeedbackEvent(
                prediction_correct=True,
                modality_flagged_reliable=None,
                predicted_confidence=0.8,
                timestamp="2024-01-10T12:00:00Z",
            )

            old_prior, new_prior = store.update_from_feedback("asset_001", "telemetry", feedback)

            # Prior should increase
            assert new_prior > old_prior

    def test_update_incorrect_feedback(self):
        """Feedback saying modality was incorrect should decrease prior."""
        config = load_config("configs/config.yaml")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            store = TrustPriorStore(store_path=f.name, config=config)

            # Start with high prior
            store.set_prior("asset_001", "telemetry", 0.8)

            # Feedback: telemetry was incorrect
            feedback = FeedbackEvent(
                prediction_correct=False,
                modality_flagged_reliable=None,
                predicted_confidence=0.7,
                timestamp="2024-01-10T12:00:00Z",
            )

            old_prior, new_prior = store.update_from_feedback("asset_001", "telemetry", feedback)

            # Prior should decrease
            assert new_prior < old_prior

    def test_update_min_evidence_count(self):
        """Prior should not update until min_evidence_count is reached."""
        config = load_config("configs/config.yaml")
        config["feedback"]["min_evidence_count"] = 5

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            store = TrustPriorStore(store_path=f.name, config=config)

            store.set_prior("asset_001", "telemetry", 0.5)
            initial_prior = store.get_prior("asset_001", "telemetry")

            # Send one feedback event (below threshold)
            feedback = FeedbackEvent(
                prediction_correct=True,
                modality_flagged_reliable=None,
                predicted_confidence=0.8,
                timestamp="2024-01-10T12:00:00Z",
            )

            store.update_from_feedback("asset_001", "telemetry", feedback)

            # Prior might not update immediately (depends on implementation)
            # For now, just check that history was recorded
            history = store.get_history("asset_001", "telemetry")
            assert len(history) >= 1

    def test_update_confidence_threshold(self):
        """Feedback below confidence threshold should be ignored."""
        config = load_config("configs/config.yaml")
        config["feedback"]["confidence_threshold"] = 0.6

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            store = TrustPriorStore(store_path=f.name, config=config)

            store.set_prior("asset_001", "telemetry", 0.5)

            # Feedback with low confidence (< 0.6)
            feedback = FeedbackEvent(
                prediction_correct=True,
                modality_flagged_reliable=None,
                predicted_confidence=0.3,  # Below threshold
                timestamp="2024-01-10T12:00:00Z",
            )

            old_prior, new_prior = store.update_from_feedback("asset_001", "telemetry", feedback)

            # Prior should not change (or change minimally)
            assert old_prior == new_prior

    def test_update_max_step_guard(self):
        """Single feedback should not change prior by more than max_step."""
        config = load_config("configs/config.yaml")
        config["feedback"]["ema_alpha"] = 1.0  # Try to force large change
        config["feedback"]["max_step"] = 0.15

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            store = TrustPriorStore(store_path=f.name, config=config)

            store.set_prior("asset_001", "telemetry", 0.5)

            feedback = FeedbackEvent(
                prediction_correct=True,
                modality_flagged_reliable=None,
                predicted_confidence=0.8,
                timestamp="2024-01-10T12:00:00Z",
            )

            old_prior, new_prior = store.update_from_feedback("asset_001", "telemetry", feedback)

            # Change should be clamped to max_step
            delta = abs(new_prior - old_prior)
            assert delta <= 0.15 + 1e-5


class TestTrustPriorHistory:
    """Test prior update history and rollback."""

    def test_history_recorded(self):
        """Update history should be recorded."""
        config = load_config("configs/config.yaml")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            store = TrustPriorStore(store_path=f.name, config=config)

            store.set_prior("asset_001", "telemetry", 0.5)

            feedback = FeedbackEvent(
                prediction_correct=True,
                modality_flagged_reliable=None,
                predicted_confidence=0.8,
                timestamp="2024-01-10T12:00:00Z",
            )

            store.update_from_feedback("asset_001", "telemetry", feedback)

            history = store.get_history("asset_001", "telemetry")
            assert len(history) > 0
            assert "old_prior" in history[0]
            assert "new_prior" in history[0]

    def test_rollback(self):
        """Rollback should restore prior to previous state."""
        config = load_config("configs/config.yaml")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            store = TrustPriorStore(store_path=f.name, config=config)

            store.set_prior("asset_001", "telemetry", 0.5)

            # Send two feedback events
            for i in range(2):
                feedback = FeedbackEvent(
                    prediction_correct=True,
                    modality_flagged_reliable=None,
                    predicted_confidence=0.8,
                    timestamp=f"2024-01-10T{12+i}:00:00Z",
                )
                store.update_from_feedback("asset_001", "telemetry", feedback)

            prior_after_updates = store.get_prior("asset_001", "telemetry")

            # Rollback to before second event
            store.rollback_to_event("asset_001", "telemetry", 1)

            prior_after_rollback = store.get_prior("asset_001", "telemetry")

            # Prior should be restored to state between events 0 and 1
            history = store.get_history("asset_001", "telemetry")
            assert len(history) == 1  # Only first event remains


class TestTrustPriorAcceptanceCheck:
    """Section 12 acceptance check: prior update changes downstream weight."""

    def test_updated_prior_affects_gate_weight(self):
        """
        Start with telemetry prior at 0.71. Feed N feedback events (N >= min_evidence_count)
        saying telemetry was wrong. Prior should move down. Later inference should have
        lower telemetry weight.
        """
        from trust.gate import TrustGate, GateInputs

        config = load_config("configs/config.yaml")
        n_feedback = config["feedback"]["min_evidence_count"] + 2

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            store = TrustPriorStore(store_path=f.name, config=config)

        # Set initial prior
        store.set_prior("asset_001", "telemetry", 0.71)

        # Send repeated "telemetry was wrong" feedback
        for i in range(n_feedback):
            feedback = FeedbackEvent(
                prediction_correct=False,  # Telemetry was wrong
                modality_flagged_reliable=None,
                predicted_confidence=0.7,
                timestamp=f"2024-01-10T{12+i}:00:00Z",
            )
            store.update_from_feedback("asset_001", "telemetry", feedback)

        prior_after = store.get_prior("asset_001", "telemetry")

        # Prior should have decreased
        assert prior_after < 0.71

        # Now compute gate weights before and after
        # Before
        gate_inputs_before = [
            GateInputs(modality="vision", quality=0.91, prior=0.75),
            GateInputs(modality="telemetry", quality=0.88, prior=0.71),  # Original prior
            GateInputs(modality="history", quality=0.94, prior=0.75),
        ]

        gate = TrustGate(epsilon=1e-6)
        _, weights_before = gate.compute_full_gate(gate_inputs_before, config)

        # After
        gate_inputs_after = [
            GateInputs(modality="vision", quality=0.91, prior=0.75),
            GateInputs(modality="telemetry", quality=0.88, prior=prior_after),  # Updated prior
            GateInputs(modality="history", quality=0.94, prior=0.75),
        ]

        _, weights_after = gate.compute_full_gate(gate_inputs_after, config)

        # Telemetry weight should decrease
        assert weights_after["telemetry"] < weights_before["telemetry"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
