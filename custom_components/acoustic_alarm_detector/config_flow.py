"""Config flow for Acoustic Alarm Detector integration."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    ALARM_TYPE_CO,
    ALARM_TYPE_SMOKE,
    CONF_ALARM_TYPE,
    CONF_DEVICE_NAME,
    DEFAULT_ALARM_TYPE,
    DEFAULT_DEVICE_NAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Path to profiles written by the add-on
PROFILES_PATH = "/config/acoustic_alarm_detector/profiles.json"


class AcousticAlarmDetectorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Acoustic Alarm Detector."""

    VERSION = 1

    async def _get_available_profiles(self) -> dict[str, str]:
        """Read available profiles from add-on config file.

        Returns:
            Dictionary mapping profile name to display name
        """
        try:
            if os.path.exists(PROFILES_PATH):
                with open(PROFILES_PATH, "r") as f:
                    data = json.load(f)

                profiles = data.get("profiles", [])
                if profiles:
                    _LOGGER.info(f"Loaded {len(profiles)} profiles from add-on config")
                    return {
                        p["name"]: p.get(
                            "friendly_name", p["name"].replace("_", " ").title()
                        )
                        for p in profiles
                    }

        except Exception as e:
            _LOGGER.warning(f"Could not load profiles from add-on: {e}")

        # Fallback to default options if file not found or invalid
        _LOGGER.info("Using default alarm types (smoke, co)")
        return {
            ALARM_TYPE_SMOKE: "Smoke Alarm",
            ALARM_TYPE_CO: "CO Alarm",
        }

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate unique device name
            await self.async_set_unique_id(
                f"{user_input[CONF_DEVICE_NAME]}_{user_input[CONF_ALARM_TYPE]}"
            )
            self._abort_if_unique_id_configured()

            # Create the config entry
            return self.async_create_entry(
                title=f"{user_input[CONF_DEVICE_NAME]} ({user_input[CONF_ALARM_TYPE].upper()})",
                data=user_input,
            )

        # Get available alarm types dynamically
        available_profiles = await self._get_available_profiles()

        # Show the configuration form
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_DEVICE_NAME,
                    default=DEFAULT_DEVICE_NAME,
                ): str,
                vol.Required(
                    CONF_ALARM_TYPE,
                    default=DEFAULT_ALARM_TYPE,
                ): vol.In(available_profiles),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> AcousticAlarmDetectorOptionsFlow:
        """Get the options flow for this handler."""
        return AcousticAlarmDetectorOptionsFlow(config_entry)


class AcousticAlarmDetectorOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Acoustic Alarm Detector."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Currently no options to configure
        # In the future, you could add sensitivity settings here
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
        )
