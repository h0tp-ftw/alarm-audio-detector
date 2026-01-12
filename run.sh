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

# Load All Configs
export DEVICE_NAME=$(get_config '.device_name')
# Fallback if device_name is empty
if [ -z "$DEVICE_NAME" ]; then
    export DEVICE_NAME="smoke_alarm_detector"
    log_warn "device_name was empty, using default: $DEVICE_NAME"
fi

export ALARM_TYPE=$(get_config '.alarm_type')
if [ -z "$ALARM_TYPE" ]; then
    export ALARM_TYPE="smoke"
    log_warn "alarm_type was empty, using default: $ALARM_TYPE"
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

log_info "ACOUSTIC ALARM DETECTOR v9.0.0 - NO MQTT"
log_info "Device: ${DEVICE_NAME} | Alarm Type: ${ALARM_TYPE}"
log_info "Target: ${TARGET_FREQ}Hz | Mag Threshold: ${MIN_MAGNITUDE}"
log_info "Pattern: Beep ${BEEP_MIN}-${BEEP_MAX}s | Pause ${PAUSE_MIN}-${PAUSE_MAX}s"
log_info "Using Home Assistant REST API (via Supervisor token)"

# Run Python
cd /app
python3 -u -m detector.main

