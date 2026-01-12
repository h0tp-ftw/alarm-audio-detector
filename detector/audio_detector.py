"""Core audio detection logic with state machine"""

import numpy as np
import time
import logging
from collections import deque
from datetime import datetime
from .config import DetectorConfig

logger = logging.getLogger(__name__)


class BeepState:
    """State machine states"""

    IDLE = 0
    BEEPING = 1
    PAUSED = 2


class AlarmDetector:
    """Acoustic alarm detector with FFT analysis and temporal pattern recognition"""

    def __init__(self, config: DetectorConfig, state_callback=None):
        self.config = config
        self.state_callback = state_callback
        self.state = BeepState.IDLE

        # Timing tracking
        self.beep_start_time = None
        self.pause_start_time = None
        self.beep_count = 0
        self.last_detection_time = time.time()
        self.confirmed_cycles = 0
        self.alarm_active = False

        # Debugging / Tuning
        self.debug_timer = time.time()
        self.max_mag_observed = 0.0
        self.max_mag_freq = 0.0

        # Audio processing
        self.freq_bins = np.fft.rfftfreq(config.chunk_size, 1.0 / config.sample_rate)
        self.target_freq_idx_min, self.target_freq_idx_max = (
            self._get_frequency_indices()
        )

        # History buffer for smoothing (Reduced to 2 for faster response)
        self.detection_history = deque(maxlen=2)

        logger.info(
            f"Detector initialized for {config.alarm_type.upper()} alarm (T{config.required_beeps})"
        )
        logger.info(
            f"Frequency range: {config.target_frequency - config.frequency_tolerance:.0f} - "
            f"{config.target_frequency + config.frequency_tolerance:.0f} Hz"
        )

    def _get_frequency_indices(self):
        """Calculate FFT bin indices for target frequency range"""
        freq_min = self.config.target_frequency - self.config.frequency_tolerance
        freq_max = self.config.target_frequency + self.config.frequency_tolerance

        idx_min = np.argmin(np.abs(self.freq_bins - freq_min))
        idx_max = np.argmin(np.abs(self.freq_bins - freq_max))

        return idx_min, idx_max

    def detect_target_frequency(self, audio_chunk):
        """FFT analysis to detect target frequency"""
        # Convert to float and normalize
        audio_float = audio_chunk.astype(np.float32) / 32768.0

        # Apply Hann window
        windowed = audio_float * np.hanning(len(audio_float))

        # Compute FFT
        fft_result = np.fft.rfft(windowed)
        fft_magnitude = np.abs(fft_result)

        # Normalize
        if np.max(fft_magnitude) > 0:
            fft_magnitude = fft_magnitude / np.max(fft_magnitude)

        # Extract target band magnitude
        target_band = fft_magnitude[self.target_freq_idx_min : self.target_freq_idx_max]
        max_magnitude = np.max(target_band) if len(target_band) > 0 else 0

        # Find dominant frequency
        if max_magnitude > self.config.min_magnitude_threshold:
            peak_idx = np.argmax(target_band) + self.target_freq_idx_min
            dominant_freq = self.freq_bins[peak_idx]
            return True, max_magnitude, dominant_freq

        return False, max_magnitude, 0

    def update_state_machine(self, freq_detected):
        """State machine for temporal pattern recognition"""
        current_time = time.time()

        # Timeout check
        if current_time - self.last_detection_time > self.config.pattern_timeout:
            if self.beep_count > 0:
                logger.info(
                    f"Pattern timeout. Resetting (Had {self.beep_count} beeps)."
                )
            self._reset_pattern()
            self.last_detection_time = current_time
            return False

        # State 0: Waiting for a beep
        if self.state == BeepState.IDLE:
            if freq_detected:
                self.state = BeepState.BEEPING
                self.beep_start_time = current_time
                self.last_detection_time = current_time
                logger.info(">>> BEEP START DETECTED")

        # State 1: We are currently hearing a beep
        elif self.state == BeepState.BEEPING:
            if not freq_detected:
                beep_duration = current_time - self.beep_start_time
                self.state = BeepState.PAUSED
                self.pause_start_time = current_time
                self.last_detection_time = current_time

                if (
                    self.config.beep_duration_min
                    <= beep_duration
                    <= self.config.beep_duration_max
                ):
                    self.beep_count += 1
                    logger.info(
                        f"*** VALID BEEP ({beep_duration:.2f}s). Count: {self.beep_count}/{self.config.required_beeps} ***"
                    )

                    # Check if pattern complete
                    if self.beep_count >= self.config.required_beeps:
                        self.confirmed_cycles += 1
                        if self.confirmed_cycles >= self.config.confirmation_cycles:
                            self._trigger_alarm()
                            return True
                        else:
                            logger.info(
                                f"Cycle #{self.confirmed_cycles} complete. Resetting for next cycle."
                            )
                            self.beep_count = 0
                            self.state = BeepState.IDLE
                else:
                    logger.info(
                        f"REJECTED BEEP: {beep_duration:.2f}s (Expected {self.config.beep_duration_min}-{self.config.beep_duration_max}s)"
                    )
                    self._reset_pattern()

        # State 2: Waiting for the next beep (silence)
        elif self.state == BeepState.PAUSED:
            if freq_detected:
                pause_duration = current_time - self.pause_start_time
                self.state = BeepState.BEEPING
                self.beep_start_time = current_time
                self.last_detection_time = current_time

                if (
                    self.config.pause_duration_min
                    <= pause_duration
                    <= self.config.pause_duration_max
                ):
                    logger.info(f"VALID PAUSE ({pause_duration:.2f}s) -> Next beep...")
                else:
                    logger.info(
                        f"REJECTED PAUSE: {pause_duration:.2f}s (Expected {self.config.pause_duration_min}-{self.config.pause_duration_max}s)"
                    )
                    self._reset_pattern()

        return False

    def _trigger_alarm(self):
        """Trigger alarm detection event"""
        logger.critical("=" * 60)
        logger.critical(f"🚨 {self.config.alarm_type.upper()} ALARM DETECTED! 🚨")
        logger.critical(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.critical(f"Confidence: {self.confirmed_cycles} consecutive cycles")
        logger.critical("=" * 60)

        self.alarm_active = True

        # Notify state change
        if self.state_callback:
            self.state_callback(True)

        # Reset for next detection
        self._reset_pattern()

    def _reset_pattern(self):
        """Reset state machine"""
        self.state = BeepState.IDLE
        self.beep_count = 0
        self.beep_start_time = None
        self.pause_start_time = None

    def process_audio_chunk(self, audio_chunk):
        """Main processing entry point"""
        self.chunk_count = getattr(self, "chunk_count", 0) + 1

        freq_detected, magnitude, dominant_freq = self.detect_target_frequency(
            audio_chunk
        )

        # Track max magnitude and RMS for debug/tuning
        rms = np.sqrt(np.mean(audio_chunk.astype(np.float32) ** 2))
        self.max_rms_observed = getattr(self, "max_rms_observed", 0.0)

        if magnitude > self.max_mag_observed:
            self.max_mag_observed = magnitude
            self.max_mag_freq = dominant_freq

        if rms > self.max_rms_observed:
            self.max_rms_observed = rms

        # Heartbeat every ~10 seconds (assuming 44100Hz and 4096 chunk size, 1 chunk ~ 0.1s)
        if self.chunk_count % 100 == 0:
            logger.debug(f"Audio heartbeat: Processed {self.chunk_count} chunks...")

        # Periodically log the "loudest" thing heard recently (Unconditional)
        current_time = time.time()
        if current_time - self.debug_timer > 5.0:
            logger.info(
                f"Monitor: Peak Vol (RMS): {self.max_rms_observed:.1f} | Max mag at band: {self.max_mag_observed:.4f} "
                f"(Freq: {self.max_mag_freq:.1f} Hz) [Threshold: {self.config.min_magnitude_threshold}]"
            )

            # Reset monitor
            self.max_mag_observed = 0.0
            self.max_rms_observed = 0.0
            self.debug_timer = current_time

        if freq_detected:
            logger.info(
                f"Target logic: Frequency detected: {dominant_freq:.1f} Hz (mag: {magnitude:.3f})"
            )

        alarm_detected = self.update_state_machine(freq_detected)

        # Auto-clear alarm after detection
        if alarm_detected and self.alarm_active:
            time.sleep(5)  # Keep alarm ON for 5 seconds
            if self.state_callback:
                self.state_callback(False)
            self.alarm_active = False

        return alarm_detected
