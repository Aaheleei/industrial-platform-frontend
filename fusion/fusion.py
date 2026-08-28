"""
Fusion engine: combine modality predictions using trust weights.

Formula: z_fused = Σ_i w_i * p_i (probability-level fusion)
"""

import numpy as np
import logging
from typing import Dict, List

from schemas.outputs import ModalityResult, FusionResult

logger = logging.getLogger(__name__)


class FusionEngine:
    """Fuse multiple modality predictions using trust-weighted combination."""

    def combine(
        self,
        modality_results: List[ModalityResult],
        weights: Dict[str, float],
    ) -> FusionResult:
        """
        Fuse modality predictions using trust weights.

        Args:
            modality_results: List of ModalityResult objects
            weights: Dict of modality -> normalized weight (sum ≈ 1)

        Returns:
            FusionResult with fused_score, weights, cross_modal_disagreement
        """
        # Validate weights sum to ~1
        weight_sum = sum(weights.values())
        assert abs(weight_sum - 1.0) < 1e-5, f"Weights sum to {weight_sum}, not 1.0"

        # Collect predictions
        predictions = {}
        for result in modality_results:
            predictions[result.name] = result.prediction

        # Fuse: z_fused = Σ_i w_i * p_i
        fused_score = 0.0
        for modality, result in zip(predictions.keys(), modality_results):
            w = weights.get(modality, 0.0)
            if w > 0:
                fused_score += w * result.prediction

        # Clamp to [0, 1]
        fused_score = float(np.clip(fused_score, 0.0, 1.0))

        # Compute cross-modal disagreement: max(p_i) - min(p_i)
        if predictions:
            disagreement = max(predictions.values()) - min(predictions.values())
        else:
            disagreement = 0.0

        result = FusionResult(
            fused_score=fused_score,
            weights=weights,
            cross_modal_disagreement=float(disagreement),
        )

        logger.debug(
            f"Fusion: predictions={predictions}, weights={weights}, "
            f"fused_score={fused_score:.3f}, disagreement={disagreement:.3f}"
        )

        return result
