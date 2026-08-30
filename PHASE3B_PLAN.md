# Phase 3b: ML Core Integration - Implementation Plan

**Status:** READY TO START 🟢  
**Estimated Duration:** 1-2 hours  
**Goal:** Integrate Person 1's ML core into backend, use synthetic data, test multimodal response

---

## Overview

Phase 3b integrates the completed ML core (Person 1's work) into the backend API. The frontend is already ready to display multimodal data—it just needs the backend to provide it.

**Key Points:**
- ML core code is complete (13 phases done)
- Synthetic data generators built into ml_core/
- No new frontend changes needed
- Stages 3-5 auto-populate once backend returns data
- All 6 stages will display pipeline with quality-based trust gating

---

## Step 1: Verify ML Core Structure

**Location:** `../ml_core/` (sibling to frontend/backend)

**Check these files exist:**
```
ml_core/
├── pipeline/
│   └── inference.py          ← Main entry point: run_inference()
├── vision/
│   ├── detector.py
│   └── ...
├── telemetry/
│   ├── detector.py
│   └── generator.py
├── history/
│   ├── detector.py
│   └── generator.py
├── quality/
│   └── estimator.py
├── trust/
│   └── gate.py
├── fusion/
│   └── engine.py
├── calibration/
│   └── scaler.py
├── schemas/
│   └── outputs.py            ← InferenceResult schema
└── requirements.txt
```

**Command to verify:**
```bash
python3 -c "from ml_core.pipeline.inference import run_inference; print('✓ ML core importable')"
```

---

## Step 2: Update Backend main.py

**Current backend (simplified):**
```python
@app.post("/predict")
async def predict(value: float):
    # Placeholder logic
    sensor_value = value
    quality_estimation = 0.72
    trend_analysis = f"Trend at {value}..."
    
    return {
        "sensor_value": sensor_value,
        "quality_estimation": quality_estimation,
        "trend_analysis": trend_analysis,
        # ... etc
    }
```

**Updated backend (with ML core):**
```python
from ml_core.pipeline.inference import run_inference

@app.post("/predict")
async def predict(value: float):
    # Call ML core with synthetic data
    result = run_inference(
        telemetry_value=value,
        image=None,  # Will be multipart upload later
        asset_id="test_asset"
    )
    
    # Result already has InferenceResult schema
    return result
```

**Files to modify:**
- `backend/main.py` — Add import, update predict() function

---

## Step 3: Test ML Core Import

**Check if ml_core is importable from backend:**
```bash
cd backend
python3 -c "from ml_core.pipeline.inference import run_inference; print('✓')"
```

**If import fails:**
- Verify ml_core/ is in parent directory
- Add to PYTHONPATH if needed:
  ```bash
  export PYTHONPATH="${PYTHONPATH}:$(pwd)/.."
  ```

---

## Step 4: Use Synthetic Data Generators

ML core has built-in synthetic data generators. Use them for testing:

```python
from ml_core.telemetry.generator import TelemetryGenerator
from ml_core.vision.generator import VisionGenerator
from ml_core.history.generator import HistoryGenerator

# Generate synthetic telemetry
gen = TelemetryGenerator()
synthetic_telemetry = gen.generate_normal()  # or .generate_anomaly()

# Generate synthetic image
vision_gen = VisionGenerator()
synthetic_image = vision_gen.generate_normal()  # Returns numpy array

# Generate synthetic history
history_gen = HistoryGenerator()
synthetic_history = history_gen.generate_normal()
```

**For Phase 3b testing, just use:**
```python
result = run_inference(
    telemetry_value=value,
    image=None,  # Will use default synthetic
    asset_id="test_asset"
)
```

---

## Step 5: Expected Response Format

**Before ML core integration (current):**
```json
{
  "sensor_value": 50,
  "quality_estimation": 0.72,
  "trend_analysis": "...",
  "rag_recommendation": "...",
  "status": "..."
}
```

**After ML core integration (expected):**
```json
{
  "sensor_value": 50,
  "trend_analysis": "...",
  "quality_estimation": 0.72,
  "rag_recommendation": "...",
  "status": "...",
  
  "trust_gate": 0.72,
  "fusion": {
    "raw_score": 0.81,
    "fused_score": 0.78,
    "disagreement": 0.28
  },
  "calibration": {
    "raw_probability": 0.81,
    "calibrated_probability": 0.78,
    "temperature": 1.1,
    "ece": 0.03
  },
  "modalities": {
    "vision": {
      "prediction": 0.91,
      "quality": 0.91,
      "weight": 0.39
    },
    "telemetry": {
      "prediction": 0.63,
      "quality": 0.52,
      "weight": 0.18
    },
    "history": {
      "prediction": 0.82,
      "quality": 0.94,
      "weight": 0.43
    }
  }
}
```

**Frontend will automatically display:**
- Stage 1: sensor_value ✅
- Stage 2: quality_estimation ✅
- Stage 3: trust_gate (NEW)
- Stage 4: fusion.fused_score (NEW)
- Stage 5: calibration values (NEW)
- Stage 6: trend_analysis ✅

---

## Step 6: Update Backend main.py (Detailed)

**File:** `backend/main.py`

**Add import at top:**
```python
from ml_core.pipeline.inference import run_inference
```

**Replace predict() function:**
```python
@app.post("/predict")
async def predict(value: float):
    """
    Predict anomaly using trust-calibrated multimodal fusion.
    
    Args:
        value: Telemetry sensor value
    
    Returns:
        InferenceResult with full pipeline breakdown
    """
    try:
        # Call ML core inference
        result = run_inference(
            telemetry_value=value,
            image=None,  # Synthetic for now
            asset_id="test_asset"
        )
        
        # Log result to database (if DB exists)
        # db_log(value, result)
        
        # Return full result schema
        return result
        
    except Exception as e:
        logger.error(f"Inference error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Step 7: Test Integration

### Manual Test 1: Backend Still Runs
```bash
cd backend
python main.py
# Should start on http://localhost:8000
```

### Manual Test 2: Endpoint Returns Multimodal Data
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"value": 50}' \
  | python3 -m json.tool
```

**Check response has:**
- ✅ sensor_value
- ✅ quality_estimation
- ✅ trend_analysis
- ✅ trust_gate (NEW)
- ✅ fusion.fused_score (NEW)
- ✅ calibration (NEW)
- ✅ modalities (NEW)

### Manual Test 3: Frontend Displays All Stages
```
1. Open http://localhost:5174
2. Enter: 50
3. Click: Run Inference
4. Watch: 3-second animation
5. Verify: All 6 stages show values
```

**Expected:**
- Stage 1: 50
- Stage 2: 72%
- Stage 3: 0.72 (trust gate)
- Stage 4: 0.78 (fused score)
- Stage 5: 0.81 → 0.78 (calibration)
- Stage 6: Prediction + confidence

### Manual Test 4: Run E2E Tests
```bash
cd frontend
node e2e-test.cjs
# Should still pass 7/7
```

---

## Step 8: Test Different Scenarios

**Scenario 1: Clean System (all quality high)**
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"value": 50}'
```
Expected: All modalities visible, balanced weights

**Scenario 2: Degraded Telemetry**
```bash
# Modify synthetic generator to add noise
# Then test prediction
```
Expected: Telemetry weight decreases due to lower quality

**Scenario 3: Multiple Predictions**
```bash
for i in {1..5}; do
  curl -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d "{\"value\": $((RANDOM % 100))}"
done
```
Expected: Consistent results, weights adjust based on quality

---

## Potential Issues & Solutions

### Issue: Import Error
```
ModuleNotFoundError: No module named 'ml_core'
```
**Solution:**
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/.."
# Or add to backend/main.py:
import sys
sys.path.insert(0, '..')
```

### Issue: Missing Dependencies
```
ImportError: No module named 'torch'
```
**Solution:**
```bash
pip install -r ../ml_core/requirements.txt
```

### Issue: Synthetic Data Fails
```
Error in data generation
```
**Solution:**
- Check ml_core/ structure is intact
- Verify generators exist in telemetry/, vision/, history/
- Run ml_core tests first: `pytest ../ml_core/tests/ -v`

### Issue: Response Format Mismatch
```
KeyError: 'trust_gate'
```
**Solution:**
- Verify ml_core returns InferenceResult schema
- Check `ml_core/schemas/outputs.py` for expected fields
- Print response: `print(json.dumps(result, indent=2))`

---

## Expected Timeline

| Task | Time | Status |
|------|------|--------|
| Verify ML core structure | 5 min | Quick check |
| Update backend/main.py | 10 min | Code change |
| Test import | 5 min | Verify |
| Manual test 1 (backend runs) | 5 min | Start server |
| Manual test 2 (response format) | 5 min | curl test |
| Manual test 3 (frontend displays) | 10 min | Visual check |
| Manual test 4 (E2E tests) | 2 min | Run suite |
| Scenario testing | 15 min | Different inputs |
| **Total** | **~1 hour** | |

---

## Success Criteria

✅ ML core imports without errors
✅ Backend still runs on port 8000
✅ /predict endpoint returns multimodal data
✅ Response includes trust_gate, fusion, calibration
✅ Modalities breakdown shows all 3 (vision, telemetry, history)
✅ Frontend automatically displays stages 3-5
✅ All 6 stages populated with values
✅ E2E tests still pass (7/7)
✅ Animations smooth and complete
✅ No console errors

---

## Quick Reference: Commands

```bash
# Verify ML core
python3 -c "from ml_core.pipeline.inference import run_inference; print('✓')"

# Start backend (with ML core)
cd backend && python main.py

# Test endpoint
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"value": 50}' | python3 -m json.tool

# Run frontend E2E tests
cd frontend && node e2e-test.cjs

# Check response has all fields
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"value": 50}' | python3 -c \
  "import json, sys; r = json.load(sys.stdin); \
   print('✓ trust_gate' if 'trust_gate' in r else '✗ missing trust_gate')"
```

---

## After Phase 3b: Validation Experiments

Once integration complete, can run:

1. **Degradation grid** (4×4: quality dropout levels)
   - Test system gracefully handles quality loss
   - Verify weights adjust dynamically

2. **Ablation study** (8 variants)
   - Validate each component (quality, trust, fusion, calib)
   - Measure impact on reliability

3. **Scenario validation** (all 7 scenarios)
   - Clean system
   - Telemetry noise
   - Missing modality
   - Contradictory predictions
   - Human feedback loop
   - Calibration effectiveness
   - Degradation vs. fixed averaging

---

## Ready to Proceed?

This plan assumes:
- ✅ ML core is complete (Person 1 finished)
- ✅ Frontend is polished (Phase 3a done)
- ✅ Backend runs and serves synthetic data
- ✅ Python environment has required packages

**Next action:** Execute Step 1 (verify ML core structure), then proceed with integration.

**Time estimate:** ~1 hour from start to "all 6 stages displaying"

---

**Phase 3b Status:** READY ✅  
**Frontend Status:** READY ✅  
**ML Core Status:** READY ✅  

Ready to integrate and test.
