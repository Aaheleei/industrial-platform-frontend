"""
Telemetry anomaly detector using per-channel z-score ensemble.
"""

import numpy as np
import logging
from typing import Dict, Optional

from schemas.outputs import ModalityResult
from telemetry.preprocessing import (
    preprocess_telemetry,
    compute_signal_to_noise_ratio,
    get_missingness_rate,
    compute_in_range_fraction,
    compute_drift_penalty,
    compute_staleness_penalty,
)

logger = logging.getLogger(__name__)

# Channel specifications (from generator)
CHANNEL_SPECS = {
    "temperature": {"min": 20.0, "max": 100.0},
    "vibration": {"min": 0.0, "max": 10.0},
    "pressure": {"min": 0.0, "max": 100.0},
    "current": {"min": 0.0, "max": 50.0},
    "rpm": {"min": 0.0, "max": 3000.0},
}


class TelemetryDetector:
    """
    Per-channel z-score ensemble for anomaly detection.

    Approach: Compute z-score for each channel independently, average across channels.
    Simple and interpretable.
    """

    def __init__(self, z_threshold: float = 1.0):
        """
        Initialize detector.

        Args:
            z_threshold: Z-score threshold above which a channel is flagged anomalous.
                        Lower threshold = more sensitive to anomalies (default 1.0 instead of 2.5)
        """
        self.z_threshold = z_threshold
        self.normal_stats = {}  # Will be fitted from data if needed

    def predict(
        self,
        channels: Dict[str, np.ndarray],
        timestamps: np.ndarray,
        config: Optional[dict] = None,
    ) -> ModalityResult:
        """
        Predict anomaly probability from telemetry.

        Args:
            channels: Dict of channel_name -> 1D array
            timestamps: Timestamps for each sample
            config: Config dict (used for quality estimation)

        Returns:
            ModalityResult with anomaly probability in [0, 1]
        """
        # Preprocess
        preprocessed = preprocess_telemetry(channels)

        # Compute per-channel z-scores
        z_scores = {}
        for ch_name, signal in preprocessed.items():
            valid = signal[~np.isnan(signal)]

            if len(valid) < 2:
                z_scores[ch_name] = 0.0  # No valid data = neutral
                continue

            mean = np.mean(valid)
            std = np.std(valid)

            if std < 1e-6:
                # No variation = use extremeness
                max_val = np.max(valid)
                min_val = np.min(valid)
                z_scores[ch_name] = 0.0
            else:
                # Compute z-score for last sample
                last_valid = signal[~np.isnan(signal)][-1]
                z = (last_valid - mean) / std
                z_scores[ch_name] = abs(z)

        # Average z-scores across channels
        avg_z = np.mean(list(z_scores.values())) if z_scores else 0.0

        # Convert to probability [0, 1]
        # Use lower threshold for sensitivity. Sigmoid with steepness=3
        raw_score = 3.0 * (avg_z - self.z_threshold)
        anomaly_prob = 1.0 / (1.0 + np.exp(-raw_score))
        anomaly_prob = float(np.clip(anomaly_prob, 0.0, 1.0))

        result = ModalityResult(
            name="telemetry",
            prediction=anomaly_prob,
            raw_score=float(raw_score),
        )

        logger.debug(f"Telemetry prediction: anomaly_prob={anomaly_prob:.3f}, avg_z={avg_z:.2f}")

        return result

    def get_quality(
        self,
        channels: Dict[str, np.ndarray],
        timestamps: np.ndarray,
        config: Optional[dict] = None,
    ) -> dict:
        """
        Get quality factors for telemetry (input properties only).

        Returns:
            Dict with 'quality' and 'factors'
        """
        if config is None:
            config = {"telemetry": {}}

        telemetry_config = config.get("telemetry", {})
        drift_penalty_scale = telemetry_config.get("drift_penalty_scale", 1.0)
        staleness_half_life_s = telemetry_config.get("staleness_half_life_s", 300)

        factors = {}

        # Missingness
        missingness_rates = {ch: get_missingness_rate(sig) for ch, sig in channels.items()}
        avg_missingness = np.mean(list(missingness_rates.values()))
        factors["missingness"] = 1.0 - avg_missingness

        # Signal-to-noise ratio
        snr_values = {ch: compute_signal_to_noise_ratio(sig) for ch, sig in channels.items()}
        avg_snr = np.mean(list(snr_values.values()))
        # Normalize SNR to [0, 1]: assume good SNR is >= 1
        snr_factor = min(avg_snr / 5.0, 1.0)
        factors["noise"] = snr_factor

        # In-range fraction
        in_range_fracs = {
            ch: compute_in_range_fraction(channels[ch], CHANNEL_SPECS[ch])
            for ch in channels
            if ch in CHANNEL_SPECS
        }
        factors["in_range"] = np.mean(list(in_range_fracs.values())) if in_range_fracs else 1.0

        # Drift penalty
        drift_penalties = {
            ch: compute_drift_penalty(sig, drift_penalty_scale)
            for ch, sig in channels.items()
        }
        factors["drift"] = np.mean(list(drift_penalties.values()))

        # Staleness penalty
        if len(timestamps) > 0:
            import time
            current_time = time.time()
            staleness_penalties = [
                compute_staleness_penalty(ts, current_time, staleness_half_life_s)
                for ts in timestamps
            ]
            factors["staleness"] = np.mean(staleness_penalties)
        else:
            factors["staleness"] = 1.0

        # Aggregate by mean
        quality = np.mean(list(factors.values()))

        return {"quality": quality, "factors": factors}
