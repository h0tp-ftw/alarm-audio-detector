# Acoustic Listener - Future Vision

## Rebranding: From "Alarm Detector" to "Acoustic Listener"

The addon is evolving from a single-purpose smoke/CO alarm detector to a **general-purpose acoustic event listener** that can detect many types of sounds.

## Vision

**"Acoustic Listener"** - A Home Assistant addon that listens for configurable sound patterns and creates binary sensors or events when detected.

### Use Cases

1. **Safety Alarms**

   - T3 Smoke alarm (3-3-3 beep pattern @ ~3100Hz)
   - T4 CO alarm (4-4-4 beep pattern @ ~3100Hz)
   - Water leak alarms
   - Door/window alarms

2. **Appliance Notifications**

   - Washing machine done (multi-frequency melody)
   - Dryer done beeps
   - Dishwasher complete
   - Oven timer
   - Microwave done

3. **Other Sounds**
   - Doorbell chimes
   - Phone ringing
   - Baby monitor alerts
   - Pet sounds (barking, meowing)

## Proposed Architecture

### Multi-Detector Configuration

```yaml
# config.yaml - Multiple sound profiles
detectors:
  - name: "smoke_alarm"
    type: "pattern"
    entity_id: "binary_sensor.smoke_alarm"
    device_class: "smoke"
    pattern:
      frequency: 3133
      tolerance: 250
      beep_duration: [0.1, 1.5] # min, max
      pause_duration: [0.05, 2.5]
      confirmation_cycles: 3

  - name: "co_alarm"
    type: "pattern"
    entity_id: "binary_sensor.co_alarm"
    device_class: "gas"
    pattern:
      frequency: 3133
      tolerance: 250
      beep_count: 4 # T4 pattern
      confirmation_cycles: 3

  - name: "washer_done"
    type: "melody"
    entity_id: "binary_sensor.washer_done"
    device_class: "running"
    melody:
      frequencies: [880, 1047, 1175, 1319] # Notes
      tolerance: 50
      duration: 2.0
```

### Sound Profile Generator

A separate tool/mode to record and analyze sounds:

```
1. Put addon in "learning mode"
2. Play the target sound (e.g., press washing machine button)
3. Addon records and analyzes:
   - Dominant frequencies
   - Pattern timing
   - Duration
4. Generates a config profile automatically
5. User can name and save the profile
```

### Entity Structure

Each detector creates its own entity:

```
binary_sensor.acoustic_smoke_alarm
binary_sensor.acoustic_co_alarm
binary_sensor.acoustic_washer_done
binary_sensor.acoustic_dryer_done
```

With attributes:

```yaml
device_class: smoke
last_triggered: 2024-01-12T09:30:00
confidence: 0.95
detection_count: 3
```

## Implementation Phases

### Phase 1: Current (v9.0) ✅

- Single alarm detector
- REST API integration
- Basic pattern detection

### Phase 2: Multi-Profile (v10.0)

- Multiple simultaneous detectors
- Per-detector configuration
- Multiple binary sensors

### Phase 3: Learning Mode (v11.0)

- Sound recording capability
- Frequency analysis
- Automatic profile generation
- Web UI for training

### Phase 4: Community Profiles (v12.0)

- Shareable sound profiles
- Community library
- Import/export profiles
- Common appliance presets

## Technical Considerations

### Audio Processing

- FFT for frequency detection (current)
- MFCC for complex pattern matching (future)
- Machine learning for voice/melody recognition (advanced)

### Performance

- Multiple detectors run in parallel
- Shared audio buffer
- Efficient frequency analysis

### Configuration

- YAML-based profiles
- Hot-reload without restart
- Validation and error reporting

## Naming Ideas

- **Acoustic Listener**
- **Sound Sentinel**
- **Audio Alert Hub**
- **Home Sound Monitor**
- **SoundSpotter**

## Priority Features

1. ✅ Get current single-detector working reliably
2. 🔄 Fix audio input issue
3. 🔄 Fix REST API authentication
4. ⬜ Add support for multiple detectors
5. ⬜ Create learning mode
6. ⬜ Web UI for configuration

---

## Current Focus

**Before expanding to multi-detector, we need to:**

1. Fix the audio device issue (PyAudio/PulseAudio)
2. Confirm REST API state updates work
3. Ensure reliable detection with current single profile
4. Document and test thoroughly

Once the foundation is solid, expanding to multiple profiles will be straightforward!
