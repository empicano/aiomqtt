# SPDX-License-Identifier: BSD-3-Clause
"""The core logic of the client."""

import asyncio
import collections
import contextlib
import logging
import random
import secrets
import socket
import time
import types
import typing

from mqtt5 import (
    ConnAckPacket,
    ConnAckReasonCode,
    ConnectPacket,
    DisconnectPacket,
    DisconnectReasonCode,
    Packet,
    PingReqPacket,
    PingRespPacket,
    PubAckPacket,
    PubAckReasonCode,
    PubCompPacket,
    PubCompReasonCode,
    PublishPacket,
    PubRecPacket,
    PubRecReasonCode,
    PubRelPacket,
    PubRelReasonCode,
    QoS,
    RetainHandling,
    SubAckPacket,
    SubAckReasonCode,
    SubscribePacket,
    Subscription,
    UnsubAckPacket,
    UnsubAckReasonCode,
    UnsubscribePacket,
    Will,
    read,
)

from ._exceptions import ConnectError, NegativeAckError, ProtocolError

T = typing.TypeVar("T")


class _SlidingWindowBuffer:
    """Fixed-size buffer that compacts by sliding the active data to the beginning.

    Args:
        size: Maximum buffer size in bytes.
    """

    def __init__(self, size: int) -> None:
        self.buffer = bytearray(size)
        self.left = 0
        self.right = 0

    def write(self, data: bytes) -> None:
        """Write data to buffer, compacting if necessary.

        Args:
            data: Bytes to write.
        """
        if len(data) > len(self.buffer) - self.right + self.left:
            msg = "Buffer overflow"
            raise RuntimeError(msg)
        if len(data) > len(self.buffer) - self.right:
            self.buffer[: self.right - self.left] = self.buffer[self.left : self.right]
            self.right = self.right - self.left
            self.left = 0
        self.buffer[self.right : self.right + len(data)] = data
        self.right += len(data)


class Client:
    """Asynchronous context manager for the connection to the MQTT broker.

    Args:
        hostname: The broker's hostname or IP address.
        port: The broker's network port.
        identifier: Client identifier (auto-generated if None). The broker might
            override this value.
        logger: Optional logger to override the default logger.
        username: The username to authenticate with.
        password: The password to authenticate with.
        clean_start: If True, the broker discards any existing session associated with
            the client identifier and creates a new session. If False, the broker
            resumes the existing session. If no session is available, then the broker
            creates a new session.
        will: The will message to publish if the client disconnects unexpectedly.
        keep_alive: The keep alive interval in seconds. The broker might override this
            value.
        session_expiry_interval: The time for the session to expire in seconds.
        authentication_method: The name of the authentication method used for extended
            authentication.
        authentication_data: The contents of this data are defined by the authentication
            method.
        request_problem_info: If False, the broker must not send a reason string or user
            properties on any packet other than PUBLISH, CONNACK, or DISCONNECT. If
            True, the broker may return a reason string or user properties on any packet
            where it is allowed.
        request_response_info: If False, the broker must not return response information
            in the CONNACK packet. If True, the broker may return response information.
        receive_max: The maximum number of unacknowledged PUBLISH packets with QoS > 0
            that the broker may send to the client.
        topic_alias_max: The maximum number of topic aliases that the broker may use
            when sending PUBLISH packets.
        max_packet_size: The maximum size of a packet in bytes that we want to accept.
            If None, there is no limit beyond limitations in the protocol.
        user_properties: Name/value pairs to send with the packet. The meaning of these
            properties is not defined by the specification. The same name is allowed to
            appear more than once. The order is preserved.
    """

    def __init__(
        self,
        hostname: str,
        *,
        port: int = 1883,
        identifier: str | None = None,
        logger: logging.Logger | None = None,
        username: str | None = None,
        password: str | None = None,
        clean_start: bool = False,
        reconnect: bool = False,
        will: Will | None = None,
        keep_alive: int = 0,
        session_expiry_interval: int = 0,
        authentication_method: str | None = None,
        authentication_data: bytes | None = None,
        request_problem_info: bool = True,
        request_response_info: bool = False,
        receive_max: int = 65535,
        topic_alias_max: int = 0,
        max_packet_size: int | None = None,
        user_properties: list[tuple[str, str]] | None = None,
    ) -> None:
        self._hostname = hostname
        self._port = port
        self.identifier = (
            identifier if identifier is not None else f"aiomqtt-{secrets.token_hex(2)}"
        )
        if logger is None:
            logger = logging.getLogger("aiomqtt")
            logger.setLevel(logging.WARNING)
        self._logger = logger
        self._username = username
        self._password = password
        self._clean_start = clean_start
        self._reconnect = reconnect
        self._will = will
        self._keep_alive = keep_alive
        self._session_expiry_interval = session_expiry_interval
        self._authentication_method = authentication_method
        self._authentication_data = authentication_data
        self._request_problem_info = request_problem_info
        self._request_response_info = request_response_info
        self._receive_max = receive_max
        self._topic_alias_max = topic_alias_max
        self._max_packet_size = max_packet_size
        self._user_properties = user_properties
        # Network settings
        self._buffer_in = _SlidingWindowBuffer(size=2**24)
        self._socket: socket.socket
        self._reader: asyncio.StreamReader
        self._writer: asyncio.StreamWriter
        # Connection status
        self._connected: asyncio.Future[ConnAckPacket] = asyncio.Future()
        self._disconnected: asyncio.Future[None]
        self._context_lock = asyncio.Lock()
        self._disconnection_lock = asyncio.Lock()
        # Message management
        self._getters: collections.deque[
            asyncio.Future[PublishPacket | PubRelPacket]
        ] = collections.deque()
        self._queue: collections.deque[PublishPacket | PubRelPacket] = (
            collections.deque()
        )
        self._pending_pubacks: dict[int, asyncio.Future[PubAckPacket]] = {}
        self._pending_pubrecs: dict[int, asyncio.Future[PubRecPacket]] = {}
        self._pending_pubcomps: dict[int, asyncio.Future[PubCompPacket]] = {}
        self._pending_subacks: dict[int, asyncio.Future[SubAckPacket]] = {}
        self._pending_unsubacks: dict[int, asyncio.Future[UnsubAckPacket]] = {}
        self._pending_pingresp: asyncio.Future[PingRespPacket]
        self._packet_ids = self._packet_id_generator()
        self._send_semaphore: asyncio.BoundedSemaphore
        self._most_recent_packet_sent_time: float

    async def __aenter__(self) -> typing.Self:
        if self._context_lock.locked():
            msg = "The client context manager is reusable but not reentrant"
            raise RuntimeError(msg)
        await self._context_lock.acquire()
        try:
            await self._connect()
        except (ProtocolError, NegativeAckError, OSError):
            self._context_lock.release()
            raise
        # Start background tasks
        self._tasks = asyncio.create_task(self._run_background_tasks())
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: types.TracebackType | None,
    ) -> None:
        if hasattr(self, "_tasks"):
            self._tasks.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._tasks
        reason_code = DisconnectReasonCode.NORMAL_DISCONNECTION
        # Disconnect with LWT if we exit the context manager with an exception
        if exc is not None and self._will is not None:
            reason_code = DisconnectReasonCode.DISCONNECT_WITH_WILL_MESSAGE
        await self._disconnect(reason_code=reason_code)
        # Release the reusability lock
        if self._context_lock.locked():
            self._context_lock.release()

    async def connected(self) -> ConnAckPacket:
        """Return CONNACK when the client (re-)connects."""
        return await self._connected

    async def disconnected(self) -> None:
        """Return when the client disconnects."""
        if not hasattr(self, "_disconnected"):
            return None
        return await self._disconnected

    async def _disconnected_or(self, fut: asyncio.Future[T]) -> T:
        if hasattr(self, "_disconnected"):
            await asyncio.wait(
                (fut, self._disconnected), return_when=asyncio.FIRST_COMPLETED
            )
            if fut.done():
                return fut.result()
        raise ConnectError(self._hostname, self._port)

    async def _send(self, packet: Packet) -> None:
        if not hasattr(self, "_writer"):
            raise ConnectError(self._hostname, self._port)
        self._writer.write(packet.write())
        try:
            await self._writer.drain()
        except ConnectionResetError as exc:
            raise ConnectError(self._hostname, self._port) from exc
        self._most_recent_packet_sent_time = time.monotonic()

    async def _receive(self) -> Packet:
        while True:
            # TODO(empicano): Check for _disconnected?
            if self._buffer_in.left < self._buffer_in.right:
                try:
                    # TODO(empicano): We don't actually know if we're reading over the
                    # buffer.right pointer -> We could check afterwards with nbytes
                    # until mqtt5 implements memoryviews; Then, also remove the
                    # if-statement and return immediately in mqtt5 if len(memview) == 0
                    packet, nbytes = read(
                        self._buffer_in.buffer, index=self._buffer_in.left
                    )
                except IndexError:  # Partial packet
                    pass
                except ValueError as exc:
                    await self._disconnect(
                        reason_code=DisconnectReasonCode.MALFORMED_PACKET,
                    )
                    msg = "Received malformed packet"
                    raise ProtocolError(msg) from exc
                else:
                    self._buffer_in.left += nbytes
                    return packet
            data = await self._reader.read(2**14)
            if not data:  # Reached EOF
                await self._disconnect()
                raise ConnectError(self._hostname, self._port)
            self._buffer_in.write(data)

    async def _receive_loop(self) -> None:
        while True:
            try:
                packet = await self._receive()
            except ConnectError:
                await self._connected
                continue
            except ProtocolError:
                self._logger.exception("Received malformed packet")
                await self._disconnect()
                await self._connected
                continue
            self._logger.debug("Received packet of type: %s", type(packet).__name__)
            match packet:
                case PublishPacket():
                    if len(self._getters) == 0:
                        if packet.qos == QoS.AT_MOST_ONCE:
                            # Drop when no consumer is immediately available
                            self._logger.debug("Dropping QoS=0 PUBLISH")
                        else:
                            self._queue.append(packet)
                    else:
                        self._getters.popleft().set_result(packet)
                case PubAckPacket():
                    try:
                        self._pending_pubacks[packet.packet_id].set_result(packet)
                    except KeyError:
                        self._logger.warning("Received unsolicited PUBACK")
                    else:
                        self._send_semaphore.release()
                case PubRecPacket():
                    try:
                        self._pending_pubrecs[packet.packet_id].set_result(packet)
                    except KeyError:
                        self._logger.warning("Received unsolicited PUBREC")
                    else:
                        if packet.reason_code not in [
                            PubRecReasonCode.SUCCESS,
                            PubRecReasonCode.NO_MATCHING_SUBSCRIBERS,
                        ]:
                            self._send_semaphore.release()
                case PubRelPacket():
                    if len(self._getters) == 0:
                        self._queue.append(packet)
                    else:
                        self._getters.popleft().set_result(packet)
                case PubCompPacket():
                    try:
                        self._pending_pubcomps[packet.packet_id].set_result(packet)
                    except KeyError:
                        self._logger.warning("Received unsolicited PUBCOMP")
                    else:
                        self._send_semaphore.release()
                case SubAckPacket():
                    try:
                        self._pending_subacks[packet.packet_id].set_result(packet)
                    except KeyError:
                        self._logger.warning("Received unsolicited SUBACK")
                case UnsubAckPacket():
                    try:
                        self._pending_unsubacks[packet.packet_id].set_result(packet)
                    except KeyError:
                        self._logger.warning("Received unsolicited UNSUBACK")
                case PingRespPacket():
                    self._pending_pingresp.set_result(packet)
                case DisconnectPacket():
                    self._logger.warning(
                        "Received DisconnectPacket with reason code: %s",
                        packet.reason_code.name,
                    )
                    # TODO(empicano): This sends DISCONNECT, which is not what we want
                    await self._disconnect()
                    await self._connected
                case _:
                    self._logger.error(
                        "Received packet of unexpected type: %s", type(packet).__name__
                    )
                    await self._disconnect(
                        reason_code=DisconnectReasonCode.PROTOCOL_ERROR
                    )
                    await self._connected

    async def _pingreq_loop(self) -> None:
        while True:
            while (  # noqa: ASYNC110
                elapsed := time.monotonic() - self._most_recent_packet_sent_time
            ) < self._keep_alive:
                await asyncio.sleep(self._keep_alive - elapsed)
            try:
                async with asyncio.timeout(self._keep_alive / 2):
                    await self._pingreq()
            except ConnectError:
                await self._connected
            except TimeoutError:
                self._logger.warning("PINGREQ timed out")
                await self._disconnect(
                    reason_code=DisconnectReasonCode.KEEP_ALIVE_TIMEOUT
                )
                await self._connected

    async def _reconnect_loop(self) -> None:
        while True:
            await self._disconnected
            attempt = 0
            while True:
                delay = random.uniform(0, 1.5**attempt)  # noqa: S311
                # Implements maximum delay
                attempt = min(10, attempt + 1)
                self._logger.info("Reconnecting in %.2f seconds", delay)
                await asyncio.sleep(delay)
                try:
                    await self._connect()
                    self._logger.info(
                        "Reconnected to %s:%d", self._hostname, self._port
                    )
                    break
                except (OSError, ProtocolError, NegativeAckError):
                    self._logger.exception("Failed to reconnect")

    async def _run_background_tasks(self) -> None:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self._receive_loop())
            if self._keep_alive > 0:
                tg.create_task(self._pingreq_loop())
            if self._reconnect:
                tg.create_task(self._reconnect_loop())

    async def messages(self) -> typing.AsyncIterator[PublishPacket | PubRelPacket]:
        """Iterate over incoming PUBLISH and PUBREL packets."""
        while True:
            if len(self._queue) > 0:
                yield self._queue.popleft()
                continue
            fut: asyncio.Future[PublishPacket | PubRelPacket] = asyncio.Future()
            self._getters.append(fut)
            # Wait until we either have a message or disconnect
            # TODO(empicano): We should do something with the getter/future on fail
            yield await self._disconnected_or(fut)

    def _packet_id_generator(self) -> typing.Iterator[int]:
        packet_id = 1
        while True:
            yield packet_id
            packet_id = packet_id % (2**16 - 1) + 1

    async def _connect(self) -> None:
        self._socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self._socket.connect((self._hostname, self._port))
        self._reader, self._writer = await asyncio.open_connection(sock=self._socket)
        await self._send(
            ConnectPacket(
                client_id=self.identifier,
                username=self._username,
                password=self._password,
                clean_start=self._clean_start,
                will=self._will,
                keep_alive=self._keep_alive,
                session_expiry_interval=self._session_expiry_interval,
                authentication_method=self._authentication_method,
                authentication_data=self._authentication_data,
                request_problem_info=self._request_problem_info,
                request_response_info=self._request_response_info,
                receive_max=self._receive_max,
                topic_alias_max=self._topic_alias_max,
                max_packet_size=self._max_packet_size,
                user_properties=self._user_properties,
            )
        )
        # Wait for the acknowledgement
        packet = await self._receive()
        if not isinstance(packet, ConnAckPacket):
            await self._disconnect(
                reason_code=DisconnectReasonCode.PROTOCOL_ERROR,
            )
            msg = f"Received packet of unexpected type: {type(packet).__name__}"
            raise ProtocolError(msg)
        if packet.reason_code != ConnAckReasonCode.SUCCESS:
            raise NegativeAckError(packet)
        if packet.assigned_client_id is not None:
            self._logger.info("Broker set client id: %s", packet.assigned_client_id)
            self.identifier = packet.assigned_client_id
        if packet.server_keep_alive is not None:
            self._logger.info("Broker set keep alive: %d", packet.server_keep_alive)
            self._keep_alive = packet.server_keep_alive
        self._send_semaphore = asyncio.BoundedSemaphore(packet.receive_max)
        self._connected.set_result(packet)
        self._disconnected = asyncio.Future()

    @typing.overload
    async def publish(
        self,
        topic: str,
        *,
        payload: bytes | None = ...,
        qos: typing.Literal[QoS.AT_MOST_ONCE] = ...,
        retain: bool = ...,
        message_expiry_interval: int | None = ...,
        content_type: str | None = ...,
        response_topic: str | None = ...,
        correlation_data: bytes | None = ...,
        user_properties: list[tuple[str, str]] | None = ...,
    ) -> None: ...

    @typing.overload
    async def publish(
        self,
        topic: str,
        *,
        payload: bytes | None = ...,
        qos: typing.Literal[QoS.AT_LEAST_ONCE] = ...,
        retain: bool = ...,
        message_expiry_interval: int | None = ...,
        content_type: str | None = ...,
        response_topic: str | None = ...,
        correlation_data: bytes | None = ...,
        user_properties: list[tuple[str, str]] | None = ...,
    ) -> PubAckPacket: ...

    @typing.overload
    async def publish(
        self,
        topic: str,
        *,
        payload: bytes | None = ...,
        qos: typing.Literal[QoS.EXACTLY_ONCE] = ...,
        retain: bool = ...,
        message_expiry_interval: int | None = ...,
        content_type: str | None = ...,
        response_topic: str | None = ...,
        correlation_data: bytes | None = ...,
        user_properties: list[tuple[str, str]] | None = ...,
    ) -> PubRecPacket: ...

    @typing.overload
    async def publish(
        self,
        topic: str,
        *,
        payload: bytes | None = ...,
        qos: QoS = ...,
        retain: bool = ...,
        message_expiry_interval: int | None = ...,
        content_type: str | None = ...,
        response_topic: str | None = ...,
        correlation_data: bytes | None = ...,
        user_properties: list[tuple[str, str]] | None = ...,
    ) -> PubAckPacket | PubRecPacket | None: ...

    async def publish(
        self,
        topic: str,
        *,
        payload: bytes | None = None,
        qos: QoS = QoS.AT_MOST_ONCE,
        retain: bool = False,
        message_expiry_interval: int | None = None,
        content_type: str | None = None,
        response_topic: str | None = None,
        correlation_data: bytes | None = None,
        user_properties: list[tuple[str, str]] | None = None,
    ) -> PubAckPacket | PubRecPacket | None:
        """Publish a message.

        Args:
            topic: The topic to publish to.
            payload: The message payload as bytes.
            qos: The QoS of the message.
            retain: Whether to retain the message. If True, any existing retained
                message for the topic will be replaced.
            message_expiry_interval: The lifetime of the message in seconds. When the
                expiry interval has passed, the message will no longer be delivered to
                any subscribers.
            content_type: Description of the content of the message. The specification
                does not dictate the format, but suggests using MIME types.
            response_topic: The topic to the subscriber should respond on in a
                request/response flow.
            correlation_data: Set by the publisher in a request/response flow to match
                responses to requests.
            user_properties: Name/value pairs to send with the packet. The meaning of
                these properties is not defined by the specification. The same name is
                allowed to appear more than once. The order is preserved.

        Returns:
            The PUBACK/PUBREC response from the broker (for QoS=1/QoS=2).
        """
        match qos:
            case QoS.AT_MOST_ONCE:
                await self._publish_at_most_once(
                    topic,
                    payload=payload,
                    retain=retain,
                    message_expiry_interval=message_expiry_interval,
                    content_type=content_type,
                    response_topic=response_topic,
                    correlation_data=correlation_data,
                    user_properties=user_properties,
                )
                return None
            case QoS.AT_LEAST_ONCE:
                if not hasattr(self, "_send_semaphore"):
                    raise ConnectError(self._hostname, self._port)
                await self._send_semaphore.acquire()
                return await self._publish_at_least_once(
                    topic,
                    payload=payload,
                    retain=retain,
                    message_expiry_interval=message_expiry_interval,
                    content_type=content_type,
                    response_topic=response_topic,
                    correlation_data=correlation_data,
                    user_properties=user_properties,
                )
            case QoS.EXACTLY_ONCE:
                if not hasattr(self, "_send_semaphore"):
                    raise ConnectError(self._hostname, self._port)
                await self._send_semaphore.acquire()
                return await self._publish_exactly_once(
                    topic,
                    payload=payload,
                    retain=retain,
                    message_expiry_interval=message_expiry_interval,
                    content_type=content_type,
                    response_topic=response_topic,
                    correlation_data=correlation_data,
                    user_properties=user_properties,
                )

    async def _publish_at_most_once(
        self,
        topic: str,
        *,
        payload: bytes | None = None,
        retain: bool = False,
        message_expiry_interval: int | None = None,
        content_type: str | None = None,
        response_topic: str | None = None,
        correlation_data: bytes | None = None,
        user_properties: list[tuple[str, str]] | None = None,
    ) -> None:
        await self._send(
            PublishPacket(
                topic=topic,
                payload=payload,
                qos=QoS.AT_MOST_ONCE,
                retain=retain,
                message_expiry_interval=message_expiry_interval,
                content_type=content_type,
                response_topic=response_topic,
                correlation_data=correlation_data,
                user_properties=user_properties,
            )
        )

    async def _publish_at_least_once(
        self,
        topic: str,
        *,
        payload: bytes | None = None,
        retain: bool = False,
        message_expiry_interval: int | None = None,
        content_type: str | None = None,
        response_topic: str | None = None,
        correlation_data: bytes | None = None,
        user_properties: list[tuple[str, str]] | None = None,
    ) -> PubAckPacket:
        packet_id = next(self._packet_ids)
        self._pending_pubacks[packet_id] = asyncio.Future()
        try:
            await self._send(
                PublishPacket(
                    packet_id=packet_id,
                    topic=topic,
                    payload=payload,
                    qos=QoS.AT_LEAST_ONCE,
                    retain=retain,
                    message_expiry_interval=message_expiry_interval,
                    content_type=content_type,
                    response_topic=response_topic,
                    correlation_data=correlation_data,
                    user_properties=user_properties,
                )
            )
            puback_packet = await self._disconnected_or(
                self._pending_pubacks[packet_id]
            )
        finally:
            del self._pending_pubacks[packet_id]
        if puback_packet.reason_code not in (
            PubAckReasonCode.SUCCESS,
            PubAckReasonCode.NO_MATCHING_SUBSCRIBERS,
        ):
            raise NegativeAckError(puback_packet)
        return puback_packet

    async def _publish_exactly_once(
        self,
        topic: str,
        *,
        payload: bytes | None = None,
        retain: bool = False,
        message_expiry_interval: int | None = None,
        content_type: str | None = None,
        response_topic: str | None = None,
        correlation_data: bytes | None = None,
        user_properties: list[tuple[str, str]] | None = None,
    ) -> PubRecPacket:
        packet_id = next(self._packet_ids)
        self._pending_pubrecs[packet_id] = asyncio.Future()
        try:
            await self._send(
                PublishPacket(
                    topic=topic,
                    payload=payload,
                    qos=QoS.EXACTLY_ONCE,
                    retain=retain,
                    packet_id=packet_id,
                    message_expiry_interval=message_expiry_interval,
                    content_type=content_type,
                    response_topic=response_topic,
                    correlation_data=correlation_data,
                    user_properties=user_properties,
                )
            )
            pubrec_packet = await self._disconnected_or(
                self._pending_pubrecs[packet_id]
            )
        finally:
            del self._pending_pubrecs[packet_id]
        if pubrec_packet.reason_code != PubRecReasonCode.SUCCESS:
            raise NegativeAckError(pubrec_packet)
        return pubrec_packet

    async def puback(
        self,
        packet_id: int,
        *,
        reason_code: PubAckReasonCode = PubAckReasonCode.SUCCESS,
        reason_str: str | None = None,
        user_properties: list[tuple[str, str]] | None = None,
    ) -> None:
        """Acknowledge receipt of QoS=1 PUBLISH packet.

        Args:
            packet_id: The identifier of the PUBLISH packet to acknowledge.
            reason_code: Indicates the result of an operation. Reason codes of 128 or
                greater indicate failure.
            reason_str: Additional information on the reason as human readable string.
            user_properties: Name/value pairs to send with the packet. The meaning of
                these properties is not defined by the specification. The same name is
                allowed to appear more than once. The order is preserved.
        """
        await self._send(
            PubAckPacket(
                packet_id=packet_id,
                reason_code=reason_code,
                reason_str=reason_str,
                user_properties=user_properties,
            )
        )

    async def pubrec(
        self,
        packet_id: int,
        *,
        reason_code: PubRecReasonCode = PubRecReasonCode.SUCCESS,
        reason_str: str | None = None,
        user_properties: list[tuple[str, str]] | None = None,
    ) -> None:
        """Acknowledge receipt of QoS=2 PUBLISH packet.

        Args:
            packet_id: The identifier of the PUBLISH packet to acknowledge.
            reason_code: Indicates the result of an operation. Reason codes of 128 or
                greater indicate failure.
            reason_str: Additional information on the reason as human readable string.
            user_properties: Name/value pairs to send with the packet. The meaning of
                these properties is not defined by the specification. The same name is
                allowed to appear more than once. The order is preserved.
        """
        await self._send(
            PubRecPacket(
                packet_id=packet_id,
                reason_code=reason_code,
                reason_str=reason_str,
                user_properties=user_properties,
            )
        )

    async def pubrel(
        self,
        packet_id: int,
        *,
        reason_code: PubRelReasonCode = PubRelReasonCode.SUCCESS,
        reason_str: str | None = None,
        user_properties: list[tuple[str, str]] | None = None,
    ) -> PubCompPacket:
        """Acknowledge receipt of PUBREC packet (QoS=2 PUBLISH flow).

        Args:
            packet_id: The identifier of the PUBLISH packet to acknowledge.
            reason_code: Indicates the result of an operation. Reason codes of 128 or
                greater indicate failure.
            reason_str: Additional information on the reason as human readable string.
            user_properties: Name/value pairs to send with the packet. The meaning of
                these properties is not defined by the specification. The same name is
                allowed to appear more than once. The order is preserved.

        Returns:
            The PUBCOMP response from the broker.
        """
        self._pending_pubcomps[packet_id] = asyncio.Future()
        try:
            await self._send(
                PubRelPacket(
                    packet_id=packet_id,
                    reason_code=reason_code,
                    reason_str=reason_str,
                    user_properties=user_properties,
                )
            )
            pubcomp_packet = await self._disconnected_or(
                self._pending_pubcomps[packet_id]
            )
        finally:
            del self._pending_pubcomps[packet_id]
        if pubcomp_packet.reason_code != PubCompReasonCode.SUCCESS:
            raise NegativeAckError(pubcomp_packet)
        return pubcomp_packet

    async def pubcomp(
        self,
        packet_id: int,
        *,
        reason_code: PubCompReasonCode = PubCompReasonCode.SUCCESS,
        reason_str: str | None = None,
        user_properties: list[tuple[str, str]] | None = None,
    ) -> None:
        """Acknowledge receipt of PUBREL packet (QoS=2 PUBLISH flow).

        Args:
            packet_id: The identifier of the PUBLISH packet to acknowledge.
            reason_code: Indicates the result of an operation. Reason codes of 128 or
                greater indicate failure.
            reason_str: Additional information on the reason as human readable string.
            user_properties: Name/value pairs to send with the packet. The meaning of
                these properties is not defined by the specification. The same name is
                allowed to appear more than once. The order is preserved.
        """
        await self._send(
            PubCompPacket(
                packet_id=packet_id,
                reason_code=reason_code,
                reason_str=reason_str,
                user_properties=user_properties,
            )
        )

    async def subscribe(
        self,
        pattern: str,
        *,
        max_qos: QoS = QoS.EXACTLY_ONCE,
        no_local: bool = False,
        retain_as_published: bool = True,
        retain_handling: RetainHandling = RetainHandling.SEND_ALWAYS,
        subscription_id: int | None = None,
        user_properties: list[tuple[str, str]] | None = None,
    ) -> SubAckPacket:
        """Subscribe to a topic or pattern.

        Args:
            pattern: The topic or pattern to subscribe to.
            max_qos: The maximum QoS that the client wants to accept for this
                subscription. Messages with higher QoS are downgraded.
            no_local: If True, messages published by the client itself are not sent to
                this subscription.
            retain_as_published: If True, messages sent to this subscription keep the
                retain flag they were published with. If False, messages have the retain
                flag set to 0. Retained messages sent when the subscription is created
                always have the retain flag set to 1.
            retain_handling: Specifies if retained messages are sent when the
                subscription is created. If SEND_ALWAYS, retained messages are sent.
                If SEND_IF_SUBSCRIPTION_NOT_EXISTS, retained messages are sent only if
                the subscription does not yet exist. If SEND_NEVER, retained messages
                are not sent.
            subscription_id: The identifier of the subscription. The broker includes
                this value in every message to the client that matches the
                subscription.
            user_properties: Name/value pairs to send with the packet. The meaning of
                these properties is not defined by the specification. The same name is
                allowed to appear more than once. The order is preserved.

        Returns:
            The SUBACK response from the broker.
        """
        packet_id = next(self._packet_ids)
        self._pending_subacks[packet_id] = asyncio.Future()
        try:
            await self._send(
                SubscribePacket(
                    packet_id=packet_id,
                    subscriptions=[
                        Subscription(
                            pattern=pattern,
                            max_qos=max_qos,
                            no_local=no_local,
                            retain_as_published=retain_as_published,
                            retain_handling=retain_handling,
                        ),
                    ],
                    subscription_id=subscription_id,
                    user_properties=user_properties,
                )
            )
            suback_packet = await self._disconnected_or(
                self._pending_subacks[packet_id]
            )
        finally:
            del self._pending_subacks[packet_id]
        if len(suback_packet.reason_codes) != 1:
            await self._disconnect(reason_code=DisconnectReasonCode.MALFORMED_PACKET)
            msg = "Received malformed packet"
            raise ProtocolError(msg)
        if suback_packet.reason_codes[0] not in (
            SubAckReasonCode.GRANTED_QOS_AT_MOST_ONCE,
            SubAckReasonCode.GRANTED_QOS_AT_LEAST_ONCE,
            SubAckReasonCode.GRANTED_QOS_EXACTLY_ONCE,
        ):
            raise NegativeAckError(suback_packet)
        return suback_packet

    async def unsubscribe(
        self,
        pattern: str,
        *,
        user_properties: list[tuple[str, str]] | None = None,
    ) -> UnsubAckPacket:
        """Unsubscribe from a topic or pattern.

        Args:
            pattern: The topic or pattern to unsubscribe from.
            user_properties: Name/value pairs to send with the packet. The meaning of
                these properties is not defined by the specification. The same name is
                allowed to appear more than once. The order is preserved.

        Returns:
            The UNSUBACK response from the broker.
        """
        packet_id = next(self._packet_ids)
        self._pending_unsubacks[packet_id] = asyncio.Future()
        try:
            await self._send(
                UnsubscribePacket(
                    packet_id=packet_id,
                    patterns=[pattern],
                    user_properties=user_properties,
                )
            )
            unsuback_packet = await self._disconnected_or(
                self._pending_unsubacks[packet_id]
            )
        finally:
            del self._pending_unsubacks[packet_id]
        if len(unsuback_packet.reason_codes) != 1:
            await self._disconnect(reason_code=DisconnectReasonCode.MALFORMED_PACKET)
            msg = "Received malformed packet"
            raise ProtocolError(msg)
        if unsuback_packet.reason_codes[0] != UnsubAckReasonCode.SUCCESS:
            raise NegativeAckError(unsuback_packet)
        return unsuback_packet

    async def _pingreq(self) -> PingRespPacket:
        self._pending_pingresp = asyncio.Future()
        await self._send(PingReqPacket())
        return await self._disconnected_or(self._pending_pingresp)

    async def _disconnect(
        self,
        *,
        reason_code: DisconnectReasonCode = DisconnectReasonCode.NORMAL_DISCONNECTION,
        session_expiry_interval: int | None = None,
        server_reference: str | None = None,
        reason_str: str | None = None,
        user_properties: list[tuple[str, str]] | None = None,
    ) -> None:
        async with self._disconnection_lock:
            # Return early if we're already disconnected
            if not hasattr(self, "_disconnected") or self._disconnected.done():
                return
            self._logger.info(
                "Disconnecting %s will message",
                "without"
                if reason_code == DisconnectReasonCode.NORMAL_DISCONNECTION
                else "with",
            )
            try:
                await self._send(
                    DisconnectPacket(
                        reason_code=reason_code,
                        session_expiry_interval=session_expiry_interval,
                        server_reference=server_reference,
                        reason_str=reason_str,
                        user_properties=user_properties,
                    )
                )
            except ConnectError:
                self._logger.exception("Failed to send DISCONNECT")
            self._writer.close()
            await self._writer.wait_closed()
            self._connected = asyncio.Future()
            self._disconnected.set_result(None)
