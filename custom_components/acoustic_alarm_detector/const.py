"""Constants for the Acoustic Alarm Detector integration."""

DOMAIN = "acoustic_alarm_detector"

# Configuration keys
CONF_ALARM_TYPE = "alarm_type"
CONF_DEVICE_NAME = "device_name"

# Alarm types
ALARM_TYPE_SMOKE = "smoke"
ALARM_TYPE_CO = "co"

# WebSocket event types
WS_TYPE_STATE_UPDATE = "acoustic_alarm_state"
WS_TYPE_REGISTER = "acoustic_alarm_register"

# Default values
DEFAULT_DEVICE_NAME = "acoustic_alarm"
DEFAULT_ALARM_TYPE = ALARM_TYPE_SMOKE

# Platforms
PLATFORMS = ["binary_sensor"]
