"""Data models for Universal Alarm Engine configuration."""

from dataclasses import dataclass, field
from typing import List, Literal, Optional


@dataclass
class Range:
    """A numeric range (min, max)."""

    min: float
    max: float

    def contains(self, value: float) -> bool:
        return self.min <= value <= self.max


@dataclass
class Segment:
    """A single step in an alarm pattern."""

    type: Literal["tone", "silence", "any"]

    # Tone specific
    frequency: Optional[Range] = None  # hz
    min_magnitude: float = 0.05

    # Timing
    duration: Range = field(default_factory=lambda: Range(0, 999))

    def __str__(self):
        if self.type == "tone":
            return f"Tone({self.frequency.min}-{self.frequency.max}Hz, {self.duration.min}-{self.duration.max}s)"
        elif self.type == "silence":
            return f"Silence({self.duration.min}-{self.duration.max}s)"
        return "Any"


@dataclass
class AlarmProfile:
    """Definition of an alarm pattern."""

    name: str
    segments: List[Segment]
    confirmation_cycles: int = 1  # How many full sequences required
    reset_timeout: float = 10.0  # Reset if next event takes too long
