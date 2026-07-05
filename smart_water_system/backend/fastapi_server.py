"""
FastAPI Backend for Smart Water Management System
Handles sensor data ingestion, validation, and storage
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime
import sqlite3
import json
from typing import List, Dict
from backend.chat_agent import router as chat_router
from ai_models.recommendation_engine import WaterRecommendationEngine
from ai_models.lstm_forecast import DemandForecaster
from ai_models.anomaly_detection import LeakDetector

app = FastAPI(title="Smart Water Management System API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Decision Intelligence: Natural language chat via Gemini
app.include_router(chat_router)

# Lazy-loaded singletons for the recommendations endpoint
import pathlib as _pl
_rec_engine  = None
_forecaster  = None
_detector    = None

def _get_rec_engine() -> WaterRecommendationEngine:
    global _rec_engine
    if _rec_engine is None:
        _rec_engine = WaterRecommendationEngine(db_path=DB_PATH)
    return _rec_engine

def _get_forecaster() -> DemandForecaster:
    global _forecaster
    if _forecaster is None:
        _model_path = str(_pl.Path(__file__).parent.parent / "ai_models" / "lstm_model.h5")
        _forecaster = DemandForecaster(db_path=DB_PATH, model_path=_model_path)
        _forecaster.load_model()
    return _forecaster

def _get_detector() -> LeakDetector:
    global _detector
    if _detector is None:
        _leak_path = str(_pl.Path(__file__).parent.parent / "ai_models" / "leak_model.pkl")
        _detector = LeakDetector(db_path=DB_PATH, model_path=_leak_path)
        _detector.load_model()
    return _detector

# Database path — absolute so the server works from any CWD
import pathlib as _pathlib
DB_PATH = str(_pathlib.Path(__file__).parent.parent / "database" / "water.db")

class SensorData(BaseModel):
    flow: float = Field(..., ge=0, description="Flow rate in L/min")
    pressure: float = Field(..., ge=0, description="Pressure in bar")
    ph: float = Field(..., ge=0, le=14, description="pH level")
    turbidity: float = Field(..., ge=0, description="Turbidity in NTU")
    temperature: float = Field(..., description="Temperature in Celsius")

def init_database():
    """Initialize SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            flow REAL NOT NULL,
            pressure REAL NOT NULL,
            ph REAL NOT NULL,
            turbidity REAL NOT NULL,
            temperature REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_database()

@app.post("/api/sensor-data")
async def receive_sensor_data(data: SensorData):
    """Receive and store sensor data"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO sensor_data (timestamp, flow, pressure, ph, turbidity, temperature)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (timestamp, data.flow, data.pressure, data.ph, data.turbidity, data.temperature))
        
        conn.commit()
        conn.close()
        
        return {
            "status": "success",
            "message": "Data stored successfully",
            "timestamp": timestamp
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sensor-data/latest")
async def get_latest_data(limit: int = 100):
    """Get latest sensor readings"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM sensor_data 
            ORDER BY id DESC 
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        data = []
        for row in rows:
            data.append({
                "id": row[0],
                "timestamp": row[1],
                "flow": row[2],
                "pressure": row[3],
                "ph": row[4],
                "turbidity": row[5],
                "temperature": row[6]
            })
        
        return {"data": data[::-1]}  # Reverse to get chronological order
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_statistics():
    """Get statistical summary of sensor data"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                AVG(flow) as avg_flow,
                AVG(pressure) as avg_pressure,
                AVG(ph) as avg_ph,
                AVG(turbidity) as avg_turbidity,
                AVG(temperature) as avg_temperature,
                COUNT(*) as total_records
            FROM sensor_data
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        return {
            "avg_flow": round(row[0], 2) if row[0] else 0,
            "avg_pressure": round(row[1], 2) if row[1] else 0,
            "avg_ph": round(row[2], 2) if row[2] else 0,
            "avg_turbidity": round(row[3], 2) if row[3] else 0,
            "avg_temperature": round(row[4], 2) if row[4] else 0,
            "total_records": row[5]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sensor-data/clear")
async def clear_data():
    """Clear all sensor data (for testing)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sensor_data")
        conn.commit()
        conn.close()
        return {"status": "success", "message": "All data cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/recommendations")
async def get_recommendations(zone: str = "Zone-1", include_forecast: bool = True):
    """
    Decision Intelligence endpoint.
    Returns prioritised, actionable recommendations for the given zone
    based on live sensor data, anomaly detection, and demand forecast.
    """
    try:
        engine    = _get_rec_engine()
        detector  = _get_detector()
        forecaster = _get_forecaster()

        # Pull latest reading from DB
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT flow, pressure, ph, turbidity, temperature "
            "FROM sensor_data ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()

        anomaly_result = None
        forecast       = None

        if row:
            flow, pressure, ph, turbidity, temperature = row
            if detector.is_trained:
                is_anomaly, score = detector.predict(flow, pressure)
                anomaly_result = {
                    "is_anomaly": bool(is_anomaly),
                    "score": float(score),
                    "flow": float(flow),
                    "pressure": float(pressure),
                    "ph": float(ph),
                    "turbidity": float(turbidity),
                    "temperature": float(temperature),
                }

        if include_forecast and forecaster.is_trained:
            forecast = forecaster.predict_next_hours(hours=24)

        recs = engine.recommend_from_model_outputs(
            zone=zone,
            anomaly_result=anomaly_result,
            forecast=forecast,
        )

        return {
            "zone": zone,
            "recommendations": recs,
            "total": len(recs),
            "high_priority": sum(1 for r in recs if r["priority"] == "HIGH"),
            "forecaster_active": forecaster.is_trained,
            "detector_active": detector.is_trained,
            "generated_at": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
