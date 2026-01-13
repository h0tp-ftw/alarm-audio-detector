"""Digital Signal Processing (DSP) layer for audio analysis."""

import numpy as np
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Peak:
    """A spectral peak."""

    frequency: float
    magnitude: float
    bin_index: int


class SpectralMonitor:
    """
    Monitors audio chunks for spectral peaks and tracks them over time
    to identify persistent tones.
    """

    def __init__(self, sample_rate: int, chunk_size: int):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.freq_bins = np.fft.rfftfreq(chunk_size, 1.0 / sample_rate)
        self.window = np.hanning(chunk_size)

        # Configuration
        self.min_magnitude = 0.05  # Minimum normalized magnitude to consider a peak
        self.min_sharpness = 1.5  # Peak required to be X times higher than neighbors

        # State tracking (simple per-chunk for now, can be expanded to multi-chunk tracking)
        self._last_peaks: List[Peak] = []

    def process(self, audio_chunk: np.ndarray) -> List[Peak]:
        """
        Process an audio chunk and return significant spectral peaks.
        """
        # 1. Windowing & Normalization
        if len(audio_chunk) != self.chunk_size:
            # Handle partial chunks if necessary, or pad
            return []

        float_chunk = audio_chunk.astype(np.float32) / 32768.0
        windowed = float_chunk * self.window

        # 2. FFT
        fft_data = np.abs(np.fft.rfft(windowed))

        # Normalize relative to max possible amplitude (approx)
        # Real-world normalization might need a dynamic noise floor
        max_val = np.max(fft_data) if len(fft_data) > 0 else 0
        if max_val == 0:
            return []

        normalized_fft = fft_data / np.max(
            fft_data
        )  # Normalize to 0-1 for relative peak finding?
        # Actually safer to keep "absolute" magnitude logic relative to full scale
        # but for peak picking, relative is easier. Let's use raw magnitude for thresholding.

        # 3. Peak Finding
        peaks: List[Peak] = []

        # Simple local maxima search
        # We skip the very first and last few bins to avoid DC/Nyquist edge cases
        for i in range(2, len(fft_data) - 2):
            mag = fft_data[i]
            if mag < self.min_magnitude:  # Absolute threshold
                continue

            # Check if it's a local peak
            if mag > fft_data[i - 1] and mag > fft_data[i + 1]:
                # Sharpness check (ratio against neighbors +2/-2)
                neighbors = (
                    fft_data[i - 2]
                    + fft_data[i - 1]
                    + fft_data[i + 1]
                    + fft_data[i + 2]
                ) / 4.0
                if neighbors == 0:
                    neighbors = 1e-6

                if mag / neighbors > self.min_sharpness:
                    freq = self.freq_bins[i]
                    peaks.append(Peak(frequency=freq, magnitude=mag, bin_index=i))

        # Sort by magnitude descending
        peaks.sort(key=lambda x: x.magnitude, reverse=True)

        # Limit to top N peaks to avoid noise
        return peaks[:5]
