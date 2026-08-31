"""
Master inference pipeline: single entry point orchestrating all components.

Steps:
1. preprocess each modality
2. per-modality prediction
3. per-modality quality estimation
4. trust-prior retrieval for asset_id
5. gate computation
6. normalization
7. fusion
8. calibration
9. uncertainty computation (cross_modal_disagreement)
10. assemble InferenceResult
"""

import numpy as np
import logging
from typing import Dict, Optional

from schemas.outputs import (
    ModalityResult,
    InferenceResult,
)
from vision.detector import VisionDetector
from telemetry.detector import TelemetryDetector
from history.detector import HistoryDetector
from quality.estimator import estimate_quality
from trust.gate import TrustGate, GateInputs
from trust.priors import TrustPriorStore
from fusion.fusion import FusionEngine
from calibration.temperature_scaling import TemperatureScaler
from calibration.metrics import compute_ece
from configs import load_config

logger = logging.getLogger(__name__)


class InferencePipeline:
    """End-to-end inference pipeline."""

    def __init__(
        self,
        config_path: str = "configs/config.yaml",
        priors_store_path: str = "priors_store.json",
        model_path: Optional[str] = None,
    ):
        """
        Initialize pipeline with all components.

        Args:
            config_path: Path to config.yaml
            priors_store_path: Path to priors JSON store
            model_path: Path to vision model weights (optional)
        """
        self.config = load_config(config_path)

        # Initialize detectors
        self.vision_detector = VisionDetector(model_path=model_path, device="cpu")
        self.telemetry_detector = TelemetryDetector()
        self.history_detector = HistoryDetector()

        # Initialize trust components
        self.trust_gate = TrustGate(
            epsilon=self.config["trust"]["epsilon"],
            prior_bounds=tuple(self.config["trust"]["prior_bounds"]),
        )
        self.prior_store = TrustPriorStore(priors_store_path, config=self.config)

        # Initialize fusion and calibration
        self.fusion_engine = FusionEngine()
        self.temperature_scaler = TemperatureScaler()

        logger.info("InferencePipeline initialized")

    def run_inference(
        self,
        image: np.ndarray,
        telemetry: Dict,  # {"channels": {...}, "timestamps": [...]}
        history: any,  # AssetHistory object
        asset_id: str,
    ) -> InferenceResult:
        """
        Run full inference pipeline.

        Args:
            image: Vision input (H, W, 3)
            telemetry: Dict with "channels" and "timestamps"
            history: AssetHistory object
            asset_id: Asset identifier

        Returns:
            InferenceResult with prediction, modality details, uncertainty, explanations
        """
        logger.info(f"Running inference for {asset_id}")

        # Step 1-2: Preprocess + predict for each modality
        vision_result = self.vision_detector.predict(image, self.config)
        telemetry_result = self.telemetry_detector.predict(
            telemetry["channels"],
            telemetry["timestamps"],
            self.config,
        )
        history_result = self.history_detector.predict(history, self.config)

        # Step 3: Quality estimation (input properties only)
        vision_quality = estimate_quality("vision", image, self.config)
        telemetry_quality = estimate_quality(
            "telemetry",
            (telemetry["channels"], telemetry["timestamps"]),
            self.config,
        )
        history_quality = estimate_quality("history", history, self.config)

        # Step 4: Retrieve trust priors for asset
        vision_prior = self.prior_store.get_prior(asset_id, "vision", default=0.5)
        telemetry_prior = self.prior_store.get_prior(asset_id, "telemetry", default=0.5)
        history_prior = self.prior_store.get_prior(asset_id, "history", default=0.5)

        # Step 5-6: Gate computation and normalization
        gate_inputs = [
            GateInputs(modality="vision", quality=vision_quality["quality"], prior=vision_prior),
            GateInputs(modality="telemetry", quality=telemetry_quality["quality"], prior=telemetry_prior),
            GateInputs(modality="history", quality=history_quality["quality"], prior=history_prior),
        ]
        gate_results, weights = self.trust_gate.compute_full_gate(gate_inputs, self.config)

        # Step 7: Fusion
        modality_results = [vision_result, telemetry_result, history_result]
        fusion_result = self.fusion_engine.combine(modality_results, weights)

        # Step 8: Calibration
        raw_prob = fusion_result.fused_score
        logit = TemperatureScaler.logit(np.array([raw_prob]))[0]
        calibrated_prob = self.temperature_scaler.transform(np.array([logit]))[0]

        # Step 9: Uncertainty (cross-modal disagreement already computed)
        disagreement = fusion_result.cross_modal_disagreement

        # Step 10: Assemble InferenceResult
        prediction = {
            "label": "anomalous" if calibrated_prob > 0.5 else "normal",
            "raw_probability": float(raw_prob),
            "calibrated_probability": float(calibrated_prob),
        }

        modalities_list = [
            {
                "name": "vision",
                "prediction": vision_result.prediction,
                "quality": vision_quality["quality"],
                "prior": vision_prior,
                "weight": weights["vision"],
            },
            {
                "name": "telemetry",
                "prediction": telemetry_result.prediction,
                "quality": telemetry_quality["quality"],
                "prior": telemetry_prior,
                "weight": weights["telemetry"],
            },
            {
                "name": "history",
                "prediction": history_result.prediction,
                "quality": history_quality["quality"],
                "prior": history_prior,
                "weight": weights["history"],
            },
        ]

        # Determine dominant modality
        dominant_idx = np.argmax([m["weight"] for m in modalities_list])
        dominant_modality = modalities_list[dominant_idx]["name"]

        explanations = {
            "dominant_modality": dominant_modality,
            "reason": f"{dominant_modality} has highest fusion weight ({weights[dominant_modality]:.2f})",
        }

        uncertainty = {
            "cross_modal_disagreement": float(disagreement),
        }

        result = InferenceResult(
            asset_id=asset_id,
            prediction=prediction,
            modalities=modalities_list,
            uncertainty=uncertainty,
            explanations=explanations,
        )

        logger.info(
            f"Inference complete: {asset_id}, prediction={prediction['label']}, "
            f"calibrated_prob={calibrated_prob:.3f}, disagreement={disagreement:.3f}"
        )

        return result
