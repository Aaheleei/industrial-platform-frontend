"""
History feature extraction for per-asset inspection records.
"""

import numpy as np
from typing import Dict, List
import datetime
from history.generator import AssetHistory, InspectionRecord


def extract_recency_feature(history: AssetHistory) -> float:
    """
    Recency: how recently was the asset inspected?
    Formula: exp(-Δt_days / recency_tau_days)

    Args:
        history: AssetHistory object

    Returns:
        recency factor in [0, 1]
    """
    if not history.inspections:
        return 0.0

    # Get time of last inspection
    last_inspection = max(history.inspections, key=lambda x: x.timestamp)
    last_ts = datetime.datetime.fromisoformat(last_inspection.timestamp.replace("Z", "+00:00"))
    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

    delta_days = (now - last_ts).days
    recency_tau_days = 30  # From config (will parameterize)

    recency = np.exp(-delta_days / recency_tau_days)
    return float(max(recency, 0.0))


def extract_record_count_feature(history: AssetHistory, count_ref: float = 20) -> float:
    """
    Record saturation: how many inspections has this asset had?
    Formula: min(record_count / count_ref, 1.0)

    Args:
        history: AssetHistory object
        count_ref: Reference count for normalization

    Returns:
        saturating factor in [0, 1]
    """
    count = history.total_inspections
    factor = min(count / count_ref, 1.0)
    return float(factor)


def extract_temporal_coverage_feature(history: AssetHistory, n_periods: int = 4) -> float:
    """
    Temporal coverage: are inspections regularly distributed?
    Formula: inspections_in_last_N_periods / expected_inspections

    Args:
        history: AssetHistory object
        n_periods: Number of periods to check (default: 4 quarters)

    Returns:
        coverage factor in [0, 1]
    """
    if not history.inspections:
        return 0.0

    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    period_length_days = 365.0 / n_periods

    # Count inspections in each period
    recent_count = 0
    for inspection in history.inspections:
        insp_ts = datetime.datetime.fromisoformat(inspection.timestamp.replace("Z", "+00:00"))
        delta_days = (now - insp_ts).days
        if delta_days <= period_length_days * n_periods:
            recent_count += 1

    expected = history.total_inspections / max(n_periods, 1)
    coverage = min(recent_count / max(expected, 1), 1.0)
    return float(coverage)


def extract_consistency_feature(history: AssetHistory, recent_window: int = 5) -> float:
    """
    Consistency: do recent labels agree?
    Formula: 1 - std(recent_labels), or explicit rolling-agreement measure

    Args:
        history: AssetHistory object
        recent_window: Number of recent inspections to consider

    Returns:
        consistency factor in [0, 1]
    """
    if not history.inspections:
        return 0.5  # Neutral if no data

    # Get recent inspections
    recent = sorted(history.inspections, key=lambda x: x.timestamp)[-recent_window:]
    labels = np.array([1.0 if insp.anomaly_detected else 0.0 for insp in recent])

    if len(labels) < 2:
        return 1.0  # Trivially consistent if only 1 sample

    # Consistency = 1 - normalized std
    std_labels = np.std(labels)
    consistency = 1.0 - std_labels  # std is [0, 0.5] for binary, so consistency is [0.5, 1.0]
    return float(max(consistency, 0.0))


def extract_anomaly_frequency_feature(history: AssetHistory) -> float:
    """
    Anomaly frequency: how often does this asset have anomalies?
    Formula: anomalies_detected / total_inspections

    Args:
        history: AssetHistory object

    Returns:
        frequency factor in [0, 1]
    """
    if history.total_inspections == 0:
        return 0.0

    freq = history.anomalies_detected / history.total_inspections
    return float(freq)


def extract_all_features(history: AssetHistory, config: Dict = None) -> Dict[str, float]:
    """
    Extract all history features.

    Args:
        history: AssetHistory object
        config: Config dict with history parameters

    Returns:
        Dict of feature_name -> value (all in [0, 1])
    """
    if config is None:
        config = {"history": {}}

    history_config = config.get("history", {})
    recency_tau_days = history_config.get("recency_tau_days", 30)
    count_ref = history_config.get("count_ref", 20)

    features = {
        "recency": extract_recency_feature(history),
        "record_count": extract_record_count_feature(history, count_ref),
        "temporal_coverage": extract_temporal_coverage_feature(history),
        "consistency": extract_consistency_feature(history),
        "anomaly_frequency": extract_anomaly_frequency_feature(history),
    }

    # Verify all in [0, 1]
    for name, val in features.items():
        assert 0.0 <= val <= 1.0, f"Feature {name}={val} out of bounds"

    return features
