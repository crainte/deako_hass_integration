"""Config flow for deako."""
# import my_pypi_dependency

from homeassistant.components import zeroconf
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_flow

from .const import DISCOVERER_ID, DOMAIN
from .discover import DeakoDiscoverer, DevicesNotFoundExecption


async def _async_has_devices(hass: HomeAssistant) -> bool:
    """Return if there are devices that can be discovered."""
    zc = await zeroconf.async_get_instance(hass)
    discoverer = DeakoDiscoverer(zc)

    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {
            DISCOVERER_ID: discoverer,
        })
    else:
        hass.data[DISCOVERER_ID] = discoverer

    try:
        await discoverer.get_address()
        # address exists, there's at least one device
        return True

    except DevicesNotFoundExecption:
        return False


config_entry_flow.register_discovery_flow(DOMAIN, "deako", _async_has_devices)
