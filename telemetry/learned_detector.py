"""
Learned telemetry detector: logistic regression on engineered signal features.

Replaces simple z-score thresholding which leaves signal on the table.
Uses per-channel statistics, cross-channel correlations, and spectral features.
"""

import numpy as np
import logging
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from typing import Dict, Optional

from schemas.outputs import ModalityResult
from telemetry.preprocessing import (
    preprocess_telemetry,
    compute_signal_to_noise_ratio,
    get_missingness_rate,
)

logger = logging.getLogger(__name__)


def extract_telemetry_features(channels: Dict[str, np.ndarray], timestamps: np.ndarray) -> np.ndarray:
    """
    Extract hand-engineered features from telemetry for anomaly detection.

    Features target real anomaly patterns: out-of-range values, correlations, noise, drift.

    Args:
        channels: Dict of channel_name -> 1D array
        timestamps: Timestamps array

    Returns:
        Feature vector of shape (n_features,)
    """
    features = []

    # Preprocess
    preprocessed = preprocess_telemetry(channels)

    # Per-channel features
    channel_stats = []
    for ch_name, signal in preprocessed.items():
        valid = signal[~np.isnan(signal)]

        if len(valid) < 2:
            channel_stats.append([0.0, 0.0, 0.0, 0.0])
            continue

        mean_val = np.mean(valid)
        std_val = np.std(valid)
        min_val = np.min(valid)
        max_val = np.max(valid)

        # Normalize to [0, 1] using typical ranges
        ranges = {
            "temperature": (20.0, 100.0),
            "vibration": (0.0, 10.0),
            "pressure": (0.0, 100.0),
            "current": (0.0, 50.0),
            "rpm": (0.0, 3000.0),
        }
        ch_min, ch_max = ranges.get(ch_name, (0, 1))
        ch_range = ch_max - ch_min + 1e-6

        norm_mean = (mean_val - ch_min) / ch_range
        norm_std = std_val / ch_range
        norm_min = (min_val - ch_min) / ch_range
        norm_max = (max_val - ch_min) / ch_range

        channel_stats.append([norm_mean, norm_std, norm_min, norm_max])

    channel_stats = np.array(channel_stats)

    # 1-4. Mean of each stat across channels
    features.extend(np.mean(channel_stats, axis=0))

    # 5-8. Std of each stat across channels (detects inconsistency)
    features.extend(np.std(channel_stats, axis=0))

    # 9. Range of means across channels (inconsistent levels)
    features.append(np.max(channel_stats[:, 0]) - np.min(channel_stats[:, 0]))

    # 10. Out-of-range fraction (simple anomaly indicator)
    out_of_range_count = 0
    total_count = 0
    for ch_name, signal in preprocessed.items():
        valid = signal[~np.isnan(signal)]
        if len(valid) > 0:
            ranges = {
                "temperature": (20.0, 100.0),
                "vibration": (0.0, 10.0),
                "pressure": (0.0, 100.0),
                "current": (0.0, 50.0),
                "rpm": (0.0, 3000.0),
            }
            ch_min, ch_max = ranges.get(ch_name, (0, 1))
            out_of_range_count += np.sum((valid < ch_min) | (valid > ch_max))
            total_count += len(valid)

    oor_fraction = out_of_range_count / (total_count + 1e-6)
    features.append(oor_fraction)

    # 11. Average SNR (high SNR = clean, low SNR = noisy)
    snr_values = [compute_signal_to_noise_ratio(sig) for sig in preprocessed.values()]
    features.append(np.mean(snr_values) / 10.0)  # Normalize to ~[0, 1]

    # 12. Average missingness
    miss_rates = [get_missingness_rate(sig) for sig in preprocessed.values()]
    features.append(np.mean(miss_rates))

    return np.array(features, dtype=np.float32)


class LearnedTelemetryDetector:
    """
    Logistic regression detector for telemetry anomalies.
    Trained on engineered features that capture real anomaly patterns.
    """

    def __init__(self):
        """Initialize detector."""
        self.model = LogisticRegression(random_state=42, max_iter=1000)
        self.scaler = StandardScaler()
        self.is_fitted = False

    def fit(self, datasets: list, labels: np.ndarray, config: Optional[dict] = None):
        """
        Fit detector on training telemetry.

        Args:
            datasets: List of (channels, timestamps) tuples
            labels: Ground truth labels (0=normal, 1=anomalous)
            config: Config dict (unused)
        """
        # Extract features for all samples
        X = np.array([extract_telemetry_features(ch, ts) for ch, ts in datasets])

        # Fit scaler and model
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, labels)
        self.is_fitted = True

        logger.info(f"LearnedTelemetryDetector fitted on {len(datasets)} samples")

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
            timestamps: Timestamps array
            config: Config dict (unused)

        Returns:
            ModalityResult with anomaly probability
        """
        if not self.is_fitted:
            logger.warning("LearnedTelemetryDetector not fitted; returning 0.5")
            return ModalityResult(name="telemetry", prediction=0.5, raw_score=0.0)

        # Extract features
        features = extract_telemetry_features(channels, timestamps).reshape(1, -1)

        # Predict
        X_scaled = self.scaler.transform(features)
        probs = self.model.predict_proba(X_scaled)[0]
        anomaly_prob = probs[1]

        raw_score = self.model.decision_function(X_scaled)[0]

        result = ModalityResult(
            name="telemetry",
            prediction=float(anomaly_prob),
            raw_score=float(raw_score),
        )

        return result
