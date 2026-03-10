/*
 * ESP32 Water Sensor Integration Example
 * Smart Water Management System
 * 
 * This code reads from multiple sensors and sends data to the FastAPI backend
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// WiFi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// API endpoint
const char* serverUrl = "http://YOUR_SERVER_IP:8000/api/sensor-data";

// Pin definitions
#define FLOW_PIN 4          // Flow sensor interrupt pin
#define PRESSURE_PIN 34     // Pressure sensor analog pin
#define PH_PIN 35           // pH sensor analog pin
#define TURBIDITY_PIN 32    // Turbidity sensor analog pin
#define TEMP_PIN 33         // Temperature sensor data pin

// Flow sensor variables
volatile int flowPulseCount = 0;
float flowRate = 0.0;
float flowCalibrationFactor = 7.5;  // Pulses per liter (calibrate for your sensor)

// Temperature sensor
OneWire oneWire(TEMP_PIN);
DallasTemperature tempSensor(&oneWire);

// Timing
unsigned long lastSendTime = 0;
const unsigned long sendInterval = 5000;  // 5 seconds

void IRAM_ATTR flowPulseCounter() {
  flowPulseCount++;
}

void setup() {
  Serial.begin(115200);
  Serial.println("\n🌊 Smart Water Management System - ESP32");
  
  // Initialize pins
  pinMode(FLOW_PIN, INPUT_PULLUP);
  pinMode(PRESSURE_PIN, INPUT);
  pinMode(PH_PIN, INPUT);
  pinMode(TURBIDITY_PIN, INPUT);
  
  // Attach interrupt for flow sensor
  attachInterrupt(digitalPinToInterrupt(FLOW_PIN), flowPulseCounter, FALLING);
  
  // Initialize temperature sensor
  tempSensor.begin();
  
  // Connect to WiFi
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\n✅ WiFi connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  unsigned long currentTime = millis();
  
  // Send data every 5 seconds
  if (currentTime - lastSendTime >= sendInterval) {
    // Read all sensors
    float flow = readFlowSensor();
    float pressure = readPressureSensor();
    float ph = readPHSensor();
    float turbidity = readTurbiditySensor();
    float temperature = readTemperatureSensor();
    
    // Display readings
    Serial.println("\n📊 Sensor Readings:");
    Serial.printf("  Flow: %.2f L/min\n", flow);
    Serial.printf("  Pressure: %.2f bar\n", pressure);
    Serial.printf("  pH: %.2f\n", ph);
    Serial.printf("  Turbidity: %.2f NTU\n", turbidity);
    Serial.printf("  Temperature: %.2f °C\n", temperature);
    
    // Send to API
    sendData(flow, pressure, ph, turbidity, temperature);
    
    lastSendTime = currentTime;
  }
}

float readFlowSensor() {
  // Calculate flow rate from pulse count
  // Flow rate (L/min) = (Pulse count / calibration factor) * (60 / time interval)
  
  noInterrupts();
  int pulses = flowPulseCount;
  flowPulseCount = 0;
  interrupts();
  
  // Calculate flow rate
  flowRate = (pulses / flowCalibrationFactor) * (60.0 / (sendInterval / 1000.0));
  
  return flowRate;
}

float readPressureSensor() {
  // Read analog value from pressure sensor
  // Assuming 0-5V sensor mapped to 0-5 bar
  
  int rawValue = analogRead(PRESSURE_PIN);
  
  // Convert to voltage (ESP32 ADC: 0-4095 = 0-3.3V)
  float voltage = (rawValue / 4095.0) * 3.3;
  
  // Convert to pressure (adjust based on your sensor specs)
  // Example: 0.5V = 0 bar, 4.5V = 5 bar
  float pressure = ((voltage - 0.5) / 4.0) * 5.0;
  
  return max(0.0f, pressure);
}

float readPHSensor() {
  // Read analog value from pH sensor
  
  int rawValue = analogRead(PH_PIN);
  
  // Convert to voltage
  float voltage = (rawValue / 4095.0) * 3.3;
  
  // Convert to pH (adjust calibration for your sensor)
  // Example calibration: pH 7 at 2.5V, slope of 0.18V per pH unit
  float ph = 7.0 - ((voltage - 2.5) / 0.18);
  
  // Constrain to valid pH range
  return constrain(ph, 0.0, 14.0);
}

float readTurbiditySensor() {
  // Read analog value from turbidity sensor
  
  int rawValue = analogRead(TURBIDITY_PIN);
  
  // Convert to voltage
  float voltage = (rawValue / 4095.0) * 3.3;
  
  // Convert to NTU (adjust based on your sensor)
  // Higher voltage = clearer water (lower turbidity)
  // Example: 4.2V = 0 NTU, 2.5V = 10 NTU
  float turbidity = ((4.2 - voltage) / 1.7) * 10.0;
  
  return max(0.0f, turbidity);
}

float readTemperatureSensor() {
  // Read DS18B20 temperature sensor
  
  tempSensor.requestTemperatures();
  float temperature = tempSensor.getTempCByIndex(0);
  
  // Check for sensor error
  if (temperature == DEVICE_DISCONNECTED_C) {
    Serial.println("⚠️  Temperature sensor error");
    return 25.0;  // Return default value
  }
  
  return temperature;
}

void sendData(float flow, float pressure, float ph, float turbidity, float temp) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("❌ WiFi not connected");
    return;
  }
  
  HTTPClient http;
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/json");
  
  // Create JSON payload
  StaticJsonDocument<256> doc;
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
    if (httpCode == HTTP_CODE_OK) {
      Serial.println("✅ Data sent successfully");
    } else {
      Serial.printf("⚠️  HTTP response: %d\n", httpCode);
    }
  } else {
    Serial.printf("❌ HTTP error: %s\n", http.errorToString(httpCode).c_str());
  }
  
  http.end();
}
