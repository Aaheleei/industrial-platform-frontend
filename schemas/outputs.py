"""
Data contracts for all modules.
Every module consumes and produces only these types.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List
import json


@dataclass
class ModalityResult:
    """Output of a single modality detector (vision, telemetry, or history)."""
    name: str  # "vision" | "telemetry" | "history"
    prediction: float  # anomaly probability, [0,1]
    raw_score: float  # pre-sigmoid / pre-normalization score, if applicable

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class QualityResult:
    """Quality of input evidence for a single modality.

    Invariant: quality is computed from *input properties only*, never from detector output.
    Quality is answerable without knowing what the model predicted.
    """
    quality: float  # overall quality in [0,1]
    factors: Dict[str, float]  # named sub-signals, each in [0,1], e.g. {"blur": 0.94}

    def __post_init__(self):
        assert 0.0 <= self.quality <= 1.0, f"quality must be in [0,1], got {self.quality}"
        for name, val in self.factors.items():
            assert 0.0 <= val <= 1.0, f"factor {name}={val} must be in [0,1]"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GateResult:
    """Per-modality gating computation: quality * prior -> weight."""
    modality: str
    quality: float
    prior: float
    gate: float  # g_i, pre-normalization
    weight: float  # w_i, post-normalization, sums to 1 across modalities

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FusionResult:
    """Result of fusing multiple modality predictions."""
    fused_score: float  # weighted average of modality predictions, [0,1]
    weights: Dict[str, float]  # modality -> w_i
    cross_modal_disagreement: float  # max(predictions) - min(predictions) across available modalities

    def __post_init__(self):
        assert 0.0 <= self.fused_score <= 1.0, f"fused_score must be in [0,1], got {self.fused_score}"
        assert abs(sum(self.weights.values()) - 1.0) < 1e-5, \
            f"weights must sum to ~1.0, got {sum(self.weights.values())}"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class InferenceResult:
    """Final output of the inference pipeline."""
    asset_id: str
    prediction: Dict  # {"label": str, "raw_probability": float, "calibrated_probability": float}
    modalities: List[Dict]  # per-modality: name, prediction, quality, prior, weight
    uncertainty: Dict  # {"cross_modal_disagreement": float}
    explanations: Dict  # {"dominant_modality": str, "reason": str}

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class FeedbackEvent:
    """User feedback on a prediction for trust prior update."""
    prediction_correct: bool
    modality_flagged_reliable: Optional[bool]  # explicit modality reliability flag, if provided
    predicted_confidence: float  # confidence of the fused prediction at feedback time
    timestamp: str  # ISO 8601, e.g. "2024-01-10T12:00:00Z"

    def to_dict(self) -> dict:
        return asdict(self)
