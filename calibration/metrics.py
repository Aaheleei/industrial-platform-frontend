"""
Calibration metrics: ECE, Brier score, reliability diagram.
"""

import numpy as np
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def compute_ece(
    probs: np.ndarray,
    labels: np.ndarray,
    n_bins: int = 10,
) -> float:
    """
    Compute Expected Calibration Error (ECE).

    ECE = Σ |accuracy_in_bin - confidence_in_bin| * (bin_size / total)

    Args:
        probs: Predicted probabilities in [0, 1] (1D array)
        labels: Binary labels (0 or 1) (1D array)
        n_bins: Number of bins for calibration curve

    Returns:
        ECE in [0, 1]
    """
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0

    for i in range(n_bins):
        mask = (probs >= bins[i]) & (probs < bins[i + 1])
        if mask.sum() == 0:
            continue

        bin_probs = probs[mask]
        bin_labels = labels[mask]

        confidence = bin_probs.mean()
        accuracy = bin_labels.mean()

        bin_weight = mask.sum() / len(probs)
        ece += abs(accuracy - confidence) * bin_weight

    return float(ece)


def compute_brier_score(
    probs: np.ndarray,
    labels: np.ndarray,
) -> float:
    """
    Compute Brier Score: mean squared difference between predictions and labels.

    BS = (1/N) * Σ (p_i - y_i)^2

    Args:
        probs: Predicted probabilities in [0, 1] (1D array)
        labels: Binary labels (0 or 1) (1D array)

    Returns:
        Brier score in [0, 1]
    """
    bs = np.mean((probs - labels) ** 2)
    return float(bs)


def compute_reliability_diagram(
    probs: np.ndarray,
    labels: np.ndarray,
    n_bins: int = 10,
) -> dict:
    """
    Compute data for reliability diagram.

    Returns bin centers, accuracies, and confidences for plotting.

    Args:
        probs: Predicted probabilities (1D array)
        labels: Binary labels (1D array)
        n_bins: Number of bins

    Returns:
        Dict with keys: 'bin_centers', 'accuracies', 'confidences', 'bin_sizes'
    """
    bins = np.linspace(0, 1, n_bins + 1)
    bin_centers = (bins[:-1] + bins[1:]) / 2

    accuracies = []
    confidences = []
    bin_sizes = []

    for i in range(n_bins):
        mask = (probs >= bins[i]) & (probs < bins[i + 1])
        if mask.sum() == 0:
            accuracies.append(np.nan)
            confidences.append(np.nan)
            bin_sizes.append(0)
        else:
            bin_probs = probs[mask]
            bin_labels = labels[mask]

            accuracies.append(bin_labels.mean())
            confidences.append(bin_probs.mean())
            bin_sizes.append(mask.sum())

    return {
        'bin_centers': bin_centers,
        'accuracies': np.array(accuracies),
        'confidences': np.array(confidences),
        'bin_sizes': np.array(bin_sizes),
    }
