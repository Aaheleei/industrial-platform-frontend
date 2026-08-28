#!/usr/bin/env python
"""
Diagnostic script: evaluate individual detectors on synthetic balanced dataset.
Helps identify which modality/detector is underperforming.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from sklearn.metrics import roc_auc_score, f1_score, accuracy_score, confusion_matrix
import logging

from telemetry.generator import generate_sample
from history.generator import generate_asset_history
from vision.detector import VisionDetector
from telemetry.detector import TelemetryDetector
from history.detector import HistoryDetector
from configs import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def diagnose_detectors(n_test: int = 100, seed: int = 42):
    """
    Evaluate each detector independently on balanced synthetic data.
    """
    np.random.seed(seed)
    config = load_config("configs/config.yaml")

    # Initialize detectors
    vision_det = VisionDetector(device="cpu")
    telemetry_det = TelemetryDetector()
    history_det = HistoryDetector()

    # Generate balanced test set
    n_anomalous = n_test // 2
    test_labels = np.array([1] * n_anomalous + [0] * (n_test - n_anomalous))

    print(f"\n{'='*70}")
    print(f"DETECTOR DIAGNOSTIC REPORT")
    print(f"{'='*70}")
    print(f"Test set: {n_test} samples ({n_anomalous} anomalous, {n_test - n_anomalous} normal)")
    print(f"{'='*70}\n")

    detectors = [
        ("Vision", lambda s, c: vision_det.predict(s, c).prediction, "image"),
        ("Telemetry", lambda s, c: telemetry_det.predict(s[0], s[1], c).prediction, "telemetry"),
        ("History", lambda s, c: history_det.predict(s, c).prediction, "history"),
    ]

    for det_name, det_fn, data_key in detectors:
        predictions = []

        for i in range(n_test):
            condition = "anomalous" if i < n_anomalous else "normal"

            # Generate data for this modality
            if data_key == "image":
                # Random images - this is the problem!
                data = np.random.rand(480, 640, 3)
            elif data_key == "telemetry":
                sample = generate_sample(condition=condition, seed=seed + i)
                data = (sample.channels, sample.timestamps)
            else:  # history
                data = generate_asset_history(asset_id=f"asset_{i:03d}", seed=seed + i)

            try:
                pred = det_fn(data, config)
                predictions.append(pred)
            except Exception as e:
                logger.error(f"Error in {det_name} detector: {e}")
                predictions.append(0.5)  # Default to uncertain

        predictions = np.array(predictions)

        # Compute metrics
        try:
            auroc = roc_auc_score(test_labels, predictions)
        except:
            auroc = 0.5  # Can't compute if only one class predicted

        preds_binary = (predictions > 0.5).astype(int)
        f1 = f1_score(test_labels, preds_binary, zero_division=0)
        acc = accuracy_score(test_labels, preds_binary)

        # Confusion matrix
        tn, fp, fn, tp = confusion_matrix(test_labels, preds_binary).ravel()
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0

        print(f"{det_name:15} Detector:")
        print(f"  AUROC:        {auroc:.4f}   (Random: 0.5000)")
        print(f"  Accuracy:     {acc:.4f}")
        print(f"  F1-Score:     {f1:.4f}")
        print(f"  Sensitivity:  {sensitivity:.4f}  (TP / (TP + FN))")
        print(f"  Specificity:  {specificity:.4f}  (TN / (TN + FP))")
        print(f"  Predictions:  min={predictions.min():.4f}, mean={predictions.mean():.4f}, max={predictions.max():.4f}")
        print(f"  Classes:      {np.unique(preds_binary)} (predicted)")
        print()


if __name__ == "__main__":
    diagnose_detectors(n_test=100, seed=42)
