"""Binary sensor platform for integration_blueprint."""
from .const import (
    DOMAIN,
)

import logging

from homeassistant.components.light import (
    ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS, LightEntity)

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Configure the platform."""
    client = hass.data[DOMAIN][entry.entry_id]

    devices = client.get_devices()
    lights = [DeakoLightSwitch(client, uuid) for uuid in devices]
    async_add_entities(lights, True)


class DeakoLightSwitch(LightEntity):
    """Deako LightEntity class."""

    def __init__(self, connection, uuid):
        self.connection = connection
        self.uuid = uuid
        self.connection.set_state_callback(self.uuid, self.on_update)

    def on_update(self):
        self.schedule_update_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {
                (DOMAIN, self.uuid)
            },
            "name": self.name,
            "uuid": self.uuid,
            "manufacturer": "Deako",
            "model": "dimmer" if self.supported_features == SUPPORT_BRIGHTNESS else "smart"
        }

    @property
    def unique_id(self):
        """Return the ID of this Deako light."""
        return self.uuid

    @property
    def name(self):
        """Return the name of the Deako light."""
        return self.connection.get_name_for_device(self.uuid)

    @property
    def is_on(self):
        """Return true if the lihgt is on."""
        state = self.connection.get_state_for_device(self.uuid)
        return state["power"]

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        state = self.connection.get_state_for_device(self.uuid)
        if state["dim"] is None:
            return None
        return state["dim"] * 2.55

    @property
    def supported_features(self):
        """Flag supported features."""
        state = self.connection.get_state_for_device(self.uuid)
        if state["dim"] is None:
            return 0
        return SUPPORT_BRIGHTNESS

    async def async_turn_on(self, **kwargs):
        state = self.connection.get_state_for_device(self.uuid)
        dim = 100
        if state["dim"] is not None:
            dim = state["dim"]
        if ATTR_BRIGHTNESS in kwargs:
            dim = (kwargs[ATTR_BRIGHTNESS] / 255) * 100
        await self.connection.send_device_control(self.uuid, True, round(dim, 0))

    async def async_turn_off(self, **kwargs):
        state = self.connection.get_state_for_device(self.uuid)
        dim = 100
        if state["dim"] is not None:
            dim = state["dim"]
        if ATTR_BRIGHTNESS in kwargs:
            dim = (kwargs[ATTR_BRIGHTNESS] / 255) * 100
        await self.connection.send_device_control(self.uuid, False, round(dim, 0))
