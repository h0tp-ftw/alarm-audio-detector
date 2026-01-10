# 🔊 Acoustic Alarm Detector for Home Assistant

**Open-source smoke and CO alarm detection using acoustic analysis**

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Add--on-blue.svg)](https://www.home-assistant.io/)
[![Version](https://img.shields.io/badge/version-1.0.0-green.svg)](https://github.com/yourusername/acoustic-alarm-detector)

## 🎯 Overview

This Home Assistant add-on uses **acoustic analysis** and **digital signal processing (DSP)** to detect smoke and carbon monoxide alarms in your home. It listens for the distinctive T3 (smoke) or T4 (CO) temporal patterns and publishes detection events via MQTT.

### Key Features

- ✅ **Real-time acoustic detection** using FFT analysis
- ✅ **Temporal pattern recognition** (T3/T4 patterns)
- ✅ **MQTT auto-discovery** - automatic Home Assistant integration
- ✅ **Configurable sensitivity** and frequency targeting
- ✅ **Low false-positive rate** with confirmation cycles
- ✅ **Raspberry Pi optimized** - runs on ARM devices
- ✅ **No cloud dependencies** - 100% local processing

## 🚀 Quick Start

### Prerequisites

- Home Assistant OS or Supervised installation
- MQTT broker (Mosquitto add-on recommended)
- USB microphone (for production use)

### Installation

1. **Place add-on files** in `/addons/alarm-audio-detector/` or `/config/addons/alarm-audio-detector/`

2. **Reload add-on store:**
   - Settings → Add-ons → ⋮ → Check for updates

3. **Install the add-on:**
   - Settings → Add-ons → Add-on Store → Local add-ons
   - Click "Acoustic Alarm Detector" → Install

4. **Configure:**
   ```yaml
   mqtt_host: "core-mosquitto"
   mqtt_port: 1883
   target_frequency: 3150
   alarm_type: "smoke"
   ```

5. **Start the add-on** and check logs

📖 **See [QUICKSTART.md](QUICKSTART.md) for detailed instructions**

## 📊 How It Works

### Detection Pipeline

```
Microphone → PyAudio → FFT Analysis → Frequency Detection
                                            ↓
MQTT ← Home Assistant ← Pattern Matcher ← Temporal Analysis
```

### Temporal Pattern Recognition

**Smoke Alarm (T3 Pattern):**
```
BEEP (0.5s) → PAUSE (1.5s) → BEEP (0.5s) → PAUSE (1.5s) → BEEP (0.5s)
```

**CO Alarm (T4 Pattern):**
```
BEEP (0.5s) → PAUSE (1.5s) → BEEP → PAUSE → BEEP → PAUSE → BEEP
```

The detector uses a **state machine** to track beep timing and confirm patterns before triggering an alarm.

## 🎛️ Configuration

### Basic Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `mqtt_host` | core-mosquitto | MQTT broker hostname |
| `mqtt_port` | 1883 | MQTT broker port |
| `device_name` | smoke_alarm_detector | Unique device identifier |
| `target_frequency` | 3150 | Target frequency in Hz |
| `alarm_type` | smoke | "smoke" (T3) or "co" (T4) |

### Advanced Tuning

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `min_magnitude_threshold` | 0.15 | 0.05-0.5 | Detection sensitivity |
| `frequency_tolerance` | 150 | 50-300 | Frequency range (±Hz) |
| `confirmation_cycles` | 2 | 1-5 | Cycles to confirm alarm |
| `beep_duration_min` | 0.4 | 0.2-1.0 | Min beep length (s) |
| `beep_duration_max` | 0.7 | 0.3-2.0 | Max beep length (s) |

## 📁 Project Structure

```
alarm-audio-detector/
├── Dockerfile              # Container build configuration
├── config.yaml             # Home Assistant add-on metadata
├── run.sh                  # Startup script with bashio
├── requirements.txt        # Python dependencies
├── validate.sh             # Pre-deployment validation
├── QUICKSTART.md          # Quick reference guide
├── README.md              # This file
├── docs/
│   ├── DEPLOYMENT_GUIDE.md    # Comprehensive deployment guide
│   ├── AUTOMATIONS.md         # Example automations
│   └── ALSA_SETUP.md          # Audio configuration
└── detector/
    ├── __init__.py        # Package marker
    ├── main.py            # Application entry point
    ├── audio_detector.py  # Core detection logic
    ├── mqtt_client.py     # MQTT integration
    ├── config.py          # Configuration management
    ├── audio_manager.py   # Audio device management (future)
    └── dsp_filters.py     # DSP filters (future)
```

## 🧪 Testing

### Validate Installation

```bash
cd /workspaces/core/alarm-audio-detector
./validate.sh
```

### Test MQTT Integration

1. **Check sensor exists:**
   - Developer Tools → States
   - Search: `binary_sensor.smoke_alarm_detector`

2. **Simulate detection:**
   - Developer Tools → MQTT
   - Topic: `homeassistant/binary_sensor/smoke_alarm_detector/state`
   - Payload: `ON`

### Test Real Alarm

1. Press test button on smoke alarm
2. Watch add-on logs for detection messages
3. Verify Home Assistant sensor updates

## 📱 Home Assistant Integration

### Binary Sensor

After starting the add-on, a binary sensor automatically appears:

- **Entity ID:** `binary_sensor.smoke_alarm_detector`
- **Device Class:** `smoke` or `gas`
- **States:** `Clear` / `Detected`

### Example Automation

```yaml
automation:
  - alias: "Smoke Alarm Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.smoke_alarm_detector
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "🚨 SMOKE ALARM DETECTED!"
          message: "Smoke alarm is sounding in your home!"
          data:
            priority: high
            ttl: 0
```

📖 **See [docs/AUTOMATIONS.md](docs/AUTOMATIONS.md) for more examples**

## 🐛 Troubleshooting

### Add-on not appearing
- Reload add-on store
- Check file location: `/addons/` or `/config/addons/`
- Verify `config.yaml` syntax

### MQTT connection failed
- Ensure Mosquitto broker is running
- Check MQTT credentials
- Try IP address instead of hostname

### Audio device not found
- Expected in dev container (no audio devices)
- On Raspberry Pi: Check `arecord -l`
- Verify `/dev/snd` device mapping

### No detection / False positives
- **Too sensitive:** Increase `min_magnitude_threshold` to 0.20
- **Not sensitive:** Decrease to 0.10
- Check actual alarm frequency with spectrum analyzer
- Adjust `frequency_tolerance`

📖 **See [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) for comprehensive troubleshooting**

## 🔧 Development

### Requirements

- Python 3.9+
- PyAudio
- NumPy
- SciPy
- paho-mqtt

### Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export MQTT_HOST=localhost
export MQTT_PORT=1883
export TARGET_FREQ=3150
export ALARM_TYPE=smoke

# Run detector
python3 -m detector.main
```

### Testing Without Hardware

Use `basic_poc.py` for testing detection logic without Home Assistant:

```bash
python3 basic_poc.py
```

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Fast deployment guide
- **[docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)** - Comprehensive setup
- **[docs/AUTOMATIONS.md](docs/AUTOMATIONS.md)** - Automation examples
- **[docs/ALSA_SETUP.md](docs/ALSA_SETUP.md)** - Audio configuration

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- [ ] Advanced DSP filtering (bandpass, noise reduction)
- [ ] Multi-alarm support (multiple sensors)
- [ ] Frequency learning mode
- [ ] Web UI for configuration
- [ ] Audio recording on detection
- [ ] Integration with other alarm types

## 📄 License

This project is open source. See LICENSE file for details.

## 🙏 Acknowledgments

- Home Assistant community
- PyAudio and NumPy developers
- NFPA 72 temporal pattern specifications

## 📞 Support

- **Issues:** Report bugs and feature requests on GitHub
- **Documentation:** See `docs/` directory
- **Validation:** Run `./validate.sh` before deployment

---

**Status:** ✅ Production Ready  
**Version:** 1.0.0  
**Last Updated:** 2026-01-09

**Made with ❤️ for the Home Assistant community**
