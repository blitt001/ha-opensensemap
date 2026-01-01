"""Constants for the OpenSenseMap integration."""
from datetime import timedelta

DOMAIN = "opensensemap"

# API Configuration
API_URL = "https://api.opensensemap.org/boxes/{box_id}/data"
SOFTWARE_TYPE = "HomeAssistant-OpenSenseMap"

# Update intervals
DEFAULT_UPDATE_INTERVAL = 300  # seconds (5 minutes)
MIN_UPDATE_INTERVAL = 60  # minimum 1 minute

# Configuration keys
CONF_BOX_ID = "box_id"
CONF_ACCESS_TOKEN = "access_token"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_DEBUG_MODE = "debug_mode"

# Sensor mapping configuration keys - OpenSenseMap sensor IDs
CONF_SENSOR_ID_PM25 = "sensor_id_pm25"
CONF_SENSOR_ID_PM10 = "sensor_id_pm10"
CONF_SENSOR_ID_TEMPERATURE = "sensor_id_temperature"
CONF_SENSOR_ID_HUMIDITY = "sensor_id_humidity"
CONF_SENSOR_ID_PRESSURE = "sensor_id_pressure"

# Home Assistant entity configuration keys
CONF_ENTITY_PM25 = "entity_pm25"
CONF_ENTITY_PM10 = "entity_pm10"
CONF_ENTITY_TEMPERATURE = "entity_temperature"
CONF_ENTITY_HUMIDITY = "entity_humidity"
CONF_ENTITY_PRESSURE = "entity_pressure"

# Measurement types for unit conversion
MEASUREMENT_PM = "pm"
MEASUREMENT_TEMPERATURE = "temperature"
MEASUREMENT_HUMIDITY = "humidity"
MEASUREMENT_PRESSURE = "pressure"

# Sensor configurations - pairs of (sensor_id_key, entity_key, label, measurement_type)
SENSOR_CONFIGS = [
    (CONF_SENSOR_ID_PM25, CONF_ENTITY_PM25, "PM2.5", MEASUREMENT_PM),
    (CONF_SENSOR_ID_PM10, CONF_ENTITY_PM10, "PM10", MEASUREMENT_PM),
    (CONF_SENSOR_ID_TEMPERATURE, CONF_ENTITY_TEMPERATURE, "Temperature", MEASUREMENT_TEMPERATURE),
    (CONF_SENSOR_ID_HUMIDITY, CONF_ENTITY_HUMIDITY, "Humidity", MEASUREMENT_HUMIDITY),
    (CONF_SENSOR_ID_PRESSURE, CONF_ENTITY_PRESSURE, "Pressure", MEASUREMENT_PRESSURE),
]

ALL_SENSOR_ID_KEYS = [
    CONF_SENSOR_ID_PM25,
    CONF_SENSOR_ID_PM10,
    CONF_SENSOR_ID_TEMPERATURE,
    CONF_SENSOR_ID_HUMIDITY,
    CONF_SENSOR_ID_PRESSURE,
]

ALL_ENTITY_KEYS = [
    CONF_ENTITY_PM25,
    CONF_ENTITY_PM10,
    CONF_ENTITY_TEMPERATURE,
    CONF_ENTITY_HUMIDITY,
    CONF_ENTITY_PRESSURE,
]
