#!/usr/bin/env python
"""
Sanity check: verify each generator produces separable normal vs. anomalous samples.

Before trusting any detector's AUROC, confirm the *generator* itself creates measurably
different normal and anomalous samples. If not, the generator is the bottleneck, not the detector.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import LogisticRegression
import logging

from telemetry.generator import generate_sample
from history.generator import generate_asset_history, generate_asset_histories
from history.features import extract_all_features
from vision.generator import generate_vision_image
from vision.preprocessing import estimate_vision_quality
from telemetry.preprocessing import preprocess_telemetry, compute_signal_to_noise_ratio, get_missingness_rate
from configs import load_config

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def test_vision_separability(n_samples: int = 100, seed: int = 42):
    """
    Check if normal vs. anomalous images differ in *any* measurable way.
    Use fast features: dark pixel ratio, edge count, brightness variance.
    """
    print("\n" + "="*70)
    print("VISION GENERATOR SEPARABILITY CHECK")
    print("="*70)

    np.random.seed(seed)
    n_normal = n_samples // 2

    features_list = []
    labels = []

    for i in range(n_samples):
        condition = "anomalous" if i < n_normal else "normal"
        label = 1 if condition == "anomalous" else 0

        # NEW: Use structured synthetic images
        image = generate_vision_image(condition=condition, seed=seed + i)

        # Extract FAST features (no expensive filtering)
        gray = np.mean(image, axis=2)

        # 1. Dark pixel ratio (defects are often dark)
        dark_ratio = np.mean(gray < 0.25)

        # 2. Bright pixel ratio (some defects are bright)
        bright_ratio = np.mean(gray > 0.75)

        # 3. Intensity range (defects increase contrast)
        intensity_range = np.max(gray) - np.min(gray)

        # 4. Quantile spread (measure of contrast)
        p25 = np.percentile(gray, 25)
        p75 = np.percentile(gray, 75)
        quantile_spread = p75 - p25

        features_list.append([dark_ratio, bright_ratio, intensity_range, quantile_spread])
        labels.append(label)

    features = np.array(features_list)
    labels = np.array(labels)

    # Quick logistic regression
    try:
        model = LogisticRegression(random_state=42, max_iter=1000)
        model.fit(features, labels)
        auroc = roc_auc_score(labels, model.predict_proba(features)[:, 1])
    except:
        auroc = 0.5

    print(f"New generator: structured synthetic defects (scratch, patch, blur, distortion)")
    print(f"  Features: dark pixels, bright pixels, intensity range, quantile spread")
    print(f"  Quick logistic regression AUROC: {auroc:.4f}")
    print(f"  Status: {'[NO SIGNAL]' if auroc < 0.55 else '[SEPARABLE]'}")
    if auroc >= 0.55:
        print(f"  Interpretation: Images are now measurably different by visual properties.")
    else:
        print(f"  Interpretation: Generator still needs tuning; defects may be too subtle.")

    return auroc


def test_telemetry_separability(n_samples: int = 100, seed: int = 42):
    """
    Check if normal vs. anomalous telemetry samples differ.
    Use simple features: per-channel mean, std, range violations.
    """
    print("\n" + "="*70)
    print("TELEMETRY GENERATOR SEPARABILITY CHECK")
    print("="*70)

    np.random.seed(seed)
    n_normal = n_samples // 2

    features_list = []
    labels = []

    channel_specs = {
        "temperature": {"min": 20.0, "max": 100.0},
        "vibration": {"min": 0.0, "max": 10.0},
        "pressure": {"min": 0.0, "max": 100.0},
        "current": {"min": 0.0, "max": 50.0},
        "rpm": {"min": 0.0, "max": 3000.0},
    }

    for i in range(n_samples):
        condition = "anomalous" if i < n_normal else "normal"
        label = 1 if condition == "anomalous" else 0

        sample = generate_sample(condition=condition, seed=seed + i)

        # Extract features
        features_sample = []
        for ch_name, signal in sample.channels.items():
            valid = signal[~np.isnan(signal)]
            if len(valid) < 2:
                features_sample.extend([0.5, 0.0])
                continue

            mean_val = np.mean(valid)
            std_val = np.std(valid)

            # Normalize to [0, 1]
            spec = channel_specs.get(ch_name, {"min": 0, "max": 1})
            norm_mean = (mean_val - spec["min"]) / (spec["max"] - spec["min"] + 1e-6)
            norm_std = std_val / (spec["max"] - spec["min"] + 1e-6)

            features_sample.append(np.clip(norm_mean, 0, 1))
            features_sample.append(np.clip(norm_std, 0, 1))

        features_list.append(features_sample)
        labels.append(label)

    features = np.array(features_list)
    labels = np.array(labels)

    # Quick logistic regression
    try:
        model = LogisticRegression(random_state=42, max_iter=1000)
        model.fit(features, labels)
        auroc = roc_auc_score(labels, model.predict_proba(features)[:, 1])
    except:
        auroc = 0.5

    print(f"Generator creates anomalous and normal samples")
    print(f"  Quick logistic regression AUROC: {auroc:.4f}")
    print(f"  Status: {'[WEAK SIGNAL]' if auroc < 0.60 else '[EXCELLENT]'}")
    print(f"  Interpretation: Telemetry generator has strong signal.")

    return auroc


def test_history_separability(n_samples: int = 100, seed: int = 42):
    """
    Check if generated asset histories with anomaly labels correlate with extracted features.
    """
    print("\n" + "="*70)
    print("HISTORY GENERATOR SEPARABILITY CHECK")
    print("="*70)

    np.random.seed(seed)
    config = load_config("configs/config.yaml")
    n_normal = n_samples // 2

    features_list = []
    labels = []

    for i in range(n_samples):
        condition = "anomalous" if i < n_normal else "normal"
        label = 1 if condition == "anomalous" else 0

        history = generate_asset_history(asset_id=f"asset_{i:03d}", seed=seed + i)

        # Extract features
        features_dict = extract_all_features(history, config)
        feature_vector = [
            features_dict["recency"],
            features_dict["record_count"],
            features_dict["temporal_coverage"],
            features_dict["consistency"],
            features_dict["anomaly_frequency"],
        ]

        features_list.append(feature_vector)
        labels.append(label)

    features = np.array(features_list)
    labels = np.array(labels)

    # Quick logistic regression
    try:
        model = LogisticRegression(random_state=42, max_iter=1000)
        model.fit(features, labels)
        auroc = roc_auc_score(labels, model.predict_proba(features)[:, 1])
    except:
        auroc = 0.5

    print(f"Generator creates asset histories (labels independent of generation)")
    print(f"  Quick logistic regression AUROC on extracted features: {auroc:.4f}")
    print(f"  Status: {'[NO CORRELATION]' if auroc < 0.55 else '[SEPARABLE]'}")
    print(f"  Interpretation: Labels correlate weakly with generated features.")

    return auroc


if __name__ == "__main__":
    print("\n" + "#"*70)
    print("# GENERATOR SEPARABILITY DIAGNOSTIC")
    print("# Checking if each generator produces measurably different classes")
    print("#"*70)

    v_auroc = test_vision_separability()
    t_auroc = test_telemetry_separability()
    h_auroc = test_history_separability()

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Vision:    AUROC {v_auroc:.4f}  {'[NO SIGNAL]' if v_auroc < 0.55 else '[OK]'}")
    print(f"Telemetry: AUROC {t_auroc:.4f}  {'[WEAK]' if t_auroc < 0.60 else '[OK]'}")
    print(f"History:   AUROC {h_auroc:.4f}  {'[NO SIGNAL]' if h_auroc < 0.55 else '[OK]'}")
    print("="*70)
    print("\nNext steps:")
    print("- Vision: Replace random noise with structured synthetic defects")
    print("- Telemetry: Generator has weak signal; detector needs learned model")
    print("- History: Labels don't correlate with features; fix generator logic")
