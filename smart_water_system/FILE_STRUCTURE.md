# File Structure - Smart Water Management System

## Complete Directory Tree

```
smart_water_system/
│
├── 📁 backend/                      # Backend API Server
│   ├── __init__.py                  # Package initializer
│   └── fastapi_server.py            # FastAPI REST API server
│
├── 📁 ai_models/                    # AI/ML Models
│   ├── __init__.py                  # Package initializer
│   ├── anomaly_detection.py         # Leak detection (Isolation Forest)
│   └── lstm_forecast.py             # Demand forecasting (LSTM)
│
├── 📁 dashboard/                    # Web Dashboard
│   ├── __init__.py                  # Package initializer
│   └── streamlit_app.py             # Streamlit dashboard application
│
├── 📁 simulator/                    # IoT Sensor Simulator
│   ├── __init__.py                  # Package initializer
│   └── sensor_simulator.py          # Sensor data generator
│
├── 📁 hardware/                     # Hardware Integration
│   └── esp32_example.ino            # ESP32/Arduino example code
│
├── 📁 database/                     # Database Directory
│   ├── .gitkeep                     # Git directory placeholder
│   └── water.db                     # SQLite database (auto-created)
│
├── 📄 requirements.txt              # Python dependencies
├── 📄 .gitignore                    # Git ignore rules
├── 📄 run_system.sh                 # System startup script (Mac/Linux)
├── 📄 test_system.py                # Test suite
├── 📄 config.example.py             # Configuration template
│
├── 📖 README.md                     # Main project documentation
├── 📖 QUICKSTART.md                 # 5-minute quick start guide
├── 📖 SETUP_GUIDE.md                # Detailed setup instructions
├── 📖 ARCHITECTURE.md               # Technical architecture
├── 📖 DIAGRAMS.md                   # Visual system diagrams
├── 📖 FEATURES.md                   # Complete feature list
├── 📖 PROJECT_SUMMARY.md            # Executive summary
└── 📖 FILE_STRUCTURE.md             # This file
```

## File Descriptions

### Backend Components

#### `backend/fastapi_server.py` (150 lines)
- FastAPI application setup
- REST API endpoints
- Database initialization
- Data validation with Pydantic
- CORS middleware configuration

**Key Functions:**
- `init_database()` - Create database schema
- `receive_sensor_data()` - POST endpoint for sensor data
- `get_latest_data()` - GET endpoint for recent readings
- `get_statistics()` - GET endpoint for data statistics
- `clear_data()` - DELETE endpoint for testing

### AI Models

#### `ai_models/anomaly_detection.py` (200 lines)
- Isolation Forest implementation
- Leak detection logic
- Model training and persistence
- Anomaly scoring

**Key Classes:**
- `LeakDetector` - Main leak detection class

**Key Methods:**
- `train()` - Train the model on historical data
- `predict()` - Detect anomalies in new readings
- `save_model()` - Persist trained model
- `load_model()` - Load existing model

#### `ai_models/lstm_forecast.py` (250 lines)
- LSTM neural network implementation
- Time-series forecasting
- Sequence preparation
- Model training and prediction

**Key Classes:**
- `DemandForecaster` - Main forecasting class

**Key Methods:**
- `train()` - Train LSTM model
- `predict_next_hours()` - Generate 24-hour forecast
- `prepare_sequences()` - Create training sequences
- `save_model()` - Save trained model

### Dashboard

#### `dashboard/streamlit_app.py` (300 lines)
- Streamlit web application
- Real-time data visualization
- Interactive charts with Plotly
- Alert system
- Model training interface

**Key Functions:**
- `load_latest_data()` - Query database
- `check_alerts()` - Evaluate alert conditions
- `main()` - Main dashboard application

**Dashboard Tabs:**
1. Flow & Pressure - Time-series monitoring
2. Water Quality - pH and turbidity
3. Demand Forecast - 24-hour predictions
4. System Health - Overall status

### Simulator

#### `simulator/sensor_simulator.py` (150 lines)
- IoT sensor data generation
- Event simulation (leaks, contamination)
- HTTP client for API communication
- Realistic data patterns

**Key Classes:**
- `WaterSensorSimulator` - Main simulator class

**Key Methods:**
- `generate_normal_data()` - Create baseline readings
- `simulate_leak()` - Trigger leak event
- `simulate_contamination()` - Trigger contamination
- `send_data()` - POST to API

### Hardware

#### `hardware/esp32_example.ino` (250 lines)
- Complete ESP32/Arduino code
- WiFi connectivity
- Sensor reading functions
- HTTP POST implementation
- JSON payload creation

**Key Functions:**
- `readFlowSensor()` - Flow rate measurement
- `readPressureSensor()` - Pressure reading
- `readPHSensor()` - pH measurement
- `readTurbiditySensor()` - Turbidity reading
- `readTemperatureSensor()` - Temperature reading
- `sendData()` - HTTP POST to API

### Configuration & Scripts

#### `requirements.txt` (10 lines)
Python package dependencies:
- fastapi==0.104.1
- uvicorn==0.24.0
- streamlit==1.28.1
- tensorflow==2.15.0
- scikit-learn==1.3.2
- pandas==2.0.3
- numpy==1.24.3
- plotly==5.18.0
- requests==2.31.0
- pydantic==2.5.0

#### `run_system.sh` (40 lines)
Automated startup script:
- Dependency checking
- Component startup
- Process management
- Error handling

#### `test_system.py` (150 lines)
Comprehensive test suite:
- API endpoint tests
- Database connectivity tests
- AI model tests
- Simulator tests

#### `config.example.py` (100 lines)
Configuration template:
- System parameters
- Sensor thresholds
- Alert settings
- Feature flags

### Documentation Files

#### `README.md` (200 lines)
- Project overview
- Quick start guide
- Feature highlights
- Technology stack
- Usage instructions

#### `QUICKSTART.md` (100 lines)
- 5-minute setup
- Essential commands
- Quick troubleshooting
- Access points

#### `SETUP_GUIDE.md` (400 lines)
- Detailed installation
- Configuration options
- Hardware setup
- Troubleshooting guide
- Testing procedures

#### `ARCHITECTURE.md` (500 lines)
- System architecture
- Component details
- Data flow diagrams
- Technology stack
- Deployment options

#### `DIAGRAMS.md` (400 lines)
- Visual diagrams
- Flow charts
- Wiring diagrams
- State machines
- Deployment architecture

#### `FEATURES.md` (300 lines)
- Complete feature list
- Capabilities
- Metrics
- Future roadmap

#### `PROJECT_SUMMARY.md` (400 lines)
- Executive summary
- Technical specifications
- Performance metrics
- Success criteria

## File Statistics

### Code Files
- **Python files**: 11
- **Arduino files**: 1
- **Total code lines**: ~2,500+

### Documentation Files
- **Markdown files**: 8
- **Total doc lines**: ~2,500+

### Configuration Files
- **Config files**: 4
- **Script files**: 2

## File Sizes (Approximate)

| File | Lines | Size |
|------|-------|------|
| fastapi_server.py | 150 | 5 KB |
| anomaly_detection.py | 200 | 7 KB |
| lstm_forecast.py | 250 | 9 KB |
| streamlit_app.py | 300 | 11 KB |
| sensor_simulator.py | 150 | 6 KB |
| esp32_example.ino | 250 | 8 KB |
| test_system.py | 150 | 6 KB |
| SETUP_GUIDE.md | 400 | 15 KB |
| ARCHITECTURE.md | 500 | 20 KB |
| DIAGRAMS.md | 400 | 18 KB |

## Generated Files (Runtime)

These files are created automatically when the system runs:

```
database/
└── water.db                    # SQLite database (auto-created)

ai_models/
├── leak_model.pkl              # Trained leak detector (after training)
├── lstm_model.h5               # Trained LSTM model (after training)
└── lstm_model_scaler.pkl       # Scaler for LSTM (after training)

logs/                           # Log files (if logging enabled)
└── swms.log
```

## Import Dependencies

### Backend Dependencies
```python
fastapi, uvicorn, pydantic, sqlite3
```

### AI Model Dependencies
```python
numpy, pandas, scikit-learn, tensorflow, pickle
```

### Dashboard Dependencies
```python
streamlit, plotly, pandas, sqlite3
```

### Simulator Dependencies
```python
requests, time, random, numpy
```

## Module Relationships

```
┌─────────────────┐
│   Dashboard     │
│ (streamlit_app) │
└────────┬────────┘
         │ imports
         ▼
┌─────────────────┐
│   AI Models     │
│ (leak_detector, │
│  forecaster)    │
└────────┬────────┘
         │ reads from
         ▼
┌─────────────────┐
│    Database     │
│   (water.db)    │
└────────┬────────┘
         │ written by
         ▼
┌─────────────────┐
│   Backend API   │
│ (fastapi_server)│
└────────┬────────┘
         │ receives from
         ▼
┌─────────────────┐
│   Simulator     │
│ (sensor_sim)    │
└─────────────────┘
```

## File Access Patterns

### Read Operations
- Dashboard → Database (frequent)
- AI Models → Database (on-demand)
- Test Suite → All components

### Write Operations
- Backend API → Database (continuous)
- AI Models → Model files (on training)
- Simulator → Backend API (every 5s)

## Backup Recommendations

### Critical Files (Backup Required)
- `database/water.db` - All sensor data
- `ai_models/*.pkl` - Trained models
- `ai_models/*.h5` - LSTM models
- `config.py` - Custom configuration

### Source Files (Version Control)
- All `.py` files
- All `.md` files
- `requirements.txt`
- `.gitignore`

### Temporary Files (No Backup Needed)
- `__pycache__/` directories
- `*.pyc` files
- Log files

## Development Workflow

1. **Edit** source files in respective directories
2. **Test** using `test_system.py`
3. **Run** using `run_system.sh` or manual commands
4. **Monitor** via dashboard at localhost:8501
5. **Debug** using logs and error messages

## Deployment Checklist

- [ ] All dependencies installed
- [ ] Database directory created
- [ ] Configuration file customized
- [ ] Scripts made executable
- [ ] Firewall rules configured
- [ ] Ports available (8000, 8501)
- [ ] Documentation reviewed

---

**Total Project Size**: ~50 KB (code) + ~100 KB (docs) = ~150 KB

**File Count**: 23 files + 6 directories

**Completion**: 100% ✅
