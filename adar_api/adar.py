import logging
from typing import AsyncGenerator
import struct
import math

from aiocoap import Context, Message, GET, PUT, DELETE

from .coap_crc import append_crc, verify_and_strip_crc
from .coap_exceptions import CoapErrorException, CoapException
from .coap_pointcloud import CoapPointCloud
from .device_errors import DeviceErrors
from .device_info import DeviceInfo
from .device_status import DeviceStatus, DeviceState
from .network_config import NetworkConfig
from .coap_resources import (
    CONFIG_CRC,
    NETWORK_CONFIG,
    FACTORY_RESET,
    ERRORS,
    DEVICE_INFO,
    OBSERVERS,
    POINTCLOUD,
    STATUS,
    TRANSMISSION_CODE,
    STATE,
    LOGIN,
    LOGOUT,
    REBOOT,
)

MAX_PASSWORD_LENGTH = 32


class Adar:
    """A class representing the ADAR sensor. It provides methods for communicating with the ADAR via CoAP.

    This class provides methods for:
    - Receiving 3D point cloud data (single frame or continuous observation)
    - Reading device status, info, and statistics
    - Configuring device settings (requires authentication)

    Example:
        Basic usage to get device info and a single point cloud::

            import asyncio
            from aiocoap import Context
            from adar_api import Adar

            async def main():
                ctx = await Context.create_client_context()
                adar = Adar(ctx, ip_address="10.20.30.40")

                # Get device info
                info = await adar.get_device_info()
                print(f"Device: {info.device_name}, FW: {info.firmware_version}")

                # Get a single point cloud
                cloud = await adar.get_point_cloud()
                print(f"Received {len(cloud.points)} points")

            asyncio.run(main())

    Example:
        Continuous point cloud observation::

            async for cloud in adar.observe_point_cloud():
                for point in cloud.points:
                    print(f"x={point.x:.2f}, y={point.y:.2f}, z={point.z:.2f}")

    Example:
        Authenticated operations (e.g., changing device state)::

            await adar.login("your_password")
            await adar.set_state(DeviceState.Enabled)
            await adar.logout()

    Note:
        Operations that modify device state (set_state, set_network_config, etc.)
        require authentication via the login() method first.
    """

    def __init__(
        self,
        ctx: Context,
        ip_address: str | None,
        device_tag: str | None = None,
    ):
        """Initialize an ADAR device connection.

        Args:
            ctx: The CoAP context for communication.
            ip_address: The IP address of the ADAR device.
            device_tag: Optional tag for logging identification (defaults to "Adar").
        """
        self.device_tag = device_tag or "Adar"
        self.ip_address = ip_address
        self.ctx = ctx
        # Reduce COAP Log details:
        ctx.log.setLevel(logging.INFO)
        self.logger = logging.getLogger(self.device_tag)
        self.auth_token = None

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

        async with CoapObserver(self, POINTCLOUD) as observer:
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

    async def set_state(self, state: DeviceState) -> None:
        """Set the state of the ADAR.

        Args:
            state: The state to set the device to.

        Raises:
            ValueError: If the state is not Enabled, Disabled, or Config.
            PermissionError: If not logged in.
        """
        if state not in (DeviceState.Enabled, DeviceState.Disabled, DeviceState.Config):
            raise ValueError(f"Invalid state: {state}")
        if self.auth_token is None:
            raise PermissionError("Not logged in")
        uri = f"coap://{self.ip_address}{STATE}?t={self.auth_token}"
        request = Message(code=PUT, uri=uri, payload=state.value.to_bytes(1))
        response = await self.send_request(request)
        self.logger.debug("Set state response: %s", response)

    async def get_network_config(self) -> NetworkConfig:
        """Read the network config.

        Returns:
            NetworkConfig: The current network configuration of the device.

        Raises:
            ValueError: If the response payload cannot be decoded into NetworkConfig.
            struct.error: If there's an error in the binary data structure.
        """
        uri = f"coap://{self.ip_address}{NETWORK_CONFIG}"
        request = Message(code=GET, uri=uri)
        response = await self.send_request(request)
        try:
            return NetworkConfig(data=response.payload)
        except (ValueError, struct.error) as e:
            self.logger.exception("Failed to decode %s into NetworkConfig: %s", response.payload, e)
            raise

    async def set_network_config(self, network_config: NetworkConfig) -> None:
        """Set the network config.

        Args:
            network_config: The network configuration to apply to the device.

        Raises:
            PermissionError: If not logged in.

        Note:
            The device will reboot to apply the new network configuration.
        """
        if self.auth_token is None:
            raise PermissionError("Not logged in")
        uri = f"coap://{self.ip_address}{NETWORK_CONFIG}?t={self.auth_token}"
        request = Message(code=PUT, uri=uri, payload=network_config.encode())
        await self.send_request(request)
        self.logger.warning("The device will now reboot to apply the new network config!!!")

    async def get_config_crc(self) -> str:
        """Read the config CRC.

        Returns:
            str: The current config CRC in hexadecimal format.
        """
        uri = f"coap://{self.ip_address}{CONFIG_CRC}"
        request = Message(code=GET, uri=uri)
        response = await self.send_request(request)
        crc = int.from_bytes(response.payload[:4], byteorder="little", signed=False)
        return f"{crc:08x}"

    async def factory_reset(self) -> None:
        """Send factory reset command.

        Raises:
            PermissionError: If not logged in.

        Note:
            The device will reboot to apply factory settings.
        """
        if self.auth_token is None:
            raise PermissionError("Not logged in")
        uri = f"coap://{self.ip_address}{FACTORY_RESET}?t={self.auth_token}"
        request = Message(code=PUT, uri=uri, payload=b"")
        await self.send_request(request)
        self.logger.warning("The device will now reboot to apply factory settings!!!")

    async def reboot(self) -> None:
        """Reboot the device.

        Raises:
            PermissionError: If not logged in.
        """
        if self.auth_token is None:
            raise PermissionError("Not logged in")
        uri = f"coap://{self.ip_address}{REBOOT}?t={self.auth_token}"
        request = Message(code=PUT, uri=uri, payload=b"")
        await self.send_request(request)
        self.logger.warning("Rebooting device...")

    async def get_device_errors(self) -> DeviceErrors:
        """Read the device errors.

        Returns:
            DeviceErrors: The current device error information.

        Raises:
            ValueError: If the response payload cannot be decoded into DeviceErrors.
            struct.error: If there's an error in the binary data structure.
        """
        uri = f"coap://{self.ip_address}{ERRORS}"
        request = Message(code=GET, uri=uri)
        response = await self.send_request(request)
        try:
            return DeviceErrors(data=response.payload)
        except (ValueError, struct.error) as e:
            self.logger.exception("Failed to decode %s into DeviceErrors: %s", response.payload, e)
            raise

    async def get_device_info(self) -> DeviceInfo:
        """Read the device info.

        Returns:
            DeviceInfo: Information about the device including identification, name, and firmware version.
        """
        uri = f"coap://{self.ip_address}{DEVICE_INFO}"
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
        uri = f"coap://{self.ip_address}{STATUS}"
        request = Message(code=GET, uri=uri)
        response = await self.send_request(request)
        try:
            status = DeviceStatus(response.payload)
            # In the public API we have a Python IntEnum DeviceState which
            # maps the integer DeviceState values reported. Here we do
            # a translation from the raw integer value returned by the
            # device to a more ergonomic enum type.
            status.device_state = DeviceState(status.device_state)
            self.logger.debug("Got status bytes %s", status)
        except (ValueError, AssertionError) as e:
            self.logger.exception("Failed to decode %s into DeviceStatus: %s", response.payload, e)
            raise
        else:
            return status

    async def get_transmission_code_id(self) -> int:
        """Read the transmission code ID of the ADAR.

        Returns:
            int: The transmission code ID (1, 2, 4, or 8).

        Raises:
            CoapException: If the response payload is None or has incorrect length.
        """
        uri = f"coap://{self.ip_address}{TRANSMISSION_CODE}"
        self.logger.info("Executing GET %s", uri)
        request = Message(code=GET, uri=uri)
        response = await self.send_request(request)
        if response.payload is None:
            raise CoapException("Response payload should not be None")
        if len(response.payload) != 1:
            raise CoapException("Response payload should have one byte")
        code_id = (
            2 ** response.payload[0]
        )  # Decode code ID from payload byte. The encoded payload represents N where 2^N is the code ID.
        self.logger.info("Got transmission code bytes %s, corresponding to code ID %d", response.payload, code_id)
        return code_id

    async def set_transmission_code_id(self, code_id: int) -> None:
        """Set the transmission code ID of the ADAR.

        Args:
            code_id: The transmission code ID to set. Must be one of 1, 2, 4, or 8.

        Raises:
            ValueError: If the code_id is not one of the valid values (1, 2, 4, 8).
            PermissionError: If not logged in.
            CoapException: If the response payload is unexpected.
        """
        if code_id not in (1, 2, 4, 8):
            raise ValueError(
                f"Invalid transmission code ID {code_id}. Must be one of 1, 2, 4 or 8",
            )
        if self.auth_token is None:
            raise PermissionError("Not logged in")
        encoded_code_id = int(math.log2(code_id))  # Encode code ID
        uri = f"coap://{self.ip_address}{TRANSMISSION_CODE}?t={self.auth_token}"
        self.logger.debug("Executing PUT %s", uri)
        request = Message(code=PUT, uri=uri, payload=encoded_code_id.to_bytes(1))
        response = await self.send_request(request)
        # Check for empty payload (success)
        if response.payload in (b"", None):
            self.logger.info("Transmission code set successfully")
        else:
            raise CoapException(f"Unexpected response payload: {response.payload}")

    async def delete_observers(self) -> None:
        """Delete all registered observers on the device."""
        uri = f"coap://{self.ip_address}{OBSERVERS}"
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
            ValueError: If the IP address of the ADAR device has not been set.
        """
        if self.ip_address is None:
            raise ValueError("The IP address of the ADAR device has not been set")
        self.log_send_message(request)

        path = "/".join(request.opt.uri_path)

        # Add CRC if there is a payload
        if len(request.payload) > 0:
            request.payload = append_crc(path, request.payload)

        response = await self.ctx.request(request).response

        # Verify and strip CRC from response if there is a payload
        if len(response.payload) >= 4:
            response.payload, crc_valid = verify_and_strip_crc(path, response.payload)
            if not crc_valid:
                self.logger.warning("CRC mismatch in response for %s", path)
                raise CoapErrorException(response=response)

        if response.code.is_successful():
            return response

        raise CoapErrorException(response=response)

    async def get_login_token(self) -> int:
        """Get the login token."""
        uri = f"coap://{self.ip_address}{LOGIN}"
        request = Message(code=GET, uri=uri)

        response = await self.send_request(request)

        # Return token
        return int.from_bytes(response.payload, "little")

    async def login(self, password: str) -> str:
        """Login to the device with a password.

        Authenticates the user and stores and returns the auth token.
        The token is used for subsequent authenticated requests.

        Args:
            password: The device user password.

        Returns:
            str: The authentication token.

        Raises:
            CoapErrorException: If authentication fails.
        """
        login_token = await self.get_login_token()
        self.logger.debug("Logging in with token")
        uri = f"coap://{self.ip_address}{LOGIN}"
        request = Message(
            code=PUT,
            uri=uri,
            payload=encode_password(password, login_token),
        )
        response = await self.send_request(request)

        # Decode login token, first 4 bytes is the length, then the rest is the token.
        length = int.from_bytes(response.payload[:4], byteorder="little", signed=False)
        token = response.payload[4 : 4 + length].decode("utf-8")
        self.auth_token = token
        return token

    async def logout(self) -> None:
        """Logout from the ADAR device."""
        uri = f"coap://{self.ip_address}{LOGOUT}"
        request = Message(code=PUT, uri=uri)
        await self.send_request(request)
        self.auth_token = None
        self.logger.debug("Logged out")

    def log_send_message(self, request: Message) -> None:
        """Log outgoing CoAP request details.

        Args:
            request: The CoAP message being sent.
        """
        msg = f"Sending request {request.code} {request.opt.uri_path}"
        if request.opt.observe is not None:
            msg += f" (observe={request.opt.observe})"
            self.logger.debug(msg)


def encode_password(password: str, token: int) -> bytes:
    """Encode a password using a 64-bit token with XOR and rotation.

    Note:
        This is not a proper hashing function, so the security is just one tiny
        step up from sending it as plain text. This will be replaced in a future
        release.

    Args:
        password: The plaintext password to encode.
        token: The 64-bit token used for encoding.

    Returns:
        bytes: The encoded password bytes.
    """
    truncated = password[:MAX_PASSWORD_LENGTH].encode("utf-8")
    encoded = bytearray(truncated)

    token_bytes = token.to_bytes(8, byteorder="little", signed=False)

    for i in range(len(encoded)):
        token_byte = token_bytes[i % 8]
        position_factor = i % 256

        value = encoded[i] ^ token_byte ^ position_factor
        encoded[i] = ((value << 1) & 0xFF) | (value >> 7)

    return bytes(encoded)
