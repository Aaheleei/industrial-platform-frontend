"""
History anomaly detector using logistic regression over extracted features.
"""

import numpy as np
import logging
from typing import Dict, Optional
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from schemas.outputs import ModalityResult
from history.features import extract_all_features
from history.generator import AssetHistory

logger = logging.getLogger(__name__)


class HistoryDetector:
    """
    Logistic regression detector for anomalies based on asset inspection history.

    Approach: Extract 5 statistical features from history, train logistic regression,
    predict anomaly probability.
    """

    def __init__(self):
        """Initialize detector."""
        self.model = LogisticRegression(random_state=42, max_iter=1000)
        self.scaler = StandardScaler()
        self.feature_names = [
            "recency",
            "record_count",
            "temporal_coverage",
            "consistency",
            "anomaly_frequency",
        ]
        self.is_fitted = False

    def fit(self, histories: Dict[str, AssetHistory], labels: np.ndarray, config: Optional[dict] = None):
        """
        Fit logistic regression on asset histories.

        Args:
            histories: Dict of asset_id -> AssetHistory
            labels: Ground truth labels (1D array, 0=normal, 1=anomalous)
            config: Config dict with history parameters
        """
        # Extract features for all assets
        X = []
        for asset_id, history in histories.items():
            features = extract_all_features(history, config)
            feature_vector = [features[name] for name in self.feature_names]
            X.append(feature_vector)

        X = np.array(X)

        # Fit scaler and model
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, labels)
        self.is_fitted = True

        logger.info(f"HistoryDetector fitted on {len(histories)} assets")

    def predict(
        self,
        history: AssetHistory,
        config: Optional[dict] = None,
    ) -> ModalityResult:
        """
        Predict anomaly probability from asset history.

        Args:
            history: AssetHistory object
            config: Config dict with history parameters

        Returns:
            ModalityResult with anomaly probability in [0, 1]
        """
        if not self.is_fitted:
            logger.warning("HistoryDetector not fitted; using feature-based heuristic")
            return self._predict_unfitted(history, config)

        # Extract features
        features = extract_all_features(history, config)
        feature_vector = np.array([features[name] for name in self.feature_names]).reshape(1, -1)

        # Predict
        X_scaled = self.scaler.transform(feature_vector)
        probs = self.model.predict_proba(X_scaled)[0]  # [prob_normal, prob_anomalous]
        anomaly_prob = probs[1]

        # Raw score (log-odds)
        raw_score = self.model.decision_function(X_scaled)[0]

        result = ModalityResult(
            name="history",
            prediction=float(anomaly_prob),
            raw_score=float(raw_score),
        )

        logger.debug(f"History prediction: anomaly_prob={anomaly_prob:.3f}")

        return result

    def _predict_unfitted(self, history: AssetHistory, config: Optional[dict] = None) -> ModalityResult:
        """
        Fallback: heuristic prediction when model not fitted.
        Use anomaly_frequency as proxy.
        """
        features = extract_all_features(history, config)

        # Heuristic: if asset has high anomaly frequency, it's higher risk
        anomaly_freq = features["anomaly_frequency"]
        recency = features["recency"]

        # Combine: high frequency + recent = higher risk
        anomaly_prob = (anomaly_freq + recency) / 2.0
        anomaly_prob = float(np.clip(anomaly_prob, 0.0, 1.0))

        result = ModalityResult(
            name="history",
            prediction=anomaly_prob,
            raw_score=float(anomaly_freq - 0.5),  # Placeholder raw score
        )

        return result

    def get_quality(
        self,
        history: AssetHistory,
        config: Optional[dict] = None,
    ) -> dict:
        """
        Get quality factors for history (input properties only).

        Returns:
            Dict with 'quality' and 'factors'
        """
        features = extract_all_features(history, config)

        # Quality factors = extracted features (they're already in [0, 1])
        factors = {
            "recency": features["recency"],
            "record_count": features["record_count"],
            "temporal_coverage": features["temporal_coverage"],
            "consistency": features["consistency"],
        }

        # Aggregate by mean
        quality = np.mean(list(factors.values()))

        return {"quality": quality, "factors": factors}
