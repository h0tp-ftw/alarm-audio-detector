"""Event definitions for various stages of the detection pipeline."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TimeRange:
    """A time interval."""

    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class AudioEvent:
    """Base class for all audio events."""

    timestamp: float
    duration: float


@dataclass
class ToneEvent(AudioEvent):
    """Represents a detected tone."""

    frequency: float
    magnitude: float
    confidence: float


@dataclass
class SilenceEvent(AudioEvent):
    """Represents a period of silence (or non-target noise)."""

    pass


@dataclass
class PatternMatchEvent(AudioEvent):
    """Represents a successful pattern match."""

    profile_name: str
    cycle_count: int
