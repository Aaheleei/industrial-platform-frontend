#!/usr/bin/env python
"""
Run ablation study: 8 variants on same held-out eval set.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.ablation import run_ablation_study
from configs import load_config


def main():
    config = load_config("configs/config.yaml")
    print("Running ablation study...")
    print(f"Config: {config['experiments']}")

    results_path = run_ablation_study()
    print(f"\nResults saved to: {results_path}")


if __name__ == "__main__":
    main()
