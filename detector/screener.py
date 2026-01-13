"""FFT-based frequency screening module."""

import numpy as np
from dataclasses import dataclass
from typing import Tuple, Optional
from config import DetectorProfile


@dataclass
class ScreenerResult:
    """Result of preliminary frequency screening."""

    detected: bool
    magnitude: float
    dominant_freq: float
    fft_magnitude: np.ndarray
    target_band: np.ndarray
    peak_index: int = 0


class FrequencyScreener:
    """Performs FFT and screens for potential alarm frequencies."""

    def __init__(self, profile: DetectorProfile, sample_rate: int, chunk_size: int):
        self.profile = profile
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size

        # Pre-calculate frequency bins
        self.freq_bins = np.fft.rfftfreq(chunk_size, 1.0 / sample_rate)

        # Calculate target indices once
        freq_min = profile.target_frequency - profile.frequency_tolerance
        freq_max = profile.target_frequency + profile.frequency_tolerance

        self.idx_min = np.argmin(np.abs(self.freq_bins - freq_min))
        self.idx_max = np.argmin(np.abs(self.freq_bins - freq_max))

    def screen(self, audio_chunk: np.ndarray) -> ScreenerResult:
        """Perform FFT and check for target frequency presence."""

        # 1. Normalize and Window
        audio_float = audio_chunk.astype(np.float32) / 32768.0
        windowed = audio_float * np.hanning(len(audio_float))

        # 2. Compute FFT
        fft_result = np.fft.rfft(windowed)
        fft_magnitude = np.abs(fft_result)

        # 3. Normalize Magnitude
        max_val = np.max(fft_magnitude)
        if max_val > 0:
            fft_magnitude = fft_magnitude / max_val

        # 4. Check Target Band
        target_band = fft_magnitude[self.idx_min : self.idx_max]

        detected = False
        max_mag = 0.0
        dominant_freq = 0.0
        peak_idx = 0

        if len(target_band) > 0:
            max_mag = np.max(target_band)

            if max_mag > self.profile.min_magnitude_threshold:
                local_peak_idx = np.argmax(target_band)
                peak_idx = self.idx_min + local_peak_idx
                dominant_freq = self.freq_bins[peak_idx]
                detected = True

        return ScreenerResult(
            detected=detected,
            magnitude=max_mag,
            dominant_freq=dominant_freq,
            fft_magnitude=fft_magnitude,
            target_band=target_band,
            peak_index=peak_idx,
        )
