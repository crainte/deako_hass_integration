import socket
import json
import asyncio
import logging
from threading import Thread

device_list_dict = {
    "transactionId": "015c44d3-abec-4be0-bb0d-34adb4b81559",
    "type": "DEVICE_LIST",
    "dst": "deako",
    "src": "ACME Corp",
}

state_change_dict = {
    "transactionId": "015c44d3-abec-4be0-bb0d-34adb4b81559",
    "type": "CONTROL",
    "dst": "deako",
    "src": "ACME Corp",
}

_LOGGER: logging.Logger = logging.getLogger(__package__)


class ConnectionThread(Thread):
    def __init__(self, on_data_callback, get_new_address):
        self.on_data_callback = on_data_callback
        self.get_new_address = get_new_address
        super().__init__()

    def connect(self, address):
        self.address = address

    async def send_data(self, data_to_send):
        if self.socket is None:
            return

        try:
            await self.loop.sock_sendall(self.socket, str.encode(data_to_send))
        except Exception as e:
            _LOGGER.error(f"error sending data: {e}")
            self.has_send_error = True

    async def read_socket(self):
        data = await self.loop.sock_recv(self.socket, 1024)

        raw_string = data.decode("utf-8")
        list_of_items = raw_string.split("\r\n")
        for item in list_of_items:
            self.leftovers = self.leftovers + item
            if len(self.leftovers) == 0:
                return
            try:
                self.on_data_callback(json.loads(self.leftovers))
                self.leftovers = ""
            except json.decoder.JSONDecodeError:
                _LOGGER.error("Got partial message")

    async def connect_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # this.s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        # this.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 1)
        # this.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 3)
        # this.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
        # this.s.settimeout(2)
        _LOGGER.info(f"connecting to {self.address}")
        [address, port] = self.address.split(":")
        await self.loop.sock_connect(self.socket, (address, port))

    async def close_socket(self):
        if self.socket is not None:
            self.socket.close()
            self.socket = None
        self.has_send_error = False

    def run(self):
        self.leftovers = ""
        self.socket = None
        self.state = 0
        self.has_send_error = False
        self.loop = asyncio.new_event_loop()
        self.loop.run_until_complete(self._run())
        self.loop.close()

    async def wait_for_connect(self):
        while self.state != 1:
            await asyncio.sleep(1)

    async def _run(self):
        while True:
            if self.state == 0:
                try:
                    await self.connect_socket()
                    self.state = 1
                    _LOGGER.info("connected to deako local integrations")
                except Exception as e:
                    _LOGGER.error(f"Failed to connect to {self.address} because {e}")
                    self.state = 2
                    continue
            elif self.state == 1:
                try:
                    await self.read_socket()
                except Exception as e:
                    _LOGGER.error(f"Failed to read socket to {self.address} because {e}")
                    self.state = 2
                    continue
            elif self.state == 2:
                try:
                    await self.close_socket()
                    self.state = 0
                    await asyncio.sleep(5)
                    # get a new address since the last one gave us issues
                    self.address = self.get_new_address(self.address)
                except KeyError:
                    _LOGGER.error("no addresses")
                    return  # if we have no addresses, there's not much we can do
                except Exception as e:
                    _LOGGER.error(f"Failed to close socket to {self.address} because {e}")
                    self.state = 2
                    continue
            else:
                _LOGGER.error("Unknown state")

            if self.has_send_error:
                _LOGGER.error("Failed to send")
                self.state = 2


async def control_device_worker(queue, callback):
    while True:
        control_params = await queue.get()
        await callback(
            control_params["uuid"], control_params["power"], control_params["dim"]
        )
        await asyncio.sleep(0.8)
        queue.task_done()


class Deako:
    def __init__(self, address, what, get_new_address):
        self.address = address
        self.src = what
        self.connection = ConnectionThread(self.incoming_json, get_new_address)

        self.devices = {}
        self.expected_devices = 0
        self.control_device_req_queue = asyncio.Queue()
        self.worker = asyncio.create_task(
            control_device_worker(
                self.control_device_req_queue, self.send_device_control_request
            )
        )

    def update_state(self, uuid, power, dim=None):
        if uuid is None:
            return
        if uuid not in self.devices:
            return

        self.devices[uuid]["state"]["power"] = power
        self.devices[uuid]["state"]["dim"] = dim

        if "callback" not in self.devices[uuid]:
            return
        self.devices[uuid]["callback"]()

    def set_state_callback(self, uuid, callback):
        if uuid not in self.devices:
            return
        self.devices[uuid]["callback"] = callback

    def incoming_json(self, in_data):
        try:
            if in_data["type"] == "DEVICE_LIST":
                subdata = in_data["data"]
                self.expected_devices = subdata["number_of_devices"]
            elif in_data["type"] == "DEVICE_FOUND":
                subdata = in_data["data"]
                state = subdata["state"]
                if "dim" in state:
                    self.record_device(
                        subdata["name"], subdata["uuid"], state["power"], state["dim"]
                    )
                else:
                    self.record_device(subdata["name"], subdata["uuid"], state["power"])
            elif in_data["type"] == "EVENT":
                subdata = in_data["data"]
                state = subdata["state"]
                if "dim" in state:
                    self.update_state(subdata["target"], state["power"], state["dim"])
                else:
                    self.update_state(subdata["target"], state["power"])
        except:
            _LOGGER.error("Failed to parse %s", in_data)

    def record_device(self, name, uuid, power, dim=None):
        if uuid is None:
            return
        if uuid not in self.devices:
            self.devices[uuid] = {}
            self.devices[uuid]["state"] = {}

        self.devices[uuid]["name"] = name
        self.devices[uuid]["uuid"] = uuid
        self.devices[uuid]["state"]["power"] = power
        self.devices[uuid]["state"]["dim"] = dim

    async def connect(self):
        self.connection.connect(self.address)
        self.connection.start()
        await self.connection.wait_for_connect()

    async def disconnect(self):
        _LOGGER.info(f"disconnecting from {self.address}")
        await self.connection.close_socket()

    def get_devices(self):
        return self.devices

    async def find_devices(self, timeout=10):
        device_list_dict["src"] = self.src
        await self.connection.send_data(json.dumps(device_list_dict))
        remaining = timeout
        while (
            self.expected_devices == 0
            or len(self.devices) != self.expected_devices
            and remaining > 0
        ):
            await asyncio.sleep(1)
            remaining -= 1

    async def send_device_control_request(self, uuid, power, dim):
        state_change = {"target": uuid, "state": {"power": power, "dim": dim}}
        state_change_dict["data"] = state_change
        state_change_dict["src"] = self.src
        await self.connection.send_data(json.dumps(state_change_dict))
        self.devices[uuid]["state"]["power"] = power
        self.devices[uuid]["state"]["dim"] = dim

    async def send_device_control(self, uuid, power, dim=None):
        await self.control_device_req_queue.put(
            {"uuid": uuid, "power": power, "dim": dim}
        )

    def get_name_for_device(self, uuid):
        return self.devices[uuid]["name"]

    def get_state_for_device(self, uuid):
        return self.devices[uuid]["state"]
