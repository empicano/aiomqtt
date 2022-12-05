# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import asyncio
import functools
import logging
import socket
import ssl
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from enum import IntEnum
from types import TracebackType
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Coroutine,
    Generator,
    Iterable,
    Iterator,
    cast,
)

if sys.version_info >= (3, 10):
    from typing import Concatenate, ParamSpec, TypeAlias
else:
    from typing_extensions import Concatenate, ParamSpec, TypeAlias

from contextlib import asynccontextmanager

import paho.mqtt.client as mqtt
from paho.mqtt.properties import Properties

from .error import MqttCodeError, MqttConnectError, MqttError
from .types import PayloadType, T

MQTT_LOGGER = logging.getLogger("mqtt")
MQTT_LOGGER.setLevel(logging.WARNING)

_PahoSocket: TypeAlias = "socket.socket | ssl.SSLSocket | mqtt.WebsocketWrapper | Any"

WebSocketHeaders: TypeAlias = (
    "dict[str, str] | Callable[[dict[str, str]], dict[str, str]]"
)


class ProtocolVersion(IntEnum):
    """A mapping of paho-mqtt protocol versions to an Enum for use in type hints."""

    V31 = mqtt.MQTTv31
    V311 = mqtt.MQTTv311
    V5 = mqtt.MQTTv5


@dataclass(frozen=True)
class Will:
    topic: str
    payload: PayloadType | None = None
    qos: int = 0
    retain: bool = False
    properties: mqtt.Properties | None = None


# TLS set parameter class
@dataclass(frozen=True)
class TLSParameters:
    ca_certs: str | None = None
    certfile: str | None = None
    keyfile: str | None = None
    cert_reqs: ssl.VerifyMode | None = None
    tls_version: Any | None = None
    ciphers: str | None = None
    keyfile_password: str | None = None


# Proxy parameters class
class ProxySettings:
    def __init__(
        self,
        *,
        proxy_type: int,
        proxy_addr: str,
        proxy_rdns: bool | None = True,
        proxy_username: str | None = None,
        proxy_password: str | None = None,
    ):
        self.proxy_args = {
            "proxy_type": proxy_type,
            "proxy_addr": proxy_addr,
            "proxy_rdns": proxy_rdns,
            "proxy_username": proxy_username,
            "proxy_password": proxy_password,
        }


# See the overloads of `socket.setsockopt` for details.
SocketOption: TypeAlias = "tuple[int, int, int | bytes] | tuple[int, int, None, int]"

SubscribeTopic: TypeAlias = "str | tuple[str, mqtt.SubscribeOptions] | list[tuple[str, mqtt.SubscribeOptions]] | list[tuple[str, int]]"

P = ParamSpec("P")

# TODO: Simplify the logic that surrounds `self._outgoing_calls_sem` with
# `nullcontext` when we support Python 3.10 (`nullcontext` becomes async-aware in
# 3.10). See: https://docs.python.org/3/library/contextlib.html#contextlib.nullcontext
def _outgoing_call(
    method: Callable[Concatenate[Client, P], Coroutine[Any, Any, T]]
) -> Callable[Concatenate[Client, P], Coroutine[Any, Any, T]]:
    @functools.wraps(method)
    async def decorated(self: Client, *args: P.args, **kwargs: P.kwargs) -> T:
        if not self._outgoing_calls_sem:
            return await method(self, *args, **kwargs)

        async with self._outgoing_calls_sem:
            return await method(self, *args, **kwargs)

    return decorated


@dataclass(frozen=True)
class Wildcard:
    """A topic, optionally with wildcards (+ and #). Can only be subscribed to."""

    value: str

    def __str__(self) -> str:
        return self.value

    def __post_init__(self) -> None:
        """Validate the wildcard."""
        if not isinstance(self.value, str):
            raise TypeError("wildcard must be a string")
        if (
            len(self.value) == 0
            or len(self.value) > 65535
            or "#/" in self.value
            or any(
                "+" in level or "#" in level
                for level in self.value.split("/")
                if len(level) > 1
            )
        ):
            raise ValueError(f"Invalid wildcard: {self.value}")


WildcardLike: TypeAlias = "str | Wildcard"


@dataclass(frozen=True)
class Topic(Wildcard):
    """A topic that can be published and subscribed to."""

    def __post_init__(self) -> None:
        """Validate the topic."""
        if not isinstance(self.value, str):
            raise TypeError("topic must be a string")
        if (
            len(self.value) == 0
            or len(self.value) > 65535
            or "+" in self.value
            or "#" in self.value
        ):
            raise ValueError(f"Invalid topic: {self.value}")

    def matches(self, wildcard: WildcardLike) -> bool:
        """Check if the topic is matched by a given wildcard."""
        if not isinstance(wildcard, Wildcard):
            wildcard = Wildcard(wildcard)
        # Split topics into levels to compare them one by one
        topic_levels = self.value.split("/")
        wildcard_levels = str(wildcard).split("/")
        if wildcard_levels[0] == "$share":
            # Shared subscriptions use the topic structure: $share/<group_id>/<topic>
            wildcard_levels = wildcard_levels[2:]

        def recurse(x: list[str], y: list[str]) -> bool:
            if not x:
                if not y:
                    return True
                return False
            if not y:
                return False
            if y[0] == "#":
                return True
            if x[0] == y[0] or y[0] == "+":
                return recurse(x[1:], y[1:])
            return False

        return recurse(topic_levels, wildcard_levels)


TopicLike: TypeAlias = "str | Topic"


class Message:
    """Custom message class that allows us to use our own Topic class."""

    def __init__(
        self,
        topic: TopicLike,
        payload: PayloadType,
        qos: int,
        retain: bool,
        mid: int,
        properties: Properties | None,
    ):
        self.topic = Topic(topic) if not isinstance(topic, Topic) else topic
        self.payload = payload
        self.qos = qos
        self.retain = retain
        self.mid = mid
        self.properties = properties

    @classmethod
    def _from_paho_message(cls, message: mqtt.MQTTMessage) -> Message:
        return cls(
            topic=message.topic,
            payload=message.payload,
            qos=message.qos,
            retain=message.retain,
            mid=message.mid,
            properties=message.properties if hasattr(message, "properties") else None,
        )


class Client:
    def __init__(  # noqa: C901
        self,
        hostname: str,
        port: int = 1883,
        *,
        username: str | None = None,
        password: str | None = None,
        logger: logging.Logger | None = None,
        client_id: str | None = None,
        tls_context: ssl.SSLContext | None = None,
        tls_params: TLSParameters | None = None,
        proxy: ProxySettings | None = None,
        protocol: ProtocolVersion | None = None,
        will: Will | None = None,
        clean_session: bool | None = None,
        transport: str = "tcp",
        keepalive: int = 60,
        bind_address: str = "",
        bind_port: int = 0,
        clean_start: int = mqtt.MQTT_CLEAN_START_FIRST_ONLY,
        properties: Properties | None = None,
        message_retry_set: int = 20,
        socket_options: Iterable[SocketOption] | None = None,
        max_concurrent_outgoing_calls: int | None = None,
        websocket_path: str | None = None,
        websocket_headers: WebSocketHeaders | None = None,
    ):
        self._hostname = hostname
        self._port = port
        self._keepalive = keepalive
        self._bind_address = bind_address
        self._bind_port = bind_port
        self._clean_start = clean_start
        self._properties = properties
        self._loop = asyncio.get_event_loop()
        self._connected: asyncio.Future[int | mqtt.ReasonCodes] = asyncio.Future()
        self._disconnected: asyncio.Future[
            int | mqtt.ReasonCodes | None
        ] = asyncio.Future()
        # Pending subscribe, unsubscribe, and publish calls
        self._pending_subscribes: dict[
            int, asyncio.Future[tuple[int] | list[mqtt.ReasonCodes]]
        ] = {}
        self._pending_unsubscribes: dict[int, asyncio.Event] = {}
        self._pending_publishes: dict[int, asyncio.Event] = {}
        self._pending_calls_threshold: int = 10
        self._misc_task: asyncio.Task[None] | None = None

        # List of all callbacks to call when a message is received
        self._on_message_callbacks: list[Callable[[Message], None]] = []
        self._unfiltered_messages_callback: Callable[
            [mqtt.Client, Any, mqtt.MQTTMessage], None
        ] | None = None

        self._outgoing_calls_sem: asyncio.Semaphore | None
        if max_concurrent_outgoing_calls is not None:
            self._outgoing_calls_sem = asyncio.Semaphore(max_concurrent_outgoing_calls)
        else:
            self._outgoing_calls_sem = None

        if protocol is None:
            protocol = ProtocolVersion.V311

        self._client: mqtt.Client = mqtt.Client(
            client_id=client_id,
            protocol=protocol,
            clean_session=clean_session,
            transport=transport,
            reconnect_on_failure=False,
        )
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_subscribe = self._on_subscribe
        self._client.on_unsubscribe = self._on_unsubscribe
        self._client.on_message = self._on_message
        self._client.on_publish = self._on_publish
        # Callbacks for custom event loop
        self._client.on_socket_open = self._on_socket_open
        self._client.on_socket_close = self._on_socket_close
        self._client.on_socket_register_write = self._on_socket_register_write
        self._client.on_socket_unregister_write = self._on_socket_unregister_write

        if logger is None:
            logger = MQTT_LOGGER
        self._client.enable_logger(logger)

        if username is not None:
            self._client.username_pw_set(username=username, password=password)

        if tls_context is not None:
            self._client.tls_set_context(tls_context)

        if tls_params is not None:
            self._client.tls_set(
                ca_certs=tls_params.ca_certs,
                certfile=tls_params.certfile,
                keyfile=tls_params.keyfile,
                cert_reqs=tls_params.cert_reqs,
                tls_version=tls_params.tls_version,
                ciphers=tls_params.ciphers,
                keyfile_password=tls_params.keyfile_password,
            )

        if proxy is not None:
            self._client.proxy_set(**proxy.proxy_args)

        if websocket_path is not None:
            self._client.ws_set_options(path=websocket_path, headers=websocket_headers)

        if will is not None:
            self._client.will_set(
                will.topic, will.payload, will.qos, will.retain, will.properties
            )

        self._client.message_retry_set(message_retry_set)
        if socket_options is None:
            socket_options = ()
        self._socket_options = tuple(socket_options)

    @property
    def id(  # noqa: A003 # TODO: When doing BREAKING CHANGES rename to avoid shadowing builtin id
        self,
    ) -> str:
        """Return the client ID.

        Note that paho-mqtt stores the client ID as `bytes` internally.
        We assume that the client ID is a UTF8-encoded string and decode
        it first.
        """
        return cast(bytes, self._client._client_id).decode()  # type: ignore[attr-defined]

    @property
    def _pending_calls(self) -> Generator[int, None, None]:
        """Yield all message IDs with pending calls."""
        yield from self._pending_subscribes.keys()
        yield from self._pending_unsubscribes.keys()
        yield from self._pending_publishes.keys()

    async def connect(self, *, timeout: int = 10) -> None:
        try:
            loop = asyncio.get_running_loop()

            # [3] Run connect() within an executor thread, since it blocks on socket
            # connection for up to `keepalive` seconds: https://git.io/Jt5Yc
            await loop.run_in_executor(
                None,
                self._client.connect,
                self._hostname,
                self._port,
                self._keepalive,
                self._bind_address,
                self._bind_port,
                self._clean_start,
                self._properties,
            )
            client_socket = self._client.socket()
            _set_client_socket_defaults(client_socket, self._socket_options)
        # paho.mqtt.Client.connect may raise one of several exceptions.
        # We convert all of them to the common MqttError for user convenience.
        # See: https://github.com/eclipse/paho.mqtt.python/blob/v1.5.0/src/paho/mqtt/client.py#L1770
        except (OSError, mqtt.WebsocketConnectionError) as error:
            raise MqttError(str(error)) from None
        await self._wait_for(self._connected, timeout=timeout)

    async def disconnect(self, *, timeout: int = 10) -> None:
        rc = self._client.disconnect()
        # Early out on error
        if rc != mqtt.MQTT_ERR_SUCCESS:
            raise MqttCodeError(rc, "Could not disconnect")
        # Wait for acknowledgement
        await self._wait_for(self._disconnected, timeout=timeout)

    async def force_disconnect(self) -> None:
        if not self._disconnected.done():
            self._disconnected.set_result(None)

    @_outgoing_call
    async def subscribe(
        self,
        topic: SubscribeTopic,
        qos: int = 0,
        options: mqtt.SubscribeOptions | None = None,
        properties: Properties | None = None,
        *args: Any,
        timeout: int = 10,
        **kwargs: Any,
    ) -> tuple[int] | list[mqtt.ReasonCodes]:
        result, mid = self._client.subscribe(
            topic, qos, options, properties, *args, **kwargs
        )
        # Early out on error
        if result != mqtt.MQTT_ERR_SUCCESS:
            raise MqttCodeError(result, "Could not subscribe to topic")
        # Create future for when the on_subscribe callback is called
        callback_result: asyncio.Future[
            tuple[int] | list[mqtt.ReasonCodes]
        ] = asyncio.Future()
        with self._pending_call(mid, callback_result, self._pending_subscribes):
            # Wait for callback_result
            return await self._wait_for(callback_result, timeout=timeout)

    @_outgoing_call
    async def unsubscribe(
        self,
        topic: str | list[str],
        properties: Properties | None = None,
        *args: Any,
        timeout: int = 10,
        **kwargs: Any,
    ) -> None:
        result, mid = self._client.unsubscribe(topic, properties, *args, **kwargs)
        # Early out on error
        if result != mqtt.MQTT_ERR_SUCCESS:
            raise MqttCodeError(result, "Could not unsubscribe from topic")
        # Create event for when the on_unsubscribe callback is called
        confirmation = asyncio.Event()
        with self._pending_call(mid, confirmation, self._pending_unsubscribes):
            # Wait for confirmation
            await self._wait_for(confirmation.wait(), timeout=timeout)

    @_outgoing_call
    async def publish(
        self,
        topic: str,
        payload: PayloadType = None,
        qos: int = 0,
        retain: bool = False,
        properties: Properties | None = None,
        *args: Any,
        timeout: int = 10,
        **kwargs: Any,
    ) -> None:
        info = self._client.publish(
            topic, payload, qos, retain, properties, *args, **kwargs
        )  # [2]
        # Early out on error
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise MqttCodeError(info.rc, "Could not publish message")
        # Early out on immediate success
        if info.is_published():
            return
        # Create event for when the on_publish callback is called
        confirmation = asyncio.Event()
        with self._pending_call(info.mid, confirmation, self._pending_publishes):
            # Wait for confirmation
            await self._wait_for(confirmation.wait(), timeout=timeout)

    @asynccontextmanager
    async def filtered_messages(
        self, topic_filter: str, *, queue_maxsize: int = 0
    ) -> AsyncGenerator[AsyncGenerator[mqtt.MQTTMessage, None], None]:
        """Return async generator of messages that match the given filter."""
        MQTT_LOGGER.warning(
            "filtered_messages() is deprecated and will be removed in a future version."
            " Use messages() together with Topic.matches() instead."
        )
        callback, generator = self._deprecated_callback_and_generator(
            log_context=f'topic_filter="{topic_filter}"', queue_maxsize=queue_maxsize
        )
        try:
            self._client.message_callback_add(topic_filter, callback)
            # Back to the caller (run whatever is inside the with statement)
            yield generator
        finally:
            # We are exiting the with statement. Remove the topic filter.
            self._client.message_callback_remove(topic_filter)

    @asynccontextmanager
    async def unfiltered_messages(
        self, *, queue_maxsize: int = 0
    ) -> AsyncGenerator[AsyncGenerator[mqtt.MQTTMessage, None], None]:
        """Return async generator of all messages that are not caught in filters."""
        MQTT_LOGGER.warning(
            "unfiltered_messages() is deprecated and will be removed in a future"
            " version. Use messages() instead."
        )
        # Early out
        if self._unfiltered_messages_callback is not None:
            raise RuntimeError(
                "Only a single unfiltered_messages generator can be used at a time."
            )
        callback, generator = self._deprecated_callback_and_generator(
            log_context="unfiltered", queue_maxsize=queue_maxsize
        )
        try:
            self._unfiltered_messages_callback = callback
            # Back to the caller (run whatever is inside the with statement)
            yield generator
        finally:
            # We are exiting the with statement. Unset the callback.
            self._unfiltered_messages_callback = None

    @asynccontextmanager
    async def messages(
        self, *, queue_maxsize: int = 0
    ) -> AsyncGenerator[AsyncGenerator[Message, None], None]:
        """Return async generator of incoming messages.

        Use queue_maxsize to restrict the queue size. If the queue is full,
        incoming messages will be discarded (and a warning is logged).
        If queue_maxsize is less than or equal to zero, the queue size is infinite.
        """
        callback, generator = self._callback_and_generator(queue_maxsize=queue_maxsize)
        try:
            # Add to the list of callbacks to call when a message is received
            self._on_message_callbacks.append(callback)
            # Back to the caller (run whatever is inside the with statement)
            yield generator
        finally:
            # We are exiting the with statement. Remove the callback from the list.
            self._on_message_callbacks.remove(callback)

    def _deprecated_callback_and_generator(
        self, *, log_context: str, queue_maxsize: int = 0
    ) -> tuple[
        Callable[[mqtt.Client, Any, mqtt.MQTTMessage], None],
        AsyncGenerator[mqtt.MQTTMessage, None],
    ]:
        # Queue to hold the incoming messages
        messages: asyncio.Queue[mqtt.MQTTMessage] = asyncio.Queue(maxsize=queue_maxsize)
        # Callback for the underlying API
        def _put_in_queue(
            client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage
        ) -> None:
            try:
                messages.put_nowait(message)
            except asyncio.QueueFull:
                MQTT_LOGGER.warning(
                    f"[{log_context}] Message queue is full. Discarding message."
                )

        # The generator that we give to the caller
        async def _message_generator() -> AsyncGenerator[mqtt.MQTTMessage, None]:
            # Forward all messages from the queue
            while True:
                # Wait until we either:
                #  1. Receive a message
                #  2. Disconnect from the broker
                get: asyncio.Task[mqtt.MQTTMessage] = self._loop.create_task(
                    messages.get()
                )
                try:
                    done, _ = await asyncio.wait(
                        (get, self._disconnected), return_when=asyncio.FIRST_COMPLETED
                    )
                except asyncio.CancelledError:
                    # If the asyncio.wait is cancelled, we must make sure
                    # to also cancel the underlying tasks.
                    get.cancel()
                    raise
                if get in done:
                    # We received a message. Return the result.
                    yield get.result()
                else:
                    # We got disconnected from the broker. Cancel the "get" task.
                    get.cancel()
                    # Stop the generator with the following exception
                    raise MqttError("Disconnected during message iteration")

        return _put_in_queue, _message_generator()

    def _callback_and_generator(
        self, *, queue_maxsize: int = 0
    ) -> tuple[Callable[[Message], None], AsyncGenerator[Message, None]]:
        # Queue to hold the incoming messages
        messages: asyncio.Queue[Message] = asyncio.Queue(maxsize=queue_maxsize)

        def _callback(message: Message) -> None:
            """Put the new message in the queue."""
            try:
                messages.put_nowait(message)
            except asyncio.QueueFull:
                MQTT_LOGGER.warning("Message queue is full. Discarding message.")

        async def _generator() -> AsyncGenerator[Message, None]:
            """Forward all messages from the message queue."""
            while True:
                # Wait until we either:
                #  1. Receive a message
                #  2. Disconnect from the broker
                get: asyncio.Task[Message] = self._loop.create_task(messages.get())
                try:
                    done, _ = await asyncio.wait(
                        (get, self._disconnected), return_when=asyncio.FIRST_COMPLETED
                    )
                except asyncio.CancelledError:
                    # If the asyncio.wait is cancelled, we must make sure
                    # to also cancel the underlying tasks.
                    get.cancel()
                    raise
                if get in done:
                    # We received a message. Return the result.
                    yield get.result()
                else:
                    # We got disconnected from the broker. Cancel the "get" task.
                    get.cancel()
                    # Stop the generator with the following exception
                    raise MqttError("Disconnected during message iteration")

        return _callback, _generator()

    async def _wait_for(
        self, fut: Awaitable[T], timeout: float | None, **kwargs: Any
    ) -> T:
        try:
            return await asyncio.wait_for(fut, timeout=timeout, **kwargs)
        except asyncio.TimeoutError:
            raise MqttError("Operation timed out") from None

    @contextmanager
    def _pending_call(
        self, mid: int, value: T, pending_dict: dict[int, T]
    ) -> Iterator[None]:
        if mid in self._pending_calls:
            raise RuntimeError(
                f'There already exists a pending call for message ID "{mid}"'
            )
        pending_dict[mid] = value  # [1]
        try:
            # Log a warning if there is a concerning number of pending calls
            pending = len(list(self._pending_calls))
            if pending > self._pending_calls_threshold:
                MQTT_LOGGER.warning(f"There are {pending} pending publish calls.")
            # Back to the caller (run whatever is inside the with statement)
            yield
        finally:
            # The normal procedure is:
            #  * We add the item at [1]
            #  * A callback will remove the item
            #
            # However, if the callback doesn't get called (e.g., due to a
            # network error) we still need to remove the item from the dict.
            try:
                del pending_dict[mid]
            except KeyError:
                pass

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: dict[str, int],
        rc: int | mqtt.ReasonCodes,
        properties: mqtt.Properties | None = None,
    ) -> None:
        # Return early if already connected. Sometimes, paho-mqtt calls _on_connect
        # multiple times. Maybe because we receive multiple CONNACK messages
        # from the server. In any case, we return early so that we don't set
        # self._connected twice (as it raises an asyncio.InvalidStateError).
        if self._connected.done():
            return

        if rc == mqtt.CONNACK_ACCEPTED:
            self._connected.set_result(rc)
        else:
            self._connected.set_exception(MqttConnectError(rc))

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        rc: int | mqtt.ReasonCodes | None,
        properties: mqtt.Properties | None = None,
    ) -> None:
        # Return early if the disconnect is already acknowledged.
        # Sometimes (e.g., due to timeouts), paho-mqtt calls _on_disconnect
        # twice. We return early to avoid setting self._disconnected twice
        # (as it raises an asyncio.InvalidStateError).
        if self._disconnected.done():
            return
        # Return early if we are not connected yet. This avoids calling
        # `_disconnected.set_exception` with an exception that will never
        # be retrieved (since `__aexit__` won't get called if `__aenter__`
        # fails). In turn, this avoids asyncio debug messages like the
        # following:
        #
        #   "[asyncio] Future exception was never retrieved"
        #
        # See also: https://docs.python.org/3/library/asyncio-dev.html#detect-never-retrieved-exceptions
        if not self._connected.done() or self._connected.exception() is not None:
            return
        if rc == mqtt.MQTT_ERR_SUCCESS:
            self._disconnected.set_result(rc)
        else:
            self._disconnected.set_exception(MqttCodeError(rc, "Unexpected disconnect"))

    def _on_subscribe(
        self,
        client: mqtt.Client,
        userdata: Any,
        mid: int,
        granted_qos: tuple[int] | list[mqtt.ReasonCodes],
        properties: mqtt.Properties | None = None,
    ) -> None:
        try:
            fut = self._pending_subscribes.pop(mid)
            if not fut.done():
                fut.set_result(granted_qos)
        except KeyError:
            MQTT_LOGGER.error(f'Unexpected message ID "{mid}" in on_subscribe callback')

    def _on_unsubscribe(
        self,
        client: mqtt.Client,
        userdata: Any,
        mid: int,
        properties: mqtt.Properties | None = None,
        reason_codes: list[mqtt.ReasonCodes] | mqtt.ReasonCodes | None = None,
    ) -> None:
        try:
            self._pending_unsubscribes.pop(mid).set()
        except KeyError:
            MQTT_LOGGER.error(
                f'Unexpected message ID "{mid}" in on_unsubscribe callback'
            )

    def _on_message(
        self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage
    ) -> None:
        # Call the deprecated unfiltered_messages callback
        if self._unfiltered_messages_callback is not None:
            self._unfiltered_messages_callback(client, userdata, message)
        # Convert the paho.mqtt message into our own Message type
        m = Message._from_paho_message(message)
        for callback in self._on_message_callbacks:
            callback(m)

    def _on_publish(self, client: mqtt.Client, userdata: Any, mid: int) -> None:
        try:
            self._pending_publishes.pop(mid).set()
        except KeyError:
            # Do nothing since [2] may call on_publish before it even returns.
            # That is, the message may already be published before we even get a
            # chance to set up the 'pending_call' logic.
            pass

    def _on_socket_open(
        self, client: mqtt.Client, userdata: Any, sock: _PahoSocket
    ) -> None:
        def callback() -> None:
            # client.loop_read() may raise an exception, such as BadPipe. It's
            # usually a sign that the underlaying connection broke, therefore we
            # disconnect straight away
            try:
                client.loop_read()
            except Exception as exc:
                if not self._disconnected.done():
                    self._disconnected.set_exception(exc)

        self._loop.add_reader(sock.fileno(), callback)
        # paho-mqtt calls this function from the executor thread on which we've called
        # `self._client.connect()` (see [3]), so we create a callback function to
        # schedule `_misc_loop()` and run it on the loop thread-safely.
        def create_task_callback() -> None:
            self._misc_task = self._loop.create_task(self._misc_loop())

        self._loop.call_soon_threadsafe(create_task_callback)

    def _on_socket_close(
        self, client: mqtt.Client, userdata: Any, sock: _PahoSocket
    ) -> None:
        fileno = sock.fileno()
        if fileno > -1:
            self._loop.remove_reader(fileno)
        if self._misc_task is not None and not self._misc_task.done():
            self._loop.call_soon_threadsafe(self._misc_task.cancel)

    def _on_socket_register_write(
        self, client: mqtt.Client, userdata: Any, sock: _PahoSocket
    ) -> None:
        def callback() -> None:
            # client.loop_write() may raise an exception, such as BadPipe. It's
            # usually a sign that the underlaying connection broke, therefore we
            # disconnect straight away
            try:
                client.loop_write()
            except Exception as exc:
                if not self._disconnected.done():
                    self._disconnected.set_exception(exc)

        self._loop.add_writer(sock, callback)

    def _on_socket_unregister_write(
        self, client: mqtt.Client, userdata: Any, sock: _PahoSocket
    ) -> None:
        self._loop.remove_writer(sock)

    async def _misc_loop(self) -> None:
        while self._client.loop_misc() == mqtt.MQTT_ERR_SUCCESS:
            await asyncio.sleep(1)

    async def __aenter__(self) -> "Client":
        """Connect to the broker."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Disconnect from the broker."""
        # Early out if already disconnected...
        if self._disconnected.done():
            disc_exc = self._disconnected.exception()
            if disc_exc is not None:
                # ...by raising the error that caused the disconnect
                raise disc_exc
            # ...by returning since the disconnect was intentional
            return
        # Try to gracefully disconnect from the broker
        try:
            await self.disconnect()
        except MqttError as error:
            # We tried to be graceful. Now there is no mercy.
            MQTT_LOGGER.warning(
                f'Could not gracefully disconnect due to "{error}". Forcing'
                " disconnection."
            )
            await self.force_disconnect()


def _set_client_socket_defaults(
    client_socket: _PahoSocket | None, socket_options: Iterable[SocketOption]
) -> None:
    # Note that socket may be None if, e.g., the username and
    # password combination didn't work. In this case, we return early.
    if client_socket is None:
        return
    # Furthermore, paho sometimes gives us a socket wrapper instead of
    # the raw socket. E.g., for WebSocket-based connections.
    if not isinstance(client_socket, socket.socket):
        return
    # At this point, we know that we got an actual socket. We change
    # some of the default options.
    for socket_option in socket_options:
        client_socket.setsockopt(*socket_option)
