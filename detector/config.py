"""Configuration management for Acoustic Alarm Detector.

Supports multiple detector profiles loaded from environment or config.
"""

import json
import os
import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DetectorProfile:
    """Configuration for a single detector profile."""

    name: str
    device_class: str = "smoke"  # "smoke", "gas", "safety"

    # Detection Parameters
    target_frequency: float = 3150.0
    frequency_tolerance: float = 150.0
    min_magnitude_threshold: float = 0.15

    # Temporal Pattern Parameters
    beep_duration_min: float = 0.1
    beep_duration_max: float = 1.5
    pause_duration_min: float = 0.05
    pause_duration_max: float = 2.5

    # Pattern Recognition
    confirmation_cycles: int = 2
    pattern_timeout: float = 10.0
    beep_count: int = 3  # T3=3 beeps, T4=4 beeps

    # Analysis / Quality Thresholds
    min_energy_ratio: float = 0.08  # Target band must contain 8% of total energy (was 0.12, conservative start)
    min_peak_sharpness: float = 2.0  # Peak must be 2x higher than neighbors (was 2.5)
    max_freq_variance: float = 60.0  # Max Hz deviation during visual beep
    min_magnitude_consistency: float = 0.3  # Min/Max magnitude ratio during beep

    @property
    def required_beeps(self) -> int:
        """Return required beeps for pattern match."""
        return self.beep_count


@dataclass
class AudioSettings:
    """Shared audio capture settings."""

    sample_rate: int = 44100
    chunk_size: int = 4096
    channels: int = 1
    device_index: Optional[int] = None


@dataclass
class DetectorConfig:
    """Main configuration container."""

    device_name: str = "acoustic_alarm"
    audio: AudioSettings = field(default_factory=AudioSettings)
    profiles: List[DetectorProfile] = field(default_factory=list)
    debug_mode: bool = False

    @classmethod
    def from_environment(cls) -> "DetectorConfig":
        """Load configuration from environment variables (legacy single-profile mode)."""

        def safe_int(key: str, default: str) -> int:
            val = os.getenv(key, default)
            return int(val) if val and val.strip() else int(default)

        def safe_float(key: str, default: str) -> float:
            val = os.getenv(key, default)
            return float(val) if val and val.strip() else float(default)

        # Audio settings
        audio = AudioSettings(
            sample_rate=safe_int("SAMPLE_RATE", "44100"),
            chunk_size=4096,
            channels=1,
            device_index=(
                int(os.getenv("AUDIO_DEVICE_INDEX"))
                if os.getenv("AUDIO_DEVICE_INDEX", "").strip()
                else None
            ),
        )

        # Get alarm type to determine pattern
        alarm_type = os.getenv("ALARM_TYPE", "smoke")
        beep_count = 4 if alarm_type == "co" else 3  # T4 vs T3
        device_class = "gas" if alarm_type == "co" else "smoke"

        # Create single profile from environment
        profile = DetectorProfile(
            name=alarm_type,
            device_class=device_class,
            target_frequency=safe_float("TARGET_FREQ", "3150"),
            frequency_tolerance=safe_float("FREQ_TOLERANCE", "150"),
            min_magnitude_threshold=safe_float("MIN_MAGNITUDE", "0.15"),
            beep_duration_min=safe_float("BEEP_MIN", "0.1"),
            beep_duration_max=safe_float("BEEP_MAX", "1.5"),
            pause_duration_min=safe_float("PAUSE_MIN", "0.05"),
            pause_duration_max=safe_float("PAUSE_MAX", "2.5"),
            confirmation_cycles=safe_int("CONFIRMATION_CYCLES", "2"),
            beep_count=beep_count,
        )

        return cls(
            device_name=os.getenv("DEVICE_NAME", "smoke_alarm_detector"),
            audio=audio,
            profiles=[profile],
            debug_mode=os.getenv("DEBUG_MODE", "false").lower() == "true",
        )

    @classmethod
    def from_json_file(cls, path: str) -> "DetectorConfig":
        """Load configuration from a JSON file (future multi-profile mode)."""
        with open(path, "r") as f:
            data = json.load(f)

        audio = AudioSettings(**data.get("audio", {}))
        profiles = [DetectorProfile(**p) for p in data.get("profiles", [])]

        return cls(
            device_name=data.get("device_name", "acoustic_alarm"),
            audio=audio,
            profiles=profiles,
            debug_mode=data.get("debug_mode", False),
        )

    def log_config(self) -> None:
        """Log the current configuration."""
        logger.info("=" * 60)
        logger.info("ACOUSTIC ALARM DETECTOR - CONFIGURATION")
        logger.info("=" * 60)
        logger.info(f"Device Name: {self.device_name}")
        logger.info(f"Sample Rate: {self.audio.sample_rate} Hz")
        logger.info(f"Audio Device: {self.audio.device_index or 'default'}")
        logger.info(f"Debug Mode: {self.debug_mode}")
        logger.info("-" * 40)
        logger.info(f"Detector Profiles: {len(self.profiles)}")
        for p in self.profiles:
            logger.info(f"  • {p.name} ({p.device_class})")
            logger.info(
                f"    Frequency: {p.target_frequency}Hz ±{p.frequency_tolerance}"
            )
            logger.info(
                f"    Beeps: {p.beep_count}, Confirmations: {p.confirmation_cycles}"
            )
        logger.info("=" * 60)


# Legacy compatibility: Keep old DetectorConfig behavior
# This allows existing code to continue working during transition
def _create_legacy_config() -> DetectorConfig:
    """Create config for legacy single-profile mode."""
    return DetectorConfig.from_environment()
