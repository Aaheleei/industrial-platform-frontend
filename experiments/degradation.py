"""
Degradation experiment engine: sweep dropout levels × degradation modes.

Grid: dropout ∈ {0%, 25%, 50%, 75%} × {noise, staleness, image_degradation, contradiction}
Repeat each cell n_trials times with different seeds.
Compare baseline (fixed averaging) vs. proposed (trust-gated fusion).
"""

import numpy as np
import pandas as pd
import json
import logging
from typing import Dict, List, Tuple
from pathlib import Path

from telemetry.generator import generate_sample
from history.generator import generate_asset_history
from pipeline.inference import InferencePipeline
from fusion.fusion import FusionEngine
from schemas.outputs import ModalityResult
from configs import load_config
from sklearn.metrics import roc_auc_score, f1_score

logger = logging.getLogger(__name__)


class DegradationExperiment:
    """Run degradation experiments comparing baseline vs. proposed."""

    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config = load_config(config_path)
        self.results = []

    def run_grid(
        self,
        output_path: str = "results/degradation_results.json",
    ) -> str:
        """
        Run full 4×4 grid sweep.

        Returns:
            Path to results JSON
        """
        dropout_levels = self.config["experiments"]["dropout_levels"]
        degradation_modes = self.config["experiments"]["degradation_modes"]
        n_trials = self.config["experiments"]["n_trials"]

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        trial_count = 0
        total_trials = len(dropout_levels) * len(degradation_modes) * n_trials * 2  # ×2 for baseline+proposed

        for dropout in dropout_levels:
            for degradation_mode in degradation_modes:
                for trial in range(n_trials):
                    seed = trial

                    # Run baseline (fixed averaging)
                    logger.info(
                        f"Trial {trial_count}/{total_trials}: "
                        f"dropout={dropout}, mode={degradation_mode}, trial={trial} (BASELINE)"
                    )
                    baseline_result = self._run_trial(
                        dropout_level=dropout,
                        degradation_mode=degradation_mode,
                        seed=seed,
                        system="baseline",
                    )
                    self.results.append(baseline_result)
                    trial_count += 1

                    # Run proposed (trust-gated)
                    logger.info(
                        f"Trial {trial_count}/{total_trials}: "
                        f"dropout={dropout}, mode={degradation_mode}, trial={trial} (PROPOSED)"
                    )
                    proposed_result = self._run_trial(
                        dropout_level=dropout,
                        degradation_mode=degradation_mode,
                        seed=seed,
                        system="proposed",
                    )
                    self.results.append(proposed_result)
                    trial_count += 1

        # Save results
        self._save_results(output_path)
        logger.info(f"Saved results to {output_path}")

        return output_path

    def _run_trial(
        self,
        dropout_level: float,
        degradation_mode: str,
        seed: int,
        system: str,
    ) -> Dict:
        """
        Run one trial: generate data with degradation, evaluate system.

        Args:
            dropout_level: Fraction of modality to drop [0, 1]
            degradation_mode: "noise" | "staleness" | "image_degradation" | "contradiction"
            seed: Random seed
            system: "baseline" | "proposed"

        Returns:
            Result dict with metrics
        """
        np.random.seed(seed)

        # Generate synthetic test data (50 samples, 50% anomalous)
        n_samples = 50
        n_anomalous = n_samples // 2

        predictions = []
        labels = []

        for i in range(n_samples):
            condition = "anomalous" if i < n_anomalous else "normal"
            label = 1 if condition == "anomalous" else 0

            # Generate degraded data
            image = np.random.rand(480, 640, 3)

            if degradation_mode == "noise":
                noise_level = dropout_level * 2.0  # Scale dropout to noise sigma
                telemetry = generate_sample(
                    condition=condition,
                    noise_level=noise_level,
                    seed=seed + i,
                )
            elif degradation_mode == "staleness":
                staleness_s = dropout_level * 600  # Scale dropout to staleness in seconds
                telemetry = generate_sample(
                    condition=condition,
                    staleness_seconds=staleness_s,
                    seed=seed + i,
                )
            elif degradation_mode == "image_degradation":
                # Blur the image by downsampling and upsampling
                if dropout_level > 0:
                    h, w = image.shape[:2]
                    scale = int(1 + dropout_level * 4)  # 1 to 5× downsampling
                    small = image[::scale, ::scale]
                    image = np.repeat(np.repeat(small, scale, axis=0), scale, axis=1)[:h, :w]
                telemetry = generate_sample(condition=condition, seed=seed + i)
            elif degradation_mode == "contradiction":
                # Generate contradictory modality predictions
                telemetry = generate_sample(condition=condition, seed=seed + i)
                if np.random.rand() < dropout_level:
                    condition = "normal" if condition == "anomalous" else "anomalous"
            else:
                telemetry = generate_sample(condition=condition, seed=seed + i)

            history = generate_asset_history(asset_id=f"asset_{i:03d}", seed=seed + i)

            # Get predictions from both modalities
            from vision.detector import VisionDetector
            from telemetry.detector import TelemetryDetector

            vision_detector = VisionDetector(device="cpu")
            telemetry_detector = TelemetryDetector()

            vision_pred = vision_detector.predict(image, self.config).prediction
            telemetry_pred = telemetry_detector.predict(
                telemetry.channels,
                telemetry.timestamps,
                self.config,
            ).prediction

            # Baseline: fixed averaging
            if system == "baseline":
                fused_pred = (vision_pred + telemetry_pred) / 2.0
            else:
                # Proposed: trust-gated (simplified for experiments)
                # Use equal priors for now
                from trust.gate import TrustGate, GateInputs

                gate_inputs = [
                    GateInputs(modality="vision", quality=0.85, prior=0.5),
                    GateInputs(modality="telemetry", quality=0.85, prior=0.5),
                ]
                gate = TrustGate(epsilon=1e-6)
                _, weights = gate.compute_full_gate(gate_inputs, self.config)

                fused_pred = weights["vision"] * vision_pred + weights["telemetry"] * telemetry_pred

            predictions.append(fused_pred)
            labels.append(label)

        predictions = np.array(predictions)
        labels = np.array(labels)

        # Compute metrics
        auroc = roc_auc_score(labels, predictions) if len(np.unique(labels)) > 1 else 0.5
        preds_binary = (predictions > 0.5).astype(int)
        f1 = f1_score(labels, preds_binary)

        result = {
            "dropout_level": float(dropout_level),
            "degradation_mode": degradation_mode,
            "system": system,
            "seed": seed,
            "auroc": float(auroc),
            "f1": float(f1),
        }

        return result

    def _save_results(self, output_path: str):
        """Save results as JSON."""
        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2)

    def compute_graceful_degradation_slope(self) -> Dict:
        """
        Fit linear regression: AUROC vs. dropout_level, per system.

        Returns:
            Dict with slopes for baseline and proposed
        """
        from sklearn.linear_model import LinearRegression

        slopes = {}

        for system in ["baseline", "proposed"]:
            system_results = [r for r in self.results if r["system"] == system]
            df = pd.DataFrame(system_results)

            if len(df) == 0:
                slopes[system] = 0.0
                continue

            # Group by dropout level, compute mean AUROC
            grouped = df.groupby("dropout_level")["auroc"].mean()

            X = grouped.index.values.reshape(-1, 1)
            y = grouped.values

            lr = LinearRegression()
            lr.fit(X, y)

            slopes[system] = float(lr.coef_[0])

        return slopes


def run_degradation_experiment(config_path: str = "configs/config.yaml") -> str:
    """
    Entry point for degradation experiments.

    Returns:
        Path to results JSON
    """
    exp = DegradationExperiment(config_path)
    results_path = exp.run_grid()
    slopes = exp.compute_graceful_degradation_slope()

    logger.info(f"Graceful degradation slopes: {slopes}")

    return results_path
