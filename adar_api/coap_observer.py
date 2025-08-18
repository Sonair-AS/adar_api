import asyncio
import logging
from enum import IntEnum

####################
# This is a hack to get the Self type from typing, but it's not available in Python 3.10
# TODO: Fix this or update to Pyhton 3.11
from typing import AsyncGenerator, TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Self
else:
    Self = "CoapObserver"
####################

from aiocoap import Message, GET, Context
from aiocoap.protocol import BlockwiseRequest, Request

from .adar import Adar
from .coap_exceptions import CoapErrorException


class Observe(IntEnum):
    Observe = 0
    NoObserve = 1


class CoapObserver:
    """
    Class to register as observer to a CoAP server and receive messages

    Typical usage:

    async with CoapObserver(adar, "/point_cloud/v0") as observer:
        async for msg in observer.messages():
            points = PointCloud(msg)
            print(points)
    """

    def __init__(self, adar: Adar, path: str):
        """Initialize a CoAP observer for the given ADAR device and path.

        Args:
            adar: The ADAR device instance to observe
            path: The CoAP path to observe (e.g., "/point_cloud/v0")
        """
        self._adar = adar
        self.ipaddr = adar.ip_address
        self.path = path
        self._context: Context | None = None
        self._cancelled = False
        self._current_request = None
        self.logger = logging.getLogger(f"{adar.device_tag}-Observe")

    async def messages(self, keep_running: bool = False, msg_count: int | None = None) -> AsyncGenerator[bytes, None]:
        """Listen for messages and yield them as they arrive.

        Args:
            keep_running: If True, the observer will attempt to keep running - i.e. ignore errors and keep trying to reconnect.
            msg_count: The number of messages to receive before stopping. If None, the observer will run until cancelled.

        Yields:
            bytes: Raw message payload data
        """
        await self._ensure_coap_context()
        try:
            cnt = 0
            connection_attempts = 0
            while msg_count != cnt and not self._cancelled:
                if connection_attempts > 0:
                    self.logger.warning("Try to re-register observer and continue")
                start_observe_message = self._make_get_request(Observe.Observe)
                try:
                    (self._current_request, _response) = await self._send_message(start_observe_message)
                except CoapErrorException as e:
                    self.logger.warning(f"Failed to connect to server: {e}")
                    if keep_running or connection_attempts < 10:
                        connection_attempts += 1
                        self.logger.warning("Trying again...")
                        continue
                    raise

                pr_iter = aiter(self._current_request.observation)
                while msg_count != cnt and not self._cancelled:
                    try:
                        obs = await asyncio.wait_for(anext(pr_iter), timeout=2)
                        if not obs.code.is_successful():
                            self.logger.error(f"Error: {obs.code} received")
                            if keep_running:
                                break
                            raise CoapErrorException(response=obs)

                        yield obs.payload

                        cnt += 1
                        if msg_count == cnt:
                            self.logger.info(f"Received {cnt} messages, stopping.")
                            break
                    except asyncio.TimeoutError:
                        if self._cancelled:
                            break
                        self.logger.error(f"Timeout waiting for {cnt} messages")
                        if keep_running:
                            break
                        raise
        finally:
            if not self._cancelled:
                await self.stop()

    async def stop(self):
        """Stop the observer and clean up resources."""
        self._cancelled = True

        try:
            # Cancel current request if it exists
            if self._current_request is not None:
                self._current_request.cancelled = True

            # Deregister the observer only if context exists
            if self._context is not None:
                self.logger.info("De-registering observer")
                stop_observe_message = self._make_get_request(Observe.NoObserve)
                pr = self._context.request(stop_observe_message)
                await pr.response
        except Exception as e:
            self.logger.warning(f"Error during observer shutdown: {e}")
            raise
        finally:
            if self._context is not None:
                try:
                    await self._context.shutdown()
                except Exception as e:
                    self.logger.warning(f"Error shutting down context: {e}")
                self._context = None

    async def _ensure_coap_context(self) -> None:
        """Ensure we have a valid CoAP context."""
        if self._context is None:
            self._context = await Context.create_client_context()

    def _make_get_request(self, observe: Observe) -> Message:
        """Create a GET request with observe option.

        Args:
            observe: Observe option value

        Returns:
            CoAP message with observe option set
        """
        return Message(
            code=GET,
            uri=f"coap://{self._adar.ip_address}{self.path}",
            observe=int(observe),  # 0 = observe, 1 = no observe
        )

    async def _send_message(self, msg: Message) -> tuple[BlockwiseRequest | Request, Message]:
        self._adar.log_send_message(msg)
        request = self._context.request(msg)
        response_message = await request.response
        if not response_message.code.is_successful():
            self.logger.error(f"Error: {response_message.code} received")
            raise CoapErrorException(response=response_message)
        return request, response_message

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *excinfo) -> None:
        await self.stop()
