import logging

from asyncio import sleep
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
from socket import inet_ntoa


DEAKO_TYPE = "_deako._tcp.local."
TIMEOUT_S = 3

_LOGGER = logging.getLogger(__name__)


class DevicesNotFoundExecption(Exception):
    pass


class DeakoDiscoverer(ServiceBrowser):
    addresses = set()  # for uniqueness
    done = False

    def __init__(self, zeroconf: Zeroconf) -> None:
        self.zeroconf = zeroconf
        super().__init__(
            self.zeroconf, DEAKO_TYPE, MyListener(self.device_address_callback)
        )

    def device_address_callback(self, address: str):
        self.addresses.add(address)
        _LOGGER.info(f"discovered device at {address}")

    async def get_address(self):
        _LOGGER.info("getting address for deako")
        total_time = 0
        while total_time < TIMEOUT_S and len(self.addresses) < 1:
            total_time += 0.1
            await sleep(0.1)
        if len(self.addresses) == 0:
            raise DevicesNotFoundExecption()
        address = self.addresses.pop()
        self.addresses.add(address)  # don't actually want this gone
        _LOGGER.info(f"Found device at {address}")
        return address

    def stop(self):
        self.zeroconf.close()


class MyListener(ServiceListener):
    def __init__(self, device_address_callback) -> None:
        self.device_address_callback = device_address_callback

    def remove_service(self, _zeroconf, _type, name):
        print("Service %s removed" % (name,))

    def update_service(self, _zeroconf, _type, name):
        print(f"service {name} update")

    def add_service(self, zeroconf: Zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        addresses = info.addresses
        port = info.port
        for address in addresses:
            self.device_address_callback(f"{inet_ntoa(address)}:{port}")
