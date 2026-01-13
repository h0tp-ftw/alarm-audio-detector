"""The Acoustic Alarm Detector integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Acoustic Alarm Detector integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Acoustic Alarm Detector from a config entry."""
    _LOGGER.info("Setting up Acoustic Alarm Detector integration")

    # Store config entry data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "config": entry.data,
        "state": False,  # Initial alarm state
    }

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register WebSocket API for add-on communication
    await _async_register_websocket_api(hass, entry)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Acoustic Alarm Detector integration")

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _async_register_websocket_api(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Register WebSocket API handlers for add-on communication."""
    from homeassistant.components import websocket_api
    import voluptuous as vol

    @websocket_api.websocket_command(
        {
            vol.Required("type"): "acoustic_alarm_detector/update_state",
            vol.Required("entry_id"): str,
            vol.Required("state"): bool,
        }
    )
    @websocket_api.async_response
    async def handle_state_update(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        """Handle state update from add-on."""
        entry_id = msg["entry_id"]
        state = msg["state"]

        if entry_id not in hass.data[DOMAIN]:
            connection.send_error(
                msg["id"], "entry_not_found", "Config entry not found"
            )
            return

        # Update stored state
        hass.data[DOMAIN][entry_id]["state"] = state

        # Fire event to update binary sensor
        hass.bus.async_fire(
            f"{DOMAIN}_state_changed",
            {"entry_id": entry_id, "state": state},
        )

        _LOGGER.info(
            f"State updated to {'ON' if state else 'OFF'} for entry {entry_id}"
        )
        connection.send_result(msg["id"], {"success": True})

    # Register the command
    websocket_api.async_register_command(hass, handle_state_update)
    _LOGGER.info("WebSocket API registered for add-on communication")
