#!/usr/bin/env python
"""
Quick degradation experiment: 1 trial per condition (verification run).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.degradation import DegradationExperiment
from configs import load_config

def main():
    config = load_config("configs/config.yaml")

    # Override n_trials to 1 for quick run
    config["experiments"]["n_trials"] = 1

    print("Running quick degradation experiment (1 trial per condition)...")
    print(f"Grid: {len(config['experiments']['dropout_levels'])} × {len(config['experiments']['degradation_modes'])} conditions")
    print(f"Expected: ~{len(config['experiments']['dropout_levels']) * len(config['experiments']['degradation_modes']) * 2} trials\n")

    experiment = DegradationExperiment("configs/config.yaml")

    # Manually set n_trials for this run
    experiment.config["experiments"]["n_trials"] = 1

    results_path = experiment.run_grid()
    print(f"\nResults saved to: {results_path}")

if __name__ == "__main__":
    main()
