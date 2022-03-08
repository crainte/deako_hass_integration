"""Config flow for deako."""
import logging

from homeassistant.components import zeroconf
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_flow

from .const import CONNECTION_ID, DOMAIN
from .deako import Deako
from .discover import DeakoDiscoverer, DevicesNotFoundExecption

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def _async_has_devices(hass: HomeAssistant) -> bool:
    """Return if there are devices that can be discovered."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})

    zc = await zeroconf.async_get_instance(hass)
    discoverer = DeakoDiscoverer(zc)

    try:
        address = await discoverer.get_address()

        _LOGGER.info(f"got address {address}, connecting to find devices")
        deako = Deako(address, "Home Assistant")
        await deako.connect()

        _LOGGER.info("connected, finding devices")
        await deako.find_devices(timeout=10)

        devices = deako.get_devices()
        _LOGGER.info(f"found {len(devices)} devices")

        hass.data[DOMAIN][CONNECTION_ID] = deako
        return len(devices) > 0

    except DevicesNotFoundExecption:
        return False


config_entry_flow.register_discovery_flow(DOMAIN, "deako", _async_has_devices)
