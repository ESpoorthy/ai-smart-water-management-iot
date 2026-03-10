# 💧 AI-Driven Smart Water Management System (SWMS)

A complete IoT-based water distribution monitoring system with real-time analytics, AI-powered leak detection, and demand forecasting.

## 🎯 Features

- **Real-time Monitoring**: Track water flow, pressure, pH, turbidity, and temperature
- **AI Leak Detection**: Isolation Forest algorithm detects anomalies in flow/pressure
- **Demand Forecasting**: LSTM neural network predicts 24-hour water demand
- **Interactive Dashboard**: Streamlit-based real-time visualization
- **Alert System**: Automatic alerts for water quality issues and leaks
- **Event Simulation**: Simulate pipe leaks and contamination events

## 🏗️ System Architecture

```
┌─────────────────┐
│  IoT Sensors    │  (Simulated or Real)
│  - Flow Rate    │
│  - Pressure     │
│  - pH           │
│  - Turbidity    │
│  - Temperature  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI        │  REST API
│  Backend        │  Data Validation
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SQLite         │  Time-series Data
│  Database       │  Storage
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  AI Models      │
│  - Leak Detect  │  Isolation Forest
│  - Forecasting  │  LSTM Network
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Streamlit      │  Real-time Dashboard
│  Dashboard      │  Visualization
└─────────────────┘
```

## 📁 Project Structure

```
smart_water_system/
│
├── backend/
│   └── fastapi_server.py       # REST API server
│
├── ai_models/
│   ├── anomaly_detection.py    # Leak detection (Isolation Forest)
│   └── lstm_forecast.py        # Demand forecasting (LSTM)
│
├── dashboard/
│   └── streamlit_app.py        # Interactive dashboard
│
├── simulator/
│   └── sensor_simulator.py     # IoT sensor simulator
│
├── database/
│   └── water.db                # SQLite database (auto-created)
│
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or navigate to the project directory
cd smart_water_system

# Install dependencies
pip install -r requirements.txt
```

### 2. Start the Backend API

```bash
# Terminal 1: Start FastAPI server
cd smart_water_system
python backend/fastapi_server.py
```

The API will be available at `http://localhost:8000`

### 3. Start the Sensor Simulator

```bash
# Terminal 2: Start sensor simulator
cd smart_water_system
python simulator/sensor_simulator.py
```

The simulator will:
- Send data every 5 seconds
- Randomly trigger leak events (2% chance)
- Randomly trigger contamination events (1.5% chance)

### 4. Launch the Dashboard

```bash
# Terminal 3: Start Streamlit dashboard
cd smart_water_system
streamlit run dashboard/streamlit_app.py
```

The dashboard will open at `http://localhost:8501`

## 🔧 Configuration

### Sensor Simulator Settings

Edit `simulator/sensor_simulator.py`:

```python
# Base values
self.base_flow = 15.0          # L/min
self.base_pressure = 2.5       # bar
self.base_ph = 7.2
self.base_turbidity = 2.0      # NTU
self.base_temperature = 25.0   # Celsius
```

### API Endpoints

- `POST /api/sensor-data` - Submit sensor readings
- `GET /api/sensor-data/latest?limit=100` - Get latest readings
- `GET /api/stats` - Get statistical summary
- `DELETE /api/sensor-data/clear` - Clear all data

## 🤖 AI Models

### 1. Leak Detection (Isolation Forest)

**Purpose**: Detect anomalies in water flow and pressure that indicate leaks

**Algorithm**: Isolation Forest (unsupervised learning)

**Features**:
- Flow rate
- Pressure

**Training**:
```python
from ai_models.anomaly_detection import LeakDetector

detector = LeakDetector()
detector.train()  # Trains on last 500 readings
```

**Detection**:
- Anomaly score < threshold → Leak detected
- Triggers alert in dashboard

### 2. Demand Forecasting (LSTM)

**Purpose**: Predict water demand for next 24 hours

**Algorithm**: LSTM (Long Short-Term Memory) neural network

**Features**:
- Historical flow rate
- Temperature
- Time patterns

**Architecture**:
```
Input (12 timesteps, 2 features)
    ↓
LSTM Layer (50 units) + Dropout
    ↓
LSTM Layer (50 units) + Dropout
    ↓
Dense Layer (25 units)
    ↓
Output (1 value - predicted flow)
```

**Training**:
```python
from ai_models.lstm_forecast import DemandForecaster

forecaster = DemandForecaster()
forecaster.train(epochs=50)
```

## 📊 Dashboard Features

### System Status Panel
- Real-time metrics for all sensors
- Color-coded status indicators
- Delta changes from previous reading

### Active Alerts
- pH level warnings (< 6 or > 8)
- High turbidity alerts (> 5 NTU)
- AI-detected leak alerts

### Charts
1. **Flow & Pressure**: Time-series trends
2. **Water Quality**: pH and turbidity monitoring
3. **Demand Forecast**: 24-hour prediction
4. **System Health**: Temperature and data quality

### AI Model Training
- Train leak detector from sidebar
- Train demand forecaster from sidebar
- Models auto-save after training

## 🎮 Simulated Events

The simulator can trigger realistic events:

### Leak Event
- 60% reduction in flow rate
- 50% reduction in pressure
- Duration: 20-40 readings (100-200 seconds)
- Probability: 2% per reading

### Contamination Event
- 3.5x increase in turbidity
- pH increase by 1.5-2.5 units
- Duration: 15-30 readings (75-150 seconds)
- Probability: 1.5% per reading

## 🔌 Hardware Integration (Optional)

To use real sensors instead of simulation:

### Required Hardware
- ESP32 or Arduino microcontroller
- YF-S201 Flow Sensor
- Pressure Sensor (0-5 bar)
- pH Sensor Module
- Turbidity Sensor
- DS18B20 Temperature Sensor

### Connection Example (ESP32)

```cpp
// Arduino/ESP32 code example
#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "YOUR_WIFI";
const char* password = "YOUR_PASSWORD";
const char* serverUrl = "http://YOUR_SERVER:8000/api/sensor-data";

void setup() {
  // Initialize sensors
  // Connect to WiFi
}

void loop() {
  // Read sensors
  float flow = readFlowSensor();
  float pressure = readPressureSensor();
  float ph = readPHSensor();
  float turbidity = readTurbiditySensor();
  float temperature = readTemperatureSensor();
  
  // Send to API
  sendData(flow, pressure, ph, turbidity, temperature);
  
  delay(5000);  // 5 seconds
}
```

## 📈 Data Flow

```
Sensors → API → Database → AI Models → Dashboard
   ↓                           ↓
Validation              Leak Detection
Timestamp              Demand Forecast
Storage                    Alerts
```

## 🛠️ Troubleshooting

### Dashboard shows "No data available"
- Ensure backend API is running
- Ensure sensor simulator is running
- Check database file exists: `database/water.db`

### AI models not working
- Train models from dashboard sidebar
- Ensure at least 50-100 readings in database
- Check TensorFlow installation for LSTM

### Simulator connection errors
- Verify API is running on port 8000
- Check firewall settings
- Ensure correct API URL in simulator

## 📝 API Usage Examples

### Submit Sensor Data
```bash
curl -X POST http://localhost:8000/api/sensor-data \
  -H "Content-Type: application/json" \
  -d '{
    "flow": 15.2,
    "pressure": 2.1,
    "ph": 7.3,
    "turbidity": 3.2,
    "temperature": 26.5
  }'
```

### Get Latest Data
```bash
curl http://localhost:8000/api/sensor-data/latest?limit=10
```

### Get Statistics
```bash
curl http://localhost:8000/api/stats
```

## 🌍 Use Cases

- **Municipal Water Systems**: Monitor city water distribution
- **Industrial Plants**: Track process water quality
- **Smart Buildings**: Optimize water usage
- **Agriculture**: Irrigation system monitoring
- **Research**: Water quality studies

## 🔮 Future Enhancements

- [ ] Multi-sensor network support
- [ ] Mobile app integration
- [ ] Cloud deployment (AWS/Azure)
- [ ] Advanced ML models (Transformer, GAN)
- [ ] Predictive maintenance scheduling
- [ ] Water quality classification
- [ ] Integration with SCADA systems
- [ ] Blockchain for data integrity

## 📄 License

MIT License - See LICENSE file

## 👥 Contributing

Contributions welcome! Please submit pull requests or open issues.

## 📧 Support

For questions or issues, please open a GitHub issue.

---

**Built with ❤️ for sustainable water management**
