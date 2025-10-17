# SPDX-License-Identifier: BSD-3-Clause
"""The core logic of the client."""

import asyncio
import collections
import contextlib
import logging
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

from .exceptions import ConnectError, NegativeAckError, ProtocolError


class _SlidingWindowBuffer:
    def __init__(self, size: int) -> None:
        self.buffer = bytearray(size)
        self.left = 0
        self.right = 0

    def write(self, data: bytes) -> None:
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
        timeout: The default timeout for all communication with the broker in seconds.
            If None, there is no timeout.
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
        max_packet_size: The maximum size of a packet in bytes that we want to accept.
            If None, there is no limit beyond limitations in the protocol.
        user_properties: Name/value pairs to send with the packet. The meaning of these
            properties is not defined by the MQTT specification. The same name is
            allowed to appear more than once. The order is preserved.
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
        will: Will | None = None,
        timeout: float = 10,
        keep_alive: int = 0,
        session_expiry_interval: int = 0,
        authentication_method: str | None = None,
        authentication_data: bytes | None = None,
        request_problem_info: bool = True,
        request_response_info: bool = False,
        receive_max: int = 65535,
        # topic_alias_max: int = 0,
        max_packet_size: int | None = None,
        user_properties: list[tuple[str, str]] | None = None,
    ) -> None:
        self._hostname = hostname
        self._port = port
        self.identifier = (
            identifier if identifier is not None else f"aiomqtt-{secrets.token_hex(4)}"
        )
        if logger is None:
            logger = logging.getLogger("aiomqtt")
            logger.setLevel(logging.DEBUG)
        self._logger = logger
        self._username = username
        self._password = password
        self._clean_start = clean_start
        self._will = will
        self._keep_alive = keep_alive
        self._session_expiry_interval = session_expiry_interval
        self._authentication_method = authentication_method
        self._authentication_data = authentication_data
        self._request_problem_info = request_problem_info
        self._request_response_info = request_response_info
        self._receive_max = receive_max
        self._max_packet_size = max_packet_size
        self._user_properties = user_properties
        # Network settings
        self._buffer_in = _SlidingWindowBuffer(size=2**24)
        self._socket: socket.socket
        self._reader: asyncio.StreamReader
        self._writer: asyncio.StreamWriter
        self._timeout = timeout
        # Connection status
        self._disconnected: asyncio.Future[None]
        self._lock: asyncio.Lock = asyncio.Lock()
        self.connack: ConnAckPacket
        # Message management
        self._getters: collections.deque[asyncio.Future[PublishPacket]] = (
            collections.deque()
        )
        self._queue: collections.deque[PublishPacket] = collections.deque()
        self._pending_pubacks: dict[int, asyncio.Future[PubAckPacket]] = {}
        self._pending_pubrels: dict[int, asyncio.Future[PubRelPacket]] = {}
        self._pending_pubrecs: dict[int, asyncio.Future[PubRecPacket]] = {}
        self._pending_pubcomps: dict[int, asyncio.Future[PubCompPacket]] = {}
        self._pending_subacks: dict[int, asyncio.Future[SubAckPacket]] = {}
        self._pending_unsubacks: dict[int, asyncio.Future[UnsubAckPacket]] = {}
        self._pending_pingresp: asyncio.Future[PingRespPacket]
        self._packet_ids = self._packet_id_generator()
        self._send_semaphore: asyncio.BoundedSemaphore
        self._most_recent_packet_sent_time: float

    async def __aenter__(self) -> typing.Self:
        if self._lock.locked():
            msg = "The client context manager is reusable but not reentrant"
            raise RuntimeError(msg)
        await self._lock.acquire()
        self._disconnected = asyncio.Future()
        # Create and connect the socket
        self._socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        try:
            self._socket.connect((self._hostname, self._port))
        except OSError as exc:
            self._lock.release()
            raise ConnectError(self._hostname, self._port) from exc
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
                topic_alias_max=0,
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
            msg = f"Received packet with unexpected type: {type(packet)}"
            raise ProtocolError(msg)
        self.connack = packet
        if self.connack.reason_code != ConnAckReasonCode.SUCCESS:
            self._lock.release()
            raise NegativeAckError(self.connack)
        if self.connack.assigned_client_id is not None:
            self._logger.info(
                "Broker set client id: %s", self.connack.assigned_client_id
            )
            self.identifier = self.connack.assigned_client_id
        if self.connack.server_keep_alive is not None:
            self._logger.info(
                "Broker set keep alive: %s", self.connack.server_keep_alive
            )
            self._keep_alive = self.connack.server_keep_alive
        self._send_semaphore = asyncio.BoundedSemaphore(self.connack.receive_max)
        # Start background tasks
        self._tasks = asyncio.create_task(self._run_background_tasks())
        return self

    async def _run_background_tasks(self) -> None:
        async with asyncio.TaskGroup() as task_group:
            task_group.create_task(self._receive_loop())
            if self._keep_alive > 0:
                task_group.create_task(self._pingreq_loop())
            # TODO(empicano): Reconnection

    def _packet_id_generator(self) -> typing.Iterator[int]:
        packet_id = 1
        while True:
            yield packet_id
            packet_id = packet_id % (2**16 - 1) + 1

    async def _send(
        self,
        packet: ConnectPacket
        | PublishPacket
        | PubAckPacket
        | PubRecPacket
        | PubRelPacket
        | PubCompPacket
        | SubscribePacket
        | UnsubscribePacket
        | PingReqPacket
        | DisconnectPacket,
    ) -> None:
        self._writer.write(packet.write())
        self._most_recent_packet_sent_time = time.monotonic()
        await self._writer.drain()

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
                        self._buffer_in.buffer,
                        index=self._buffer_in.left,
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
            except ProtocolError:
                self._logger.exception("Received malformed packet")
                raise
            self._logger.debug("Received packet with type: %s", type(packet).__name__)
            match packet:
                case PublishPacket():
                    if len(self._getters) == 0:
                        if packet.qos == QoS.AT_MOST_ONCE:
                            # Drop when no getter is immediately available
                            self._logger.debug("Dropping QoS=0 PublishPacket")
                        else:
                            self._queue.append(packet)
                    else:
                        self._getters.popleft().set_result(packet)
                case PubAckPacket():
                    self._pending_pubacks[packet.packet_id].set_result(packet)
                    self._send_semaphore.release()
                case PubRecPacket():
                    self._pending_pubrecs[packet.packet_id].set_result(packet)
                    if packet.reason_code not in [
                        PubRecReasonCode.SUCCESS,
                        PubRecReasonCode.NO_MATCHING_SUBSCRIBERS,
                    ]:
                        self._send_semaphore.release()
                case PubRelPacket():
                    self._pending_pubrels[packet.packet_id].set_result(packet)
                case PubCompPacket():
                    self._pending_pubcomps[packet.packet_id].set_result(packet)
                    self._send_semaphore.release()
                case SubAckPacket():
                    self._pending_subacks[packet.packet_id].set_result(packet)
                case UnsubAckPacket():
                    self._pending_unsubacks[packet.packet_id].set_result(packet)
                case DisconnectPacket():
                    self._logger.warning(
                        "Received DisconnectPacket with reason code: %s",
                        packet.reason_code.name,
                    )
                    await self._disconnect()
                    return
                case PingRespPacket():
                    self._pending_pingresp.set_result(packet)
                case _:
                    self._logger.error(
                        "Received packet with unexpected type: %s",
                        type(packet).__name__,
                    )
                    await self._disconnect(
                        reason_code=DisconnectReasonCode.PROTOCOL_ERROR,
                    )
                    return

    async def _pingreq_loop(self) -> None:
        while True:
            while (  # noqa: ASYNC110
                elapsed := time.monotonic() - self._most_recent_packet_sent_time
            ) < self._keep_alive:
                await asyncio.sleep(self._keep_alive - elapsed)
            try:
                await asyncio.wait_for(self._pingreq(), timeout=self._timeout)
            except TimeoutError:
                self._logger.warning("Operation timed out: PingReq")
                await self._disconnect(
                    reason_code=DisconnectReasonCode.DISCONNECT_WITH_WILL_MESSAGE
                )

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
        """Publish a message."""
        if not hasattr(self, "_disconnected") or self._disconnected.done():
            raise ConnectError(self._hostname, self._port)
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
        # Track the acknowledgement
        self._pending_pubacks[packet_id] = asyncio.Future()
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
        # Wait for the acknowledgement
        puback_packet = await self._pending_pubacks[packet_id]
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
        # Track the acknowledgement
        self._pending_pubrecs[packet_id] = asyncio.Future()
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
        # Wait for the acknowledgement
        pubrec_packet = await self._pending_pubrecs[packet_id]
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
        """Acknowledge receipt of QoS=1 PUBLISH packet."""
        if not hasattr(self, "_disconnected") or self._disconnected.done():
            raise ConnectError(self._hostname, self._port)
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
    ) -> PubRelPacket:
        """Acknowledge receipt of QoS=2 PUBLISH packet."""
        if not hasattr(self, "_disconnected") or self._disconnected.done():
            raise ConnectError(self._hostname, self._port)
        # Track the acknowledgement
        self._pending_pubrels[packet_id] = asyncio.Future()
        await self._send(
            PubRecPacket(
                packet_id=packet_id,
                reason_code=reason_code,
                reason_str=reason_str,
                user_properties=user_properties,
            )
        )
        # Wait for the acknowledgement
        pubrel_packet = await self._pending_pubrels[packet_id]
        del self._pending_pubrels[packet_id]
        if pubrel_packet.reason_code != PubRelReasonCode.SUCCESS:
            raise NegativeAckError(pubrel_packet)
        return pubrel_packet

    async def pubrel(
        self,
        packet_id: int,
        *,
        reason_code: PubRelReasonCode = PubRelReasonCode.SUCCESS,
        reason_str: str | None = None,
        user_properties: list[tuple[str, str]] | None = None,
    ) -> PubCompPacket:
        """Acknowledge receipt of PUBREC packet (QoS=2 PUBLISH flow)."""
        if not hasattr(self, "_disconnected") or self._disconnected.done():
            raise ConnectError(self._hostname, self._port)
        # Track the acknowledgement
        self._pending_pubcomps[packet_id] = asyncio.Future()
        await self._send(
            PubRelPacket(
                packet_id=packet_id,
                reason_code=reason_code,
                reason_str=reason_str,
                user_properties=user_properties,
            )
        )
        # Wait for the acknowledgement
        pubcomp_packet = await self._pending_pubcomps[packet_id]
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
        """Acknowledge receipt of PUBREL packet (QoS=2 PUBLISH flow)."""
        if not hasattr(self, "_disconnected") or self._disconnected.done():
            raise ConnectError(self._hostname, self._port)
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
            user_properties: Name/value pairs to send with the packet. The meaning of
                these properties is not defined by the MQTT specification. The same name
                is allowed to appear more than once. The order is preserved.

        Returns:
            The SUBACK response from the broker.
        """
        if not hasattr(self, "_disconnected") or self._disconnected.done():
            raise ConnectError(self._hostname, self._port)
        packet_id = next(self._packet_ids)
        # Track the acknowledgement
        self._pending_subacks[packet_id] = asyncio.Future()
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
                user_properties=user_properties,
            )
        )
        # Wait for the acknowledgement
        suback_packet = await self._pending_subacks[packet_id]
        del self._pending_subacks[packet_id]
        if len(suback_packet.reason_codes) != 1:
            # TODO(empicano): We should disconnect here
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
                these properties is not defined by the MQTT specification. The same name
                is allowed to appear more than once. The order is preserved.

        Returns:
            The UNSUBACK response from the broker.
        """
        if not hasattr(self, "_disconnected") or self._disconnected.done():
            raise ConnectError(self._hostname, self._port)
        packet_id = next(self._packet_ids)
        # Track the acknowledgement
        self._pending_unsubacks[packet_id] = asyncio.Future()
        await self._send(
            UnsubscribePacket(
                packet_id=packet_id,
                patterns=[pattern],
                user_properties=user_properties,
            )
        )
        # Wait for the acknowledgement
        unsuback_packet = await self._pending_unsubacks[packet_id]
        del self._pending_unsubacks[packet_id]
        if len(unsuback_packet.reason_codes) != 1:
            # TODO(empicano): We should disconnect here
            msg = "Received malformed packet"
            raise ProtocolError(msg)
        if unsuback_packet.reason_codes[0] != UnsubAckReasonCode.SUCCESS:
            raise NegativeAckError(unsuback_packet)
        return unsuback_packet

    async def _pingreq(self) -> PingRespPacket:
        if not hasattr(self, "_disconnected") or self._disconnected.done():
            raise ConnectError(self._hostname, self._port)
        # Track the acknowledgement
        self._pending_pingresp = asyncio.Future()
        await self._send(PingReqPacket())
        # Wait for the acknowledgement
        return await self._pending_pingresp

    async def _disconnect(
        self,
        *,
        reason_code: DisconnectReasonCode = DisconnectReasonCode.NORMAL_DISCONNECTION,
        session_expiry_interval: int | None = None,
        server_reference: str | None = None,
        reason_str: str | None = None,
        user_properties: list[tuple[str, str]] | None = None,
    ) -> None:
        # Return early if we're already disconnected
        if not hasattr(self, "_disconnected") or self._disconnected.done():
            return
        self._disconnected.set_result(None)
        self._logger.info(
            "Disconnecting %s will message",
            "with"
            if reason_code == DisconnectReasonCode.DISCONNECT_WITH_WILL_MESSAGE
            else "without",
        )
        await self._send(
            DisconnectPacket(
                reason_code=reason_code,
                session_expiry_interval=session_expiry_interval,
                server_reference=server_reference,
                reason_str=reason_str,
                user_properties=user_properties,
            )
        )
        # Close the socket
        self._writer.close()
        await self._writer.wait_closed()

    async def messages(self) -> typing.AsyncIterator[PublishPacket]:
        """Iterate over incoming messages."""
        while True:
            if not hasattr(self, "_disconnected") or self._disconnected.done():
                raise ConnectError(self._hostname, self._port)
            if len(self._queue) > 0:
                yield self._queue.popleft()
                continue
            fut: asyncio.Future[PublishPacket] = asyncio.Future()
            self._getters.append(fut)
            # Wait until we either have a message or disconnect
            await asyncio.wait(
                (fut, self._disconnected),
                return_when=asyncio.FIRST_COMPLETED,
            )
            if fut.done():
                yield fut.result()
                continue
            raise ConnectError(self._hostname, self._port)

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
        if self._lock.locked():
            self._lock.release()
