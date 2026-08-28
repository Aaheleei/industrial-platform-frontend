"""
Telemetry preprocessing: windowing, resampling, missing-value handling.
"""

import numpy as np
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


def preprocess_telemetry(
    channels: Dict[str, np.ndarray],
    window_size: int = 100,
    resample_rate: int = None,
) -> Dict[str, np.ndarray]:
    """
    Preprocess telemetry channels.

    Args:
        channels: Dict of channel_name -> 1D array
        window_size: Expected window size (validate/trim)
        resample_rate: If specified, resample to this rate (not used in prototype)

    Returns:
        Preprocessed channels (NaN handling applied)
    """
    preprocessed = {}

    for ch_name, signal in channels.items():
        # Ensure correct shape
        if len(signal.shape) != 1:
            signal = signal.flatten()

        # Trim or pad to window size (assume already correct in generator)
        if len(signal) > window_size:
            signal = signal[:window_size]
        elif len(signal) < window_size:
            # Pad with NaN
            signal = np.pad(signal, (0, window_size - len(signal)), constant_values=np.nan)

        preprocessed[ch_name] = signal

    return preprocessed


def compute_signal_to_noise_ratio(signal: np.ndarray) -> float:
    """
    Compute SNR for a channel (simple: var(signal) / var(noise)).
    Noise is estimated as high-frequency component (diff).

    Args:
        signal: 1D array (may contain NaN)

    Returns:
        SNR in [0, inf), or 0 if all NaN
    """
    # Remove NaN
    valid = signal[~np.isnan(signal)]

    if len(valid) < 2:
        return 0.0

    # Signal variance (mean-centered)
    signal_var = np.var(valid)

    # Noise estimate: first-order differences
    diffs = np.diff(valid)
    noise_var = np.var(diffs) if len(diffs) > 0 else 1e-6

    if noise_var < 1e-8:
        return 10.0  # Cap SNR at 10 if no noise

    snr = signal_var / noise_var
    return float(snr)


def get_missingness_rate(signal: np.ndarray) -> float:
    """Fraction of NaN values in signal."""
    if len(signal) == 0:
        return 1.0
    return float(np.isnan(signal).sum() / len(signal))


def compute_in_range_fraction(signal: np.ndarray, valid_range: Tuple[float, float]) -> float:
    """Fraction of non-NaN values that fall within valid range."""
    valid = signal[~np.isnan(signal)]
    if len(valid) == 0:
        return 0.0
    in_range = np.sum((valid >= valid_range[0]) & (valid <= valid_range[1]))
    return float(in_range / len(valid))


def compute_drift_penalty(signal: np.ndarray, drift_penalty_scale: float = 1.0) -> float:
    """
    Estimate linear drift and return penalty (exponential decay).

    Args:
        signal: 1D array (may contain NaN)
        drift_penalty_scale: Scale factor for drift impact

    Returns:
        Penalty in [0, 1], where 0 = high drift, 1 = no drift
    """
    valid = signal[~np.isnan(signal)]

    if len(valid) < 2:
        return 1.0

    # Fit linear trend
    indices = np.arange(len(valid))
    try:
        coeffs = np.polyfit(indices, valid, 1)
        drift_magnitude = abs(coeffs[0])
    except:
        drift_magnitude = 0.0

    # Exponential decay penalty
    penalty = np.exp(-drift_magnitude / drift_penalty_scale)
    return float(max(penalty, 0.0))


def compute_staleness_penalty(timestamp: float, current_time: float, half_life_s: float = 300) -> float:
    """
    Compute staleness penalty based on lag (current_time - timestamp).

    Args:
        timestamp: Reported timestamp (UTC epoch)
        current_time: Current time (UTC epoch)
        half_life_s: Half-life for exponential decay

    Returns:
        Penalty in [0, 1], where 1 = fresh, 0 = very stale
    """
    staleness_s = max(current_time - timestamp, 0.0)
    penalty = np.exp(-staleness_s / half_life_s)
    return float(max(penalty, 0.0))
