"""
Configuration File for Smart Water Management System
Copy this file to config.py and adjust values as needed
"""

# API Configuration
API_HOST = "0.0.0.0"
API_PORT = 8000
API_RELOAD = False  # Set to True for development

# Database Configuration
DB_PATH = "database/water.db"
DB_BACKUP_ENABLED = False
DB_BACKUP_INTERVAL = 3600  # seconds

# Sensor Configuration
SENSOR_INTERVAL = 5  # seconds between readings
SENSOR_TIMEOUT = 10  # seconds before timeout

# Normal operating ranges
NORMAL_FLOW_MIN = 10.0  # L/min
NORMAL_FLOW_MAX = 20.0  # L/min
NORMAL_PRESSURE_MIN = 2.0  # bar
NORMAL_PRESSURE_MAX = 3.0  # bar
NORMAL_PH_MIN = 6.5
NORMAL_PH_MAX = 8.5
NORMAL_TURBIDITY_MAX = 5.0  # NTU
NORMAL_TEMP_MIN = 15.0  # Celsius
NORMAL_TEMP_MAX = 30.0  # Celsius

# Alert Thresholds
ALERT_PH_LOW = 6.0
ALERT_PH_HIGH = 8.5
ALERT_TURBIDITY_HIGH = 5.0
ALERT_FLOW_DROP_PERCENT = 40  # % drop indicates leak
ALERT_PRESSURE_DROP_PERCENT = 30  # % drop indicates leak

# AI Model Configuration
LEAK_DETECTOR_CONTAMINATION = 0.1  # Expected anomaly rate
LEAK_DETECTOR_ESTIMATORS = 100
LEAK_DETECTOR_MIN_SAMPLES = 50

FORECASTER_SEQUENCE_LENGTH = 12  # Number of past readings to use
FORECASTER_EPOCHS = 50
FORECASTER_BATCH_SIZE = 16
FORECASTER_MIN_SAMPLES = 100

# Dashboard Configuration
DASHBOARD_PORT = 8501
DASHBOARD_AUTO_REFRESH = True
DASHBOARD_REFRESH_INTERVAL = 10  # seconds
DASHBOARD_DATA_LIMIT = 100  # Number of points to display

# Simulator Configuration
SIMULATOR_BASE_FLOW = 15.0  # L/min
SIMULATOR_BASE_PRESSURE = 2.5  # bar
SIMULATOR_BASE_PH = 7.2
SIMULATOR_BASE_TURBIDITY = 2.0  # NTU
SIMULATOR_BASE_TEMPERATURE = 25.0  # Celsius

SIMULATOR_LEAK_PROBABILITY = 0.02  # 2% chance per reading
SIMULATOR_CONTAMINATION_PROBABILITY = 0.015  # 1.5% chance per reading
SIMULATOR_LEAK_DURATION_MIN = 20  # readings
SIMULATOR_LEAK_DURATION_MAX = 40  # readings
SIMULATOR_CONTAMINATION_DURATION_MIN = 15  # readings
SIMULATOR_CONTAMINATION_DURATION_MAX = 30  # readings

# Logging Configuration
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE = "logs/swms.log"
LOG_MAX_SIZE = 10485760  # 10 MB
LOG_BACKUP_COUNT = 5

# Hardware Configuration (if using real sensors)
HARDWARE_ENABLED = False
HARDWARE_FLOW_PIN = 4
HARDWARE_PRESSURE_PIN = 34
HARDWARE_PH_PIN = 35
HARDWARE_TURBIDITY_PIN = 32
HARDWARE_TEMP_PIN = 33

# Network Configuration
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
SERVER_URL = "http://localhost:8000"

# Feature Flags
ENABLE_LEAK_DETECTION = True
ENABLE_DEMAND_FORECASTING = True
ENABLE_ALERTS = True
ENABLE_DATA_BACKUP = False
ENABLE_EMAIL_NOTIFICATIONS = False

# Email Configuration (if enabled)
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_SMTP_PORT = 587
EMAIL_USERNAME = "your-email@gmail.com"
EMAIL_PASSWORD = "your-app-password"
EMAIL_RECIPIENTS = ["admin@example.com"]

# Advanced Settings
MAX_DATA_AGE_DAYS = 30  # Auto-delete data older than this
MODEL_RETRAIN_INTERVAL = 86400  # seconds (24 hours)
API_RATE_LIMIT = 100  # requests per minute
CACHE_ENABLED = True
CACHE_TTL = 60  # seconds
