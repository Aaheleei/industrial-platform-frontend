"""
Vision localization stub.

Note (prototype simplification): Pixel-level anomaly localization is not implemented.
This module is a documented placeholder returning None.
"""

from typing import Optional
import numpy as np


def compute_anomaly_heatmap(image: np.ndarray) -> Optional[np.ndarray]:
    """
    Compute pixel-level anomaly heatmap.

    Prototype simplification: Not implemented.
    Returns None to indicate localization is not available.

    Future: Could implement PatchCore-style memory-bank embedding distance,
    or fine-tune to output segmentation masks.

    Args:
        image: Input image

    Returns:
        None (localization not implemented for this prototype)
    """
    return None
