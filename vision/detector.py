"""
Vision anomaly detector using fine-tuned ResNet18.
"""

import torch
import torch.nn as nn
import torchvision.models as models
import numpy as np
from typing import Optional, Tuple
from pathlib import Path
import logging

from schemas.outputs import ModalityResult
from vision.preprocessing import resize_and_normalize, estimate_vision_quality

logger = logging.getLogger(__name__)


class VisionDetector:
    """
    Fine-tuned ResNet18 for binary anomaly classification (normal vs anomalous).

    Note (prototype simplification): This uses image-level classification only.
    No pixel-level localization is implemented — localization.py returns None.
    """

    def __init__(self, model_path: Optional[str] = None, device: str = "cpu"):
        """
        Initialize vision detector.

        Args:
            model_path: Path to saved model weights. If None, uses pretrained ResNet18.
            device: "cpu" or "cuda"
        """
        self.device = device
        self.model = self._build_model()

        if model_path and Path(model_path).exists():
            state_dict = torch.load(model_path, map_location=device)
            self.model.load_state_dict(state_dict)
            logger.info(f"Loaded model from {model_path}")
        else:
            logger.info("Using pretrained ResNet18 weights (fine-tuning placeholder)")

        self.model.eval()
        self.target_size = 224

    def _build_model(self) -> nn.Module:
        """Build fine-tuned ResNet18 for binary classification."""
        model = models.resnet18(pretrained=True)
        # Replace final layer for binary classification
        model.fc = nn.Linear(model.fc.in_features, 2)
        return model.to(self.device)

    def predict(
        self,
        image: np.ndarray,
        config: Optional[dict] = None,
    ) -> ModalityResult:
        """
        Predict anomaly probability from an image.

        Args:
            image: Input image (H, W, 3) with values in [0, 1] or [0, 255]
            config: Config dict (used for quality estimation, not prediction)

        Returns:
            ModalityResult with anomaly probability in [0, 1]
        """
        # Preprocess
        if image.dtype == np.uint8:
            image = image.astype(np.float32) / 255.0

        processed = resize_and_normalize(image, self.target_size)

        # Estimate quality (input property, not model confidence)
        if config is None:
            config = {"vision": {}}
        quality_result = estimate_vision_quality(processed, config)

        # Forward pass
        with torch.no_grad():
            # Convert to tensor: (H, W, 3) -> (1, 3, H, W)
            tensor = torch.from_numpy(processed).permute(2, 0, 1).unsqueeze(0).to(self.device)

            # Normalize using ImageNet stats
            mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1).to(self.device)
            std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1).to(self.device)
            tensor = (tensor - mean) / std

            logits = self.model(tensor)  # (1, 2)
            probs = torch.softmax(logits, dim=1)  # (1, 2)
            anomaly_prob = probs[0, 1].item()  # probability of anomaly class
            raw_score = logits[0, 1].item()  # raw logit

        result = ModalityResult(
            name="vision",
            prediction=float(anomaly_prob),
            raw_score=float(raw_score),
        )

        logger.debug(f"Vision prediction: anomaly_prob={anomaly_prob:.3f}, quality={quality_result['quality']:.3f}")

        return result

    def get_quality(self, image: np.ndarray, config: Optional[dict] = None) -> dict:
        """
        Get quality factors for an image (without making a prediction).

        Returns:
            Dict with 'quality' and 'factors'
        """
        if image.dtype == np.uint8:
            image = image.astype(np.float32) / 255.0

        processed = resize_and_normalize(image, self.target_size)

        if config is None:
            config = {"vision": {}}

        return estimate_vision_quality(processed, config)
