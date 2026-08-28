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
    quality_estimation = 0.95 if abs(trend_score) < 0.5 else 0.72

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
            (str(data.value), float(trend_score), float(quality_estimation))
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("Database logging error:", e)

    return {
        "sensor_value": data.value,
        "trend_score": trend_score,
        "trend_analysis": trend_message,
        "quality_estimation": quality_estimation,
        "rag_recommendation": rag_recommendation,
        "status": "Logged successfully to database"
    }