"""Auto-Tuner: Analyzes audio samples and proposes AlarmProfile configurations.

This module provides:
1. Audio analysis to detect tone/silence patterns
2. Clustering of similar segments
3. Profile generation with appropriate tolerances
"""

import numpy as np
import logging
from typing import List, Optional
from dataclasses import dataclass
from collections import defaultdict

from detector.models import AlarmProfile, Segment, Range
from detector.dsp import SpectralMonitor

logger = logging.getLogger(__name__)


@dataclass
class DetectedSegment:
    """A segment detected during analysis."""

    type: str  # 'tone' or 'silence'
    start_time: float
    end_time: float
    frequency: Optional[float] = None  # Only for tones
    magnitude: Optional[float] = None

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


@dataclass
class AnalysisResult:
    """Result of auto-tuner analysis."""

    segments: List[DetectedSegment]
    proposed_profile: AlarmProfile
    confidence: float  # 0-1, how confident we are in the extraction
    warnings: List[str]


class AutoTuner:
    """Analyzes audio and proposes AlarmProfile configurations."""

    def __init__(self, sample_rate: int = 44100, chunk_size: int = 4096):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.dsp = SpectralMonitor(sample_rate, chunk_size)

        # Tuning parameters
        self.silence_threshold = 0.02  # RMS below this = silence
        self.min_segment_duration = 0.05  # Ignore segments shorter than this
        self.frequency_tolerance_pct = 0.05  # ±5% frequency tolerance
        self.duration_tolerance_pct = 0.20  # ±20% duration tolerance

    def analyze(
        self, audio_data: np.ndarray, profile_name: str = "AutoTuned"
    ) -> AnalysisResult:
        """Analyze audio data and propose an AlarmProfile.

        Args:
            audio_data: Audio samples as numpy array (int16 or float32)
            profile_name: Name for the generated profile

        Returns:
            AnalysisResult with detected segments and proposed profile
        """
        warnings = []

        # Normalize audio
        if audio_data.dtype == np.int16:
            audio = audio_data.astype(np.float32) / 32768.0
        else:
            audio = audio_data.astype(np.float32)

        # Step 1: Segment audio into tone/silence regions
        raw_segments = self._extract_segments(audio)

        if not raw_segments:
            warnings.append(
                "No segments detected. Audio may be too quiet or too noisy."
            )
            return AnalysisResult(
                segments=[],
                proposed_profile=AlarmProfile(name=profile_name, segments=[]),
                confidence=0.0,
                warnings=warnings,
            )

        # Step 2: Merge very short segments (noise)
        merged_segments = self._merge_short_segments(raw_segments)

        # Step 3: Cluster similar segments
        clustered = self._cluster_segments(merged_segments)

        # Step 4: Generate profile with tolerances
        profile_segments = self._generate_profile_segments(clustered)

        # Step 5: Detect cycles (repetition)
        cycles_detected = self._detect_cycles(merged_segments)

        if cycles_detected > 1:
            logger.info(f"Detected {cycles_detected} repetitions of the pattern")

        # Calculate confidence
        confidence = self._calculate_confidence(merged_segments, clustered)

        if confidence < 0.5:
            warnings.append(
                "Low confidence extraction. Consider recording a cleaner sample."
            )

        profile = AlarmProfile(
            name=profile_name,
            segments=profile_segments,
            confirmation_cycles=max(1, cycles_detected),
            reset_timeout=10.0,
        )

        return AnalysisResult(
            segments=merged_segments,
            proposed_profile=profile,
            confidence=confidence,
            warnings=warnings,
        )

    def _extract_segments(self, audio: np.ndarray) -> List[DetectedSegment]:
        """Extract raw tone/silence segments from audio."""
        segments = []

        current_type = None
        segment_start = 0.0
        current_mag = None
        freq_history = []

        for i in range(0, len(audio) - self.chunk_size, self.chunk_size):
            chunk = audio[i : i + self.chunk_size]
            timestamp = i / self.sample_rate

            # Calculate RMS
            rms = np.sqrt(np.mean(chunk**2))

            if rms < self.silence_threshold:
                # Silence
                if current_type == "tone":
                    # End previous tone
                    avg_freq = np.median(freq_history) if freq_history else 0
                    segments.append(
                        DetectedSegment(
                            type="tone",
                            start_time=segment_start,
                            end_time=timestamp,
                            frequency=avg_freq,
                            magnitude=current_mag,
                        )
                    )
                    freq_history = []
                    segment_start = timestamp
                    current_type = "silence"
                elif current_type is None:
                    current_type = "silence"
                    segment_start = timestamp
            else:
                # Potential tone - analyze spectrum
                chunk_int16 = (chunk * 32767).astype(np.int16)
                peaks = self.dsp.process(chunk_int16)

                if peaks:
                    dominant_freq = peaks[0].frequency
                    dominant_mag = peaks[0].magnitude

                    if current_type == "silence":
                        # End previous silence
                        segments.append(
                            DetectedSegment(
                                type="silence",
                                start_time=segment_start,
                                end_time=timestamp,
                            )
                        )
                        segment_start = timestamp
                        current_type = "tone"
                        freq_history = [dominant_freq]
                        current_mag = dominant_mag
                    elif current_type == "tone":
                        freq_history.append(dominant_freq)
                        current_mag = max(current_mag or 0, dominant_mag)
                    elif current_type is None:
                        current_type = "tone"
                        segment_start = timestamp
                        freq_history = [dominant_freq]
                        current_mag = dominant_mag

        # Close final segment
        final_time = len(audio) / self.sample_rate
        if current_type == "tone" and freq_history:
            segments.append(
                DetectedSegment(
                    type="tone",
                    start_time=segment_start,
                    end_time=final_time,
                    frequency=np.median(freq_history),
                    magnitude=current_mag,
                )
            )
        elif current_type == "silence":
            segments.append(
                DetectedSegment(
                    type="silence", start_time=segment_start, end_time=final_time
                )
            )

        return segments

    def _merge_short_segments(
        self, segments: List[DetectedSegment]
    ) -> List[DetectedSegment]:
        """Merge segments that are too short (likely noise)."""
        if not segments:
            return []

        merged = []
        for seg in segments:
            if seg.duration < self.min_segment_duration:
                # Too short, try to merge with previous
                if merged and merged[-1].type == seg.type:
                    # Extend previous
                    merged[-1] = DetectedSegment(
                        type=merged[-1].type,
                        start_time=merged[-1].start_time,
                        end_time=seg.end_time,
                        frequency=merged[-1].frequency,
                        magnitude=merged[-1].magnitude,
                    )
                elif merged:
                    # Different type, extend previous anyway (absorb noise)
                    merged[-1] = DetectedSegment(
                        type=merged[-1].type,
                        start_time=merged[-1].start_time,
                        end_time=seg.end_time,
                        frequency=merged[-1].frequency,
                        magnitude=merged[-1].magnitude,
                    )
                # else: skip if first segment is too short
            else:
                merged.append(seg)

        return merged

    def _cluster_segments(self, segments: List[DetectedSegment]) -> dict:
        """Cluster similar segments together."""
        tone_clusters = defaultdict(list)
        silence_clusters = []

        for seg in segments:
            if seg.type == "tone" and seg.frequency:
                # Group by frequency (within tolerance)
                matched = False
                for cluster_freq in list(tone_clusters.keys()):
                    if abs(seg.frequency - cluster_freq) / cluster_freq < 0.1:
                        tone_clusters[cluster_freq].append(seg)
                        matched = True
                        break
                if not matched:
                    tone_clusters[seg.frequency].append(seg)
            else:
                silence_clusters.append(seg)

        return {"tones": dict(tone_clusters), "silences": silence_clusters}

    def _generate_profile_segments(self, clustered: dict) -> List[Segment]:
        """Generate profile segments from clustered data."""
        profile_segments = []

        # For each tone cluster, create a segment with tolerances
        for freq, segs in clustered["tones"].items():
            durations = [s.duration for s in segs]
            avg_dur = np.mean(durations)

            profile_segments.append(
                Segment(
                    type="tone",
                    frequency=Range(
                        min=freq * (1 - self.frequency_tolerance_pct),
                        max=freq * (1 + self.frequency_tolerance_pct),
                    ),
                    duration=Range(
                        min=avg_dur * (1 - self.duration_tolerance_pct),
                        max=avg_dur * (1 + self.duration_tolerance_pct),
                    ),
                    min_magnitude=0.05,
                )
            )

        # For silences
        if clustered["silences"]:
            durations = [s.duration for s in clustered["silences"]]
            avg_dur = np.mean(durations)

            profile_segments.append(
                Segment(
                    type="silence",
                    duration=Range(
                        min=avg_dur * (1 - self.duration_tolerance_pct),
                        max=avg_dur * (1 + self.duration_tolerance_pct),
                    ),
                )
            )

        return profile_segments

    def _detect_cycles(self, segments: List[DetectedSegment]) -> int:
        """Detect how many times the pattern repeats."""
        if len(segments) < 4:
            return 1

        # Simple heuristic: count tone segments
        tone_count = sum(1 for s in segments if s.type == "tone")

        # Try to find repeating pattern length
        for pattern_len in range(2, min(6, tone_count // 2 + 1)):
            if tone_count % pattern_len == 0:
                return tone_count // pattern_len

        return 1

    def _calculate_confidence(
        self, segments: List[DetectedSegment], clustered: dict
    ) -> float:
        """Calculate confidence score for the extraction."""
        if not segments:
            return 0.0

        score = 1.0

        # Penalize if too few segments
        if len(segments) < 3:
            score *= 0.5

        # Penalize high frequency variance in clusters
        for freq, segs in clustered["tones"].items():
            if len(segs) > 1:
                freqs = [s.frequency for s in segs if s.frequency]
                if freqs:
                    variance = np.std(freqs) / np.mean(freqs)
                    if variance > 0.1:
                        score *= 0.8

        # Penalize very short total duration
        total_duration = segments[-1].end_time - segments[0].start_time
        if total_duration < 1.0:
            score *= 0.7

        return min(1.0, max(0.0, score))


def analyze_audio_file(
    file_path: str, profile_name: str = "AutoTuned"
) -> AnalysisResult:
    """Convenience function to analyze a WAV file."""
    import wave

    with wave.open(file_path, "rb") as wf:
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()
        audio_bytes = wf.readframes(n_frames)
        audio = np.frombuffer(audio_bytes, dtype=np.int16)

    tuner = AutoTuner(sample_rate=sample_rate)
    return tuner.analyze(audio, profile_name)
