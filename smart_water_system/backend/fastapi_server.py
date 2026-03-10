"""
FastAPI Backend for Smart Water Management System
Handles sensor data ingestion, validation, and storage
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime
import sqlite3
import json
from typing import List, Dict

app = FastAPI(title="Smart Water Management System API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database path
DB_PATH = "database/water.db"

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
