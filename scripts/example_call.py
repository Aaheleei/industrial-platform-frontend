#!/usr/bin/env python
"""
Example inference call: demonstrating end-to-end pipeline with synthetic data.
"""

import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.inference import InferencePipeline
from telemetry.generator import generate_sample
from history.generator import generate_asset_history


def main():
    print("=" * 80)
    print("Trust-Calibrated Multimodal Industrial Anomaly Intelligence")
    print("Example Inference Call")
    print("=" * 80)

    # Initialize pipeline
    print("\n[1/3] Initializing pipeline...")
    pipeline = InferencePipeline(
        config_path="configs/config.yaml",
        priors_store_path="priors_store.json",
    )
    print("✓ Pipeline initialized")

    # Generate synthetic inputs
    print("\n[2/3] Generating synthetic inputs...")
    asset_id = "asset_example_001"

    # Vision: synthetic image
    image = np.random.rand(480, 640, 3)
    print(f"  - Vision: {image.shape} image")

    # Telemetry: synthetic sensor stream
    telemetry_sample = generate_sample(condition="normal", noise_level=0.1, seed=42)
    telemetry = {
        "channels": telemetry_sample.channels,
        "timestamps": telemetry_sample.timestamps,
    }
    print(f"  - Telemetry: {len(telemetry['channels'])} channels, {len(telemetry['timestamps'])} samples")

    # History: synthetic maintenance record
    history = generate_asset_history(asset_id=asset_id, n_inspections=15, seed=42)
    print(f"  - History: {history.total_inspections} inspections, {history.anomalies_detected} anomalies")

    # Run inference
    print(f"\n[3/3] Running inference for {asset_id}...")
    result = pipeline.run_inference(image, telemetry, history, asset_id)

    # Print result
    print("\n" + "=" * 80)
    print("INFERENCE RESULT")
    print("=" * 80)

    print(f"\nAsset ID: {result.asset_id}")
    print(f"\nPrediction:")
    print(f"  - Label: {result.prediction['label']}")
    print(f"  - Raw Probability: {result.prediction['raw_probability']:.4f}")
    print(f"  - Calibrated Probability: {result.prediction['calibrated_probability']:.4f}")

    print(f"\nPer-Modality Details:")
    for mod in result.modalities:
        print(f"\n  {mod['name'].upper()}:")
        print(f"    - Prediction: {mod['prediction']:.4f}")
        print(f"    - Quality: {mod['quality']:.4f}")
        print(f"    - Prior: {mod['prior']:.4f}")
        print(f"    - Fusion Weight: {mod['weight']:.4f}")

    print(f"\nUncertainty:")
    print(f"  - Cross-Modal Disagreement: {result.uncertainty['cross_modal_disagreement']:.4f}")

    print(f"\nExplanations:")
    print(f"  - Dominant Modality: {result.explanations['dominant_modality']}")
    print(f"  - Reason: {result.explanations['reason']}")

    print("\n" + "=" * 80)
    print("JSON Output:")
    print("=" * 80)
    print(result.to_json())
    print("=" * 80)


if __name__ == "__main__":
    main()
