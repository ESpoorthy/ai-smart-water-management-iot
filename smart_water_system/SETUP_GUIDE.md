# Setup Guide - Smart Water Management System

## Prerequisites

### Software Requirements
- Python 3.8 or higher
- pip (Python package manager)
- Git (optional, for cloning)

### Hardware Requirements (Optional)
- ESP32 or Arduino microcontroller
- Flow sensor (YF-S201)
- Pressure sensor (0-5 bar)
- pH sensor module
- Turbidity sensor
- Temperature sensor (DS18B20)
- Breadboard and jumper wires

## Installation Steps

### Step 1: Download/Clone the Project

```bash
# If using Git
git clone <repository-url>
cd smart_water_system

# Or download and extract the ZIP file
```

### Step 2: Install Python Dependencies

```bash
# Install all required packages
pip install -r requirements.txt

# Or install individually
pip install fastapi uvicorn pydantic requests
pip install numpy pandas scikit-learn
pip install streamlit plotly
pip install tensorflow
```

**Note**: TensorFlow installation may take several minutes.

### Step 3: Verify Installation

```bash
# Check Python version
python --version  # Should be 3.8+

# Verify key packages
python -c "import fastapi; print('FastAPI OK')"
python -c "import streamlit; print('Streamlit OK')"
python -c "import tensorflow; print('TensorFlow OK')"
```

## Running the System

### Option 1: Automated Startup (Linux/Mac)

```bash
# Make script executable
chmod +x run_system.sh

# Run all components
./run_system.sh
```

### Option 2: Manual Startup (All Platforms)

Open three separate terminal windows:

**Terminal 1 - Backend API:**
```bash
cd smart_water_system
python backend/fastapi_server.py
```

**Terminal 2 - Sensor Simulator:**
```bash
cd smart_water_system
python simulator/sensor_simulator.py
```

**Terminal 3 - Dashboard:**
```bash
cd smart_water_system
streamlit run dashboard/streamlit_app.py
```

### Step 4: Access the System

- **Dashboard**: http://localhost:8501
- **API Documentation**: http://localhost:8000/docs
- **API Base**: http://localhost:8000

## First-Time Setup

### 1. Wait for Data Collection

The system needs data before AI models can be trained:
- Wait 5-10 minutes for simulator to generate data
- Monitor the simulator terminal for readings
- Check dashboard shows incoming data

### 2. Train AI Models

In the dashboard sidebar:

1. Click "Train Leak Detector"
   - Requires at least 50 readings
   - Takes ~10 seconds
   - Success message will appear

2. Click "Train Demand Forecaster"
   - Requires at least 100 readings
   - Takes ~1-2 minutes
   - Success message will appear

### 3. Verify Functionality

- Check real-time charts are updating
- Verify alerts appear when events occur
- Generate a demand forecast
- Observe leak detection during simulated events

## Configuration

### Adjust Sensor Simulator

Edit `simulator/sensor_simulator.py`:

```python
# Change base values
self.base_flow = 15.0          # Normal flow rate
self.base_pressure = 2.5       # Normal pressure
self.base_ph = 7.2             # Normal pH

# Change event probabilities
if random.random() < 0.02:     # 2% leak chance
if random.random() < 0.015:    # 1.5% contamination chance

# Change data interval
simulator.run(interval=5)      # Seconds between readings
```

### Adjust Dashboard Refresh

In the dashboard sidebar:
- Toggle "Auto-refresh"
- Adjust "Refresh interval" slider (5-60 seconds)
- Adjust "Data points to display" slider (50-500)

### Adjust Alert Thresholds

Edit `dashboard/streamlit_app.py`:

```python
# pH thresholds
if latest_data['ph'] < 6:      # Low pH alert
if latest_data['ph'] > 8:      # High pH alert

# Turbidity threshold
if latest_data['turbidity'] > 5:  # High turbidity alert
```

## Troubleshooting

### Issue: "Module not found" errors

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade

# Or install missing package specifically
pip install <package-name>
```

### Issue: Dashboard shows "No data available"

**Solution:**
1. Verify backend is running (check Terminal 1)
2. Verify simulator is running (check Terminal 2)
3. Check database file exists: `database/water.db`
4. Restart simulator if needed

### Issue: Port already in use

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000  # Mac/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process
kill -9 <PID>  # Mac/Linux
taskkill /PID <PID> /F  # Windows

# Or change port in code
uvicorn.run(app, host="0.0.0.0", port=8001)
```

### Issue: TensorFlow not installing

**Solution:**
```bash
# Try specific version
pip install tensorflow==2.15.0

# Or use CPU-only version
pip install tensorflow-cpu

# On Mac M1/M2
pip install tensorflow-macos
pip install tensorflow-metal
```

### Issue: AI models not training

**Solution:**
1. Ensure enough data (50+ readings for leak detector, 100+ for forecaster)
2. Check database has data: `sqlite3 database/water.db "SELECT COUNT(*) FROM sensor_data;"`
3. Check terminal for error messages
4. Try clearing data and restarting: DELETE /api/sensor-data/clear

### Issue: Charts not updating

**Solution:**
1. Enable "Auto-refresh" in sidebar
2. Manually refresh browser (F5)
3. Check browser console for errors (F12)
4. Verify data is being received (check API endpoint)

## Testing the System

### Test 1: API Endpoint

```bash
# Test sensor data submission
curl -X POST http://localhost:8000/api/sensor-data \
  -H "Content-Type: application/json" \
  -d '{
    "flow": 15.2,
    "pressure": 2.1,
    "ph": 7.3,
    "turbidity": 3.2,
    "temperature": 26.5
  }'

# Expected response:
# {"status":"success","message":"Data stored successfully","timestamp":"..."}
```

### Test 2: Data Retrieval

```bash
# Get latest 10 readings
curl http://localhost:8000/api/sensor-data/latest?limit=10

# Get statistics
curl http://localhost:8000/api/stats
```

### Test 3: Simulated Events

Watch the simulator terminal for:
- "🚨 LEAK EVENT TRIGGERED!" - Flow/pressure will drop
- "⚠️ CONTAMINATION EVENT TRIGGERED!" - Turbidity/pH will spike

Check dashboard for corresponding alerts.

### Test 4: AI Models

```bash
# Test leak detector
cd smart_water_system
python ai_models/anomaly_detection.py

# Test forecaster
python ai_models/lstm_forecast.py
```

## Hardware Setup (Optional)

### ESP32 Wiring Diagram

```
ESP32                    Sensors
-----                    -------
GPIO 4  ────────────────> Flow Sensor (Signal)
GPIO 34 ────────────────> Pressure Sensor (Analog)
GPIO 35 ────────────────> pH Sensor (Analog)
GPIO 32 ────────────────> Turbidity Sensor (Analog)
GPIO 33 ────────────────> Temperature Sensor (Data)

3.3V    ────────────────> Sensors VCC
GND     ────────────────> Sensors GND
```

### Arduino Code Template

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* serverUrl = "http://YOUR_SERVER_IP:8000/api/sensor-data";

// Pin definitions
#define FLOW_PIN 4
#define PRESSURE_PIN 34
#define PH_PIN 35
#define TURBIDITY_PIN 32
#define TEMP_PIN 33

void setup() {
  Serial.begin(115200);
  
  // Connect to WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
  
  // Initialize sensors
  pinMode(FLOW_PIN, INPUT);
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

void sendData(float flow, float pressure, float ph, float turbidity, float temp) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");
    
    // Create JSON payload
    StaticJsonDocument<200> doc;
    doc["flow"] = flow;
    doc["pressure"] = pressure;
    doc["ph"] = ph;
    doc["turbidity"] = turbidity;
    doc["temperature"] = temp;
    
    String jsonString;
    serializeJson(doc, jsonString);
    
    // Send POST request
    int httpCode = http.POST(jsonString);
    
    if (httpCode > 0) {
      Serial.printf("Data sent: %d\n", httpCode);
    } else {
      Serial.printf("Error: %s\n", http.errorToString(httpCode).c_str());
    }
    
    http.end();
  }
}

// Implement sensor reading functions
float readFlowSensor() {
  // Your flow sensor code
  return 15.0;
}

float readPressureSensor() {
  // Your pressure sensor code
  return 2.5;
}

float readPHSensor() {
  // Your pH sensor code
  return 7.2;
}

float readTurbiditySensor() {
  // Your turbidity sensor code
  return 2.0;
}

float readTemperatureSensor() {
  // Your temperature sensor code
  return 25.0;
}
```

## Next Steps

1. **Explore the Dashboard**: Familiarize yourself with all tabs and features
2. **Observe Events**: Watch for simulated leaks and contamination
3. **Train Models**: Ensure both AI models are trained
4. **Customize**: Adjust thresholds and parameters to your needs
5. **Integrate Hardware**: Connect real sensors if available

## Support

For issues or questions:
1. Check this guide first
2. Review README.md for architecture details
3. Check ARCHITECTURE.md for technical details
4. Open an issue on GitHub

## Quick Reference

| Component | Command | Port |
|-----------|---------|------|
| Backend | `python backend/fastapi_server.py` | 8000 |
| Simulator | `python simulator/sensor_simulator.py` | - |
| Dashboard | `streamlit run dashboard/streamlit_app.py` | 8501 |

| File | Purpose |
|------|---------|
| `water.db` | SQLite database |
| `leak_model.pkl` | Trained leak detector |
| `lstm_model.h5` | Trained forecaster |

Happy monitoring! 💧
