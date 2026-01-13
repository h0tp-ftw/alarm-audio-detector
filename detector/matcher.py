"""State machine for matching event streams against alarm profiles."""

import time
import logging
from typing import List, Optional, Dict
from dataclasses import dataclass

from detector.models import AlarmProfile, Segment
from detector.events import AudioEvent, ToneEvent, PatternMatchEvent

logger = logging.getLogger(__name__)


class MatcherState:
    """Tracks progress of a single profile match."""

    def __init__(self, profile: AlarmProfile):
        self.profile = profile
        self.current_segment_index = 0
        self.cycle_count = 0
        self.last_event_time = 0.0
        self.start_time = 0.0

    def reset(self):
        self.current_segment_index = 0
        self.cycle_count = 0
        self.last_event_time = 0.0


class SequenceMatcher:
    """
    Maintains state for multiple alarm profiles and matches incoming events.
    """

    def __init__(self, profiles: List[AlarmProfile]):
        self.profiles = profiles
        self.states = {p.name: MatcherState(p) for p in profiles}

    def process(self, event: AudioEvent) -> List[PatternMatchEvent]:
        """
        Process a new event and return any full pattern matches.
        """
        matches = []

        for profile in self.profiles:
            match_event = self._update_profile(self.states[profile.name], event)
            if match_event:
                matches.append(match_event)

        return matches

    def _update_profile(
        self, state: MatcherState, event: AudioEvent
    ) -> Optional[PatternMatchEvent]:
        p = state.profile

        # Current expected segment
        if state.current_segment_index >= len(p.segments):
            # Should have reset or wrapped?
            state.current_segment_index = 0

        expected = p.segments[state.current_segment_index]

        # 0. Check Timeout (Global reset if silence too long between relevant events)
        # Note: We only check timeout if we have technically started matching (index > 0)
        if state.current_segment_index > 0:
            time_since_last = event.timestamp - state.last_event_time
            # Allow for the *expected* silence duration + grace period
            # But currently `event` comes IN after silence.
            # So `time_since_last` IS the silence duration (roughly).

            # If the current expected segment IS a silence, we check if this "gap" fits.
            # If expected is Tone, and we got a Tone, the "gap" was the time before this tone.
            pass

        # 1. Match Logic
        is_match = False

        if isinstance(event, ToneEvent):
            # Check implicit silence before this tone (Gap)
            gap_duration = event.timestamp - (
                state.last_event_time + (0 if state.last_event_time == 0 else 0)
            )  # wait, last_event_time tracked end of previous?
            # We need to track end of previous event to calculate gap.
            # For now, let's assume last_event_time is END of previous event.

            # If we are expecting a SILENCE, we check if the gap matches
            if expected.type == "silence":
                if expected.duration.contains(gap_duration):
                    # Good silence! Advance to next expectation
                    state.current_segment_index += 1

                    if state.current_segment_index >= len(p.segments):
                        state.cycle_count += 1
                        state.current_segment_index = 0
                        logger.debug(
                            f"[{p.name}] Cycle {state.cycle_count}/{p.confirmation_cycles} Complete (on Silence)"
                        )

                        if state.cycle_count >= p.confirmation_cycles:
                            state.cycle_count = 0
                            return PatternMatchEvent(
                                timestamp=event.timestamp,
                                duration=0,
                                profile_name=p.name,
                                cycle_count=p.confirmation_cycles,
                            )

                    expected = p.segments[state.current_segment_index]
                else:
                    # Silence matched type but Wrong duration?
                    # Or we just ignore minor mismatches in silence if strictness allows?
                    # Strict for now.
                    if state.current_segment_index > 0:
                        logger.debug(
                            f"[{p.name}] Reset: Gap {gap_duration:.2f}s not in {expected.duration.min}-{expected.duration.max}s"
                        )
                        state.reset()
                        expected = p.segments[0]  # Restart matching with this tone

            # Now check if this TONE matches the current expectation (which might be 0 or N after matched silence)
            if expected.type == "tone":
                freq_match = expected.frequency.contains(event.frequency)
                dur_match = expected.duration.contains(event.duration)

                if freq_match and dur_match:
                    is_match = True
                    logger.debug(
                        f"[{p.name}] Step {state.current_segment_index} OK: {event.frequency:.0f}Hz, {event.duration:.2f}s"
                    )
                else:
                    if state.current_segment_index > 0:
                        logger.debug(
                            f"[{p.name}] Mismatch at step {state.current_segment_index}: {event.frequency:.0f}Hz/{event.duration:.2f}s"
                        )
                        state.reset()
                        # Try to match step 0?
                        expected = p.segments[0]
                        if (
                            expected.type == "tone"
                            and expected.frequency.contains(event.frequency)
                            and expected.duration.contains(event.duration)
                        ):
                            is_match = True

        # 2. Advance State
        if is_match:
            # Update timing tracking
            state.last_event_time = event.timestamp + event.duration
            state.current_segment_index += 1

            # Check for Cycle Completion
            if state.current_segment_index >= len(p.segments):
                state.cycle_count += 1
                state.current_segment_index = 0  # Loop back for next cycle
                logger.debug(
                    f"[{p.name}] Cycle {state.cycle_count}/{p.confirmation_cycles} Complete"
                )

                if state.cycle_count >= p.confirmation_cycles:
                    state.cycle_count = 0  # Optional: reset or keep counting? Reset for continuous re-trigger
                    return PatternMatchEvent(
                        timestamp=event.timestamp,
                        duration=0,
                        profile_name=p.name,
                        cycle_count=p.confirmation_cycles,
                    )

        return None
