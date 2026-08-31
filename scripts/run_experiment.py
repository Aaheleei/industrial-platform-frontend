#!/usr/bin/env python
"""
Run degradation experiments: 4×4 grid sweep.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.degradation import run_degradation_experiment
from configs import load_config


def main():
    config = load_config("configs/config.yaml")
    print("Running degradation experiments...")
    print(f"Config: {config['experiments']}")

    results_path = run_degradation_experiment()
    print(f"\nResults saved to: {results_path}")


if __name__ == "__main__":
    main()
