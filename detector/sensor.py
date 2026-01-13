"""Sensor component for Home Assistant integration.

This module handles:
- Communication with Home Assistant via REST API
- Sensor state management
- Writing available profiles for the integration config flow
"""

import json
import logging
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

from integration_client import IntegrationClient

logger = logging.getLogger(__name__)


@dataclass
class SensorProfile:
    """Represents a detector profile for HA sensor creation."""

    name: str
    device_class: str  # "smoke", "gas", "safety", etc.
    friendly_name: Optional[str] = None

    def __post_init__(self):
        if not self.friendly_name:
            self.friendly_name = self.name.replace("_", " ").title()


class SensorManager:
    """Manages sensor state updates and profile sharing with HA integration."""

    def __init__(self, device_name: str, profiles: List[SensorProfile]):
        """Initialize the sensor manager.

        Args:
            device_name: Base device name for sensors
            profiles: List of detector profiles to register
        """
        self.device_name = device_name
        self.profiles = profiles
        self._clients: dict[str, IntegrationClient] = {}
        self._connected = False

        # Path where profiles are written for the integration to read
        self._profiles_dir = Path("/config/acoustic_alarm_detector")
        self._profiles_file = self._profiles_dir / "profiles.json"

    def setup(self) -> bool:
        """Initialize HA clients and write profile config.

        Returns:
            True if at least one client connected successfully
        """
        logger.info("=" * 50)
        logger.info("SENSOR MANAGER - INITIALIZATION")
        logger.info("=" * 50)

        # Write profiles for integration config flow
        self._write_profiles()

        # Create a client for each profile
        success_count = 0
        for profile in self.profiles:
            client = IntegrationClient(
                device_name=self.device_name, alarm_type=profile.name
            )

            if client.connect():
                logger.info(f"✅ Connected sensor: {profile.name}")
                success_count += 1
            else:
                logger.warning(f"⚠️ Failed to connect sensor: {profile.name}")

            self._clients[profile.name] = client

        self._connected = success_count > 0
        logger.info(f"Connected {success_count}/{len(self.profiles)} sensors")
        return self._connected

    def _write_profiles(self) -> None:
        """Write available profiles to shared JSON for integration."""
        try:
            self._profiles_dir.mkdir(parents=True, exist_ok=True)

            profile_data = {
                "device_name": self.device_name,
                "profiles": [
                    {
                        "name": p.name,
                        "device_class": p.device_class,
                        "friendly_name": p.friendly_name,
                    }
                    for p in self.profiles
                ],
            }

            with open(self._profiles_file, "w") as f:
                json.dump(profile_data, f, indent=2)

            logger.info(f"📝 Wrote profiles to {self._profiles_file}")

        except Exception as e:
            logger.error(f"Failed to write profiles: {e}")

    def update_state(self, profile_name: str, detected: bool) -> bool:
        """Update sensor state in Home Assistant.

        Args:
            profile_name: Name of the profile/sensor to update
            detected: True if alarm detected, False otherwise

        Returns:
            True if state update succeeded
        """
        client = self._clients.get(profile_name)
        if not client:
            logger.error(f"No client for profile: {profile_name}")
            return False

        state_str = "DETECTED" if detected else "CLEAR"
        logger.info(f"🔔 {profile_name}: {state_str}")

        success = client.update_state(detected)
        if success:
            logger.info(f"✅ Updated {profile_name} sensor")
        else:
            logger.error(f"❌ Failed to update {profile_name} sensor")

        return success

    def create_detection_callback(self, profile_name: str):
        """Create a callback function for detector to call on detection.

        Args:
            profile_name: Name of the profile this callback is for

        Returns:
            Callback function that accepts detected: bool
        """

        def callback(detected: bool) -> None:
            self.update_state(profile_name, detected)

        return callback

    def cleanup(self) -> None:
        """Disconnect all clients."""
        logger.info("Cleaning up sensor connections...")
        for name, client in self._clients.items():
            try:
                client.disconnect()
            except Exception:
                pass
        self._clients.clear()
        logger.info("Sensor cleanup complete")
