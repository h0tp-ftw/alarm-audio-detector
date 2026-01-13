"""YAML configuration loader for AlarmProfiles."""

import yaml
import logging
from typing import List, Union
from pathlib import Path

from detector.models import AlarmProfile, Segment, Range

logger = logging.getLogger(__name__)


def load_profile_from_yaml(path: Union[str, Path]) -> AlarmProfile:
    """Load a single AlarmProfile from a YAML file.

    Example YAML format:
    ```yaml
    name: "SmokeAlarm"
    confirmation_cycles: 2
    segments:
      - type: "tone"
        frequency:
          min: 2900
          max: 3100
        duration:
          min: 0.4
          max: 0.6
      - type: "silence"
        duration:
          min: 0.1
          max: 0.3
    ```
    """
    with open(path, "r") as f:
        data = yaml.safe_load(f)

    return _parse_profile(data)


def load_profiles_from_yaml(path: Union[str, Path]) -> List[AlarmProfile]:
    """Load multiple AlarmProfiles from a YAML file.

    Supports three formats:
    1. Single profile (dict with 'name', 'segments')
    2. List of profiles (list of dicts)
    3. Bundled profiles (dict with 'profiles' key containing list)
    """
    with open(path, "r") as f:
        data = yaml.safe_load(f)

    # Format 3: Bundled profiles (dict with 'profiles' key)
    if isinstance(data, dict) and "profiles" in data:
        return [_parse_profile(p) for p in data["profiles"]]

    # Format 2: List of profiles
    if isinstance(data, list):
        return [_parse_profile(p) for p in data]

    # Format 1: Single profile
    return [_parse_profile(data)]


def _parse_profile(data: dict) -> AlarmProfile:
    """Parse a profile dictionary into an AlarmProfile object."""
    segments = []

    for seg_data in data.get("segments", []):
        seg_type = seg_data.get("type", "tone")

        # Parse frequency range (only for tones)
        frequency = None
        if seg_type == "tone" and "frequency" in seg_data:
            freq_data = seg_data["frequency"]
            if isinstance(freq_data, dict):
                frequency = Range(
                    min=float(freq_data.get("min", 0)),
                    max=float(freq_data.get("max", 20000)),
                )
            else:
                # Single value: apply ±5% tolerance
                freq = float(freq_data)
                frequency = Range(min=freq * 0.95, max=freq * 1.05)

        # Parse duration range
        dur_data = seg_data.get("duration", {"min": 0.1, "max": 1.0})
        if isinstance(dur_data, dict):
            duration = Range(
                min=float(dur_data.get("min", 0.1)), max=float(dur_data.get("max", 1.0))
            )
        else:
            # Single value: apply ±20% tolerance
            dur = float(dur_data)
            duration = Range(min=dur * 0.8, max=dur * 1.2)

        segments.append(
            Segment(
                type=seg_type,
                frequency=frequency,
                duration=duration,
                min_magnitude=float(seg_data.get("min_magnitude", 0.05)),
            )
        )

    return AlarmProfile(
        name=data.get("name", "UnnamedProfile"),
        segments=segments,
        confirmation_cycles=int(data.get("confirmation_cycles", 1)),
        reset_timeout=float(data.get("reset_timeout", 10.0)),
    )


def save_profile_to_yaml(profile: AlarmProfile, path: Union[str, Path]) -> None:
    """Save an AlarmProfile to a YAML file."""
    data = {
        "name": profile.name,
        "confirmation_cycles": profile.confirmation_cycles,
        "reset_timeout": profile.reset_timeout,
        "segments": [],
    }

    for seg in profile.segments:
        seg_data = {
            "type": seg.type,
            "duration": {"min": seg.duration.min, "max": seg.duration.max},
        }

        if seg.type == "tone" and seg.frequency:
            seg_data["frequency"] = {"min": seg.frequency.min, "max": seg.frequency.max}
            seg_data["min_magnitude"] = seg.min_magnitude

        data["segments"].append(seg_data)

    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    logger.info(f"Saved profile '{profile.name}' to {path}")
