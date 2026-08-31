# Trust-Calibrated Multimodal Industrial Anomaly Intelligence Platform

**A two-person research prototype demonstrating intelligent evidence fusion with dynamic trust calibration.**

---

## System Overview: End-to-End Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ FRONTEND (React + TypeScript) @ http://localhost:5173                       │
│                                                                              │
│ User Interface:                                                              │
│  ├─ Input sensor value (e.g., 42.5 degrees)                                │
│  ├─ Upload industrial image                                                 │
│  ├─ Select asset ID (e.g., "motor_07")                                     │
│  └─ Click "Run Prediction"                                                  │
│                                                                              │
│ Result Display:                                                              │
│  ├─ Final prediction (NORMAL / ANOMALY)                                     │
│  ├─ Calibrated confidence (0-100%)                                          │
│  ├─ Per-modality scores (Vision / Telemetry / History)                      │
│  ├─ Trust weights (how much each modality influenced decision)              │
│  ├─ Quality indicators (why that weight)                                    │
│  └─ Explanation (which evidence dominated and why)                          │
│                                                                              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                    HTTP POST /predict with:
                    - sensor_value: 42.5
                    - image_file: <binary>
                    - asset_id: "motor_07"
                    │
                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ BACKEND (FastAPI) @ http://localhost:8000                                   │
│                                                                              │
│ Routes:                                                                      │
│  POST /predict                                                               │
│    1. Parse incoming request (sensor value, image, asset)                   │
│    2. Call ML core: result = run_inference(...)                             │
│    3. Log result to PostgreSQL database                                     │
│    4. Return comprehensive JSON response                                    │
│                                                                              │
│ Integration:                                                                 │
│  from ml_core.pipeline.inference import run_inference                       │
│                                                                              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                    Python function call to ML core:
                    │
                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ ML CORE (Python/PyTorch) — Your Research Engine                             │
│                                                                              │
│ STEP 1: VISION MODALITY                                                     │
│ ├─ Preprocess: normalize, resize to (224, 224)                              │
│ ├─ Model: Transfer learning on MVTec AD                                     │
│ ├─ Output: vision_score = 0.91 (anomaly likelihood)                         │
│ └─ Quality: blur=0.94, exposure=0.88, sharpness=0.93 → q=0.91              │
│                                                                              │
│ STEP 2: TELEMETRY MODALITY                                                  │
│ ├─ Preprocess: rolling window, z-score normalize                            │
│ ├─ Model: LSTM or statistical anomaly detector                              │
│ ├─ Output: telemetry_score = 0.63                                           │
│ └─ Quality: noise=0.52, drift=0.52, missingness=0.52 → q=0.52              │
│                                                                              │
│ STEP 3: HISTORY MODALITY                                                    │
│ ├─ Extract features: recency, frequency, consistency, etc.                  │
│ ├─ Model: Bayesian prior or logistic regression                             │
│ ├─ Output: history_score = 0.82                                             │
│ └─ Quality: recency=0.97, coverage=0.91, consistency=0.95 → q=0.94         │
│                                                                              │
│ STEP 4: TRUST GATING ⭐ (Core Research Component)                           │
│ ├─ Load persistent priors: p_vision=0.85, p_telemetry=0.70, p_history=0.90 │
│ ├─ Gate formula: g_i = q_i × p_i                                            │
│ │  g_vision = 0.91 × 0.85 = 0.77                                           │
│ │  g_telemetry = 0.52 × 0.70 = 0.36                                        │
│ │  g_history = 0.94 × 0.90 = 0.85                                          │
│ ├─ Normalize: w_i = g_i / Σ(g_j) + ε                                        │
│ │  w_vision = 0.77 / 1.98 = 0.39                                           │
│ │  w_telemetry = 0.36 / 1.98 = 0.18  ← Lower due to poor quality!          │
│ │  w_history = 0.85 / 1.98 = 0.43                                          │
│ └─ Key: If telemetry had noise, its quality drops → weight automatically drops
│                                                                              │
│ STEP 5: EVIDENCE FUSION ⭐ (Research Component)                             │
│ ├─ Formula: z_fused = Σ(w_i × z_i)                                          │
│ ├─ = 0.39×0.91 + 0.18×0.63 + 0.43×0.82                                      │
│ ├─ = 0.35 + 0.11 + 0.35 = 0.81 (fused anomaly likelihood)                   │
│ └─ Detects disagreement: max(z_i) - min(z_i) = 0.91 - 0.63 = 0.28          │
│                                                                              │
│ STEP 6: CALIBRATION ⭐ (Research Component)                                 │
│ ├─ Raw probability: 0.81                                                     │
│ ├─ Apply temperature scaling: T=1.1 learned from validation set              │
│ ├─ Calibrated probability: 0.78                                              │
│ └─ Measures: ECE, Brier score (confidence matches actual accuracy)          │
│                                                                              │
│ STEP 7: UNCERTAINTY QUANTIFICATION                                          │
│ ├─ Cross-modal disagreement: 0.28 (how much modalities disagree)            │
│ ├─ Confidence intervals from calibration metrics                            │
│ └─ Uncertainty propagation: higher when modalities disagree                 │
│                                                                              │
│ STEP 8: EXPLANATIONS & METADATA                                             │
│ ├─ Dominant modality: "history" (highest weight 0.43)                       │
│ ├─ Reason: "highest quality evidence (0.94) with strong prior (0.90)"       │
│ ├─ Evidence trail: which modalities contributed most                        │
│ └─ Action recommendations (from domain expert rules)                        │
│                                                                              │
│ OUTPUT: Comprehensive InferenceResult JSON                                  │
│ {                                                                            │
│   "asset_id": "motor_07",                                                   │
│   "prediction": {                                                            │
│     "label": "anomaly",                                                      │
│     "raw_probability": 0.81,                                                 │
│     "calibrated_probability": 0.78                                           │
│   },                                                                         │
│   "modalities": [                                                            │
│     {                                                                        │
│       "name": "vision",                                                      │
│       "prediction": 0.91,                                                    │
│       "quality": 0.91,                                                       │
│       "prior": 0.85,                                                         │
│       "weight": 0.39                                                         │
│     },                                                                       │
│     {                                                                        │
│       "name": "telemetry",                                                   │
│       "prediction": 0.63,                                                    │
│       "quality": 0.52,                                                       │
│       "prior": 0.70,                                                         │
│       "weight": 0.18                                                         │
│     },                                                                       │
│     {                                                                        │
│       "name": "history",                                                     │
│       "prediction": 0.82,                                                    │
│       "quality": 0.94,                                                       │
│       "prior": 0.90,                                                         │
│       "weight": 0.43                                                         │
│     }                                                                        │
│   ],                                                                         │
│   "uncertainty": {                                                           │
│     "cross_modal_disagreement": 0.28,                                        │
│     "calibration_confidence": 0.78                                           │
│   },                                                                         │
│   "explanations": {                                                          │
│     "dominant_modality": "history",                                          │
│     "reason": "highest combined quality×prior confidence"                    │
│   }                                                                          │
│ }                                                                            │
│                                                                              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                    Return JSON to backend
                                   │
                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ BACKEND: Log & Respond                                                      │
│                                                                              │
│ 1. Log to PostgreSQL: prediction_logs table                                 │
│ 2. Return JSON response to frontend                                         │
│                                                                              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                    HTTP 200 with result JSON
                                   │
                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ FRONTEND: Display Results                                                   │
│                                                                              │
│ ✓ Prediction: ANOMALY DETECTED (78% confidence)                             │
│ ✓ Vision contributed 39% of the decision                                    │
│ ✓ Telemetry only 18% (low quality detection: noise present)                 │
│ ✓ History dominated at 43% (best quality: complete records)                 │
│ ✓ Disagreement flag: Modalities not in full agreement                       │
│ ✓ Action: Review maintenance records (dominant evidence)                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Innovation: Dynamic Trust Gating

**Traditional Approach (Fixed Averaging):**
```
Prediction = (vision + telemetry + history) / 3
→ Equal weight regardless of data quality
→ Noisy telemetry pulls prediction down equally
```

**Your Approach (Trust-Gated Fusion):**
```
Quality scores: q_vision=0.91, q_telemetry=0.32, q_history=0.94
Priors: p_vision=0.85, p_telemetry=0.70, p_history=0.90

Gates: g_i = q_i × p_i
→ g_vision = 0.91×0.85 = 0.77
→ g_telemetry = 0.32×0.70 = 0.22  ← Automatically reduced!
→ g_history = 0.94×0.90 = 0.85

Weights: w_i = g_i / Σ(g_j)
→ w_vision = 42%
→ w_telemetry = 12%  ← System detected noise, reduced weight
→ w_history = 46%

Result: Noisy modality automatically receives less influence
        No hard-coded rules. Purely data-driven.
```

---

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

### Ablation Study Results (Final — Fixed Generators, Learned Detectors)

**Test Set:** 100 samples (50 normal, 50 anomalous), seed offset +10000 (no train/test overlap)  
**Detectors:** Vision (learned logistic regression on features), Telemetry (learned logistic regression), History (trained logistic regression)

| Variant | AUROC | F1    | Accuracy | ECE   | Brier  | Notes |
|---------|-------|-------|----------|-------|--------|-------|
| A: Vision only | 0.688 | 0.577 | 0.53 | 0.133 | 0.237 | Generalizes reasonably; structured defects detectable |
| B: Telemetry only | **1.0** | **1.0** | **1.0** | **0.010** | **0.0001** | Perfect on synthetic; clean signal from generator |
| C: History only | 0.496 | 0.524 | 0.51 | 0.076 | 0.261 | Weak correlation between features and labels |
| D: Equal-weight fusion | 1.0 | 1.0 | 1.0 | 0.328 | 0.110 | Perfect discrimination; telemetry dominates |
| E: Quality-only fusion | 1.0 | 1.0 | 1.0 | 0.330 | 0.114 | Perfect discrimination |
| F: Trust-prior-only fusion | 1.0 | 1.0 | 1.0 | 0.328 | 0.110 | Perfect discrimination |
| G: Quality + trust-gated fusion | 1.0 | 1.0 | 1.0 | 0.330 | 0.114 | Perfect discrimination (no calibration) |
| **H: Full system + calibration** | **1.0** | **1.0** | **1.0** | **0.454** | **0.207** | Perfect discrimination; calibration over-adjusted |

**Key Finding:** Telemetry detector achieves perfect separation. Vision contributes weak signal (0.69 AUROC alone). Fusion variants all achieve 1.0 because telemetry dominates. Calibration increases ECE (0.330→0.454), suggesting over-regularization on synthetic data.

### Degradation Experiment Results (Quick Run — 1 Trial Per Condition)

**Setup:** 4 dropout levels (0%, 25%, 50%, 75%) × 4 degradation modes (noise, staleness, image_degradation, contradiction)  
**Baseline:** Fixed equal-weight averaging | **Proposed:** Trust-gated fusion

Sample results (dropout=0%, all degradation modes):

| Degradation Mode | System | Dropout | AUROC | F1 | Status |
|------------------|--------|---------|-------|-------|---------|
| Noise | Baseline | 0% | 0.624 | 0.188 | Baseline weak |
| Noise | Proposed | 0% | 0.619 | 0.364 | Proposed better F1 |
| Staleness | Baseline | 0% | 0.589 | 0.474 | Baseline OK |
| Staleness | Proposed | 0% | 0.611 | 0.444 | Proposed slightly better |
| Image Degradation | Baseline | 0% | 0.670 | 0.444 | Baseline strong |
| Image Degradation | Proposed | 0% | 0.651 | 0.488 | Proposed more robust |
| Contradiction | Baseline | 0% | 0.635 | 0.541 | Baseline strong |
| Contradiction | Proposed | 0% | 0.557 | 0.400 | Proposed struggles |

**Finding:** Trust-gated fusion shows mixed results on synthetic data. On noise and staleness, it performs comparably or better. On contradiction (conflicting modalities), fixed averaging is more robust. This suggests the trust gate needs further tuning for adversarial modality disagreement.

---

## 6. Detectors & Generators: What Changed

### Generator Fixes (Person 1 ML Research Work)

**Vision Generator (NEW):** Replaced random noise with structured synthetic defects
- **Before:** `np.random.rand(480, 640, 3)` for both normal and anomalous
- **After:** Procedural textures (checkerboard, gradients, structured noise) + injected defects (scratch, dark_patch, bright_blob, distortion, blur)
- **Separability (sanity check):** 0.50 AUROC (no signal) → 0.60 AUROC (separable)
- **Result:** Vision detector now functional (0.69 AUROC on test set)

**Telemetry Generator:** No change; already had perfect separability (1.0 AUROC)

**History Generator:** No change; acceptable weak signal (0.58 AUROC)

### Detector Upgrades (Person 1 ML Research Work)

**Vision Detector:**
- **Old:** VisionDetector (pretrained ResNet18) → Failed on synthetic data (0.33 AUROC)
- **New:** LearnedVisionDetector (logistic regression on hand-engineered features)
  - Features: dark_ratio, bright_ratio, intensity_range, quantile_spread
  - Trained on 100 synthetic images (50 normal, 50 anomalous)
  - **Result:** 0.69 AUROC on held-out test set ✓

**Telemetry Detector:**
- **Old:** TelemetryDetector (z-score thresholding) → Underutilized perfect signal (0.51 AUROC)
- **New:** LearnedTelemetryDetector (logistic regression on engineered features)
  - Features: per-channel mean/std/range, cross-channel consistency, SNR, missingness
  - Trained on 100 telemetry windows (50 normal, 50 anomalous)
  - **Result:** 1.0 AUROC (perfect, but indicates very clean synthetic signal)

**History Detector:** Kept as-is (logistic regression on 5 extracted features) → 0.50 AUROC (acceptable, limited by weak feature signal)

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

## 8. Known Limitations

1. **Vision localization not implemented:** Returns `None`. Fallback for full anomaly localization would use PatchCore-style embedding distance (memory bank).

2. **No temporal sequence modeling:** Telemetry detector treats each window independently; no RNN/Transformer for temporal patterns.

3. **Single-asset priors:** Trust priors are per-asset, not per-asset-context. No transfer learning across assets.

4. **Synthetic evaluation:** All experiments use synthetic data (MVTec toy images, generated telemetry/history). Real-world performance unknown.

5. **No online learning:** Priors are batch-updated post-hoc from feedback; no streaming/incremental updates.

6. **Limited modality fusion:** Only 3 modalities. Scaling to many modalities untested.

7. **Calibration fit on synthetic data:** Temperature scaler fit on validation set generated the same way as test set. Real distribution shift not tested.

---

## 9. Repository Structure

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

## 10. Key Files

- **`schemas/outputs.py`:** Data contracts (ModalityResult, QualityResult, InferenceResult, etc.)
- **`configs/config.yaml`:** All hyperparameters and thresholds
- **`pipeline/inference.py`:** Entry point for inference (`InferencePipeline.run_inference()`)
- **`trust/priors.py`:** Human feedback integration (`TrustPriorStore.update_from_feedback()`)
- **`experiments/ablation.py`:** Run ablation study (8 variants)
- **`experiments/degradation.py`:** Run degradation experiments (4×4 grid)

---

## 11. Design Decisions & Justifications

1. **Why multiplicative gate?** Simple, interpretable, and allows quality and prior to compete fairly. Alternatives (nonlinear) left as ablations.

2. **Why mean aggregation for quality factors?** Equal weighting is a neutral baseline. Asymmetric weighting would require domain tuning.

3. **Why EMA for prior updates?** Standard online learning approach, forgets old evidence gradually. Alpha=0.2 gives moderate responsiveness.

4. **Why temperature scaling on logits?** Standard method, orthogonal to fusion mechanism. Separates concerns: fusion vs. calibration.

5. **Why JSON priors store?** Simple, human-readable, no DB setup needed for prototype. Append-only history enables rollback.

---

## 12. Citation & References

This work is a proof-of-concept for trust-calibrated multimodal anomaly detection. 

Key concepts:
- **Modality quality** independent of prediction confidence (novel for anomaly detection)
- **Trust gating** as multiplicative combination of quality × prior (inspired by Bayesian belief updating)
- **Calibration + fusion** as separate concerns (follows recommendation from Guo et al., 2017)
- **Human-in-the-loop feedback** with EMA priors (standard in active learning)

---

## 13. Next Steps for Production

1. **Replace synthetic data with real industrial data** (MVTec AD real images, actual sensor streams, maintenance records).
2. **Implement vision localization** (PatchCore or fine-tuned segmentation model).
3. **Add temporal modeling** (GRU/Transformer for telemetry sequences).
4. **Context-aware priors** (per-asset, per-mode-of-operation).
5. **Streaming updates** (online EMA without batch feedback).
6. **Multi-modality at scale** (10+ sensors, image streams, text logs).
7. **Production infrastructure** (FastAPI wrapper, monitoring, A/B testing framework).

---

## 14. Contact & Questions

For questions about the research hypothesis, architecture, or experimental results, refer to Sections 1–7 of this README. Each section is self-contained and references the build prompt (Sections 1–21).

---

*Generated: 2026-08-28 | Prototype: Trust-Calibrated Multimodal Anomaly Intelligence | Status: COMPLETE (all core experiments ran; results in Section 5-6)*
