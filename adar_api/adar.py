import logging
from typing import AsyncGenerator
import struct
import math

from aiocoap import Context, Message, GET, PUT, DELETE

from .coap_exceptions import CoapErrorException, CoapException
from .coap_pointcloud import CoapPointCloud
from .device_errors import DeviceErrors
from .device_info import DeviceInfo
from .device_status import DeviceStatus, DeviceState
from .network_config import NetworkConfig
from .statistics import Statistics
from .coap_resources import (
    NETWORK_CONFIG_V0,
    FACTORY_RESET_V0,
    ERRORS_V0,
    DEVICE_INFO_V0,
    STATISTICS_V0,
    OBSERVERS_V0,
    POINTCLOUD_V0,
    STATUS_V0,
    TRANSMISSION_CODE_V0,
)


class Adar:
    """A class representing the Adar sensor."""

    def __init__(self, ctx: Context, ip_address: str | None, device_tag: str | None = None):
        """Initialize an ADAR device connection.

        Args:
            ctx: The CoAP context for communication
            ip_address: The IP address of the ADAR
            device_tag: Optional device tag for identification (defaults to "Adar")
        """
        self.device_tag = device_tag or "Adar"
        self.ip_address = ip_address
        self.ctx = ctx
        # Reduce COAP Log details:
        ctx.log.setLevel(logging.INFO)
        self.logger = logging.getLogger(device_tag)

    async def observe_point_cloud(
        self, keep_running: bool = False, msg_count: int | None = None
    ) -> AsyncGenerator[CoapPointCloud, None]:
        """Observe the ADAR Point cloud.

        Args:
            keep_running: If True, the observer will ignore errors and attempt to automatically reconnect.
            msg_count: If not None, the observer will be stopped once the requested number of messages are received.

        Yields:
            CoapPointCloud: Decoded point cloud instances.
        """
        # Need to import here in order to avoid circular dependency
        from .coap_observer import CoapObserver

        async with CoapObserver(self, POINTCLOUD_V0) as observer:
            async for response in observer.messages(keep_running, msg_count):
                try:
                    point_cloud = CoapPointCloud(response)
                except Exception as e:
                    if keep_running:
                        self.logger.warning(
                            "Failed to decode point cloud: %s. Ignoring because keep_running is True",
                            e,
                        )
                        continue
                    raise
                yield point_cloud

    async def get_point_cloud(self) -> CoapPointCloud:
        """Get one point cloud.

        Returns:
            CoapPointCloud: A single point cloud from the device.

        Raises:
            CoapException: If no response is received from the point cloud observer.
        """
        async for response in self.observe_point_cloud(msg_count=1):
            return response

        msg = "No response from point cloud info observer"
        raise CoapException(msg)

    async def get_network_config(self) -> NetworkConfig:
        """Read the network config.

        Returns:
            NetworkConfig: The current network configuration of the device.

        Raises:
            ValueError: If the response payload cannot be decoded into NetworkConfig.
            struct.error: If there's an error in the binary data structure.
        """
        uri = f"coap://{self.ip_address}{NETWORK_CONFIG_V0}"
        request = Message(code=GET, uri=uri)
        response = await self.send_request(request)
        try:
            return NetworkConfig(data=response.payload)
        except (ValueError, struct.error) as e:
            self.logger.exception(f"Failed to decode {response.payload} into NetworkConfig: {e}")
            raise

    async def set_network_config(self, network_config: NetworkConfig) -> None:
        """Set the network config.

        Args:
            network_config: The network configuration to apply to the device.

        Note:
            The device will reboot to apply the new network configuration.
        """
        uri = f"coap://{self.ip_address}{NETWORK_CONFIG_V0}"
        request = Message(code=PUT, uri=uri, payload=network_config.encode())
        await self.send_request(request)
        self.logger.warning("The device will now reboot to apply the new network config!!!")

    async def factory_reset(self) -> None:
        """Send factory reset command.

        Note:
            The device will reboot to apply factory settings.
        """
        uri = f"coap://{self.ip_address}{FACTORY_RESET_V0}"
        request = Message(code=PUT, uri=uri, payload="")
        await self.send_request(request)
        self.logger.warning("The device will now reboot to apply factory settings!!!")

    async def get_device_errors(self) -> DeviceErrors:
        """Read the device errors.

        Returns:
            DeviceErrors: The current device error information.

        Raises:
            ValueError: If the response payload cannot be decoded into DeviceErrors.
            struct.error: If there's an error in the binary data structure.
        """
        uri = f"coap://{self.ip_address}{ERRORS_V0}"
        request = Message(code=GET, uri=uri)
        response = await self.send_request(request)
        try:
            return DeviceErrors(data=response.payload)
        except (ValueError, struct.error) as e:
            self.logger.exception(f"Failed to decode {response.payload} into DeviceErrors: {e}")
            raise

    async def get_device_info(self) -> DeviceInfo:
        """Read the device info.

        Returns:
            DeviceInfo: Information about the device including identification, name, and firmware version.
        """
        uri = f"coap://{self.ip_address}{DEVICE_INFO_V0}"
        request = Message(code=GET, uri=uri)
        response = await self.send_request(request)
        return DeviceInfo(data=response.payload)

    async def get_status(self) -> DeviceStatus:
        """Read the status of the ADAR.

        Returns:
            DeviceStatus: The current status of the device including zone status, device state, and error information.

        Raises:
            ValueError: If the response payload cannot be decoded into DeviceStatus.
            AssertionError: If the response payload has an unexpected format.
        """
        uri = f"coap://{self.ip_address}{STATUS_V0}"
        request = Message(code=GET, uri=uri)
        response = await self.send_request(request)
        try:
            status = DeviceStatus(response.payload)
            # In the public API we have a Python IntEnum DeviceState which
            # maps the integer DeviceState values reported. Here we do
            # a translation from the raw integer value returned by the
            # device to a more ergonomic enum type.
            status.device_state = DeviceState(status.device_state)
            self.logger.debug(f"Got status bytes {status}")
        except (ValueError, AssertionError) as e:
            self.logger.exception(f"Failed to decode {response.payload} into DeviceStatus: {e}")
            raise
        else:
            return status

    async def get_statistics(self) -> Statistics:
        """Read the statistics.

        Returns:
            Statistics: Statistical information about the device.
        """
        uri = f"coap://{self.ip_address}{STATISTICS_V0}"
        request = Message(code=GET, uri=uri)
        response = await self.send_request(request)
        return Statistics(data=response.payload)

    async def get_transmission_code_id(self) -> int:
        """Read the transmission code ID of the ADAR.

        Returns:
            int: The transmission code ID (1, 2, 4, or 8).

        Raises:
            CoapException: If the response payload is None or has incorrect length.
        """
        uri = f"coap://{self.ip_address}{TRANSMISSION_CODE_V0}"
        self.logger.info(f"Executing GET {uri}")
        request = Message(code=GET, uri=uri)
        response = await self.send_request(request)
        if response.payload is None:
            raise CoapException("Response payload should not be None")
        if len(response.payload) != 1:
            raise CoapException("Response payload should have one byte")
        code_id = (
            2 ** response.payload[0]
        )  # Decode code ID from payload byte. The encoded payload represents N where 2^N is the code ID.
        self.logger.info(f"Got transmission code bytes {response.payload}, corresponding to code ID {code_id}")
        return code_id

    async def set_transmission_code_id(self, code_id: int) -> None:
        """Set the transmission code ID of the ADAR.

        Args:
            code_id: The transmission code ID to set. Must be one of 1, 2, 4, or 8.

        Raises:
            ValueError: If the code_id is not one of the valid values (1, 2, 4, 8).
            CoapException: If the response payload is unexpected.
        """
        if code_id not in (1, 2, 4, 8):
            raise ValueError(
                f"Invalid transmission code ID {code_id}. Must be one of 1, 2, 4 or 8",
            )
        encoded_code_id = int(math.log2(code_id))  # Encode code ID
        uri = f"coap://{self.ip_address}{TRANSMISSION_CODE_V0}"
        self.logger.info(f"Executing PUT {uri}")
        request = Message(code=PUT, uri=uri, payload=encoded_code_id.to_bytes(1))
        response = await self.send_request(request)
        # Check for empty payload (success)
        if response.payload in (b"", None):
            self.logger.info("Transmission code set successfully")
        else:
            raise CoapException(f"Unexpected response payload: {response.payload}")

    async def delete_observers(self) -> None:
        """Delete all registered observers on the device."""
        uri = f"coap://{self.ip_address}{OBSERVERS_V0}"
        request = Message(code=DELETE, uri=uri)
        await self.send_request(request)

    async def send_request(self, request: Message) -> Message:
        """Send a coap request to the ADAR.

        Args:
            request: The CoAP message to send to the device.

        Returns:
            Message: The response from the device.

        Raises:
            CoapErrorException: If the request fails or returns an error response.
            AssertionError: If the IP address of the ADAR device has not been set.
        """
        assert self.ip_address is not None, "The IP address of the ADAR device has not been set"
        self.log_send_message(request)
        response = await self.ctx.request(request).response
        if response.code.is_successful():
            return response

        raise CoapErrorException(response=response)

    def log_send_message(self, request: Message) -> None:
        """Log outgoing CoAP request details.

        Args:
            request: The CoAP message being sent.
        """
        msg = f"Sending request {request.code} {request.opt.uri_path}"
        if request.opt.observe is not None:
            msg += f" (observe={request.opt.observe})"
            self.logger.debug(msg)
