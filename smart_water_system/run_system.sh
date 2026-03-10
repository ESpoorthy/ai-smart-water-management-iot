#!/bin/bash

# Smart Water Management System - Startup Script

echo "💧 Starting Smart Water Management System..."
echo "=========================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check if dependencies are installed
if ! python3 -c "import fastapi" &> /dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Create database directory
mkdir -p database

echo ""
echo "🚀 Starting components..."
echo ""

# Start FastAPI backend
echo "1️⃣  Starting FastAPI backend on port 8000..."
python3 backend/fastapi_server.py &
BACKEND_PID=$!
sleep 3

# Start sensor simulator
echo "2️⃣  Starting sensor simulator..."
python3 simulator/sensor_simulator.py &
SIMULATOR_PID=$!
sleep 2

# Start Streamlit dashboard
echo "3️⃣  Starting Streamlit dashboard on port 8501..."
streamlit run dashboard/streamlit_app.py &
DASHBOARD_PID=$!

echo ""
echo "✅ All components started!"
echo ""
echo "📊 Dashboard: http://localhost:8501"
echo "🔌 API: http://localhost:8000"
echo "📡 Simulator: Running"
echo ""
echo "Press Ctrl+C to stop all components..."

# Wait for Ctrl+C
trap "echo ''; echo '🛑 Stopping all components...'; kill $BACKEND_PID $SIMULATOR_PID $DASHBOARD_PID; exit" INT
wait
