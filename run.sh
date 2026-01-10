#!/bin/bash

# Independent Log functions
log_info() { echo "[INFO] $(date +'%H:%M:%S') $1"; }
log_warn() { echo "[WARNING] $(date +'%H:%M:%S') $1"; }
log_error() { echo "[ERROR] $(date +'%H:%M:%S') $1"; }

log_info "--- CONTAINER DEBUG INFO ---"
log_info "PID: $$"
log_info "USER: $(id)"
log_info "---------------------------"

# Config Path
OPTIONS_JSON="/data/options.json"

# Audio Setup
if [ -S "/run/audio/pulse.sock" ]; then
    log_info "PulseAudio socket found."
    export PULSE_SERVER="unix:/run/audio/pulse.sock"
    # Link cookie if provided
    if [ -f "/data/pulse-cookie" ]; then
        mkdir -p /root/.config/pulse
        ln -sf /data/pulse-cookie /root/.config/pulse/cookie
        log_info "PulseAudio cookie linked."
    fi
    # Force unmute
    pactl set-source-mute @DEFAULT_SOURCE@ false &>/dev/null || true
    pactl set-source-volume @DEFAULT_SOURCE@ 100% &>/dev/null || true
else
    log_warn "PulseAudio socket NOT found. Audio might fail."
fi

# Helper to get config and handle "null"
get_config() {
    local val=$(jq -r "$1" $OPTIONS_JSON)
    if [ "$val" == "null" ] || [ -z "$val" ]; then
        echo ""
    else
        echo "$val"
    fi
}

# MQTT Discovery via Supervisor API (Bashio independent)
log_info "Discovering MQTT settings via Supervisor API..."
MQTT_SERVICE=$(curl -s -H "Authorization: Bearer $SUPERVISOR_TOKEN" http://supervisor/services/mqtt)
RESULT=$(echo "$MQTT_SERVICE" | jq -r '.result')

if [ "$RESULT" == "ok" ]; then
    log_info "MQTT service detected via API."
    export MQTT_HOST=$(echo "$MQTT_SERVICE" | jq -r '.data.host')
    export MQTT_PORT=$(echo "$MQTT_SERVICE" | jq -r '.data.port')
    export MQTT_USER=$(echo "$MQTT_SERVICE" | jq -r '.data.username')
    export MQTT_PASSWORD=$(echo "$MQTT_SERVICE" | jq -r '.data.password')
else
    log_warn "Supervisor MQTT service not available. Using manual config."
    export MQTT_HOST=$(get_config '.mqtt_host')
    export MQTT_PORT=$(get_config '.mqtt_port')
    export MQTT_USER=$(get_config '.mqtt_user')
    export MQTT_PASSWORD=$(get_config '.mqtt_password')
fi

# Load All Configs
export DEVICE_NAME=$(get_config '.device_name')
# Fallback if device_name is empty
if [ -z "$DEVICE_NAME" ]; then
    export DEVICE_NAME="smoke_alarm_detector"
    log_warn "device_name was empty, using default: $DEVICE_NAME"
fi

export TARGET_FREQ=$(get_config '.target_frequency')
export MIN_MAGNITUDE=$(get_config '.min_magnitude_threshold')
export BEEP_MIN=$(get_config '.beep_duration_min')
export BEEP_MAX=$(get_config '.beep_duration_max')
export PAUSE_MIN=$(get_config '.pause_duration_min')
export PAUSE_MAX=$(get_config '.pause_duration_max')
export CONFIRMATION_CYCLES=$(get_config '.confirmation_cycles')
export AUDIO_DEVICE_INDEX=$(get_config '.audio_device_index')

export FREQ_TOLERANCE=$(get_config '.frequency_tolerance')
export SAMPLE_RATE=44100
export ALARM_TYPE="smoke"

if [ -z "$MQTT_USER" ]; then
    log_warn "MQTT User is empty. If connection fails (RC 5), please set mqtt_user/mqtt_password manually in configuration."
else
    log_info "Using MQTT User: $MQTT_USER"
fi

export LONG_LIVED_TOKEN=$(get_config '.long_lived_token')
log_info "ACOUSTIC ALARM DETECTOR v8.6.3"
log_info "Final MQTT Connection: ${MQTT_HOST}:${MQTT_PORT} (User: ${MQTT_USER:-NONE})"
log_info "Target: ${TARGET_FREQ}Hz | Mag Threshold: ${MIN_MAGNITUDE}"
log_info "Pattern: Beep ${BEEP_MIN}-${BEEP_MAX}s | Pause ${PAUSE_MIN}-${PAUSE_MAX}s"

# Run Python
cd /app
python3 -u -m detector.main
