"""REST API client for communicating with Home Assistant."""

import json
import logging
import os
import urllib.request
import urllib.error
from typing import Optional

logger = logging.getLogger(__name__)


class IntegrationClient:
    """Client for communicating with HA via REST API (fires events)."""

    def __init__(self, device_name: str = "", alarm_type: str = ""):
        """Initialize the integration client."""
        self.device_name = device_name or os.getenv("DEVICE_NAME", "smoke_alarm")
        self.alarm_type = alarm_type or os.getenv("ALARM_TYPE", "smoke")
        self.connected = False

        # Get HA API URL and token (via Supervisor proxy)
        self.api_url = "http://supervisor/core/api"
        self.token = os.getenv("SUPERVISOR_TOKEN")

        if self.token:
            logger.info(
                f"Integration client initialized (token length: {len(self.token)})"
            )
            logger.info(f"Device: {self.device_name}, Alarm type: {self.alarm_type}")
        else:
            logger.warning("No SUPERVISOR_TOKEN found in environment!")

    def connect(self) -> bool:
        """Test connection to Home Assistant API."""
        if not self.token:
            logger.warning("No SUPERVISOR_TOKEN available")
            return False

        try:
            # Test API connection
            req = urllib.request.Request(
                f"{self.api_url}/",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    logger.info("✅ Connected to Home Assistant API")
                    self.connected = True
                    return True
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP error connecting to HA: {e.code} {e.reason}")
        except urllib.error.URLError as e:
            logger.error(f"URL error connecting to HA: {e.reason}")
        except Exception as e:
            logger.error(f"Failed to connect to HA API: {e}")

        return False

    def update_state(self, detected: bool) -> bool:
        """Update alarm state by firing an event and setting entity state."""
        if not self.token:
            logger.warning("No token - cannot update state")
            return False

        entity_id = f"binary_sensor.{self.device_name}_{self.alarm_type}"

        # First, try to set the binary sensor state directly
        success = self._set_entity_state(entity_id, detected)

        # Also fire an event for any other listeners
        self._fire_event(detected)

        return success

    def _set_entity_state(self, entity_id: str, detected: bool) -> bool:
        """Set binary sensor state via REST API."""
        state = "on" if detected else "off"

        payload = {
            "state": state,
            "attributes": {
                "device_class": "smoke" if self.alarm_type == "smoke" else "gas",
                "friendly_name": f"{self.device_name.replace('_', ' ').title()} {self.alarm_type.title()} Alarm",
            },
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.api_url}/states/{entity_id}",
                data=data,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status in (200, 201):
                    logger.info(f"✅ Set {entity_id} to {state}")
                    return True
                else:
                    logger.error(f"Unexpected response: {response.status}")
                    return False

        except urllib.error.HTTPError as e:
            logger.error(f"HTTP error setting state: {e.code} {e.reason}")
            try:
                error_body = e.read().decode("utf-8")
                logger.error(f"Error details: {error_body}")
            except:
                pass
        except Exception as e:
            logger.error(f"Failed to set entity state: {e}")

        return False

    def _fire_event(self, detected: bool) -> bool:
        """Fire an event for other listeners."""
        event_type = "acoustic_alarm_detector_state_changed"

        payload = {
            "device_name": self.device_name,
            "alarm_type": self.alarm_type,
            "state": detected,
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.api_url}/events/{event_type}",
                data=data,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    logger.debug(f"Event fired: {event_type}")
                    return True

        except Exception as e:
            logger.debug(f"Failed to fire event: {e}")

        return False

    def disconnect(self):
        """Disconnect (no-op for REST API)."""
        self.connected = False
        logger.info("Integration client disconnected")


# Synchronous wrapper (for compatibility with existing code)
class SyncIntegrationClient:
    """Synchronous wrapper for IntegrationClient."""

    def __init__(self, entry_id: Optional[str] = None):
        """Initialize sync client."""
        # entry_id is ignored for REST API approach
        self.client = IntegrationClient()
        self.connected = False

    def connect(self) -> bool:
        """Connect (synchronous)."""
        self.connected = self.client.connect()
        return self.connected

    def update_state(self, state: bool) -> bool:
        """Update state (synchronous)."""
        return self.client.update_state(state)

    def disconnect(self):
        """Disconnect (synchronous)."""
        self.client.disconnect()
        self.connected = False
