"""Generates discrete events from continuous DSP data."""

import time
import logging
from typing import List, Optional, Dict
from dataclasses import dataclass

from detector.events import AudioEvent, ToneEvent, SilenceEvent
from detector.dsp import Peak

logger = logging.getLogger(__name__)


@dataclass
class ActiveTone:
    """Tracks a currently playing tone."""

    start_time: float
    frequency: float
    max_magnitude: float
    last_seen_time: float
    samples_count: int


class EventGenerator:
    """
    Consumes spectral peaks chunk-by-chunk and emits Tone/Silence events.
    Handles debouncing and tone continuity.
    """

    def __init__(self, sample_rate: int, chunk_size: int):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.chunk_duration = chunk_size / sample_rate

        # Configuration
        self.frequency_tolerance = 50.0  # hz to match same tone
        self.min_tone_duration = 0.1  # Minimum duration to be a valid tone
        self.dropout_tolerance = 0.15  # Max time a tone can be missing before ending

        # State
        self.active_tones: List[ActiveTone] = []
        self.last_process_time = 0.0

    def process(self, peaks: List[Peak], timestamp: float) -> List[AudioEvent]:
        """
        Ingest peaks for a time slice and return completed events.
        """
        events: List[AudioEvent] = []
        current_active_indices = set()

        # 1. Match current peaks to active tones
        for peak in peaks:
            matched = False
            for i, tone in enumerate(self.active_tones):
                if abs(peak.frequency - tone.frequency) < self.frequency_tolerance:
                    # Update existing tone
                    tone.max_magnitude = max(tone.max_magnitude, peak.magnitude)
                    tone.last_seen_time = timestamp
                    tone.samples_count += 1
                    # Average frequency tracking could go here
                    current_active_indices.add(i)
                    matched = True
                    break

            if not matched:
                # New potential tone
                new_tone = ActiveTone(
                    start_time=timestamp,
                    frequency=peak.frequency,
                    max_magnitude=peak.magnitude,
                    last_seen_time=timestamp,
                    samples_count=1,
                )
                self.active_tones.append(new_tone)
                current_active_indices.add(len(self.active_tones) - 1)

        # 2. Check for ended tones (timeouts)
        active_tones_next: List[ActiveTone] = []

        for i, tone in enumerate(self.active_tones):
            if i in current_active_indices:
                active_tones_next.append(tone)
            else:
                # Tone missing in this chunk
                time_since_seen = timestamp - tone.last_seen_time

                if time_since_seen > self.dropout_tolerance:
                    # Tone officially ended
                    # Calculate duration based on number of active chunks
                    duration = tone.samples_count * self.chunk_duration

                    if duration >= self.min_tone_duration:
                        # Valid tone event
                        event = ToneEvent(
                            timestamp=tone.start_time,
                            duration=duration,
                            frequency=tone.frequency,
                            magnitude=tone.max_magnitude,
                            confidence=1.0,
                        )
                        events.append(event)
                        logger.debug(
                            f"Generated Tone: {event.frequency:.0f}Hz, {event.duration:.2f}s"
                        )

                        # Also generate a Silence event for the gap between the *true end* and now?
                        # Or let the matcher infer silence?
                        # Explicit silence events are tricky because "silence" is just "absence of specific tone".
                        # Let's emit tones, and let matcher calculate gaps.
                        pass
                    else:
                        # Too short, noise glitch
                        pass
                else:
                    # keep waiting, might come back (dropout)
                    active_tones_next.append(tone)

        self.active_tones = active_tones_next
        self.last_process_time = timestamp

        return events
