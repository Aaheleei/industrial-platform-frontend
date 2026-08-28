# Trust-Calibrated Multimodal Industrial Anomaly Intelligence — ML Core

## 1. Research Problem & Hypothesis

When multiple industrial modalities (vision, telemetry, historical records) provide evidence of an anomaly, the system should:

**(a)** Estimate the reliability of each modality **independently of its predicted class** — quality is an input property, not model confidence.

**(b)** Dynamically convert that reliability into a fusion weight, rather than averaging blindly.

**(c)** Fuse evidence accordingly: `z_fused = Σ_i w_i * p_i`, where weights depend on both current evidence quality and persistent trust priors.

**(d)** Report a confidence that is **honest (calibrated)** about how much reliable evidence it had — not overconfident when modalities disagree or are degraded.

**(e)** Adjust modality/asset trust over time using human correction feedback, with safeguards against drift and cascading failures.

This is a research prototype, not a production system. Every design choice prioritizes proving the hypothesis over engineering robustness.

---

## 2. Architecture Diagram

```
INPUT (image, telemetry, history)
    ↓
┌─────────────────────────────────────────────────────────────┐
│                    MODALITY LAYER                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Vision           Telemetry           History               │
│  Detector         Detector            Detector              │
│  (ResNet18)       (z-score)           (Logistic Reg)       │
│      ↓                ↓                    ↓                │
│  ModalityResult   ModalityResult      ModalityResult        │
│  p_vision=0.7     p_telemetry=0.3    p_history=0.5         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│                    QUALITY LAYER                            │
├─────────────────────────────────────────────────────────────┤
│  [Input properties ONLY, not model predictions]             │
│  Vision Quality         Telemetry Quality                   │
│  (blur, exposure, ...)  (missingness, noise, ...)           │
│  q_vision=0.91         q_telemetry=0.32                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│                    TRUST LAYER                              │
├─────────────────────────────────────────────────────────────┤
│  Prior Store (persisted)                                    │
│  p_prior(vision|asset)=0.75                                │
│  p_prior(telemetry|asset)=0.69                             │
│                                                              │
│  Trust Gate: g_i = q_i * p_prior_i                         │
│  g_vision = 0.91 * 0.75 = 0.68                            │
│  g_telemetry = 0.32 * 0.69 = 0.22                         │
│                                                              │
│  Normalize: w_i = g_i / (Σ_j g_j + ε)                      │
│  w_vision = 0.75, w_telemetry = 0.25                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│                    FUSION LAYER                             │
├─────────────────────────────────────────────────────────────┤
│  z_fused = 0.75 * 0.7 + 0.25 * 0.3 = 0.60                 │
│  disagreement = max(p_i) - min(p_i) = 0.4                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│                  CALIBRATION LAYER                          │
├─────────────────────────────────────────────────────────────┤
│  logit(0.60) → T-scale / T=1.2 → sigmoid → 0.58           │
│  Calibrated probability reflects actual reliability         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
    ↓
OUTPUT (InferenceResult)
  - prediction: {"label": "anomalous", "calibrated_probability": 0.58}
  - modalities: [per-modality detail]
  - uncertainty: {"cross_modal_disagreement": 0.4}
  - explanations: {"dominant_modality": "vision", ...}
```

---

## 3. Mathematical Formulation

### Quality Estimation (Section 7)

**Invariant:** Quality is independent of model confidence. It depends on input properties only.

**Vision Quality:**
```
blur_factor       = laplacian_variance / blur_ref (clipped to [0,1])
exposure_factor   = 1 - |mean_pixel - midpoint| / range
illumination_factor = 1 - std(grayscale) / threshold
quality_vision    = mean([blur, exposure, illumination])
```

**Telemetry Quality:**
```
missingness       = 1 - missing_rate
noise_factor      = 1 / (1 + snr_inverse)
in_range_frac     = count_in_range / total
drift_penalty     = exp(-|drift| / drift_scale)
staleness_penalty = exp(-staleness_seconds / staleness_half_life)
quality_telemetry = mean([missingness, noise, in_range, drift, staleness])
```

**History Quality:**
```
recency           = exp(-Δt_days / recency_tau_days)
record_saturation = min(count / count_ref, 1.0)
temporal_coverage = recent_inspections / expected
consistency       = 1 - std(recent_labels)
quality_history   = mean([recency, saturation, coverage, consistency])
```

### Trust Gating (Section 8)

**Gate Formula (multiplicative):**
```
g_i = q_i * p_i(a)

where:
  q_i     = current quality of modality i
  p_i(a)  = persistent prior for modality i on asset a ∈ [0.05, 0.99]
  ε       = 1e-6 (normalization floor)
```

**Normalization:**
```
w_i = g_i / (Σ_j g_j + ε)

Constraint: Σ_i w_i ≈ 1.0 (within 1e-5)
```

**Missing Modality Handling:**
```
If modality i unavailable, set g_i = 0 explicitly, renormalize over remaining
```

### Fusion (Section 9)

**Probability-Level Fusion:**
```
z_fused = Σ_i w_i * p_i

where p_i ∈ [0,1] is anomaly probability from modality i
```

**Cross-Modal Disagreement:**
```
disagreement = max(p_i) - min(p_i)  (across available modalities)
```

### Calibration (Section 11)

**Temperature Scaling on Logits:**
```
1. logit(p) = log(p / (1-p))  [clipped to avoid log(0)]
2. scaled_logit = logit / T
3. calibrated_p = sigmoid(scaled_logit)
```

**Temperature Fitting:**
```
Minimize ECE on validation set via grid search over T ∈ [0.1, 10.0]
```

### Trust Prior Updates (Section 12)

**EMA Update Rule:**
```
observed_reliability = 1 if prediction_correct else 0

new_prior = α * observed_reliability + (1-α) * old_prior

where α = ema_alpha (default 0.2)
```

**Safeguards:**
```
1. min_evidence_count = 5: accumulate before updating
2. confidence_threshold = 0.6: ignore uncertain predictions
3. prior_bounds = [0.05, 0.99]: clamp always
4. max_step = 0.15: cap per-update change
5. Rollback: append-only history log for reversion
```

---

## 4. How to Reproduce Every Experiment

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize config (already in configs/config.yaml)
```

### Unit Tests (validate all modules)
```bash
# All unit tests
pytest tests/unit/ -v

# Specific module
pytest tests/unit/test_quality.py -v
pytest tests/unit/test_trust_gate.py -v
pytest tests/unit/test_priors.py -v
```

### Integration Tests (validate end-to-end)
```bash
pytest tests/integration/ -v
```

### Run Ablation Study (8 variants, same eval set)
```bash
python -c "from experiments.ablation import run_ablation_study; run_ablation_study()"
# Results: results/ablation_results.json
```

### Run Degradation Experiments (4×4 grid)
```bash
python -c "from experiments.degradation import run_degradation_experiment; run_degradation_experiment()"
# Results: results/degradation_results.json
```

### Example Inference Call
```bash
python scripts/example_call.py
# Prints InferenceResult JSON for one synthetic asset
```

---

## 5. Actual Results Tables

### Ablation Study Results (NOT YET RUN)

```
TODO: run_ablation_study() and paste results
(8 rows: A–H, columns: AUROC, F1, Accuracy, ECE, Brier)
```

### Degradation Experiment Results (NOT YET RUN)

```
TODO: run_degradation_experiment() and paste results
(32 rows: 4 dropout × 4 modes × 2 systems, columns: AUROC, F1, graceful_degradation_slope)
```

---

## 6. Prototype Simplifications vs. Research Claims vs. Assumptions

### Prototype Simplifications (not research contributions)
- **Vision:** Image-level binary classification (ResNet18 fine-tuned on MVTec). No pixel-level localization yet.
- **Telemetry:** Per-channel z-score ensemble (simple, interpretable). Not state-of-the-art anomaly detection.
- **History:** Logistic regression over 5 features. Not a deep model.
- **Fusion:** Probability-level only. No embedding-level fusion.
- **Calibration:** Temperature scaling (standard method). No advanced calibration.

### Research Claims (hypothesis support)
1. Quality can be estimated independently of model confidence (Section 7 invariant).
2. Trust-weighted gating (g_i = q_i * p_i) dynamically adapts to modality degradation (Section 8 worked example).
3. Honest calibration (ECE/Brier measured) reflects actual evidence reliability.
4. Human feedback with EMA updates adjusts priors over time (Section 12 acceptance check).
5. Trust-gated fusion outperforms or degrades more gracefully than fixed averaging (degradation experiments).

### Assumptions
- All modalities are independent (no explicit correlation modeling).
- Quality factors are equally weighted (simple mean aggregation).
- Priors persist per asset, not per context (no context-dependent adaptation).
- Feedback events carry ground truth labels (no label noise handling).
- Prior bounds [0.05, 0.99] prevent degenerate states (tuned for prototype; not data-driven).

---

## 7. Known Limitations

1. **Vision localization not implemented:** Returns `None`. Fallback for full anomaly localization would use PatchCore-style embedding distance (memory bank).

2. **No temporal sequence modeling:** Telemetry detector treats each window independently; no RNN/Transformer for temporal patterns.

3. **Single-asset priors:** Trust priors are per-asset, not per-asset-context. No transfer learning across assets.

4. **Synthetic evaluation:** All experiments use synthetic data (MVTec toy images, generated telemetry/history). Real-world performance unknown.

5. **No online learning:** Priors are batch-updated post-hoc from feedback; no streaming/incremental updates.

6. **Limited modality fusion:** Only 3 modalities. Scaling to many modalities untested.

7. **Calibration fit on synthetic data:** Temperature scaler fit on validation set generated the same way as test set. Real distribution shift not tested.

---

## 8. Repository Structure

```
ml_core/
├── vision/
│   ├── detector.py            # VisionDetector (ResNet18)
│   ├── preprocessing.py       # Image quality factors
│   └── localization.py        # Stub (returns None)
├── telemetry/
│   ├── generator.py           # Synthetic data + degradation
│   ├── detector.py            # Per-channel z-score ensemble
│   └── preprocessing.py       # Windowing, quality factors
├── history/
│   ├── generator.py           # Synthetic inspection records
│   ├── features.py            # 5 feature extractors
│   └── detector.py            # Logistic regression
├── quality/
│   └── estimator.py           # Dispatch to modality quality
├── trust/
│   ├── gate.py                # TrustGate (g_i = q_i * p_i)
│   └── priors.py              # TrustPriorStore (JSON persistence)
├── fusion/
│   └── fusion.py              # Probability-level fusion
├── calibration/
│   ├── temperature_scaling.py # TemperatureScaler
│   └── metrics.py             # ECE, Brier, reliability diagram
├── experiments/
│   ├── degradation.py         # 4×4 grid sweep
│   └── ablation.py            # 8 variants
├── pipeline/
│   └── inference.py           # InferencePipeline (10-step)
├── schemas/
│   └── outputs.py             # ModalityResult, FusionResult, etc.
├── configs/
│   └── config.yaml            # All numeric constants
├── tests/
│   ├── unit/                  # Per-module tests
│   └── integration/           # End-to-end tests
├── scripts/
│   └── example_call.py        # Single inference example
├── requirements.txt
└── README.md (this file)
```

---

## 9. Key Files

- **`schemas/outputs.py`:** Data contracts (ModalityResult, QualityResult, InferenceResult, etc.)
- **`configs/config.yaml`:** All hyperparameters and thresholds
- **`pipeline/inference.py`:** Entry point for inference (`InferencePipeline.run_inference()`)
- **`trust/priors.py`:** Human feedback integration (`TrustPriorStore.update_from_feedback()`)
- **`experiments/ablation.py`:** Run ablation study (8 variants)
- **`experiments/degradation.py`:** Run degradation experiments (4×4 grid)

---

## 10. Design Decisions & Justifications

1. **Why multiplicative gate?** Simple, interpretable, and allows quality and prior to compete fairly. Alternatives (nonlinear) left as ablations.

2. **Why mean aggregation for quality factors?** Equal weighting is a neutral baseline. Asymmetric weighting would require domain tuning.

3. **Why EMA for prior updates?** Standard online learning approach, forgets old evidence gradually. Alpha=0.2 gives moderate responsiveness.

4. **Why temperature scaling on logits?** Standard method, orthogonal to fusion mechanism. Separates concerns: fusion vs. calibration.

5. **Why JSON priors store?** Simple, human-readable, no DB setup needed for prototype. Append-only history enables rollback.

---

## 11. Citation & References

This work is a proof-of-concept for trust-calibrated multimodal anomaly detection. 

Key concepts:
- **Modality quality** independent of prediction confidence (novel for anomaly detection)
- **Trust gating** as multiplicative combination of quality × prior (inspired by Bayesian belief updating)
- **Calibration + fusion** as separate concerns (follows recommendation from Guo et al., 2017)
- **Human-in-the-loop feedback** with EMA priors (standard in active learning)

---

## 12. Next Steps for Production

1. **Replace synthetic data with real industrial data** (MVTec AD real images, actual sensor streams, maintenance records).
2. **Implement vision localization** (PatchCore or fine-tuned segmentation model).
3. **Add temporal modeling** (GRU/Transformer for telemetry sequences).
4. **Context-aware priors** (per-asset, per-mode-of-operation).
5. **Streaming updates** (online EMA without batch feedback).
6. **Multi-modality at scale** (10+ sensors, image streams, text logs).
7. **Production infrastructure** (FastAPI wrapper, monitoring, A/B testing framework).

---

## 13. Contact & Questions

For questions about the research hypothesis, architecture, or experimental results, refer to Sections 1–7 of this README. Each section is self-contained and references the build prompt (Sections 1–21).

---

*Generated: 2026-08-28 | Prototype: Trust-Calibrated Multimodal Anomaly Intelligence | Status: NOT YET RUN (experiments)*
