"""
Ablation study: run 8 variants on same held-out evaluation set.

Variants:
A. Vision only
B. Telemetry only
C. History only
D. Fixed equal-weight fusion
E. Quality-only fusion (q_i alone, prior fixed at 1)
F. Trust-prior-only fusion (p_i alone, quality fixed at 1)
G. Quality + trust-gated fusion (full gate, no calibration)
H. Full system: trust-gated fusion + calibration
"""

import numpy as np
import pandas as pd
import json
import logging
from typing import Dict, List
from pathlib import Path
from sklearn.metrics import roc_auc_score, f1_score, accuracy_score

from telemetry.generator import generate_sample, generate_batch
from history.generator import generate_asset_history, generate_asset_histories
from vision.detector import VisionDetector
from telemetry.detector import TelemetryDetector
from history.detector import HistoryDetector
from trust.gate import TrustGate, GateInputs
from fusion.fusion import FusionEngine
from calibration.temperature_scaling import TemperatureScaler
from calibration.metrics import compute_ece, compute_brier_score
from configs import load_config

logger = logging.getLogger(__name__)


class AblationStudy:
    """Run ablation study with 8 variants."""

    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config = load_config(config_path)
        self.vision_detector = VisionDetector(device="cpu")
        self.telemetry_detector = TelemetryDetector()
        self.history_detector = HistoryDetector()
        self.fusion_engine = FusionEngine()
        self.trust_gate = TrustGate(
            epsilon=self.config["trust"]["epsilon"],
            prior_bounds=tuple(self.config["trust"]["prior_bounds"]),
        )
        self.temperature_scaler = TemperatureScaler()

    def run_study(
        self,
        n_test_samples: int = 100,
        output_path: str = "results/ablation_results.json",
        seed: int = 42,
    ) -> str:
        """
        Run full ablation study on held-out test set.

        Returns:
            Path to results JSON
        """
        np.random.seed(seed)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Generate test set
        logger.info(f"Generating {n_test_samples} test samples...")
        n_anomalous = n_test_samples // 2

        test_data = []
        test_labels = []

        for i in range(n_test_samples):
            condition = "anomalous" if i < n_anomalous else "normal"
            label = 1 if condition == "anomalous" else 0

            image = np.random.rand(480, 640, 3)
            telemetry_sample = generate_sample(condition=condition, seed=seed + i)
            history = generate_asset_history(asset_id=f"asset_{i:03d}", seed=seed + i)

            test_data.append({
                "image": image,
                "telemetry": telemetry_sample,
                "history": history,
                "label": label,
            })
            test_labels.append(label)

        test_labels = np.array(test_labels)

        # Fit calibration on synthetic validation set
        logger.info("Fitting calibration scaler...")
        self._fit_calibration(seed=seed + 1000)

        # Run all 8 variants
        results = []
        variants = [
            ("A", "Vision only", self._variant_a),
            ("B", "Telemetry only", self._variant_b),
            ("C", "History only", self._variant_c),
            ("D", "Fixed equal-weight fusion", self._variant_d),
            ("E", "Quality-only fusion", self._variant_e),
            ("F", "Trust-prior-only fusion", self._variant_f),
            ("G", "Quality + trust-gated fusion", self._variant_g),
            ("H", "Full system + calibration", self._variant_h),
        ]

        for variant_id, variant_name, variant_fn in variants:
            logger.info(f"Running variant {variant_id}: {variant_name}")

            predictions = []
            for sample in test_data:
                pred = variant_fn(sample)
                predictions.append(pred)

            predictions = np.array(predictions)

            # Compute metrics
            auroc = roc_auc_score(test_labels, predictions)
            preds_binary = (predictions > 0.5).astype(int)
            f1 = f1_score(test_labels, preds_binary)
            accuracy = accuracy_score(test_labels, preds_binary)
            ece = compute_ece(predictions, test_labels)
            brier = compute_brier_score(predictions, test_labels)

            result = {
                "variant_id": variant_id,
                "variant_name": variant_name,
                "auroc": float(auroc),
                "f1": float(f1),
                "accuracy": float(accuracy),
                "ece": float(ece),
                "brier": float(brier),
            }
            results.append(result)

        # Save results
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

        logger.info(f"Saved ablation results to {output_path}")

        # Print summary table
        df = pd.DataFrame(results)
        logger.info(f"\nAblation Study Results:\n{df.to_string()}")

        return output_path

    def _fit_calibration(self, seed: int):
        """Fit temperature scaler on synthetic validation set."""
        np.random.seed(seed)
        n_val = 50

        val_logits = []
        val_labels = []

        for i in range(n_val):
            condition = "anomalous" if i < n_val // 2 else "normal"
            label = 1 if condition == "anomalous" else 0

            image = np.random.rand(480, 640, 3)
            telemetry_sample = generate_sample(condition=condition, seed=seed + i)
            history = generate_asset_history(asset_id=f"val_asset_{i:03d}", seed=seed + i)

            # Get predictions and compute logit
            pred = self._variant_g({
                "image": image,
                "telemetry": telemetry_sample,
                "history": history,
                "label": label,
            })
            logit = TemperatureScaler.logit(np.array([pred]))[0]

            val_logits.append(logit)
            val_labels.append(label)

        val_logits = np.array(val_logits)
        val_labels = np.array(val_labels)

        self.temperature_scaler.fit(val_logits, val_labels)

    def _get_modality_predictions(self, sample: Dict) -> Dict:
        """Get predictions from all three modalities."""
        image = sample["image"]
        telemetry = sample["telemetry"]
        history = sample["history"]

        vision_pred = self.vision_detector.predict(image, self.config).prediction
        telemetry_pred = self.telemetry_detector.predict(
            telemetry.channels,
            telemetry.timestamps,
            self.config,
        ).prediction
        history_pred = self.history_detector.predict(history, self.config).prediction

        return {
            "vision": vision_pred,
            "telemetry": telemetry_pred,
            "history": history_pred,
        }

    def _get_quality_scores(self, sample: Dict) -> Dict:
        """Get quality factors for all modalities."""
        from quality.estimator import estimate_quality

        image = sample["image"]
        telemetry = sample["telemetry"]
        history = sample["history"]

        vision_quality = estimate_quality("vision", image, self.config)["quality"]
        telemetry_quality = estimate_quality(
            "telemetry",
            (telemetry.channels, telemetry.timestamps),
            self.config,
        )["quality"]
        history_quality = estimate_quality("history", history, self.config)["quality"]

        return {
            "vision": vision_quality,
            "telemetry": telemetry_quality,
            "history": history_quality,
        }

    def _variant_a(self, sample: Dict) -> float:
        """Variant A: Vision only."""
        preds = self._get_modality_predictions(sample)
        return preds["vision"]

    def _variant_b(self, sample: Dict) -> float:
        """Variant B: Telemetry only."""
        preds = self._get_modality_predictions(sample)
        return preds["telemetry"]

    def _variant_c(self, sample: Dict) -> float:
        """Variant C: History only."""
        preds = self._get_modality_predictions(sample)
        return preds["history"]

    def _variant_d(self, sample: Dict) -> float:
        """Variant D: Fixed equal-weight fusion."""
        preds = self._get_modality_predictions(sample)
        return np.mean([preds["vision"], preds["telemetry"], preds["history"]])

    def _variant_e(self, sample: Dict) -> float:
        """Variant E: Quality-only fusion (q_i alone, prior fixed at 1)."""
        preds = self._get_modality_predictions(sample)
        quality = self._get_quality_scores(sample)

        # g_i = q_i * 1.0 (prior=1)
        gates = {m: quality[m] * 1.0 for m in quality}
        weights = self.trust_gate.compute_weights(gates)

        fused = sum(weights[m] * preds[m] for m in preds)
        return float(fused)

    def _variant_f(self, sample: Dict) -> float:
        """Variant F: Trust-prior-only fusion (p_i alone, quality fixed at 1)."""
        preds = self._get_modality_predictions(sample)

        # g_i = 1.0 * p_i (quality=1)
        priors = {"vision": 0.5, "telemetry": 0.5, "history": 0.5}  # Use fixed priors
        gates = {m: 1.0 * priors[m] for m in priors}
        weights = self.trust_gate.compute_weights(gates)

        fused = sum(weights[m] * preds[m] for m in preds)
        return float(fused)

    def _variant_g(self, sample: Dict) -> float:
        """Variant G: Quality + trust-gated fusion (full gate, no calibration)."""
        preds = self._get_modality_predictions(sample)
        quality = self._get_quality_scores(sample)

        priors = {"vision": 0.5, "telemetry": 0.5, "history": 0.5}  # Fixed priors
        gates = {m: quality[m] * priors[m] for m in quality}
        weights = self.trust_gate.compute_weights(gates)

        fused = sum(weights[m] * preds[m] for m in preds)
        return float(fused)

    def _variant_h(self, sample: Dict) -> float:
        """Variant H: Full system + calibration."""
        raw_prob = self._variant_g(sample)

        # Apply calibration
        logit = TemperatureScaler.logit(np.array([raw_prob]))[0]
        calibrated = self.temperature_scaler.transform(np.array([logit]))[0]

        return float(calibrated)


def run_ablation_study(config_path: str = "configs/config.yaml") -> str:
    """
    Entry point for ablation study.

    Returns:
        Path to results JSON
    """
    study = AblationStudy(config_path)
    return study.run_study()
