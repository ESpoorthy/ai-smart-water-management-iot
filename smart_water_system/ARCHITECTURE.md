# System Architecture - Smart Water Management System

## Overview

The Smart Water Management System (SWMS) is a modular, IoT-based solution for monitoring and managing water distribution infrastructure using AI/ML techniques.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        SENSING LAYER                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  Flow    │  │ Pressure │  │    pH    │  │Turbidity │       │
│  │ Sensor   │  │  Sensor  │  │  Sensor  │  │  Sensor  │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │             │              │              │              │
│       └─────────────┴──────────────┴──────────────┘              │
│                          │                                        │
│                   ┌──────▼──────┐                               │
│                   │ ESP32/Arduino│                               │
│                   │ Microcontroller│                             │
│                   └──────┬──────┘                               │
└──────────────────────────┼────────────────────────────────────┘
                           │ WiFi/HTTP
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   DATA INGESTION LAYER                           │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              FastAPI REST API Server                    │    │
│  │                                                          │    │
│  │  Endpoints:                                             │    │
│  │  • POST /api/sensor-data      (Ingest data)           │    │
│  │  • GET  /api/sensor-data/latest (Query data)          │    │
│  │  • GET  /api/stats             (Statistics)           │    │
│  │                                                          │    │
│  │  Features:                                              │    │
│  │  • Data validation (Pydantic)                          │    │
│  │  • Timestamp generation                                 │    │
│  │  • CORS support                                         │    │
│  └────────────────────┬───────────────────────────────────┘    │
└───────────────────────┼──────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER                               │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │                  SQLite Database                        │    │
│  │                                                          │    │
│  │  Table: sensor_data                                     │    │
│  │  ├── id (PRIMARY KEY)                                   │    │
│  │  ├── timestamp (TEXT)                                   │    │
│  │  ├── flow (REAL)                                        │    │
│  │  ├── pressure (REAL)                                    │    │
│  │  ├── ph (REAL)                                          │    │
│  │  ├── turbidity (REAL)                                   │    │
│  │  └── temperature (REAL)                                 │    │
│  └────────────────────┬───────────────────────────────────┘    │
└───────────────────────┼──────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ANALYTICS LAYER                              │
│                                                                   │
│  ┌──────────────────────────┐  ┌──────────────────────────┐   │
│  │   Leak Detection Model   │  │  Demand Forecasting Model│   │
│  │                          │  │                          │   │
│  │  Algorithm:              │  │  Algorithm:              │   │
│  │  • Isolation Forest      │  │  • LSTM Neural Network   │   │
│  │                          │  │                          │   │
│  │  Input Features:         │  │  Input Features:         │   │
│  │  • Flow rate             │  │  • Historical flow       │   │
│  │  • Pressure              │  │  • Temperature           │   │
│  │                          │  │  • Time patterns         │   │
│  │  Output:                 │  │                          │   │
│  │  • Anomaly score         │  │  Output:                 │   │
│  │  • Leak alert            │  │  • 24-hour forecast      │   │
│  │                          │  │  • Demand predictions    │   │
│  └──────────┬───────────────┘  └──────────┬───────────────┘   │
└─────────────┼──────────────────────────────┼──────────────────┘
              │                              │
              └──────────────┬───────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PRESENTATION LAYER                             │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              Streamlit Dashboard                        │    │
│  │                                                          │    │
│  │  Components:                                            │    │
│  │  ┌────────────────────────────────────────────────┐   │    │
│  │  │  System Status Panel                           │   │    │
│  │  │  • Real-time metrics                           │   │    │
│  │  │  • Color-coded indicators                      │   │    │
│  │  └────────────────────────────────────────────────┘   │    │
│  │                                                          │    │
│  │  ┌────────────────────────────────────────────────┐   │    │
│  │  │  Alert System                                  │   │    │
│  │  │  • pH warnings                                 │   │    │
│  │  │  • Turbidity alerts                            │   │    │
│  │  │  • Leak detection alerts                       │   │    │
│  │  └────────────────────────────────────────────────┘   │    │
│  │                                                          │    │
│  │  ┌────────────────────────────────────────────────┐   │    │
│  │  │  Visualization Charts                          │   │    │
│  │  │  • Flow & Pressure trends                      │   │    │
│  │  │  • Water quality graphs                        │   │    │
│  │  │  • Demand forecast                             │   │    │
│  │  │  • System health                               │   │    │
│  │  └────────────────────────────────────────────────┘   │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
┌─────────┐
│ Sensors │
└────┬────┘
     │ Every 5 seconds
     │ JSON payload
     ▼
┌─────────────┐
│   FastAPI   │
│   Validate  │
│  Timestamp  │
└────┬────────┘
     │
     ▼
┌─────────────┐
│   SQLite    │
│   INSERT    │
└────┬────────┘
     │
     ├──────────────────┬──────────────────┐
     │                  │                  │
     ▼                  ▼                  ▼
┌──────────┐    ┌──────────┐      ┌──────────┐
│Dashboard │    │  Leak    │      │ Forecast │
│  Query   │    │ Detector │      │  Model   │
└──────────┘    └────┬─────┘      └────┬─────┘
                     │                  │
                     │ Anomaly?         │ Prediction
                     ▼                  ▼
                ┌─────────────────────────┐
                │   Dashboard Alerts      │
                └─────────────────────────┘
```

## Component Details

### 1. Sensing Layer

**Purpose**: Collect real-time water quality and flow parameters

**Components**:
- Flow Sensor (YF-S201): Measures water flow rate (L/min)
- Pressure Sensor: Monitors pipe pressure (bar)
- pH Sensor: Measures water acidity/alkalinity
- Turbidity Sensor: Detects water clarity (NTU)
- Temperature Sensor: Monitors water temperature (°C)

**Communication**: 
- Protocol: HTTP POST
- Format: JSON
- Interval: 5 seconds

### 2. Data Ingestion Layer

**Technology**: FastAPI (Python)

**Responsibilities**:
- Receive sensor data via REST API
- Validate data using Pydantic models
- Add timestamps to each reading
- Store data in database
- Provide query endpoints

**API Endpoints**:
```
POST   /api/sensor-data          # Submit sensor reading
GET    /api/sensor-data/latest   # Get recent readings
GET    /api/stats                # Get statistics
DELETE /api/sensor-data/clear    # Clear database
```

### 3. Storage Layer

**Technology**: SQLite

**Schema**:
```sql
CREATE TABLE sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    flow REAL NOT NULL,
    pressure REAL NOT NULL,
    ph REAL NOT NULL,
    turbidity REAL NOT NULL,
    temperature REAL NOT NULL
);
```

**Characteristics**:
- Time-series data storage
- Fast read/write operations
- No external dependencies
- Suitable for prototype/edge deployment

### 4. Analytics Layer

#### 4.1 Leak Detection Model

**Algorithm**: Isolation Forest (Unsupervised Learning)

**Purpose**: Detect anomalies indicating pipe leaks

**Features**:
- Flow rate (L/min)
- Pressure (bar)

**Process**:
1. Train on normal operating data
2. Learn normal patterns
3. Identify outliers as anomalies
4. Generate alerts for detected leaks

**Parameters**:
- Contamination: 10% (expected anomaly rate)
- Estimators: 100 trees
- Random state: 42 (reproducibility)

#### 4.2 Demand Forecasting Model

**Algorithm**: LSTM (Long Short-Term Memory) Neural Network

**Purpose**: Predict water demand for next 24 hours

**Architecture**:
```
Input Layer (12 timesteps, 2 features)
    ↓
LSTM Layer (50 units, return_sequences=True)
    ↓
Dropout (0.2)
    ↓
LSTM Layer (50 units)
    ↓
Dropout (0.2)
    ↓
Dense Layer (25 units, ReLU)
    ↓
Output Layer (1 unit)
```

**Features**:
- Historical flow rate
- Temperature
- Time patterns

**Training**:
- Optimizer: Adam
- Loss: MSE (Mean Squared Error)
- Epochs: 50
- Batch size: 16

### 5. Presentation Layer

**Technology**: Streamlit

**Features**:
- Real-time data visualization
- Interactive charts (Plotly)
- Alert notifications
- Model training interface
- Auto-refresh capability

**Tabs**:
1. Flow & Pressure: Time-series monitoring
2. Water Quality: pH and turbidity tracking
3. Demand Forecast: 24-hour predictions
4. System Health: Overall status

## Security Considerations

1. **API Security**:
   - Input validation via Pydantic
   - CORS configuration
   - Rate limiting (future)

2. **Data Integrity**:
   - Timestamp verification
   - Range validation for sensor values
   - Database constraints

3. **Model Security**:
   - Model versioning
   - Anomaly threshold tuning
   - False positive monitoring

## Scalability

### Current (Prototype):
- Single sensor node
- SQLite database
- Local deployment

### Future (Production):
- Multiple sensor nodes
- PostgreSQL/TimescaleDB
- Cloud deployment (AWS/Azure)
- Load balancing
- Distributed processing

## Performance Metrics

- **Data Ingestion**: ~200 requests/second
- **Query Response**: <100ms
- **Model Inference**: <50ms
- **Dashboard Refresh**: 5-60 seconds (configurable)

## Deployment Options

### 1. Local Development
```bash
python backend/fastapi_server.py
python simulator/sensor_simulator.py
streamlit run dashboard/streamlit_app.py
```

### 2. Docker (Future)
```bash
docker-compose up
```

### 3. Cloud (Future)
- Backend: AWS Lambda / Azure Functions
- Database: RDS / Azure SQL
- Dashboard: EC2 / App Service
- IoT: AWS IoT Core / Azure IoT Hub

## Monitoring & Maintenance

1. **System Health**:
   - API uptime monitoring
   - Database size tracking
   - Model performance metrics

2. **Data Quality**:
   - Missing data detection
   - Outlier analysis
   - Sensor calibration alerts

3. **Model Maintenance**:
   - Periodic retraining
   - Performance degradation detection
   - Version control

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Sensing | ESP32/Arduino | Microcontroller |
| API | FastAPI | REST API server |
| Database | SQLite | Data storage |
| ML Framework | Scikit-learn | Anomaly detection |
| DL Framework | TensorFlow | LSTM forecasting |
| Visualization | Streamlit + Plotly | Dashboard |
| Language | Python 3.8+ | Core development |

## Future Enhancements

1. **Multi-node Support**: Network of sensors
2. **Advanced ML**: Transformer models, GANs
3. **Mobile App**: iOS/Android monitoring
4. **Cloud Integration**: AWS/Azure deployment
5. **Predictive Maintenance**: Equipment failure prediction
6. **SCADA Integration**: Industrial system connectivity
