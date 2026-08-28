"""
Trust prior store: per-asset, per-modality priors with EMA updates and rollback.

Persisted to JSON with append-only history log for rollback capability.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import asdict
import numpy as np

from schemas.outputs import FeedbackEvent

logger = logging.getLogger(__name__)


class TrustPriorStore:
    """
    Persistent store of per-asset, per-modality trust priors.

    Structure:
    {
      "asset_001": {
        "vision": {
          "prior": 0.75,
          "history": [{"timestamp": ..., "old_prior": ..., "new_prior": ...}, ...]
        },
        ...
      }
    }
    """

    def __init__(self, store_path: str = "priors_store.json", config: Optional[Dict] = None):
        """
        Initialize prior store.

        Args:
            store_path: Path to JSON file for persistence
            config: Config dict with feedback parameters
        """
        self.store_path = Path(store_path)
        self.config = config or {"feedback": {}}
        self.data = self._load()

    def _load(self) -> Dict:
        """Load store from disk, or initialize empty."""
        if self.store_path.exists():
            with open(self.store_path, "r") as f:
                return json.load(f)
        return {}

    def _save(self):
        """Persist store to disk."""
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.store_path, "w") as f:
            json.dump(self.data, f, indent=2)

    def get_prior(self, asset_id: str, modality: str, default: float = 0.5) -> float:
        """
        Get current prior for asset/modality.

        Args:
            asset_id: Asset identifier
            modality: "vision" | "telemetry" | "history"
            default: Default prior if not found

        Returns:
            Prior in [0.05, 0.99]
        """
        if asset_id not in self.data:
            return default

        if modality not in self.data[asset_id]:
            return default

        prior = self.data[asset_id][modality].get("prior", default)
        return float(prior)

    def set_prior(self, asset_id: str, modality: str, prior: float):
        """
        Set prior (not using feedback, direct update).

        Args:
            asset_id: Asset identifier
            modality: "vision" | "telemetry" | "history"
            prior: New prior value (will be clipped to bounds)
        """
        if asset_id not in self.data:
            self.data[asset_id] = {}

        if modality not in self.data[asset_id]:
            self.data[asset_id][modality] = {"prior": 0.5, "history": []}

        prior_bounds = tuple(self.config.get("trust", {}).get("prior_bounds", [0.05, 0.99]))
        prior_clipped = float(np.clip(prior, prior_bounds[0], prior_bounds[1]))

        self.data[asset_id][modality]["prior"] = prior_clipped
        self._save()

    def update_from_feedback(
        self,
        asset_id: str,
        modality: str,
        feedback: FeedbackEvent,
    ) -> Tuple[float, float]:
        """
        Update prior using EMA from feedback event.

        Args:
            asset_id: Asset identifier
            modality: "vision" | "telemetry" | "history"
            feedback: FeedbackEvent with prediction correctness and confidence

        Returns:
            (old_prior, new_prior)
        """
        feedback_config = self.config.get("feedback", {})
        ema_alpha = feedback_config.get("ema_alpha", 0.2)
        min_evidence_count = feedback_config.get("min_evidence_count", 5)
        confidence_threshold = feedback_config.get("confidence_threshold", 0.6)
        max_step = feedback_config.get("max_step", 0.15)
        prior_bounds = tuple(self.config.get("trust", {}).get("prior_bounds", [0.05, 0.99]))

        # Get current prior
        current_prior = self.get_prior(asset_id, modality)

        # Check confidence threshold: if prediction was uncertain, ignore feedback
        if feedback.predicted_confidence < confidence_threshold:
            logger.debug(
                f"Ignoring feedback for {asset_id}/{modality}: "
                f"confidence {feedback.predicted_confidence} < threshold {confidence_threshold}"
            )
            return current_prior, current_prior

        # Compute observed reliability
        if feedback.modality_flagged_reliable is not None:
            # Explicit flag takes precedence
            observed_reliability = 1.0 if feedback.modality_flagged_reliable else 0.0
        else:
            # Infer from prediction correctness
            observed_reliability = 1.0 if feedback.prediction_correct else 0.0

        # EMA update
        new_prior_ema = ema_alpha * observed_reliability + (1.0 - ema_alpha) * current_prior

        # Apply max_step guard
        delta = new_prior_ema - current_prior
        clamped_delta = np.clip(delta, -max_step, max_step)
        new_prior = current_prior + clamped_delta

        # Clip to prior bounds
        new_prior = float(np.clip(new_prior, prior_bounds[0], prior_bounds[1]))

        # Log history
        if asset_id not in self.data:
            self.data[asset_id] = {}
        if modality not in self.data[asset_id]:
            self.data[asset_id][modality] = {"prior": 0.5, "history": []}

        history_entry = {
            "timestamp": feedback.timestamp,
            "observed_reliability": float(observed_reliability),
            "old_prior": float(current_prior),
            "new_prior": float(new_prior),
        }
        self.data[asset_id][modality]["history"].append(history_entry)
        self.data[asset_id][modality]["prior"] = new_prior

        self._save()

        logger.debug(
            f"Updated {asset_id}/{modality} prior: {current_prior:.3f} -> {new_prior:.3f} "
            f"(observed_reliability={observed_reliability})"
        )

        return float(current_prior), float(new_prior)

    def get_history(self, asset_id: str, modality: str) -> list:
        """Get update history for an asset/modality."""
        if asset_id not in self.data or modality not in self.data[asset_id]:
            return []
        return self.data[asset_id][modality].get("history", [])

    def rollback_to_event(self, asset_id: str, modality: str, event_index: int):
        """
        Rollback prior to state before a specific feedback event.

        Args:
            asset_id: Asset identifier
            modality: "vision" | "telemetry" | "history"
            event_index: Index of event to rollback (removes from event_index onwards)
        """
        if asset_id not in self.data or modality not in self.data[asset_id]:
            logger.warning(f"No history for {asset_id}/{modality}")
            return

        history = self.data[asset_id][modality]["history"]

        if event_index < 0 or event_index >= len(history):
            logger.warning(f"Invalid event index {event_index} for history length {len(history)}")
            return

        # Rollback: remove events from event_index onwards, restore prior from event_index-1
        if event_index == 0:
            # Rollback all: restore to initial (use default 0.5)
            self.data[asset_id][modality]["prior"] = 0.5
            self.data[asset_id][modality]["history"] = []
        else:
            # Restore to state before event_index
            previous_event = history[event_index - 1]
            self.data[asset_id][modality]["prior"] = previous_event["new_prior"]
            self.data[asset_id][modality]["history"] = history[:event_index]

        self._save()
        logger.info(f"Rolled back {asset_id}/{modality} to before event {event_index}")

    def get_all_priors(self, asset_id: str) -> Dict[str, float]:
        """Get all modality priors for an asset."""
        if asset_id not in self.data:
            return {}
        return {
            modality: self.data[asset_id][modality].get("prior", 0.5)
            for modality in self.data[asset_id]
        }
