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
        # Statistical model attributes (used when TensorFlow is unavailable)
        self._train_avg = None
        self._train_std = None
        self._day_profile = None
        
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
        """Train model — uses LSTM when TensorFlow is available, otherwise fits a
        statistical model (moving-average + daily seasonality) that is persisted
        and used for all subsequent forecasts."""

        print("🔧 Training demand forecasting model...")

        # Load data
        df = self.load_data(limit=1000)

        if len(df) < 100:
            print("⚠️  Not enough data to train model (need at least 100 samples)")
            return False

        # Fit scaler on available data (needed for both paths)
        features = df[['flow', 'temperature']].values
        self.scaler.fit_transform(features)

        if TENSORFLOW_AVAILABLE:
            # ── LSTM path ──────────────────────────────────────────────
            scaled_data = self.scaler.transform(features)
            X, y = self.prepare_sequences(scaled_data, self.sequence_length)

            if len(X) < 50:
                print("⚠️  Not enough sequences for LSTM training")
                return False

            split = int(0.8 * len(X))
            X_train, X_test = X[:split], X[split:]
            y_train, y_test = y[:split], y[split:]

            self.model = Sequential([
                LSTM(50, activation='relu', return_sequences=True,
                     input_shape=(self.sequence_length, 2)),
                Dropout(0.2),
                LSTM(50, activation='relu'),
                Dropout(0.2),
                Dense(25, activation='relu'),
                Dense(1)
            ])
            self.model.compile(optimizer='adam', loss='mse', metrics=['mae'])
            history = self.model.fit(
                X_train, y_train,
                epochs=epochs,
                batch_size=16,
                validation_data=(X_test, y_test),
                verbose=0
            )
            self.is_trained = True
            self.save_model()
            final_loss = history.history['loss'][-1]
            print(f"✅ LSTM model trained — final loss: {final_loss:.4f}")
        else:
            # ── Statistical fallback path ───────────────────────────────
            # Compute per-reading-index mean to capture a daily pattern,
            # then store summary stats so _simple_forecast can use them.
            flow_series = df['flow'].values
            self._train_avg = float(np.mean(flow_series))
            self._train_std = float(np.std(flow_series))

            # Build a 144-step (12 min × 12 = 1-"day" cycle) mean profile
            cycle = 144
            profile = np.zeros(cycle)
            counts = np.zeros(cycle)
            for i, v in enumerate(flow_series):
                bucket = i % cycle
                profile[bucket] += v
                counts[bucket] += 1
            counts[counts == 0] = 1
            self._day_profile = profile / counts  # shape (144,)

            self.is_trained = True
            self._save_stats()
            print(f"✅ Statistical model trained — avg flow: {self._train_avg:.2f} L/min "
                  f"over {len(flow_series)} readings")

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
        """Statistical forecast — uses the trained day-profile when available,
        otherwise falls back to a sine-wave approximation."""
        steps = hours * 12  # 5-second intervals → 12 per minute → 720 per hour

        # Use trained profile if we have one
        if self.is_trained and hasattr(self, '_day_profile') and self._day_profile is not None:
            profile = self._day_profile
            cycle = len(profile)
            std = self._train_std if hasattr(self, '_train_std') else 1.0
            predictions = []
            for i in range(steps):
                bucket = i % cycle
                noise = np.random.normal(0, std * 0.05)
                predictions.append(max(0, profile[bucket] + noise))
            return predictions

        # Fallback: load recent data and use sine approximation
        df = self.load_data(limit=100)
        if len(df) < 10:
            return [15.0] * steps

        avg_flow = df['flow'].tail(50).mean()
        std_flow = df['flow'].tail(50).std()

        predictions = []
        for i in range(steps):
            hour_factor = 1.0 + 0.2 * np.sin(2 * np.pi * i / 144)
            noise = np.random.normal(0, std_flow * 0.1)
            predictions.append(max(0, avg_flow * hour_factor + noise))
        return predictions
    
    def _save_stats(self):
        """Persist the statistical model params alongside the scaler."""
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            stats = {
                'avg': self._train_avg,
                'std': self._train_std,
                'day_profile': self._day_profile.tolist(),
            }
            stats_path = self.model_path.replace('.h5', '_stats.pkl')
            with open(stats_path, 'wb') as f:
                pickle.dump(stats, f)
            scaler_path = self.model_path.replace('.h5', '_scaler.pkl')
            with open(scaler_path, 'wb') as f:
                pickle.dump(self.scaler, f)
            print(f"💾 Statistical model saved")
        except Exception as e:
            print(f"Error saving stats: {e}")

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
        """Load trained model — LSTM when TF available, stats otherwise."""
        scaler_path = self.model_path.replace('.h5', '_scaler.pkl')
        stats_path = self.model_path.replace('.h5', '_stats.pkl')

        if TENSORFLOW_AVAILABLE:
            try:
                if os.path.exists(self.model_path):
                    self.model = keras.models.load_model(self.model_path)
                    if os.path.exists(scaler_path):
                        with open(scaler_path, 'rb') as f:
                            self.scaler = pickle.load(f)
                    self.is_trained = True
                    print(f"📂 LSTM model loaded from {self.model_path}")
                    return True
                return False
            except Exception as e:
                print(f"Error loading LSTM model: {e}")
                return False
        else:
            # Try to load statistical model
            try:
                if os.path.exists(stats_path):
                    with open(stats_path, 'rb') as f:
                        stats = pickle.load(f)
                    self._train_avg = stats['avg']
                    self._train_std = stats['std']
                    self._day_profile = np.array(stats['day_profile'])
                    if os.path.exists(scaler_path):
                        with open(scaler_path, 'rb') as f:
                            self.scaler = pickle.load(f)
                    self.is_trained = True
                    print("📂 Statistical model loaded")
                    return True
                return False
            except Exception as e:
                print(f"Error loading statistical model: {e}")
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
