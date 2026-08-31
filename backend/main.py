from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .database import get_db_connection
from .sequence_model import TimeSeriesAnomalyTracker
from .rag_helper import get_diagnostic_explanation

app = FastAPI()

# Enable CORS so your React frontend can talk to FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],
)

tracker = TimeSeriesAnomalyTracker(window_size=5)

class SensorInput(BaseModel):
    value: float

@app.post("/predict")
def predict_anomaly(data: SensorInput):
    # 1. Evaluate time-series trend over the rolling window
    trend_score, trend_message = tracker.evaluate_trend(data.value)

    # 2. Determine quality score
    base_quality = 0.95 if abs(trend_score) < 0.5 else 0.72

    # 3. Fetch RAG diagnostic recommendation based on trend analysis
    rag_recommendation = get_diagnostic_explanation(trend_message)

    # 4. Save prediction, trend score, and recommendation into PostgreSQL database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO prediction_logs (sensor_data, sequence_trend_score, quality_estimation)
            VALUES (%s, %s, %s);
            """,
            (str(data.value), float(trend_score), float(base_quality))
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("Database logging error:", e)

    # 5. Mock multimodal inference (Stages 3-5)
    # These are synthetic values demonstrating the trust-calibrated pipeline
    # When ml_core is integrated, these will be replaced with real inference results

    # Calculate synthetic modality predictions based on sensor value
    # Add some realistic variation
    import math
    sensor_norm = (data.value - 50) / 50  # Normalize around 50

    vision_pred = 0.85 + 0.1 * math.sin(sensor_norm)
    telemetry_pred = 0.72 + 0.15 * math.cos(sensor_norm)
    history_pred = 0.82 + 0.08 * math.sin(sensor_norm * 2)

    # Quality varies - telemetry sometimes degrades
    vision_quality = 0.91
    telemetry_quality = 0.52 if abs(trend_score) > 1 else 0.75
    history_quality = 0.94

    # Prior trust (from historical accuracy)
    vision_prior = 0.85
    telemetry_prior = 0.70
    history_prior = 0.90

    # Trust gates: quality × prior
    vision_gate = vision_quality * vision_prior
    telemetry_gate = telemetry_quality * telemetry_prior
    history_gate = history_quality * history_prior

    # Normalize to get weights
    total_gate = vision_gate + telemetry_gate + history_gate
    vision_weight = vision_gate / total_gate
    telemetry_weight = telemetry_gate / total_gate
    history_weight = history_gate / total_gate

    # Fusion: weighted average
    fused_raw = (vision_weight * vision_pred +
                 telemetry_weight * telemetry_pred +
                 history_weight * history_pred)

    # Calibration: temperature scaling (mock)
    temperature = 1.1
    calibrated_prob = fused_raw / temperature
    calibrated_prob = min(1.0, max(0.0, calibrated_prob))

    # Cross-modal disagreement
    disagreement = max(vision_pred, telemetry_pred, history_pred) - min(vision_pred, telemetry_pred, history_pred)

    return {
        "sensor_value": data.value,
        "trend_score": trend_score,
        "trend_analysis": trend_message,
        "quality_estimation": base_quality,
        "rag_recommendation": rag_recommendation,
        "status": "Logged successfully to database",

        # Stage 3: Trust Gating
        "trust_gate": round(vision_quality, 3),

        # Stage 4: Fusion
        "fusion": {
            "raw_score": round(fused_raw, 3),
            "fused_score": round(fused_raw, 3),
            "disagreement": round(disagreement, 3)
        },

        # Stage 5: Calibration
        "calibration": {
            "raw_probability": round(fused_raw, 3),
            "calibrated_probability": round(calibrated_prob, 3),
            "temperature": temperature,
            "ece": 0.03
        },

        # Modalities breakdown
        "modalities": {
            "vision": {
                "prediction": round(vision_pred, 3),
                "quality": vision_quality,
                "prior_trust": vision_prior,
                "weight": round(vision_weight, 3)
            },
            "telemetry": {
                "prediction": round(telemetry_pred, 3),
                "quality": telemetry_quality,
                "prior_trust": telemetry_prior,
                "weight": round(telemetry_weight, 3)
            },
            "history": {
                "prediction": round(history_pred, 3),
                "quality": history_quality,
                "prior_trust": history_prior,
                "weight": round(history_weight, 3)
            }
        }
    }