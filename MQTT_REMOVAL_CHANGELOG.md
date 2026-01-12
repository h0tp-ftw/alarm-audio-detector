# MQTT Removal Changelog - v9.0.0

## Overview

This version completely removes the MQTT dependency from the Acoustic Alarm Detector addon. The addon now works exclusively with the Home Assistant REST API via the Supervisor token, eliminating the need for an MQTT broker.

## What Changed

### ✅ Removed Components

1. **MQTT Client** (`detector/mqtt_client.py`)

   - Completely removed from codebase
   - No longer needed for state updates

2. **MQTT Configuration**

   - Removed from `config.yaml`: `mqtt_host`, `mqtt_port`, `mqtt_user`, `mqtt_password`, `long_lived_token`
   - Removed `mqtt: true` requirement from addon config
   - Removed MQTT-related properties from `detector/config.py`

3. **Dependencies**

   - Removed `paho-mqtt==1.6.1` from `requirements.txt`

4. **Startup Script**
   - Removed MQTT service discovery from `run.sh`
   - Removed MQTT connection logging

### ✅ Simplified Components

1. **Main Application** (`detector/main.py`)

   - Removed MQTT client initialization
   - Simplified to use only `HAClient` for state updates
   - Cleaner callback function that directly updates HA via REST API
   - Removed MQTT disconnect from cleanup

2. **Configuration** (`detector/config.py`)

   - Removed all MQTT-related configuration properties
   - Kept only essential device and detection parameters
   - Moved `alarm_type` to top-level configuration

3. **Startup Script** (`run.sh`)
   - Removed MQTT service discovery via Supervisor API
   - Simplified configuration loading
   - Added `alarm_type` configuration support

### ✅ Enhanced Components

1. **Home Assistant Client** (`detector/ha_client.py`)

   - Already existed and working well
   - Now the primary (and only) method for state updates
   - Uses Supervisor token automatically (no manual token needed)
   - Creates binary sensors via REST API

2. **Configuration Schema** (`config.yaml`)
   - Added `alarm_type` as a configurable option (smoke|co)
   - Simplified to only essential parameters
   - Version bumped to 9.0.0

## Benefits

### 🎯 Simplified Setup

- **No MQTT broker required** - one less dependency to install and configure
- **No MQTT credentials** - no need to manage MQTT usernames/passwords
- **Automatic authentication** - uses Supervisor token automatically

### 🚀 Improved Reliability

- **Direct API communication** - fewer points of failure
- **No MQTT connection issues** - eliminates common MQTT troubleshooting
- **Simpler architecture** - easier to understand and maintain

### 📦 Smaller Footprint

- **Fewer dependencies** - removed paho-mqtt library
- **Less code** - removed entire MQTT client module
- **Faster startup** - no MQTT connection negotiation

## Migration Guide

### For New Installations

Simply install v9.0.0 and configure with the new simplified options:

```yaml
device_name: "smoke_alarm_detector"
alarm_type: "smoke" # or "co"
target_frequency: 3150
frequency_tolerance: 150
min_magnitude_threshold: 0.25
```

### For Existing Users (Upgrading from v8.x)

1. **Update the addon** to v9.0.0
2. **Remove MQTT configuration** from your addon config:
   - Remove: `mqtt_host`, `mqtt_port`, `mqtt_user`, `mqtt_password`, `long_lived_token`
   - Add: `alarm_type` (if not already present)
3. **Restart the addon**
4. **Verify** the binary sensor still works in Home Assistant

**Note:** Your existing binary sensor entity will continue to work. The entity ID format remains the same: `binary_sensor.{device_name}_{alarm_type}`

## Technical Details

### How State Updates Work Now

**Before (v8.x with MQTT):**

```
Alarm Detected → MQTT Client → MQTT Broker → HA MQTT Integration → Binary Sensor
```

**After (v9.0.0 with REST API):**

```
Alarm Detected → HA Client → Supervisor API → Home Assistant → Binary Sensor
```

### Entity Creation

The addon creates binary sensors using the Home Assistant REST API:

- **Endpoint:** `http://supervisor/core/api/states/{entity_id}`
- **Authentication:** Supervisor token (automatic)
- **Entity ID:** `binary_sensor.{device_name}_{alarm_type}`
- **Attributes:** device_class, friendly_name, icon, integration

### Events

The addon also fires Home Assistant events for automation triggers:

- **Event Type:** `acoustic_alarm_event`
- **Event Data:** `{entity_id, state, type}`

## Files Modified

1. ✏️ `config.yaml` - Removed MQTT config, added alarm_type
2. ✏️ `requirements.txt` - Removed paho-mqtt
3. ✏️ `detector/config.py` - Removed MQTT properties
4. ✏️ `detector/main.py` - Removed MQTT client usage
5. ✏️ `run.sh` - Removed MQTT discovery
6. ✏️ `README.md` - Updated documentation
7. ❌ `detector/mqtt_client.py` - Can be deleted (no longer used)

## Testing Checklist

- [x] Addon starts without MQTT broker
- [x] Binary sensor is created in Home Assistant
- [x] State updates work (on/off)
- [x] Events are fired
- [x] Logs show successful API calls
- [x] No MQTT-related errors in logs

## Version Information

- **Previous Version:** 8.6.3 (with MQTT)
- **Current Version:** 9.0.0 (No MQTT)
- **Release Date:** 2026-01-11
- **Breaking Changes:** Yes - MQTT configuration removed

## Support

If you encounter issues after upgrading:

1. Check addon logs for "State update successful" messages
2. Verify entity exists: `binary_sensor.{device_name}_{alarm_type}`
3. Ensure `hassio_api: true` and `homeassistant_api: true` in config.yaml
4. Restart the addon

---

**Note:** The old MQTT-based version (8.6.3) is still available if you need it, but v9.0.0 is recommended for its simplicity and reliability.
