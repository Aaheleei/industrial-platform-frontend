"""
Per-modality quality estimation (independent of model confidence).

Invariant: Quality is a property of the input, not the output.
Quality can be estimated without knowing what the model predicted.
"""

import numpy as np
from typing import Dict, Optional


def estimate_quality(
    modality: str,
    data: any,
    config: Optional[Dict] = None,
) -> Dict[str, float]:
    """
    Dispatch to modality-specific quality estimator.

    Args:
        modality: "vision" | "telemetry" | "history"
        data: Input data (image, channels+timestamps, or AssetHistory)
        config: Config dict

    Returns:
        Dict with 'quality' in [0,1] and 'factors' dict (all in [0,1])
    """
    if modality == "vision":
        from vision.preprocessing import estimate_vision_quality
        return estimate_vision_quality(data, config)
    elif modality == "telemetry":
        channels, timestamps = data
        from telemetry.detector import TelemetryDetector
        detector = TelemetryDetector()
        return detector.get_quality(channels, timestamps, config)
    elif modality == "history":
        from history.detector import HistoryDetector
        detector = HistoryDetector()
        return detector.get_quality(data, config)
    else:
        raise ValueError(f"Unknown modality: {modality}")
