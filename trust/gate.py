"""
Trust gate: (quality, prior) -> gate value -> normalized weights.

Core formula: g_i = q_i * p_i(a)
Normalize: w_i = g_i / (Σ_j g_j + ε)

This is the central novel mechanism of the system.
"""

import numpy as np
import logging
from typing import Dict, List
from dataclasses import dataclass

from schemas.outputs import GateResult

logger = logging.getLogger(__name__)


@dataclass
class GateInputs:
    """Inputs to trust gate computation."""
    modality: str
    quality: float  # q_i in [0,1]
    prior: float  # p_i(a) in [0.05, 0.99]


class TrustGate:
    """
    Compute trust-weighted fusion gates from quality and priors.
    """

    def __init__(self, epsilon: float = 1e-6, prior_bounds: tuple = (0.05, 0.99)):
        """
        Initialize gate.

        Args:
            epsilon: Normalization denominator floor (prevents division by zero)
            prior_bounds: (min_prior, max_prior) - priors clipped to this range
        """
        self.epsilon = epsilon
        self.prior_bounds = prior_bounds

    def compute_gate_value(self, quality: float, prior: float) -> float:
        """
        Compute unnormalized gate value: g_i = q_i * p_i(a)

        Args:
            quality: Quality factor in [0,1]
            prior: Trust prior in [prior_bounds[0], prior_bounds[1]]

        Returns:
            Gate value (pre-normalization)
        """
        # Ensure prior is in bounds
        prior_clipped = np.clip(prior, self.prior_bounds[0], self.prior_bounds[1])
        gate = quality * prior_clipped
        return float(gate)

    def compute_weights(
        self,
        gates: Dict[str, float],
        available_modalities: List[str] = None,
    ) -> Dict[str, float]:
        """
        Normalize gate values to weights that sum to 1 (across available modalities).

        Args:
            gates: Dict of modality -> unnormalized gate value
            available_modalities: List of modality names (if None, all in gates)

        Returns:
            Dict of modality -> normalized weight w_i
        """
        if available_modalities is None:
            available_modalities = list(gates.keys())

        # Sum only over available modalities
        gate_sum = sum(gates.get(m, 0.0) for m in available_modalities if gates.get(m, 0.0) > 0)
        denominator = gate_sum + self.epsilon

        weights = {}
        for m in available_modalities:
            gate_val = gates.get(m, 0.0)
            weight = gate_val / denominator if gate_val > 0 else 0.0
            weights[m] = float(weight)

        return weights

    def compute_full_gate(
        self,
        inputs: List[GateInputs],
        config: Dict = None,
    ) -> tuple[List[GateResult], Dict[str, float]]:
        """
        Compute full gate pipeline for multiple modalities.

        Args:
            inputs: List of GateInputs (modality, quality, prior)
            config: Config dict (for epsilon, prior_bounds)

        Returns:
            (List of GateResult objects, Dict of final weights)
        """
        if config is None:
            config = {"trust": {}}

        trust_config = config.get("trust", {})
        epsilon = trust_config.get("epsilon", 1e-6)
        prior_bounds = tuple(trust_config.get("prior_bounds", [0.05, 0.99]))

        gate = TrustGate(epsilon=epsilon, prior_bounds=prior_bounds)

        # Step 1: Compute unnormalized gate values
        gates = {}
        gate_results = []

        for inp in inputs:
            gate_val = gate.compute_gate_value(inp.quality, inp.prior)
            gates[inp.modality] = gate_val

            gate_result = GateResult(
                modality=inp.modality,
                quality=inp.quality,
                prior=inp.prior,
                gate=gate_val,
                weight=0.0,  # Will be filled in next step
            )
            gate_results.append(gate_result)

        # Step 2: Normalize to weights
        modalities = [inp.modality for inp in inputs]
        weights = gate.compute_weights(gates, modalities)

        # Step 3: Update gate results with final weights
        for gr in gate_results:
            gr.weight = weights[gr.modality]

        # Validate weights sum to ~1
        weight_sum = sum(weights.values())
        assert abs(weight_sum - 1.0) < 1e-5, f"Weights sum to {weight_sum}, not 1.0"

        logger.debug(f"Gate computation: gates={gates}, weights={weights}")

        return gate_results, weights
