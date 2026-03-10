"""
Anomaly Detection for Leak Detection
Uses Isolation Forest algorithm to detect anomalies in water flow and pressure
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import sqlite3
import pickle
import os

class LeakDetector:
    def __init__(self, db_path="database/water.db", model_path="ai_models/leak_model.pkl"):
        self.db_path = db_path
        self.model_path = model_path
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        
    def load_data(self, limit=1000):
        """Load sensor data from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            query = f"""
                SELECT flow, pressure, ph, turbidity, temperature 
                FROM sensor_data 
                ORDER BY id DESC 
                LIMIT {limit}
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            print(f"Error loading data: {e}")
            return pd.DataFrame()
    
    def train(self, contamination=0.1):
        """Train Isolation Forest model"""
        print("🔧 Training leak detection model...")
        
        # Load data
        df = self.load_data(limit=500)
        
        if len(df) < 50:
            print("⚠️  Not enough data to train model (need at least 50 samples)")
            return False
        
        # Select features for anomaly detection
        features = ['flow', 'pressure']
        X = df[features].values
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train Isolation Forest
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.model.fit(X_scaled)
        
        self.is_trained = True
        
        # Save model
        self.save_model()
        
        print(f"✅ Model trained on {len(df)} samples")
        return True
    
    def predict(self, flow, pressure):
        """Predict if current reading is anomalous"""
        if not self.is_trained:
            # Try to load existing model
            if not self.load_model():
                return None, 0.0
        
        # Prepare data
        X = np.array([[flow, pressure]])
        X_scaled = self.scaler.transform(X)
        
        # Predict (-1 = anomaly, 1 = normal)
        prediction = self.model.predict(X_scaled)[0]
        
        # Get anomaly score (lower = more anomalous)
        score = self.model.score_samples(X_scaled)[0]
        
        is_anomaly = prediction == -1
        
        return is_anomaly, score
    
    def detect_anomalies_batch(self, df):
        """Detect anomalies in a batch of data"""
        if not self.is_trained:
            if not self.load_model():
                return []
        
        features = ['flow', 'pressure']
        X = df[features].values
        X_scaled = self.scaler.transform(X)
        
        predictions = self.model.predict(X_scaled)
        scores = self.model.score_samples(X_scaled)
        
        anomalies = []
        for i, (pred, score) in enumerate(zip(predictions, scores)):
            if pred == -1:
                anomalies.append({
                    'index': i,
                    'flow': df.iloc[i]['flow'],
                    'pressure': df.iloc[i]['pressure'],
                    'score': score
                })
        
        return anomalies
    
    def save_model(self):
        """Save trained model to disk"""
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            with open(self.model_path, 'wb') as f:
                pickle.dump({
                    'model': self.model,
                    'scaler': self.scaler
                }, f)
            print(f"💾 Model saved to {self.model_path}")
        except Exception as e:
            print(f"Error saving model: {e}")
    
    def load_model(self):
        """Load trained model from disk"""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.model = data['model']
                    self.scaler = data['scaler']
                self.is_trained = True
                print(f"📂 Model loaded from {self.model_path}")
                return True
            return False
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    
    def get_alert_message(self, flow, pressure, score):
        """Generate alert message for anomaly"""
        return {
            "type": "LEAK_DETECTED",
            "severity": "HIGH",
            "message": f"Anomaly detected in water flow/pressure",
            "details": {
                "flow": round(flow, 2),
                "pressure": round(pressure, 2),
                "anomaly_score": round(score, 4)
            },
            "recommendation": "Check for pipe leaks or valve malfunctions"
        }

if __name__ == "__main__":
    # Test the leak detector
    detector = LeakDetector()
    
    # Train model
    detector.train()
    
    # Test prediction
    print("\n🧪 Testing predictions:")
    
    # Normal reading
    is_anomaly, score = detector.predict(15.0, 2.5)
    print(f"Normal reading: Anomaly={is_anomaly}, Score={score:.4f}")
    
    # Anomalous reading (leak)
    is_anomaly, score = detector.predict(6.0, 1.2)
    print(f"Leak reading: Anomaly={is_anomaly}, Score={score:.4f}")
