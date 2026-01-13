"""Core audio detection logic with state machine.

This module handles:
- FFT analysis for frequency detection
- Temporal pattern recognition (beep-pause patterns)
- State machine for alarm pattern matching
"""

import numpy as np
import time
import logging
from datetime import datetime
from typing import Callable, Optional

from config import DetectorProfile

try:
    from detector.screener import FrequencyScreener
    from detector.analyzer import SpectralAnalyzer
except ImportError:
    # Fallback for when running directly or flat structure
    from screener import FrequencyScreener
    from analyzer import SpectralAnalyzer

logger = logging.getLogger(__name__)


class BeepState:
    """State machine states."""

    IDLE = 0
    BEEPING = 1
    PAUSED = 2


class PatternDetector:
    """Acoustic alarm detector with 4-stage processing pipeline."""

    def __init__(
        self,
        profile: DetectorProfile,
        sample_rate: int,
        chunk_size: int,
        on_detection: Optional[Callable[[bool], None]] = None,
    ):
        """Initialize the pattern detector pipeline.

        Args:
            profile: Detection profile configuration
            sample_rate: Audio sample rate in Hz
            chunk_size: Audio chunk size in samples
            on_detection: Callback when alarm state changes
        """
        self.profile = profile
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.on_detection = on_detection
        self.state = BeepState.IDLE

        # Pipeline Components
        self.screener = FrequencyScreener(profile, sample_rate, chunk_size)
        self.analyzer = SpectralAnalyzer(profile)

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
        self.chunk_count = 0
        self.max_rms_observed = 0.0
        # self.rejection_reasons = {}  # Could track stats on rejections

        logger.info(
            f"Detector [{profile.name}] pipeline initialized:\n"
            f"  • Target: {profile.target_frequency}Hz ±{profile.frequency_tolerance}\n"
            f"  • Quality: >{profile.min_energy_ratio * 100:.0f}% energy, >{profile.min_peak_sharpness}x sharpness\n"
            f"  • Pattern: {profile.beep_count} beeps, {profile.confirmation_cycles} cycles"
        )

    def update_state_machine(self, freq_detected: bool) -> bool:
        """State machine for temporal pattern recognition.

        Returns:
            True if alarm pattern was successfully matched
        """
        current_time = time.time()
        p = self.profile

        # Timeout check
        if current_time - self.last_detection_time > p.pattern_timeout:
            if self.beep_count > 0:
                logger.info(
                    f"[{p.name}] Pattern timeout. Resetting (Had {self.beep_count} beeps)."
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
                logger.debug(f"[{p.name}] >>> BEEP START DETECTED")

        # State 1: Currently hearing a beep
        elif self.state == BeepState.BEEPING:
            if not freq_detected:
                beep_duration = current_time - self.beep_start_time
                self.state = BeepState.PAUSED
                self.pause_start_time = current_time
                self.last_detection_time = current_time

                if p.beep_duration_min <= beep_duration <= p.beep_duration_max:
                    self.beep_count += 1
                    logger.info(
                        f"[{p.name}] *** VALID BEEP ({beep_duration:.2f}s). "
                        f"Count: {self.beep_count}/{p.required_beeps} ***"
                    )

                    # Check if pattern complete
                    if self.beep_count >= p.required_beeps:
                        self.confirmed_cycles += 1
                        if self.confirmed_cycles >= p.confirmation_cycles:
                            self._trigger_alarm()
                            return True
                        else:
                            logger.info(
                                f"[{p.name}] Cycle #{self.confirmed_cycles} complete. "
                                "Resetting for next cycle."
                            )
                            self.beep_count = 0
                            self.state = BeepState.IDLE
                else:
                    logger.debug(
                        f"[{p.name}] REJECTED BEEP: {beep_duration:.2f}s "
                        f"(Expected {p.beep_duration_min}-{p.beep_duration_max}s)"
                    )
                    self._reset_pattern()

        # State 2: Waiting for the next beep (silence)
        elif self.state == BeepState.PAUSED:
            if freq_detected:
                pause_duration = current_time - self.pause_start_time
                self.state = BeepState.BEEPING
                self.beep_start_time = current_time
                self.last_detection_time = current_time

                if p.pause_duration_min <= pause_duration <= p.pause_duration_max:
                    logger.debug(
                        f"[{p.name}] VALID PAUSE ({pause_duration:.2f}s) -> Next beep..."
                    )
                else:
                    logger.debug(
                        f"[{p.name}] REJECTED PAUSE: {pause_duration:.2f}s "
                        f"(Expected {p.pause_duration_min}-{p.pause_duration_max}s)"
                    )
                    self._reset_pattern()

        return False

    def _trigger_alarm(self) -> None:
        """Trigger alarm detection event."""
        logger.critical("=" * 60)
        logger.critical(f"🚨 [{self.profile.name.upper()}] ALARM DETECTED! 🚨")
        logger.critical(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.critical(f"Confidence: {self.confirmed_cycles} consecutive cycles")
        logger.critical("=" * 60)

        self.alarm_active = True

        # Notify state change
        if self.on_detection:
            self.on_detection(True)

        # Reset for next detection
        self._reset_pattern()

    def _reset_pattern(self) -> None:
        """Reset state machine."""
        self.state = BeepState.IDLE
        self.beep_count = 0
        self.beep_start_time = None
        self.pause_start_time = None

    def process(self, audio_chunk: np.ndarray) -> bool:
        """Process an audio chunk for pattern detection.

        Args:
            audio_chunk: Audio samples as numpy array

        Returns:
            True if alarm was detected in this chunk
        """
        self.chunk_count += 1

        # 1. SCREENER: Preliminary Frequency Detection
        screen_result = self.screener.screen(audio_chunk)

        # Track max magnitude and RMS for debug/tuning
        rms = np.sqrt(np.mean(audio_chunk.astype(np.float32) ** 2))
        if screen_result.magnitude > self.max_mag_observed:
            self.max_mag_observed = screen_result.magnitude
            self.max_mag_freq = screen_result.dominant_freq

        if rms > self.max_rms_observed:
            self.max_rms_observed = rms

        # Periodic monitoring (every ~5 seconds)
        current_time = time.time()
        if current_time - self.debug_timer > 5.0:
            logger.info(
                f"[{self.profile.name}] Monitor: RMS={self.max_rms_observed:.1f} | "
                f"Mag={self.max_mag_observed:.4f} @ {self.max_mag_freq:.1f}Hz "
                f"[Threshold: {self.profile.min_magnitude_threshold}]"
            )
            # Reset monitor
            self.max_mag_observed = 0.0
            self.max_rms_observed = 0.0
            self.debug_timer = current_time

        # 2. ANALYZER: Spectral Quality Validation
        target_detected = False

        if screen_result.detected:
            analysis = self.analyzer.analyze(screen_result)

            if analysis.is_valid:
                target_detected = True
                logger.info(
                    f"[{self.profile.name}] Hit: {screen_result.dominant_freq:.1f}Hz "
                    f"(Mag: {screen_result.magnitude:.2f}, E-Ratio: {analysis.energy_ratio:.2f}, Sharp: {analysis.sharpness:.1f})"
                )
            else:
                # Log rejections occasionally or if debugging
                if self.chunk_count % 20 == 0:  # Don't spam logs
                    logger.debug(
                        f"[{self.profile.name}] Rejected: {', '.join(analysis.reasons)}"
                    )

        # 3. PATTERN MATCHER: Temporal State Machine
        alarm_detected = self.update_state_machine(target_detected)

        # Auto-clear alarm after detection
        if alarm_detected and self.alarm_active:
            time.sleep(5)  # Keep alarm ON for 5 seconds
            if self.on_detection:
                self.on_detection(False)
            self.alarm_active = False

        return alarm_detected


# Legacy compatibility alias
AlarmDetector = PatternDetector
