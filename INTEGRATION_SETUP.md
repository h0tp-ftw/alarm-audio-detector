# One-Click Installation Guide

## Overview

The addon now **auto-installs the custom integration** - no manual copying needed! Just install the addon and it sets everything up automatically.

## Installation Steps

### Step 1: Install the Add-on

1. Copy the entire `alarm-audio-detector` folder to Home Assistant:

   ```bash
   # If using SSH:
   scp -r alarm-audio-detector hassio@homeassistant.local:/addons/

   # Or if using Samba:
   # Copy the folder to the visible "addons" share
   ```

2. **Reload the Add-on Store:**

   - Settings → Add-ons → ⋮ (top right) → Check for updates

3. **Install the Add-on:**

   - Settings → Add-ons → Add-on Store
   - Scroll to "Local add-ons" section
   - Click **"Acoustic Alarm Detector v9"**
   - Click **INSTALL**

4. **The integration installs automatically!**
   - When the addon starts, it copies the integration to `/config/custom_components/`
   - Check the addon logs - you should see: `✅ Integration installed to /config/custom_components/`

### Step 2: Restart Home Assistant

**Important:** Restart Home Assistant to load the new integration:

- Settings → System → Restart
- Wait for restart to complete

### Step 3: Add the Integration

1. **Go to Settings → Devices & Services**

2. **Click "+ ADD INTEGRATION"**

3. **Search for "Acoustic Alarm Detector"**

4. **Configure:**

   - **Device Name**: e.g., `kitchen_alarm`
   - **Alarm Type**: `smoke` or `co`
   - Click **SUBMIT**

5. **A binary sensor is created!**
   - Entity ID: `binary_sensor.kitchen_alarm_smoke` (or `_co`)
   - Device: Shows in device list

### Step 4: Configure the Add-on

1. **Go to the add-on Configuration tab**

2. **Set matching configuration:**

   ```yaml
   device_name: "kitchen_alarm" # Must match step 3!
   alarm_type: "smoke" # Must match step 3!
   target_frequency: 3133
   frequency_tolerance: 250
   min_magnitude_threshold: 0.25
   beep_duration_min: 0.1
   beep_duration_max: 1.5
   pause_duration_min: 0.05
   pause_duration_max: 2.5
   confirmation_cycles: 1
   ```

3. **Start the add-on**

4. **Check the logs** - you should see:
   ```
   ✅ Using Integration Client (native HA integration)
   ```

## That's It!

The addon and integration are now working together. When an alarm is detected:

1. Add-on detects the pattern
2. Sends message to integration via WebSocket
3. Integration updates the binary sensor
4. Your automations trigger!

## File Structure (Auto-Installed)

After installation, Home Assistant will have:

```
/config/
├── custom_components/
│   └── acoustic_alarm_detector/   ← Auto-installed by addon!
│       ├── __init__.py
│       ├── binary_sensor.py
│       ├── config_flow.py
│       ├── const.py
│       ├── manifest.json
│       ├── strings.json
│       └── translations/
│           └── en.json
```

## Benefits of Bundled Integration

✅ **One-click installation** - Just install the addon  
✅ **No manual file copying** - Integration auto-installs  
✅ **Always in sync** - Addon and integration versions match  
✅ **Easy updates** - Update addon, integration updates too  
✅ **Simplified distribution** - Single package to share

## How Auto-Install Works

1. Addon's `config.yaml` includes `map: ["config:rw"]`
2. This gives addon read/write access to `/config` directory
3. On startup, `run.sh` copies integration files:
   ```bash
   cp -r /app/custom_components /config/custom_components
   ```
4. After HA restart, integration is loaded
5. User adds integration via UI
6. Addon connects to integration via WebSocket

## Troubleshooting

### Integration not auto-installed

- **Check addon logs** for "Integration installed" message
- **Verify** addon has `map: ["config:rw"]` in config.yaml
- **Manually check** `/config/custom_components/acoustic_alarm_detector/` exists

### Integration not appearing in UI

- **Restart Home Assistant** after first addon start
- **Check** Settings → System → Logs for integration errors
- **Verify** manifest.json is valid

### Binary sensor not updating

- **Check integration entry ID** matches addon config
- **Verify** both use same device_name and alarm_type
- **Look for** "State updated via Integration" in addon logs

### Using REST API fallback

If you see "No integration entry ID" in logs:

- This means addon couldn't find integration
- REST API fallback will be used
- Still works but less secure than integration method

## Security Note

The addon needs `map: ["config:rw"]` to auto-install the integration. This is safe because:

- Only writes to `/config/custom_components` (standard location)
- Only on first startup (idempotent operation)
- Doesn't modify existing files
- Standard practice for addons that provide integrations

---

**Enjoy your truly one-click alarm detection system!** 🎉
