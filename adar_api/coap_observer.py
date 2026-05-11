import asyncio
import logging
from collections.abc import AsyncGenerator
from enum import IntEnum
from typing import Self

from aiocoap import Message, GET, Context, TransportTuning
from aiocoap.protocol import BlockwiseRequest, Request

from .adar import Adar
from .coap_crc import verify_and_strip_crc
from .coap_exceptions import CoapErrorException

# Use default inter-notification timeout rule in ``messages`` (see docstring).
_DEFAULT_INTER_NOTIFICATION_TIMEOUT = object()


class Observe(IntEnum):
    Observe = 0
    NoObserve = 1


class FastTimeout(TransportTuning):
    """Custom transport tuning with shorter timeouts for faster failure detection"""

    ACK_TIMEOUT = 0.1
    MAX_RETRANSMIT = 2
    ACK_RANDOM_FACTOR = 1.0


class CoapObserver:
    """
    Class to register as observer to a CoAP server and receive messages

    Typical usage:

    async with CoapObserver(adar, "/pointcloud/v1") as observer:
        async for msg in observer.messages():
            points = PointCloud(msg)

            # Process point cloud
            # Use to_thread to avoid blocking the underlying async network io task,
            # which could cause network buffer overflow if process_points takes too long.
            await asyncio.to_thread(process_points, points)
    """

    def __init__(self, adar: Adar, path: str):
        """Initialize a CoAP observer for the given ADAR device and path.

        Args:
            adar: The ADAR device instance to observe
            path: The CoAP path to observe (e.g., "/pointcloud/v1")
        """
        self._adar = adar
        self.ipaddr = adar.ip_address
        self.path = path
        self._context: Context | None = None
        self._cancelled = False
        self._stopped = False
        self._current_request = None
        self.logger = logging.getLogger(f"{adar.device_tag}-Observe")

    async def messages(
        self,
        keep_running: bool = False,
        msg_count: int | None = None,
        *,
        inter_notification_timeout: float | None | object = _DEFAULT_INTER_NOTIFICATION_TIMEOUT,
    ) -> AsyncGenerator[bytes, None]:
        """Listen for messages and yield them as they arrive.

        For blocking and compute intensive tasks use asyncio.to_thread to avoid blocking the network io task. See
        class docstring for example.

        If too much time is spent processing a message, this iterator will skip messages and yield the newest observation.

        Args:
            keep_running: If True, the observer will attempt to keep running - i.e. ignore errors and keep trying to reconnect.
            msg_count: The number of messages to receive before stopping. If None, the observer will run until
                cancelled, and there is no timeout between consecutive notifications (suited to gated streams).
                If set, at most 2 seconds may elapse between notifications before a timeout/reconnect path runs
                (unless ``inter_notification_timeout`` overrides this).
            inter_notification_timeout: Maximum seconds to wait for each notification. ``None`` means wait indefinitely.
                If omitted, the default is no limit when ``msg_count`` is None, otherwise 2 seconds.

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
                    self.logger.warning("Failed to connect to server: %s", e)
                    if keep_running or connection_attempts < 10:
                        connection_attempts += 1
                        self.logger.warning("Trying again...")
                        continue
                    raise

                pr_iter = aiter(self._current_request.observation)
                if inter_notification_timeout is _DEFAULT_INTER_NOTIFICATION_TIMEOUT:
                    # When collecting forever (msg_count None), do not bound time between notifications.
                    # Gated resources may be silent for a long time; a short timeout would break the inner
                    # loop and re-register observe, dropping the subscription.
                    observation_timeout = None if msg_count is None else 2.0
                elif inter_notification_timeout is None:
                    observation_timeout = None
                else:
                    observation_timeout = float(inter_notification_timeout)
                while msg_count != cnt and not self._cancelled:
                    try:
                        # NOTE:
                        # This does not accumulate observations, so if the next observation in a sequence is not
                        # processed in time it is dropped in favour of the following observation.
                        obs = await asyncio.wait_for(anext(pr_iter), timeout=observation_timeout)
                        if not obs.code.is_successful():
                            self.logger.error("Error: %s received", obs.code)
                            if keep_running:
                                break
                            raise CoapErrorException(response=obs)

                        # Verify and strip CRC from observed notification
                        if self._adar.crc_enabled and len(obs.payload) > 4:
                            obs.payload, crc_valid = verify_and_strip_crc(self.path, obs.payload)
                            if not crc_valid:
                                self.logger.error("CRC mismatch for %s", self.path)
                                continue

                        yield obs.payload

                        cnt += 1
                        if msg_count == cnt:
                            self.logger.info("Received %d messages, stopping.", cnt)
                            break
                    except asyncio.TimeoutError:
                        if self._cancelled:
                            break
                        self.logger.error("Timeout waiting for %d messages", cnt)
                        if keep_running:
                            break
                        raise
        finally:
            if not self._cancelled:
                await self.stop()

    async def stop(self):
        """Stop the observer and clean up resources.

        Safe to call multiple times — only the first call performs cleanup.
        The de-registration GET (Observe=1) is sent before shutting down the
        CoAP context so the sensor stops sending notifications.
        """
        if self._stopped:
            return
        self._stopped = True
        self._cancelled = True

        if self._current_request is not None:
            self._current_request.cancelled = True
            self._current_request = None

        if self._context is not None:
            try:
                self.logger.info("De-registering observer")
                stop_observe_message = self._make_get_request(Observe.NoObserve)
                pr = self._context.request(stop_observe_message)
                await asyncio.wait_for(pr.response, timeout=2.0)
            except Exception as e:
                self.logger.warning("Observer de-registration failed: %s", e)
            finally:
                ctx, self._context = self._context, None
                try:
                    await ctx.shutdown()
                except Exception as e:
                    self.logger.warning("Error shutting down CoAP context: %s", e)

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
        match observe:
            case Observe.Observe:
                transport_tuning = FastTimeout()
            case Observe.NoObserve:
                transport_tuning = TransportTuning()
        token = ""
        if self._adar.auth_token is not None:
            token = f"?t={self._adar.auth_token}"
        return Message(
            code=GET,
            uri=f"coap://{self._adar.ip_address}{self.path}{token}",
            observe=int(observe),  # 0 = observe, 1 = no observe
            transport_tuning=transport_tuning,
        )

    async def _send_message(self, msg: Message) -> tuple[BlockwiseRequest | Request, Message]:
        self._adar.log_send_message(msg)
        request = self._context.request(msg)
        response_message = await request.response
        if not response_message.code.is_successful():
            self.logger.error("Error: %s received", response_message.code)
            raise CoapErrorException(response=response_message)
        return request, response_message

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *excinfo) -> None:
        await self.stop()
