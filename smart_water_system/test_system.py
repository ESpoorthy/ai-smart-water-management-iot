"""
System Test Script
Tests all components of the Smart Water Management System
"""
import requests
import time
import sqlite3
import os

def test_api():
    """Test FastAPI backend"""
    print("\n🧪 Testing API Backend...")
    
    try:
        # Test sensor data submission
        data = {
            "flow": 15.2,
            "pressure": 2.1,
            "ph": 7.3,
            "turbidity": 3.2,
            "temperature": 26.5
        }
        
        response = requests.post("http://localhost:8000/api/sensor-data", json=data, timeout=5)
        
        if response.status_code == 200:
            print("✅ API POST endpoint working")
        else:
            print(f"❌ API POST failed: {response.status_code}")
            return False
        
        # Test data retrieval
        response = requests.get("http://localhost:8000/api/sensor-data/latest?limit=10", timeout=5)
        
        if response.status_code == 200:
            print("✅ API GET endpoint working")
        else:
            print(f"❌ API GET failed: {response.status_code}")
            return False
        
        # Test statistics
        response = requests.get("http://localhost:8000/api/stats", timeout=5)
        
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Statistics endpoint working - {stats['total_records']} records")
        else:
            print(f"❌ Statistics failed: {response.status_code}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def test_database():
    """Test database connectivity"""
    print("\n🧪 Testing Database...")
    
    try:
        if not os.path.exists("database/water.db"):
            print("❌ Database file not found")
            return False
        
        conn = sqlite3.connect("database/water.db")
        cursor = conn.cursor()
        
        # Check table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sensor_data'")
        if cursor.fetchone():
            print("✅ Database table exists")
        else:
            print("❌ Database table not found")
            return False
        
        # Check data count
        cursor.execute("SELECT COUNT(*) FROM sensor_data")
        count = cursor.fetchone()[0]
        print(f"✅ Database has {count} records")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_ai_models():
    """Test AI models"""
    print("\n🧪 Testing AI Models...")
    
    try:
        from ai_models.anomaly_detection import LeakDetector
        from ai_models.lstm_forecast import DemandForecaster
        
        # Test leak detector
        detector = LeakDetector()
        if detector.load_model():
            print("✅ Leak detector model loaded")
            
            # Test prediction
            is_anomaly, score = detector.predict(15.0, 2.5)
            print(f"✅ Leak detector prediction working (anomaly={is_anomaly})")
        else:
            print("⚠️  Leak detector model not trained yet")
        
        # Test forecaster
        forecaster = DemandForecaster()
        if forecaster.load_model():
            print("✅ Forecaster model loaded")
        else:
            print("⚠️  Forecaster model not trained yet")
        
        return True
        
    except Exception as e:
        print(f"❌ AI models test failed: {e}")
        return False

def test_simulator():
    """Test sensor simulator"""
    print("\n🧪 Testing Sensor Simulator...")
    
    try:
        from simulator.sensor_simulator import WaterSensorSimulator
        
        simulator = WaterSensorSimulator()
        
        # Generate test data
        data = simulator.get_sensor_reading()
        
        if all(key in data for key in ['flow', 'pressure', 'ph', 'turbidity', 'temperature']):
            print("✅ Simulator generating valid data")
            print(f"   Sample: Flow={data['flow']:.2f}, Pressure={data['pressure']:.2f}")
        else:
            print("❌ Simulator data incomplete")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Simulator test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("🌊 Smart Water Management System - Test Suite")
    print("=" * 60)
    
    results = {
        "API": test_api(),
        "Database": test_database(),
        "AI Models": test_ai_models(),
        "Simulator": test_simulator()
    }
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    for component, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{component:20s} {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed. Check the output above.")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    main()
