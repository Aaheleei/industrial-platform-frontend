"""
Temperature scaling for probability calibration.

Pipeline: raw probability p -> logit(p) -> T-scale -> sigmoid -> calibrated p
"""

import numpy as np
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class TemperatureScaler:
    """Calibrate probabilities using temperature scaling on logits."""

    def __init__(self, temperature: float = 1.0):
        """
        Initialize scaler.

        Args:
            temperature: Temperature parameter (> 0). T=1 = no scaling.
        """
        self.temperature = temperature
        self.is_fitted = False

    def fit(
        self,
        val_logits: np.ndarray,
        val_labels: np.ndarray,
        search_range: Tuple[float, float] = (0.1, 10.0),
        grid_size: int = 50,
    ) -> None:
        """
        Fit temperature by minimizing ECE on validation set.

        Args:
            val_logits: Validation logits (1D array)
            val_labels: Validation labels (1D binary array)
            search_range: (T_min, T_max) for grid search
            grid_size: Number of temperature values to try
        """
        from calibration.metrics import compute_ece

        best_ece = float('inf')
        best_temp = 1.0

        temps = np.linspace(search_range[0], search_range[1], grid_size)

        for temp in temps:
            # Transform logits
            scaled_logits = val_logits / temp
            # Convert to probabilities
            probs = self._logits_to_probs(scaled_logits)
            # Compute ECE
            ece = compute_ece(probs, val_labels)

            if ece < best_ece:
                best_ece = ece
                best_temp = temp

        self.temperature = best_temp
        self.is_fitted = True
        logger.info(f"Temperature fitted: T={self.temperature:.4f}, ECE={best_ece:.4f}")

    def transform(self, logits: np.ndarray) -> np.ndarray:
        """
        Transform logits using temperature scaling.

        Args:
            logits: Raw logits (1D array)

        Returns:
            Calibrated probabilities in [0, 1]
        """
        scaled_logits = logits / self.temperature
        probs = self._logits_to_probs(scaled_logits)
        return probs

    @staticmethod
    def _logits_to_probs(logits: np.ndarray) -> np.ndarray:
        """Convert logits to probabilities via sigmoid."""
        return 1.0 / (1.0 + np.exp(-logits))

    @staticmethod
    def logit(probs: np.ndarray) -> np.ndarray:
        """Convert probabilities to logits."""
        # Clip to avoid log(0)
        probs_clipped = np.clip(probs, 1e-7, 1.0 - 1e-7)
        return np.log(probs_clipped / (1.0 - probs_clipped))
