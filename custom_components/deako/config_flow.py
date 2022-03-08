"""Config flow for deako."""
# import my_pypi_dependency

from homeassistant.components import zeroconf
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_flow

from .const import DOMAIN
from .deako import Deako
from .discover import DeakoDiscoverer, DevicesNotFoundExecption


async def _async_has_devices(hass: HomeAssistant) -> bool:
    """Return if there are devices that can be discovered."""
    zc = await zeroconf.async_get_instance(hass)
    discoverer = DeakoDiscoverer(zc)

    try:
        address = await discoverer.get_address()
        deako = Deako(address, "Home Assistant")
        await deako.connect()
        await deako.find_devices(timeout=5)
        devices = deako.get_devices()
        await deako.disconnect()  # TODO: reuse this connection
        return len(devices) > 0

    except DevicesNotFoundExecption:
        return False


config_entry_flow.register_discovery_flow(DOMAIN, "deako", _async_has_devices)
