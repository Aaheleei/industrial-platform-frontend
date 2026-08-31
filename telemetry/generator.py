"""
Synthetic telemetry generator for normal/anomalous industrial sensor streams.
Supports independent composition of degradation modes: noise, missing data, drift, staleness, etc.
"""

import numpy as np
from typing import Dict, List, Literal, Tuple
from dataclasses import dataclass
import datetime


@dataclass
class TelemetrySample:
    """One telemetry sample snapshot."""
    condition: Literal["normal", "anomalous"]
    channels: Dict[str, np.ndarray]  # channel_name -> 1D array of samples
    timestamps: np.ndarray  # UTC timestamps for each sample
    ground_truth: int  # 0=normal, 1=anomalous


CHANNEL_SPECS = {
    "temperature": {"min": 20.0, "max": 100.0, "normal_mean": 60.0, "normal_std": 5.0},
    "vibration": {"min": 0.0, "max": 10.0, "normal_mean": 1.0, "normal_std": 0.3},
    "pressure": {"min": 0.0, "max": 100.0, "normal_mean": 50.0, "normal_std": 3.0},
    "current": {"min": 0.0, "max": 50.0, "normal_mean": 25.0, "normal_std": 2.0},
    "rpm": {"min": 0.0, "max": 3000.0, "normal_mean": 1500.0, "normal_std": 100.0},
}


def generate_sample(
    condition: Literal["normal", "anomalous"] = "normal",
    noise_level: float = 0.0,
    missing_rate: float = 0.0,
    drift: float = 0.0,
    staleness_seconds: float = 0.0,
    range_violation: bool = False,
    spike_probability: float = 0.0,
    window_size: int = 100,
    seed: int = None,
) -> TelemetrySample:
    """
    Generate a synthetic telemetry sample with independent degradation modes.

    Args:
        condition: "normal" or "anomalous"
        noise_level: Gaussian noise σ added to each channel
        missing_rate: fraction of samples dropped/NaN'd per channel
        drift: linear drift added over the window
        staleness_seconds: how far the reported timestamp lags real time
        range_violation: if True, force one channel outside its physical range
        spike_probability: chance of an abnormal spike per sample
        window_size: number of samples in the window
        seed: random seed for reproducibility

    Returns:
        TelemetrySample with channels, timestamps, condition, ground_truth
    """
    if seed is not None:
        np.random.seed(seed)

    channels = {}
    ground_truth = 1 if condition == "anomalous" else 0

    # Generate base signals
    for ch_name, spec in CHANNEL_SPECS.items():
        if condition == "normal":
            signal = np.random.normal(spec["normal_mean"], spec["normal_std"], window_size)
        else:
            # Anomalous: mean shifts, variance increases
            signal = np.random.normal(
                spec["normal_mean"] + 0.3 * (spec["max"] - spec["min"]),
                spec["normal_std"] * 2.0,
                window_size
            )

        # Add drift
        if drift != 0.0:
            signal += np.linspace(0, drift, window_size)

        # Add noise
        if noise_level > 0:
            signal += np.random.normal(0, noise_level, window_size)

        # Add spikes
        if spike_probability > 0:
            spike_indices = np.random.choice(
                window_size,
                int(window_size * spike_probability),
                replace=False
            )
            for idx in spike_indices:
                signal[idx] = np.random.uniform(spec["min"], spec["max"])

        # Apply range violation to one channel if requested
        if range_violation and ch_name == "temperature":
            signal[window_size // 2] = spec["max"] + 10

        # Clip to valid range
        signal = np.clip(signal, spec["min"], spec["max"])

        # Apply missing data
        if missing_rate > 0:
            missing_indices = np.random.choice(
                window_size,
                int(window_size * missing_rate),
                replace=False
            )
            signal[missing_indices] = np.nan

        channels[ch_name] = signal

    # Generate timestamps (stale if requested)
    base_time = datetime.datetime.utcnow()
    timestamps = np.array([
        (base_time - datetime.timedelta(seconds=staleness_seconds) +
         datetime.timedelta(seconds=i)).timestamp()
        for i in range(window_size)
    ])

    return TelemetrySample(
        condition=condition,
        channels=channels,
        timestamps=timestamps,
        ground_truth=ground_truth,
    )


def generate_batch(
    n_samples: int,
    condition_ratio: float = 0.5,
    noise_level: float = 0.0,
    missing_rate: float = 0.0,
    drift: float = 0.0,
    staleness_seconds: float = 0.0,
    range_violation: bool = False,
    spike_probability: float = 0.0,
    seed: int = None,
) -> List[TelemetrySample]:
    """Generate a batch of telemetry samples with specified degradation."""
    if seed is not None:
        np.random.seed(seed)

    n_anomalous = int(n_samples * condition_ratio)
    samples = []

    for i in range(n_samples):
        condition = "anomalous" if i < n_anomalous else "normal"
        sample = generate_sample(
            condition=condition,
            noise_level=noise_level,
            missing_rate=missing_rate,
            drift=drift,
            staleness_seconds=staleness_seconds,
            range_violation=range_violation,
            spike_probability=spike_probability,
            seed=seed + i if seed is not None else None,
        )
        samples.append(sample)

    return samples
