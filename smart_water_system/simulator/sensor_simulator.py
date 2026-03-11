"""
IoT Sensor Simulator for Smart Water Management System
Generates realistic sensor data and simulates events like leaks and contamination
"""
import requests
import time
import random
import numpy as np
from datetime import datetime

class WaterSensorSimulator:
    def __init__(self, api_url="http://localhost:8000"):
        self.api_url = api_url
        self.base_flow = 15.0  # L/min
        self.base_pressure = 2.5  # bar
        self.base_ph = 7.2
        self.base_turbidity = 2.0  # NTU
        self.base_temperature = 25.0  # Celsius
        
        # Event flags
        self.leak_active = False
        self.contamination_active = False
        self.event_duration = 0
        
    def generate_normal_data(self):
        """Generate normal sensor readings with slight variations"""
        data = {
            "flow": self.base_flow + random.uniform(-1.0, 1.0),
            "pressure": self.base_pressure + random.uniform(-0.2, 0.2),
            "ph": self.base_ph + random.uniform(-0.3, 0.3),
            "turbidity": self.base_turbidity + random.uniform(-0.5, 0.5),
            "temperature": self.base_temperature + random.uniform(-1.0, 1.0)
        }
        
        # Ensure values are within valid ranges
        data["flow"] = max(0, data["flow"])
        data["pressure"] = max(0, data["pressure"])
        data["ph"] = max(0, min(14, data["ph"]))
        data["turbidity"] = max(0, data["turbidity"])
        
        return data
    
    def simulate_leak(self, data):
        """Simulate pipe leak - sudden drop in flow and pressure"""
        data["flow"] *= 0.4  # 60% reduction in flow
        data["pressure"] *= 0.5  # 50% reduction in pressure
        return data
    
    def simulate_contamination(self, data):
        """Simulate water contamination - spike in turbidity and pH change"""
        data["turbidity"] *= 3.5  # Significant increase in turbidity
        data["ph"] += random.uniform(1.5, 2.5)  # pH increases
        return data
    
    def trigger_random_events(self):
        """Randomly trigger leak or contamination events"""
        if not self.leak_active and not self.contamination_active:
            # 2% chance of leak
            if random.random() < 0.02:
                self.leak_active = True
                self.event_duration = random.randint(20, 40)  # 20-40 readings
                print("\n" + "=" * 70)
                print("[EVENT] LEAK EVENT TRIGGERED")
                print("=" * 70)
            
            # 1.5% chance of contamination
            elif random.random() < 0.015:
                self.contamination_active = True
                self.event_duration = random.randint(15, 30)
                print("\n" + "=" * 70)
                print("[EVENT] CONTAMINATION EVENT TRIGGERED")
                print("=" * 70)
        
        # Countdown event duration
        if self.event_duration > 0:
            self.event_duration -= 1
            if self.event_duration == 0:
                self.leak_active = False
                self.contamination_active = False
                print("\n" + "=" * 70)
                print("[EVENT] Event resolved - returning to normal")
                print("=" * 70)
    
    def get_sensor_reading(self):
        """Get current sensor reading with possible events"""
        data = self.generate_normal_data()
        
        # Apply events if active
        if self.leak_active:
            data = self.simulate_leak(data)
        
        if self.contamination_active:
            data = self.simulate_contamination(data)
        
        return data
    
    def send_data(self, data):
        """Send sensor data to API"""
        try:
            response = requests.post(
                f"{self.api_url}/api/sensor-data",
                json=data,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error sending data: {e}")
            return False
    
    def run(self, interval=5):
        """Run continuous simulation"""
        print("=" * 70)
        print("SMART WATER MANAGEMENT SYSTEM - Sensor Simulator")
        print("=" * 70)
        print(f"API Endpoint: {self.api_url}")
        print(f"Data Interval: {interval} seconds")
        print("=" * 70)
        
        reading_count = 0
        
        try:
            while True:
                # Trigger random events
                self.trigger_random_events()
                
                # Get sensor reading
                data = self.get_sensor_reading()
                
                # Send to API
                success = self.send_data(data)
                
                reading_count += 1
                status = "[OK]" if success else "[FAIL]"
                
                # Display reading
                print(f"\n[Reading {reading_count}] {datetime.now().strftime('%H:%M:%S')} {status}")
                print(f"  Flow: {data['flow']:.2f} L/min | Pressure: {data['pressure']:.2f} bar")
                print(f"  pH: {data['ph']:.2f} | Turbidity: {data['turbidity']:.2f} NTU")
                print(f"  Temperature: {data['temperature']:.2f}°C")
                
                if self.leak_active:
                    print("  [ALERT] LEAK DETECTED")
                if self.contamination_active:
                    print("  [ALERT] CONTAMINATION DETECTED")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n" + "=" * 70)
            print("Simulator stopped by user")
            print(f"Total readings sent: {reading_count}")
            print("=" * 70)

if __name__ == "__main__":
    simulator = WaterSensorSimulator()
    simulator.run(interval=5)
