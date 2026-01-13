# Home Assistant Integration Architecture Plan

## Overview

Convert the Acoustic Alarm Detector to use a **proper Home Assistant Integration** instead of REST API workarounds.

## Architecture: Add-on + Integration (Hybrid)

```
┌─────────────────────────────────────────────────────────────┐
│                    Home Assistant Core                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Acoustic Alarm Detector Integration (custom_components)│ │
│  │  • Binary Sensor Platform                              │ │
│  │  • Config Flow (UI setup)                              │ │
│  │  • WebSocket Server/Client                             │ │
│  │  • Device Registry                                     │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ↕ (WebSocket/HTTP)                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Acoustic Alarm Detector Add-on                        │ │
│  │  • Audio Processing (PyAudio, FFT)                     │ │
│  │  • Pattern Detection                                   │ │
│  │  • Send events to Integration                          │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ↕                                  │
│                    Audio Hardware                            │
└─────────────────────────────────────────────────────────────┘
```

## Benefits

### Security

- ✅ Integration runs with standard permissions (no admin role)
- ✅ Add-on only needs audio access (can enable AppArmor)
- ✅ Proper separation of concerns

### User Experience

- ✅ Shows in "Devices & Services" UI
- ✅ Config flow for easy setup
- ✅ Proper device/entity management
- ✅ Automatic discovery (optional)

### Maintainability

- ✅ Follows Home Assistant best practices
- ✅ Native entity creation
- ✅ Better debugging and logging
- ✅ Can be submitted to HACS

## Implementation Plan

### Part 1: Create Integration (custom_components)

**Directory Structure:**

```
custom_components/acoustic_alarm_detector/
├── __init__.py          # Integration setup
├── manifest.json        # Integration metadata
├── config_flow.py       # UI configuration
├── const.py             # Constants
├── binary_sensor.py     # Binary sensor platform
├── strings.json         # UI strings (i18n)
└── translations/
    └── en.json          # English translations
```

**Key Files:**

1. **manifest.json**

```json
{
  "domain": "acoustic_alarm_detector",
  "name": "Acoustic Alarm Detector",
  "documentation": "https://github.com/...",
  "requirements": [],
  "codeowners": ["@yourusername"],
  "config_flow": true,
  "iot_class": "local_polling",
  "version": "9.0.0"
}
```

2. **binary_sensor.py** - Creates native binary sensors
3. **config_flow.py** - UI-based configuration
4. ****init**.py** - Integration setup and WebSocket listener

### Part 2: Modify Add-on

**Changes:**

- Remove `ha_client.py` (no longer needed!)
- Add WebSocket/HTTP client to send events to integration
- Simplify to just audio processing
- Can reduce permissions significantly

**Updated config.yaml:**

```yaml
apparmor: true # Now possible!
hassio_role: default # No longer need admin!
hassio_api: false # Don't need it anymore
homeassistant_api: false # Integration handles this
```

## Communication Protocol

### Option 1: WebSocket (Recommended)

```python
# Add-on sends to Integration via WS
{
  "type": "alarm_detected",
  "alarm_type": "smoke",
  "state": "on"  # or "off"
}
```

### Option 2: HTTP Polling

Integration polls add-on's HTTP endpoint every few seconds.

## File Structure

```
Project Root/
├── alarm-audio-detector/           # Add-on (existing)
│   ├── detector/
│   │   ├── main.py
│   │   ├── audio_detector.py
│   │   ├── websocket_client.py   # NEW
│   │   └── config.py
│   ├── config.yaml
│   └── ...
│
└── custom_components/             # NEW - Integration
    └── acoustic_alarm_detector/
        ├── __init__.py
        ├── manifest.json
        ├── binary_sensor.py
        ├── config_flow.py
        └── const.py
```

## Migration Path

### Phase 1: Create Integration (current priority)

1. Create custom_components structure
2. Implement binary sensor platform
3. Add config flow
4. Test with mock data

### Phase 2: Add Communication

1. Add WebSocket server to integration
2. Add WebSocket client to add-on
3. Test bidirectional communication

### Phase 3: Migrate Users

1. Documentation for migration
2. Keep both approaches working during transition
3. Eventually deprecate REST API method

## Next Steps

Would you like me to:

1. ✅ Create the full integration structure
2. ✅ Implement the binary sensor platform
3. ✅ Set up the config flow
4. ✅ Modify the add-on to communicate with integration

This is the proper "Home Assistant way" and will solve all your security concerns!
