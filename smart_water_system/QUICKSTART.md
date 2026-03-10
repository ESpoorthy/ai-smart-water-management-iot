# Quick Start Guide

Get the Smart Water Management System running in 5 minutes!

## Prerequisites

- Python 3.8 or higher installed
- Terminal/Command Prompt access

## Step 1: Install Dependencies (2 minutes)

```bash
cd smart_water_system
pip install -r requirements.txt
```

Wait for all packages to install. This may take a few minutes, especially TensorFlow.

## Step 2: Start the System (1 minute)

### Option A: Automated (Mac/Linux)

```bash
chmod +x run_system.sh
./run_system.sh
```

### Option B: Manual (All Platforms)

Open 3 terminal windows:

**Terminal 1 - Backend:**
```bash
cd smart_water_system
python backend/fastapi_server.py
```

**Terminal 2 - Simulator:**
```bash
cd smart_water_system
python simulator/sensor_simulator.py
```

**Terminal 3 - Dashboard:**
```bash
cd smart_water_system
streamlit run dashboard/streamlit_app.py
```

## Step 3: Access the Dashboard (30 seconds)

Open your browser and go to:
```
http://localhost:8501
```

You should see the dashboard with real-time data!

## Step 4: Train AI Models (1 minute)

Wait 2-3 minutes for data to accumulate, then:

1. In the dashboard sidebar, click **"Train Leak Detector"**
2. Wait ~10 seconds
3. Click **"Train Demand Forecaster"**
4. Wait ~1-2 minutes

Done! Your system is now fully operational with AI capabilities.

## What to Expect

### Real-time Monitoring
- Flow rate, pressure, pH, turbidity, and temperature charts
- Auto-refreshing every 10 seconds
- Color-coded status indicators

### Simulated Events
The simulator will randomly trigger:
- **Leak events** (2% chance) - Watch flow/pressure drop
- **Contamination events** (1.5% chance) - Watch turbidity spike

### AI Features
- **Leak Detection**: Alerts when anomalies detected
- **Demand Forecasting**: Click "Generate Forecast" in the dashboard

## Quick Test

Verify everything works:

```bash
cd smart_water_system
python test_system.py
```

All tests should pass ✅

## Troubleshooting

### "Module not found" error
```bash
pip install -r requirements.txt --upgrade
```

### "No data available" in dashboard
- Wait 30 seconds for simulator to send data
- Check Terminal 2 shows sensor readings
- Refresh browser (F5)

### Port already in use
```bash
# Kill process on port 8000
lsof -i :8000  # Find PID
kill -9 <PID>  # Kill it
```

## Next Steps

- Explore all dashboard tabs
- Watch for simulated events
- Generate demand forecasts
- Read SETUP_GUIDE.md for detailed configuration
- Check ARCHITECTURE.md to understand the system

## Quick Commands

| Action | Command |
|--------|---------|
| Start backend | `python backend/fastapi_server.py` |
| Start simulator | `python simulator/sensor_simulator.py` |
| Start dashboard | `streamlit run dashboard/streamlit_app.py` |
| Run tests | `python test_system.py` |
| View API docs | Open `http://localhost:8000/docs` |

## Support

Having issues? Check:
1. SETUP_GUIDE.md - Detailed troubleshooting
2. README.md - Full documentation
3. ARCHITECTURE.md - Technical details

Happy monitoring! 💧
