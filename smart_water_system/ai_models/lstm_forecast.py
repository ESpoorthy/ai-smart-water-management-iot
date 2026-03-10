"""
LSTM-based Water Demand Forecasting
Predicts water demand for the next 24 hours using historical data
"""
import numpy as np
import pandas as pd
import sqlite3
from sklearn.preprocessing import MinMaxScaler
import pickle
import os

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("⚠️  TensorFlow not available. Using simple forecasting instead.")

class DemandForecaster:
    def __init__(self, db_path="database/water.db", model_path="ai_models/lstm_model.h5"):
        self.db_path = db_path
        self.model_path = model_path
        self.scaler = MinMaxScaler()
        self.model = None
        self.is_trained = False
        self.sequence_length = 12  # Use last 12 readings (1 minute of data at 5s intervals)
        
    def load_data(self, limit=2000):
        """Load historical sensor data"""
        try:
            conn = sqlite3.connect(self.db_path)
            query = f"""
                SELECT timestamp, flow, temperature 
                FROM sensor_data 
                ORDER BY id DESC 
                LIMIT {limit}
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            # Reverse to get chronological order
            df = df.iloc[::-1].reset_index(drop=True)
            return df
        except Exception as e:
            print(f"Error loading data: {e}")
            return pd.DataFrame()
    
    def prepare_sequences(self, data, sequence_length):
        """Prepare sequences for LSTM training"""
        X, y = [], []
        for i in range(len(data) - sequence_length):
            X.append(data[i:i + sequence_length])
            y.append(data[i + sequence_length, 0])  # Predict flow
        return np.array(X), np.array(y)
    
    def train(self, epochs=50):
        """Train LSTM model"""
        if not TENSORFLOW_AVAILABLE:
            print("⚠️  Cannot train LSTM model without TensorFlow")
            return False
        
        print("🔧 Training demand forecasting model...")
        
        # Load data
        df = self.load_data(limit=1000)
        
        if len(df) < 100:
            print("⚠️  Not enough data to train model (need at least 100 samples)")
            return False
        
        # Prepare features
        features = df[['flow', 'temperature']].values
        
        # Scale data
        scaled_data = self.scaler.fit_transform(features)
        
        # Create sequences
        X, y = self.prepare_sequences(scaled_data, self.sequence_length)
        
        if len(X) < 50:
            print("⚠️  Not enough sequences for training")
            return False
        
        # Split train/test
        split = int(0.8 * len(X))
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]
        
        # Build LSTM model
        self.model = Sequential([
            LSTM(50, activation='relu', return_sequences=True, input_shape=(self.sequence_length, 2)),
            Dropout(0.2),
            LSTM(50, activation='relu'),
            Dropout(0.2),
            Dense(25, activation='relu'),
            Dense(1)
        ])
        
        self.model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        
        # Train model
        history = self.model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=16,
            validation_data=(X_test, y_test),
            verbose=0
        )
        
        self.is_trained = True
        
        # Save model
        self.save_model()
        
        final_loss = history.history['loss'][-1]
        print(f"✅ Model trained - Final loss: {final_loss:.4f}")
        return True
    
    def predict_next_hours(self, hours=24):
        """Predict water demand for next N hours"""
        if not TENSORFLOW_AVAILABLE:
            return self._simple_forecast(hours)
        
        if not self.is_trained:
            if not self.load_model():
                return self._simple_forecast(hours)
        
        # Load recent data
        df = self.load_data(limit=self.sequence_length)
        
        if len(df) < self.sequence_length:
            return self._simple_forecast(hours)
        
        # Prepare input sequence
        features = df[['flow', 'temperature']].values
        scaled_data = self.scaler.transform(features)
        
        # Generate predictions
        predictions = []
        current_sequence = scaled_data[-self.sequence_length:].copy()
        
        # Predict one step at a time
        steps = hours * 12  # 12 readings per hour (5s intervals)
        for _ in range(min(steps, 288)):  # Cap at 24 hours
            # Reshape for prediction
            X = current_sequence.reshape(1, self.sequence_length, 2)
            
            # Predict next value
            pred_scaled = self.model.predict(X, verbose=0)[0, 0]
            
            # Create next input (use predicted flow, keep last temperature)
            next_input = np.array([[pred_scaled, current_sequence[-1, 1]]])
            
            # Update sequence
            current_sequence = np.vstack([current_sequence[1:], next_input])
            
            # Inverse transform to get actual value
            pred_actual = self.scaler.inverse_transform(
                np.array([[pred_scaled, current_sequence[-1, 1]]])
            )[0, 0]
            
            predictions.append(max(0, pred_actual))
        
        return predictions
    
    def _simple_forecast(self, hours=24):
        """Simple moving average forecast when LSTM is not available"""
        df = self.load_data(limit=100)
        
        if len(df) < 10:
            # Return constant baseline
            return [15.0] * (hours * 12)
        
        # Calculate moving average
        avg_flow = df['flow'].tail(50).mean()
        std_flow = df['flow'].tail(50).std()
        
        # Generate forecast with some variation
        predictions = []
        for i in range(hours * 12):
            # Add daily pattern (higher during day, lower at night)
            hour_factor = 1.0 + 0.2 * np.sin(2 * np.pi * i / 144)  # 144 = 12 hours
            noise = np.random.normal(0, std_flow * 0.1)
            pred = avg_flow * hour_factor + noise
            predictions.append(max(0, pred))
        
        return predictions
    
    def save_model(self):
        """Save trained model"""
        if not TENSORFLOW_AVAILABLE or self.model is None:
            return
        
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            self.model.save(self.model_path)
            
            # Save scaler separately
            scaler_path = self.model_path.replace('.h5', '_scaler.pkl')
            with open(scaler_path, 'wb') as f:
                pickle.dump(self.scaler, f)
            
            print(f"💾 Model saved to {self.model_path}")
        except Exception as e:
            print(f"Error saving model: {e}")
    
    def load_model(self):
        """Load trained model"""
        if not TENSORFLOW_AVAILABLE:
            return False
        
        try:
            if os.path.exists(self.model_path):
                self.model = keras.models.load_model(self.model_path)
                
                # Load scaler
                scaler_path = self.model_path.replace('.h5', '_scaler.pkl')
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                
                self.is_trained = True
                print(f"📂 Model loaded from {self.model_path}")
                return True
            return False
        except Exception as e:
            print(f"Error loading model: {e}")
            return False

if __name__ == "__main__":
    # Test the forecaster
    forecaster = DemandForecaster()
    
    # Train model
    forecaster.train(epochs=30)
    
    # Generate forecast
    print("\n🔮 Generating 24-hour forecast...")
    predictions = forecaster.predict_next_hours(hours=24)
    print(f"Generated {len(predictions)} predictions")
    print(f"Average predicted flow: {np.mean(predictions):.2f} L/min")
