"""Spectral quality analysis module for validating alarm candidacy."""

import numpy as np
import logging
from collections import deque
from dataclasses import dataclass
from typing import List

from config import DetectorProfile
from screener import ScreenerResult

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Result of spectral quality analysis."""

    is_valid: bool
    reasons: List[str]
    energy_ratio: float = 0.0
    sharpness: float = 0.0
    freq_variance: float = 0.0
    mag_consistency: float = 0.0


class SpectralAnalyzer:
    """Analyzes audio spectral characteristics to filter false positives."""

    def __init__(self, profile: DetectorProfile):
        self.profile = profile

        # State tracking for stability checks
        self.freq_history = deque(maxlen=10)
        self.mag_history = deque(maxlen=5)

    def analyze(self, result: ScreenerResult) -> AnalysisResult:
        """Run spectral quality checks on a preliminary detection."""
        if not result.detected:
            self._reset_history()
            return AnalysisResult(False, ["No primary detection"])

        reasons = []
        is_valid = True

        # 1. Energy Ratio Check
        # Alarms concentrate energy in narrow band; music spreads it out.
        total_energy = np.sum(result.fft_magnitude**2)
        target_energy = np.sum(result.target_band**2)
        energy_ratio = target_energy / (total_energy + 1e-10)

        if energy_ratio < self.profile.min_energy_ratio:
            is_valid = False
            reasons.append(
                f"Low energy ratio: {energy_ratio:.3f} < {self.profile.min_energy_ratio}"
            )

        # 2. Peak Sharpness Check
        # Alarm peaks are sharp; music peaks are often broad/harmonic.
        peak_idx = result.peak_index
        peak_val = result.fft_magnitude[peak_idx]

        # Average of neighbors (avoiding self)
        window_width = 10
        start = max(0, peak_idx - window_width)
        end = min(len(result.fft_magnitude), peak_idx + window_width + 1)
        neighbors = result.fft_magnitude[start:end]

        # Exclude the peak itself from average
        neighbor_sum = np.sum(neighbors) - peak_val
        neighbor_count = len(neighbors) - 1
        neighbor_avg = neighbor_sum / (neighbor_count + 1e-10)

        sharpness = peak_val / (neighbor_avg + 1e-10)

        if sharpness < self.profile.min_peak_sharpness:
            is_valid = False
            reasons.append(
                f"Low sharpness: {sharpness:.1f} < {self.profile.min_peak_sharpness}"
            )

        # 3. Frequency Stability (Temporal)
        self.freq_history.append(result.dominant_freq)
        freq_variance = 0.0

        if len(self.freq_history) >= 3:
            freq_variance = np.std(self.freq_history)
            if freq_variance > self.profile.max_freq_variance:
                is_valid = False
                reasons.append(
                    f"Unstable frequency: std={freq_variance:.1f} > {self.profile.max_freq_variance}"
                )

        # 4. Magnitude Consistency (Temporal)
        self.mag_history.append(result.magnitude)
        mag_consistency = 1.0

        if len(self.mag_history) >= 3:
            min_mag = min(self.mag_history)
            max_mag = max(self.mag_history)
            mag_consistency = min_mag / (max_mag + 1e-10)

            if mag_consistency < self.profile.min_magnitude_consistency:
                is_valid = False
                reasons.append(
                    f"Inconsistent magnitude: {mag_consistency:.2f} < {self.profile.min_magnitude_consistency}"
                )

        if not is_valid:
            logger.debug(f"Analysis Rejected: {', '.join(reasons)}")
            # If invalid, we might want to reset history or just let it slide?
            # Usually better to not clear history immediately on one bad frame to handle noise,
            # but cleared here for simplicity if it persists.

        return AnalysisResult(
            is_valid=is_valid,
            reasons=reasons,
            energy_ratio=energy_ratio,
            sharpness=sharpness,
            freq_variance=freq_variance,
            mag_consistency=mag_consistency,
        )

    def _reset_history(self):
        """Reset temporal tracking history."""
        self.freq_history.clear()
        self.mag_history.clear()
