"""
Learned vision detector: simple logistic regression on image features.

Replaces pretrained ResNet18 which fails on synthetic defects.
Uses hand-engineered features that directly target our defect types.
"""

import numpy as np
import logging
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from typing import Dict, Optional

from schemas.outputs import ModalityResult

logger = logging.getLogger(__name__)


def extract_vision_features(image: np.ndarray) -> np.ndarray:
    """
    Extract hand-engineered features from an image for anomaly detection.

    Features target our defect types: scratches, dark patches, bright blobs, blur, distortion.

    Args:
        image: RGB image in [0, 1], shape (H, W, 3)

    Returns:
        Feature vector of shape (n_features,)
    """
    gray = np.mean(image, axis=2)
    h, w = gray.shape

    features = []

    # 1. Dark pixel ratio (scratches and dark patches)
    features.append(np.mean(gray < 0.25))

    # 2. Bright pixel ratio (bright blobs, overexposure)
    features.append(np.mean(gray > 0.75))

    # 3. Intensity range (defects increase contrast)
    features.append(np.max(gray) - np.min(gray))

    # 4. Quantile spread (another contrast measure)
    p25 = np.percentile(gray, 25)
    p75 = np.percentile(gray, 75)
    features.append(p75 - p25)

    # 5. Edge density (scratches have high local gradients)
    # Simple: differences between adjacent pixels
    dy = np.abs(np.diff(gray, axis=0)).mean()
    dx = np.abs(np.diff(gray, axis=1)).mean()
    features.append(dy + dx)

    # 6. Spatial variance (patchy defects increase local variance)
    # Divide image into 4 quadrants, measure variance of their means
    h_half, w_half = h // 2, w // 2
    quadrant_means = [
        np.mean(gray[:h_half, :w_half]),
        np.mean(gray[:h_half, w_half:]),
        np.mean(gray[h_half:, :w_half]),
        np.mean(gray[h_half:, w_half:]),
    ]
    features.append(np.var(quadrant_means))

    # 7. Mean intensity (some defects change overall brightness)
    features.append(np.mean(gray))

    return np.array(features, dtype=np.float32)


class LearnedVisionDetector:
    """
    Simple logistic regression detector trained on synthetic data.
    """

    def __init__(self):
        """Initialize detector."""
        self.model = LogisticRegression(random_state=42, max_iter=1000)
        self.scaler = StandardScaler()
        self.is_fitted = False

    def fit(self, images: list, labels: np.ndarray):
        """
        Fit detector on training images.

        Args:
            images: List of images in [0, 1]
            labels: Ground truth labels (0=normal, 1=anomalous)
        """
        # Extract features for all images
        X = np.array([extract_vision_features(img) for img in images])

        # Fit scaler and model
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, labels)
        self.is_fitted = True

        logger.info(f"LearnedVisionDetector fitted on {len(images)} images")

    def predict(self, image: np.ndarray, config: Optional[dict] = None) -> ModalityResult:
        """
        Predict anomaly probability from an image.

        Args:
            image: Input image in [0, 1]
            config: Config dict (unused)

        Returns:
            ModalityResult with anomaly probability
        """
        if not self.is_fitted:
            logger.warning("LearnedVisionDetector not fitted; returning 0.5")
            return ModalityResult(name="vision", prediction=0.5, raw_score=0.0)

        # Extract features
        features = extract_vision_features(image).reshape(1, -1)

        # Predict
        X_scaled = self.scaler.transform(features)
        probs = self.model.predict_proba(X_scaled)[0]
        anomaly_prob = probs[1]

        raw_score = self.model.decision_function(X_scaled)[0]

        result = ModalityResult(
            name="vision",
            prediction=float(anomaly_prob),
            raw_score=float(raw_score),
        )

        return result
