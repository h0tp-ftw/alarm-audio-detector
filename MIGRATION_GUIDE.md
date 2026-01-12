# Quick Migration Guide - v9.0.0

## What Changed?

**MQTT has been completely removed!** The addon now uses the Home Assistant REST API exclusively.

## New Configuration (v9.0.0)

```yaml
device_name: "smoke_alarm_detector"
alarm_type: "smoke" # or "co"
target_frequency: 3133
frequency_tolerance: 250
min_magnitude_threshold: 0.25
beep_duration_min: 0.1
beep_duration_max: 1.5
pause_duration_min: 0.05
pause_duration_max: 2.5
confirmation_cycles: 1
```

## Old Configuration (v8.x) - NO LONGER NEEDED

```yaml
mqtt_host: "core-mosquitto" # ❌ REMOVED
mqtt_port: 1883 # ❌ REMOVED
mqtt_user: "" # ❌ REMOVED
mqtt_password: "" # ❌ REMOVED
long_lived_token: "" # ❌ REMOVED
```

## Benefits

✅ **No MQTT broker required** - One less thing to install and configure  
✅ **Simpler setup** - Just install and configure detection parameters  
✅ **Automatic authentication** - Uses Supervisor token automatically  
✅ **More reliable** - Direct API communication, fewer points of failure  
✅ **Smaller footprint** - Removed paho-mqtt dependency

## How to Upgrade

1. Update to v9.0.0
2. Remove MQTT settings from your config
3. Add `alarm_type` setting if not present
4. Restart the addon
5. Verify the binary sensor still works

## Entity ID

The binary sensor entity ID remains the same:

- `binary_sensor.{device_name}_{alarm_type}`
- Example: `binary_sensor.smoke_alarm_detector_smoke`

## Need Help?

Check the logs for "State update successful" messages. If you see errors, ensure:

- `hassio_api: true` in config.yaml (should be automatic)
- `homeassistant_api: true` in config.yaml (should be automatic)
- The addon is running on Home Assistant OS or Supervised

---

**Full details:** See MQTT_REMOVAL_CHANGELOG.md
