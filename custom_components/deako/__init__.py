"""The deako integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.components import zeroconf

from .const import CONNECTION_ID, DISCOVERER_ID, DOMAIN

from .deako import Deako
from .discover import DeakoDiscoverer, DevicesNotFoundExecption

_LOGGER: logging.Logger = logging.getLogger(__package__)

PLATFORMS: list[Platform] = [Platform.LIGHT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up deako from a config entry."""

    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})

    try:
        deako_discoverer = hass.data[DOMAIN][DISCOVERER_ID]
    except KeyError:
        zc = await zeroconf.async_get_instance(hass)
        deako_discoverer = DeakoDiscoverer(zc)

    address = await deako_discoverer.get_address()
    connection = Deako(address, "Home Assistant")
    await connection.connect()
    await connection.find_devices()

    hass.data[DOMAIN][entry.entry_id] = connection

    for platform in PLATFORMS:
        if entry.options.get(platform, True):
            await hass.async_add_job(
                hass.config_entries.async_forward_entry_setup(entry, platform)
            )

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
