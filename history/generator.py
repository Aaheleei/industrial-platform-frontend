"""
Synthetic history/maintenance record generator for per-asset inspection history.
"""

import numpy as np
from typing import Dict, List, Literal
from dataclasses import dataclass, asdict
import datetime


@dataclass
class InspectionRecord:
    """One historical inspection/maintenance event."""
    asset_id: str
    timestamp: str  # ISO 8601
    anomaly_detected: bool  # ground truth label
    inspection_type: Literal["routine", "maintenance", "urgent"]  # event type


@dataclass
class AssetHistory:
    """Complete history record for one asset."""
    asset_id: str
    inspections: List[InspectionRecord]
    total_inspections: int
    anomalies_detected: int


def generate_asset_history(
    asset_id: str,
    n_inspections: int = 20,
    anomaly_frequency: float = 0.3,
    seed: int = None,
) -> AssetHistory:
    """
    Generate a synthetic historical record for an asset.

    Args:
        asset_id: identifier for the asset
        n_inspections: number of historical inspection records
        anomaly_frequency: fraction of inspections that detected anomalies
        seed: random seed for reproducibility

    Returns:
        AssetHistory with inspection records
    """
    if seed is not None:
        np.random.seed(seed)

    inspections = []
    n_anomalies = int(n_inspections * anomaly_frequency)

    # Generate timestamps spread over the last 2 years
    now = datetime.datetime.utcnow()
    timestamps = sorted([
        now - datetime.timedelta(days=int(np.random.uniform(0, 730)))
        for _ in range(n_inspections)
    ])

    # Assign anomaly labels (roughly anomaly_frequency fraction are True)
    anomaly_labels = [True] * n_anomalies + [False] * (n_inspections - n_anomalies)
    np.random.shuffle(anomaly_labels)

    for i, (ts, anomaly) in enumerate(zip(timestamps, anomaly_labels)):
        inspection_type = np.random.choice(
            ["routine", "maintenance", "urgent"],
            p=[0.6, 0.3, 0.1]
        )
        inspections.append(InspectionRecord(
            asset_id=asset_id,
            timestamp=ts.isoformat() + "Z",
            anomaly_detected=anomaly,
            inspection_type=inspection_type,
        ))

    return AssetHistory(
        asset_id=asset_id,
        inspections=inspections,
        total_inspections=n_inspections,
        anomalies_detected=n_anomalies,
    )


def generate_asset_histories(
    n_assets: int = 10,
    n_inspections_per_asset: int = 20,
    anomaly_frequency: float = 0.3,
    seed: int = None,
) -> Dict[str, AssetHistory]:
    """Generate histories for multiple assets."""
    if seed is not None:
        np.random.seed(seed)

    histories = {}
    for i in range(n_assets):
        asset_id = f"asset_{i:03d}"
        histories[asset_id] = generate_asset_history(
            asset_id=asset_id,
            n_inspections=n_inspections_per_asset,
            anomaly_frequency=anomaly_frequency,
            seed=seed + i if seed is not None else None,
        )

    return histories
