"""Configuration management for Acoustic Alarm Detector"""

import os
from dataclasses import dataclass


@dataclass
class DetectorConfig:
    """Configuration loaded from environment variables"""

    @staticmethod
    def _safe_int(key: str, default: str) -> int:
        val = os.getenv(key, default)
        return int(val) if val and val.strip() else int(default)

    @staticmethod
    def _safe_float(key: str, default: str) -> float:
        val = os.getenv(key, default)
        return float(val) if val and val.strip() else float(default)

    # Device Configuration
    device_name: str = os.getenv("DEVICE_NAME", "smoke_alarm_detector")
    alarm_type: str = os.getenv("ALARM_TYPE", "smoke")  # "smoke" (T3) or "co" (T4)

    # Audio Configuration
    sample_rate: int = _safe_int("SAMPLE_RATE", "44100")
    chunk_size: int = 4096
    channels: int = 1
    audio_device_index: int = (
        int(os.getenv("AUDIO_DEVICE_INDEX"))
        if os.getenv("AUDIO_DEVICE_INDEX") and os.getenv("AUDIO_DEVICE_INDEX").strip()
        else None
    )

    # Detection Parameters
    target_frequency: float = _safe_float("TARGET_FREQ", "3150")
    frequency_tolerance: float = _safe_float("FREQ_TOLERANCE", "150")
    min_magnitude_threshold: float = _safe_float("MIN_MAGNITUDE", "0.15")

    # Temporal Pattern Parameters
    beep_duration_min: float = _safe_float("BEEP_MIN", "0.1")
    beep_duration_max: float = _safe_float("BEEP_MAX", "1.5")
    pause_duration_min: float = _safe_float("PAUSE_MIN", "0.05")
    pause_duration_max: float = _safe_float("PAUSE_MAX", "2.5")

    # Pattern Recognition
    confirmation_cycles: int = _safe_int("CONFIRMATION_CYCLES", "2")
    pattern_timeout: float = 10.0

    @property
    def required_beeps(self) -> int:
        """Return required beeps based on alarm type"""
        return 3 if self.alarm_type == "smoke" else 4  # T3 vs T4
