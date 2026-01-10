"""Advanced DSP filtering for improved alarm detection"""
import numpy as np
from scipy import signal
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

class AlarmSignalProcessor:
    """
    DSP pipeline for alarm signal enhancement
    Based on SciPy documentation for bandpass filters and spectral analysis
    """

    def __init__(self, sample_rate: int, target_freq: float, freq_tolerance: float):
        self.sample_rate = sample_rate
        self.target_freq = target_freq
        self.freq_tolerance = freq_tolerance

        # Design bandpass filter for alarm frequency range
        self.sos = self._design_bandpass_filter()

        # Initialize filter state for continuous processing
        self.zi = signal.sosfilt_zi(self.sos)

        logger.info(f"DSP processor initialized with bandpass filter: "
                   f"{target_freq - freq_tolerance:.0f} - {target_freq + freq_tolerance:.0f} Hz")

    def _design_bandpass_filter(self):
        """
        Design Butterworth bandpass filter for alarm frequency isolation
        Reference: SciPy documentation - Butterworth filter design
        """
        # Calculate normalized frequencies (0 to 1, where 1 is Nyquist)
        nyquist = self.sample_rate / 2
        low_freq = (self.target_freq - self.freq_tolerance) / nyquist
        high_freq = (self.target_freq + self.freq_tolerance) / nyquist

        # Clamp to valid range
        low_freq = max(0.001, min(0.999, low_freq))
        high_freq = max(0.001, min(0.999, high_freq))

        # Design 4th-order Butterworth bandpass filter
        # Using SOS (second-order sections) for numerical stability
        sos = signal.butter(
            N=4,
            Wn=[low_freq, high_freq],
            btype='bandpass',
            analog=False,
            output='sos'
        )

        logger.debug(f"Bandpass filter: {low_freq*nyquist:.1f} - {high_freq*nyquist:.1f} Hz")
        return sos

    def process_chunk(self, audio_chunk: np.ndarray) -> np.ndarray:
        """
        Apply bandpass filter to audio chunk with state preservation
        Maintains filter state across chunks for continuous processing
        """
        # Convert to float
        audio_float = audio_chunk.astype(np.float32) / 32768.0

        # Apply bandpass filter with state
        filtered, self.zi = signal.sosfilt(self.sos, audio_float, zi=self.zi)

        return filtered

    def estimate_psd_welch(self, audio_chunk: np.ndarray,
                          nperseg: int = 2048) -> Tuple[np.ndarray, np.ndarray]:
        """
        Power Spectral Density estimation using Welch's method
        Reference: SciPy documentation - Welch's method for spectral estimation

        Provides smoother, more reliable frequency analysis than raw FFT
        """
        audio_float = audio_chunk.astype(np.float32) / 32768.0

        # Welch's method: segments, windows, averages for reduced noise
        f, Pxx = signal.welch(
            audio_float,
            fs=self.sample_rate,
            nperseg=min(nperseg, len(audio_float)),
            scaling='density'
        )

        return f, Pxx

    def detect_alarm_frequency_advanced(self, audio_chunk: np.ndarray) -> Tuple[bool, float, float]:
        """
        Advanced frequency detection using bandpass filtering + Welch's method
        More robust than simple FFT for noisy environments
        """
        # Step 1: Apply bandpass filter to isolate alarm frequency range
        filtered = self.process_chunk(audio_chunk)

        # Step 2: Use Welch's method for robust PSD estimation
        f, Pxx = self.estimate_psd_welch(filtered)

        # Step 3: Find indices corresponding to target frequency range
        freq_mask = (f >= self.target_freq - self.freq_tolerance) & \
                   (f <= self.target_freq + self.freq_tolerance)

        if not np.any(freq_mask):
            return False, 0.0, 0.0

        # Step 4: Calculate power in target band
        target_power = np.sum(Pxx[freq_mask])
        total_power = np.sum(Pxx)

        # Normalized power ratio
        power_ratio = target_power / total_power if total_power > 0 else 0

        # Find dominant frequency in target band
        target_pxx = Pxx[freq_mask]
        target_freqs = f[freq_mask]

        if len(target_pxx) > 0:
            dominant_idx = np.argmax(target_pxx)
            dominant_freq = target_freqs[dominant_idx]

            # Detection threshold based on power concentration
            is_detected = power_ratio > 0.3  # 30% of power in target band

            return is_detected, power_ratio, dominant_freq

        return False, 0.0, 0.0
