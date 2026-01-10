#!/usr/bin/env python3
"""
Smoke & CO Alarm Detector - Proof of Concept
Detects Temporal-3 (T3) smoke alarm pattern using FFT analysis
Author: Lead Engineer POC
License: Open Source
"""

import pyaudio
import numpy as np
from scipy import signal
from collections import deque
from dataclasses import dataclass
from datetime import datetime
import time

# =========================
# CONFIGURATION PARAMETERS
# =========================

@dataclass
class Config:
    """Tunable parameters for alarm detection"""

    # Audio capture settings
    SAMPLE_RATE: int = 44100  # Hz - Standard audio sample rate
    CHUNK_SIZE: int = 4096    # Samples per chunk (larger = better freq resolution, more latency)
    CHANNELS: int = 1         # Mono audio

    # Frequency detection parameters
    TARGET_FREQ: float = 3150.0      # Hz - Center frequency of alarm (tune between 3100-3200)
    FREQ_TOLERANCE: float = 150.0    # Hz - Bandwidth to consider (+/- from target)
    MIN_MAGNITUDE_THRESHOLD: float = 0.15  # Relative magnitude (0-1) to consider "loud enough"

    # Temporal pattern parameters (T3 for smoke)
    BEEP_DURATION_MIN: float = 0.4   # seconds - Minimum beep length
    BEEP_DURATION_MAX: float = 0.7   # seconds - Maximum beep length
    PAUSE_DURATION_MIN: float = 1.2  # seconds - Minimum pause between beeps
    PAUSE_DURATION_MAX: float = 1.8  # seconds - Maximum pause between beeps

    # Pattern recognition
    REQUIRED_BEEPS: int = 3          # T3 pattern = 3 beeps
    PATTERN_TIMEOUT: float = 10.0    # seconds - Reset pattern if too much time passes
    CONFIRMATION_CYCLES: int = 2     # Number of T3 cycles needed to confirm (reduce false positives)


class BeepState:
    """State machine for tracking beep patterns"""
    IDLE = 0
    BEEPING = 1
    PAUSED = 2


class AlarmDetector:
    def __init__(self, config: Config):
        self.config = config
        self.state = BeepState.IDLE

        # Timing tracking
        self.beep_start_time = None
        self.pause_start_time = None
        self.beep_count = 0
        self.last_detection_time = time.time()
        self.confirmed_cycles = 0

        # Audio processing
        self.freq_bins = np.fft.rfftfreq(config.CHUNK_SIZE, 1.0 / config.SAMPLE_RATE)
        self.target_freq_idx_min, self.target_freq_idx_max = self._get_frequency_indices()

        # History buffer for smoothing (reduces false triggers)
        self.detection_history = deque(maxlen=3)

    def _get_frequency_indices(self):
        """Calculate FFT bin indices for target frequency range"""
        freq_min = self.config.TARGET_FREQ - self.config.FREQ_TOLERANCE
        freq_max = self.config.TARGET_FREQ + self.config.FREQ_TOLERANCE

        idx_min = np.argmin(np.abs(self.freq_bins - freq_min))
        idx_max = np.argmin(np.abs(self.freq_bins - freq_max))

        print(f"[INIT] Monitoring frequency range: {freq_min:.0f} - {freq_max:.0f} Hz")
        print(f"[INIT] FFT bin indices: {idx_min} - {idx_max}")
        return idx_min, idx_max

    def detect_target_frequency(self, audio_chunk):
        """
        Perform FFT analysis to detect if target frequency is present
        Returns: (is_present, magnitude, dominant_freq)
        """
        # Convert to float and normalize
        audio_float = audio_chunk.astype(np.float32) / 32768.0

        # Apply Hann window to reduce spectral leakage
        windowed = audio_float * np.hanning(len(audio_float))

        # Compute FFT (only positive frequencies for real signal)
        fft_result = np.fft.rfft(windowed)
        fft_magnitude = np.abs(fft_result)

        # Normalize magnitude to 0-1 range
        if np.max(fft_magnitude) > 0:
            fft_magnitude = fft_magnitude / np.max(fft_magnitude)

        # Extract magnitude in target frequency range
        target_band = fft_magnitude[self.target_freq_idx_min:self.target_freq_idx_max]
        max_magnitude = np.max(target_band) if len(target_band) > 0 else 0

        # Find dominant frequency in target band
        if max_magnitude > self.config.MIN_MAGNITUDE_THRESHOLD:
            peak_idx = np.argmax(target_band) + self.target_freq_idx_min
            dominant_freq = self.freq_bins[peak_idx]
            return True, max_magnitude, dominant_freq

        return False, max_magnitude, 0

    def update_state_machine(self, freq_detected):
        """
        State machine to track temporal pattern of beeps
        T3 Pattern: BEEP (0.5s) - PAUSE (1.5s) - BEEP (0.5s) - PAUSE (1.5s) - BEEP (0.5s)
        """
        current_time = time.time()

        # Add current detection to history buffer (smoothing)
        self.detection_history.append(freq_detected)
        smoothed_detection = sum(self.detection_history) >= 2  # Majority vote

        # Timeout check - reset if pattern takes too long
        if current_time - self.last_detection_time > self.config.PATTERN_TIMEOUT:
            if self.beep_count > 0:
                print(f"[TIMEOUT] Pattern incomplete. Resetting. (Had {self.beep_count} beeps)")
            self._reset_pattern()
            return False

        if self.state == BeepState.IDLE:
            if smoothed_detection:
                # Start of new beep
                self.state = BeepState.BEEPING
                self.beep_start_time = current_time
                self.last_detection_time = current_time
                print(f"[BEEP START] Beep #{self.beep_count + 1}")

        elif self.state == BeepState.BEEPING:
            if not smoothed_detection:
                # End of beep - validate duration
                beep_duration = current_time - self.beep_start_time

                if self.config.BEEP_DURATION_MIN <= beep_duration <= self.config.BEEP_DURATION_MAX:
                    # Valid beep duration
                    self.beep_count += 1
                    self.state = BeepState.PAUSED
                    self.pause_start_time = current_time
                    self.last_detection_time = current_time
                    print(f"[BEEP END] Valid beep ({beep_duration:.2f}s). Count: {self.beep_count}/{self.config.REQUIRED_BEEPS}")

                    # Check if we completed a T3 cycle
                    if self.beep_count >= self.config.REQUIRED_BEEPS:
                        self.confirmed_cycles += 1
                        print(f"[CYCLE COMPLETE] T3 pattern cycle #{self.confirmed_cycles} detected!")

                        if self.confirmed_cycles >= self.config.CONFIRMATION_CYCLES:
                            print("\n" + "="*60)
                            print("🚨 SMOKE ALARM DETECTED! 🚨")
                            print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                            print(f"Confidence: {self.confirmed_cycles} consecutive T3 cycles")
                            print("="*60 + "\n")
                            self._reset_pattern()
                            return True
                        else:
                            # Reset beep count but keep tracking cycles
                            self.beep_count = 0
                            self.state = BeepState.IDLE
                else:
                    # Invalid beep duration
                    print(f"[INVALID BEEP] Duration {beep_duration:.2f}s out of range. Resetting.")
                    self._reset_pattern()

        elif self.state == BeepState.PAUSED:
            if smoothed_detection:
                # New beep started - validate pause duration
                pause_duration = current_time - self.pause_start_time

                if self.config.PAUSE_DURATION_MIN <= pause_duration <= self.config.PAUSE_DURATION_MAX:
                    # Valid pause, continue pattern
                    self.state = BeepState.BEEPING
                    self.beep_start_time = current_time
                    self.last_detection_time = current_time
                    print(f"[PAUSE VALID] Pause was {pause_duration:.2f}s. Next beep starting.")
                else:
                    # Invalid pause duration
                    print(f"[INVALID PAUSE] Duration {pause_duration:.2f}s out of range. Resetting.")
                    self._reset_pattern()

        return False

    def _reset_pattern(self):
        """Reset the state machine"""
        self.state = BeepState.IDLE
        self.beep_count = 0
        self.beep_start_time = None
        self.pause_start_time = None
        # Don't reset confirmed_cycles to allow accumulation

    def process_audio_chunk(self, audio_chunk):
        """Main processing function for each audio chunk"""
        freq_detected, magnitude, dominant_freq = self.detect_target_frequency(audio_chunk)

        if freq_detected:
            print(f"[FREQ DETECT] {dominant_freq:.1f} Hz detected (magnitude: {magnitude:.3f})")

        return self.update_state_machine(freq_detected)


def main():
    """Main audio capture and processing loop"""
    config = Config()
    detector = AlarmDetector(config)

    # Initialize PyAudio
    p = pyaudio.PyAudio()

    print("\n" + "="*60)
    print("SMOKE ALARM DETECTOR - POC")
    print("="*60)
    print(f"Sample Rate: {config.SAMPLE_RATE} Hz")
    print(f"Chunk Size: {config.CHUNK_SIZE} samples")
    print(f"Target Frequency: {config.TARGET_FREQ} Hz ± {config.FREQ_TOLERANCE} Hz")
    print(f"Pattern: T3 (3 beeps, ~0.5s each, ~1.5s pause)")
    print(f"Confirmation Required: {config.CONFIRMATION_CYCLES} cycles")
    print("="*60 + "\n")

    try:
        # Open audio stream
        stream = p.open(
            format=pyaudio.paInt16,
            channels=config.CHANNELS,
            rate=config.SAMPLE_RATE,
            input=True,
            frames_per_buffer=config.CHUNK_SIZE
        )

        print("[LISTENING] Monitoring for smoke alarm pattern...\n")

        while True:
            # Read audio chunk
            audio_data = stream.read(config.CHUNK_SIZE, exception_on_overflow=False)
            audio_chunk = np.frombuffer(audio_data, dtype=np.int16)

            # Process chunk
            alarm_detected = detector.process_audio_chunk(audio_chunk)

            if alarm_detected:
                # Here you would trigger MQTT publish, notifications, etc.
                pass

    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Stopping detector...")

    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        print("[SHUTDOWN] Audio stream closed.")


if __name__ == "__main__":
    main()
