# 🚀 Quick Start Guide - Acoustic Alarm Detector

## ✅ Pre-Deployment Status

**All files verified and ready!**
- ✅ Dockerfile fixed (correct chmod path)
- ✅ requirements.txt corrected (Python packages)
- ✅ run.sh has executable permissions
- ✅ All Python modules present
- ✅ Configuration files validated

---

## 📦 Installation (3 Steps)

### 1️⃣ Reload Add-on Store
```
Settings → Add-ons → ⋮ (menu) → Check for updates
```
**Wait:** 10-30 seconds

### 2️⃣ Install Add-on
```
Settings → Add-ons → Add-on Store → Local add-ons
→ "Acoustic Alarm Detector" → Install
```
**Wait:** 3-5 minutes (first build)

### 3️⃣ Configure & Start
**Configuration tab:**
```yaml
mqtt_host: "core-mosquitto"
mqtt_port: 1883
mqtt_user: ""
mqtt_password: ""
```
**Then:** Click "Start"

---

## 🧪 Quick Test (MQTT)

### Test 1: Check Sensor Exists
```
Developer Tools → States → Search: "smoke_alarm"
```
**Expected:** `binary_sensor.smoke_alarm_detector` = "Clear"

### Test 2: Simulate Detection
```
Developer Tools → MQTT → Publish
Topic: homeassistant/binary_sensor/smoke_alarm_detector/state
Payload: ON
```
**Expected:** Sensor changes to "Detected"

---

## 📊 Monitor Logs

**Add-on page → Log tab**

**Success indicators:**
```
✓ "Connected to MQTT broker"
✓ "Audio stream opened successfully"
✓ "Detector is running. Listening..."
```

---

## 🎯 Key Configuration Parameters

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `target_frequency` | 3150 | Alarm frequency (Hz) |
| `min_magnitude_threshold` | 0.15 | Sensitivity (0.05-0.5) |
| `confirmation_cycles` | 2 | Cycles to confirm |
| `alarm_type` | smoke | "smoke" or "co" |

**Adjust sensitivity:**
- Too many false alarms → Increase threshold to 0.20
- Missing real alarms → Decrease threshold to 0.10

---

## 🐛 Common Issues

### Issue: Add-on not in store
**Fix:** Reload add-on store, check file location

### Issue: MQTT connection failed
**Fix:** Verify Mosquitto broker is running, check credentials

### Issue: Audio device error
**Expected in dev container** - Will work on real hardware

### Issue: No detection
**Fix:** Adjust `min_magnitude_threshold` and `frequency_tolerance`

---

## 📚 Full Documentation

- **Deployment Guide:** `docs/DEPLOYMENT_GUIDE.md`
- **Automations:** `docs/AUTOMATIONS.md`
- **ALSA Setup:** `docs/ALSA_SETUP.md`

---

## 🎓 Next Steps

1. ✅ Files validated (DONE)
2. 🔄 Install add-on in Home Assistant
3. 🔄 Configure MQTT settings
4. 🔄 Test with MQTT Developer Tools
5. 🔄 Deploy to Raspberry Pi with microphone
6. 🔄 Test with real smoke alarm
7. 🔄 Create automations for notifications

---

## 📞 Validation Command

Run anytime to check file integrity:
```bash
cd /workspaces/core/alarm-audio-detector
./validate.sh
```

---

**Status:** ✅ Ready for deployment  
**Version:** 1.0.0  
**Last Validated:** 2026-01-09
