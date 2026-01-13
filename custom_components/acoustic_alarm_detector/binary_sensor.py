"""Binary sensor platform for Acoustic Alarm Detector."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ALARM_TYPE_CO,
    ALARM_TYPE_SMOKE,
    CONF_ALARM_TYPE,
    CONF_DEVICE_NAME,
    DEFAULT_DEVICE_NAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Acoustic Alarm Detector binary sensor."""
    _LOGGER.info("Setting up binary sensor platform")

    device_name = entry.data.get(CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME)
    alarm_type = entry.data.get(CONF_ALARM_TYPE, ALARM_TYPE_SMOKE)

    # Create the binary sensor entity
    sensor = AcousticAlarmBinarySensor(
        entry_id=entry.entry_id,
        device_name=device_name,
        alarm_type=alarm_type,
    )

    async_add_entities([sensor])


class AcousticAlarmBinarySensor(BinarySensorEntity):
    """Representation of an Acoustic Alarm Detector binary sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        entry_id: str,
        device_name: str,
        alarm_type: str,
    ) -> None:
        """Initialize the binary sensor."""
        self._entry_id = entry_id
        self._device_name = device_name
        self._alarm_type = alarm_type
        self._attr_is_on = False

        # Set device class based on alarm type
        if alarm_type == ALARM_TYPE_SMOKE:
            self._attr_device_class = BinarySensorDeviceClass.SMOKE
            sensor_name = "Smoke Alarm"
        elif alarm_type == ALARM_TYPE_CO:
            self._attr_device_class = BinarySensorDeviceClass.GAS
            sensor_name = "CO Alarm"
        else:
            self._attr_device_class = BinarySensorDeviceClass.SAFETY
            sensor_name = "Alarm"

        # Set unique ID and name
        self._attr_unique_id = f"{device_name}_{alarm_type}"
        self._attr_name = sensor_name

        # Set device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_name)},
            name=f"Acoustic {sensor_name} Detector",
            manufacturer="Open Source",
            model="Acoustic DSP Detector",
            sw_version="9.0.0",
        )

        _LOGGER.info(
            f"Created binary sensor: {self._attr_unique_id} "
            f"(device_class: {self._attr_device_class})"
        )

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self._attr_is_on

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "alarm_type": self._alarm_type,
            "device_name": self._device_name,
            "integration": "acoustic_alarm_detector",
        }

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()

        # Subscribe to state change events
        self.async_on_remove(
            self.hass.bus.async_listen(
                f"{DOMAIN}_state_changed",
                self._handle_state_changed,
            )
        )

        _LOGGER.info(f"Binary sensor {self._attr_unique_id} added to Home Assistant")

    @callback
    def _handle_state_changed(self, event: Event) -> None:
        """Handle state change event from integration."""
        if event.data.get("entry_id") == self._entry_id:
            new_state = event.data.get("state", False)

            if new_state != self._attr_is_on:
                self._attr_is_on = new_state
                self.async_write_ha_state()

                _LOGGER.info(
                    f"Binary sensor {self._attr_unique_id} state changed to "
                    f"{'ON' if new_state else 'OFF'}"
                )
