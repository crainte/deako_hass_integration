import logging

from asyncio import sleep
from zeroconf import ServiceBrowser, Zeroconf
from socket import inet_ntoa


DEAKO_TYPE = "_deako._tcp.local."
TIMEOUT_S = 10

_LOGGER = logging.getLogger(__name__)


class DevicesNotFoundExecption(Exception):
    pass


class DeakoDiscoverer(ServiceBrowser):
    addresses = set()

    def __init__(self, zeroconf: Zeroconf) -> None:
        self.zeroconf = zeroconf
        super().__init__(
            self.zeroconf,
            DEAKO_TYPE,
            MyListener(
                self.device_address_callback, self.device_address_removed_callback
            ),
        )

    def device_address_callback(self, address: str):
        _LOGGER.info(f"adding address {address} to set of available devices, new list: {self.addresses}")
        self.addresses.add(address)

    def device_address_removed_callback(self, address: str):
        _LOGGER.info(f"removing address {address} from set of available devices, new list: {self.addresses}")
        self.addresses.pop()

    async def get_address(self):
        _LOGGER.info("getting address for deako")
        total_time = 0
        while total_time < TIMEOUT_S and len(self.addresses) < 1:
            total_time += 0.1
            await sleep(0.1)
        if len(self.addresses) == 0:
            _LOGGER.error("No devices found!")
            raise DevicesNotFoundExecption()
        address = self.addresses.pop()
        self.addresses.add(address)
        _LOGGER.info(f"Found device at {address}")
        self.cancel()
        return address

    def stop(self):
        self.zeroconf.close()


class MyListener:
    def __init__(
        self, device_address_callback, device_address_removed_callback
    ) -> None:
        self.device_address_callback = device_address_callback
        self.device_address_removed_callback = device_address_removed_callback

    def remove_service(self, zeroconf, type, name):
        addresses = self.get_addresses(zeroconf, type, name)
        for address in addresses:
            self.device_address_removed_callback(address)

    def add_service(self, zeroconf: Zeroconf, type, name):
        addresses = self.get_addresses(zeroconf, type, name)
        for address in addresses:
            self.device_address_callback(address)

    def update_service(self, zeroconf, type, name):
        pass  # suppress warnings

    def get_addresses(self, zeroconf: Zeroconf, type, name):
        _LOGGER.info(f"getting mdns info for {type}:{name}")
        info = zeroconf.get_service_info(type, name)
        if info is not None:
            addresses = info.addresses
            port = info.port
            return [f"{inet_ntoa(address)}:{port}" for address in addresses]
        return []
