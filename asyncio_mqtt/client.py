# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import functools
import logging
import socket
import ssl
import sys
from contextlib import AsyncExitStack, contextmanager, suppress
from dataclasses import dataclass
from enum import IntEnum
from types import TracebackType
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Coroutine,
    Dict,
    Generator,
    Generic,
    Iterable,
    Iterator,
    List,
    Tuple,
    Union,
    cast,
)

import anyio
import anyio.abc
import sniffio

if sys.version_info >= (3, 10):
    from typing import Concatenate, ParamSpec
else:
    from typing_extensions import Concatenate, ParamSpec

from contextlib import asynccontextmanager

import paho.mqtt.client as mqtt
from paho.mqtt.properties import Properties

from .error import MqttCodeError, MqttConnectError, MqttError
from .types import PayloadType, T

MQTT_LOGGER = logging.getLogger("mqtt")
MQTT_LOGGER.setLevel(logging.WARNING)

_PahoSocket = Union[socket.socket, ssl.SSLSocket, mqtt.WebsocketWrapper, Any]

WebSocketHeaders = Union[
    Dict[str, str],
    Callable[[Dict[str, str]], Dict[str, str]],
]


class ProtocolVersion(IntEnum):
    """
    A mapping of Paho MQTT protocol version constants to an Enum for use in type hints.
    """

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
SocketOption = Union[
    Tuple[int, int, Union[int, bytes]],
    Tuple[int, int, None, int],
]

SubscribeTopic = Union[
    str,
    Tuple[str, mqtt.SubscribeOptions],
    List[Tuple[str, mqtt.SubscribeOptions]],
    List[Tuple[str, int]],
]

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


class Client:
    def __init__(
        self,
        tg: anyio.abc.TaskGroup,
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
        self._tg = tg
        self._hostname = hostname
        self._port = port
        self._keepalive = keepalive
        self._bind_address = bind_address
        self._bind_port = bind_port
        self._clean_start = clean_start
        self._properties = properties
        self._connected: Promise[int | mqtt.ReasonCodes] = Promise()
        self._disconnected: Promise[int | mqtt.ReasonCodes | None] = Promise()
        self._event_write = anyio.Event()
        self._cancel_scopes: set[anyio.CancelScope] = set()
        # Pending subscribe, unsubscribe, and publish calls
        self._pending_subscribes: dict[
            int, Promise[tuple[int] | list[mqtt.ReasonCodes]]
        ] = {}
        self._pending_unsubscribes: dict[int, anyio.abc.Event] = {}
        self._pending_publishes: dict[int, anyio.abc.Event] = {}
        self._pending_calls_threshold: int = 10

        self._outgoing_calls_sem: anyio.Semaphore | None
        if max_concurrent_outgoing_calls is not None:
            self._outgoing_calls_sem = anyio.Semaphore(max_concurrent_outgoing_calls)
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
        self._client.on_message = None
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
    def id(self) -> str:
        """Return the client ID.

        Note that paho-mqtt stores the client ID as `bytes` internally.
        We assume that the client ID is a UTF8-encoded string and decode
        it first.
        """
        return cast(bytes, self._client._client_id).decode()  # type: ignore[attr-defined]

    @property
    def _pending_calls(self) -> Generator[int, None, None]:
        """
        Yield all message IDs with pending calls.
        """
        yield from self._pending_subscribes.keys()
        yield from self._pending_unsubscribes.keys()
        yield from self._pending_publishes.keys()

    async def _connect(self) -> None:
        assert not self._connected.done()  # [4]
        try:
            try:
                # Run connect() in a thread, since it blocks on socket
                # connection for up to `keepalive` seconds: https://git.io/Jt5Yc
                await anyio.to_thread.run_sync(
                    self._client.connect,
                    self._hostname,
                    self._port,
                    self._keepalive,
                    self._bind_address,
                    self._bind_port,
                    self._clean_start,
                    self._properties,
                )
            # paho.mqtt.Client.connect may raise one of several exceptions.
            # We convert all of them to the common MqttError for user convenience.
            # See: https://github.com/eclipse/paho.mqtt.python/blob/v1.5.0/src/paho/mqtt/client.py#L1770
            except (OSError, mqtt.WebsocketConnectionError) as error:
                raise MqttError(str(error))
            self._start_loops()
            # Wait for acknowledgement
            await self._connected
        finally:
            # Prime the _disconnect logic
            self._disconnected = Promise()

    async def _disconnect(self) -> None:
        try:
            # Early out if already disconnected. Note that disconnects can
            # occur spuriously. E.g., due to a sudden network error. Therefore,
            # we can't simply assert like we do in _connect (see [4]).
            if self._disconnected.done():
                return
            rc = self._client.disconnect()
            # Early out on error
            if rc != mqtt.MQTT_ERR_SUCCESS:
                raise MqttCodeError(rc, "Could not disconnect")
            # Wait for acknowledgement
            await self._disconnected
        finally:
            # Prime the _connect logic
            self._connected = Promise()

    @_outgoing_call
    async def subscribe(
        self,
        topic: SubscribeTopic,
        qos: int = 0,
        options: mqtt.SubscribeOptions | None = None,
        properties: Properties | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> tuple[int] | list[mqtt.ReasonCodes]:
        result, mid = self._client.subscribe(
            topic, qos, options, properties, *args, **kwargs
        )
        # Early out on error
        if result != mqtt.MQTT_ERR_SUCCESS:
            raise MqttCodeError(result, "Could not subscribe to topic")
        # Create future for when the on_subscribe callback is called
        cb_result: Promise[tuple[int] | list[mqtt.ReasonCodes]] = Promise()
        with self._pending_call(mid, cb_result, self._pending_subscribes):
            # Wait for cb_result
            return await cb_result

    @_outgoing_call
    async def unsubscribe(
        self,
        topic: str | list[str],
        properties: Properties | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        result, mid = self._client.unsubscribe(topic, properties, *args, **kwargs)
        # Early out on error
        if result != mqtt.MQTT_ERR_SUCCESS:
            raise MqttCodeError(result, "Could not unsubscribe from topic")
        # Create event for when the on_unsubscribe callback is called
        confirmation = anyio.Event()
        with self._pending_call(mid, confirmation, self._pending_unsubscribes):
            # Wait for confirmation
            await confirmation.wait()

    @_outgoing_call
    async def publish(
        self,
        topic: str,
        payload: PayloadType = None,
        qos: int = 0,
        retain: bool = False,
        properties: Properties | None = None,
        *args: Any,
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
        confirmation = anyio.Event()
        with self._pending_call(info.mid, confirmation, self._pending_publishes):
            # Wait for confirmation
            await confirmation.wait()

    @asynccontextmanager
    async def filtered_messages(
        self, topic_filter: str, *, max_buffer_size: int = 0
    ) -> AsyncGenerator[AsyncGenerator[mqtt.MQTTMessage, None], None]:
        """Return async generator of messages that match the given filter.

        Use max_buffer_size to restrict the queue size. If the queue is full,
        incoming messages will be discarded (and a warning is logged).
        If max_buffer_size is less than or equal to zero, the queue size is infinite.

        Example use:
            async with client.filtered_messages('floors/+/humidity') as messages:
                async for message in messages:
                    print(f'Humidity reading: {message.payload.decode()}')
        """
        async with AsyncExitStack() as stack:
            cb, generator = await self._cb_and_generator(
                stack,
                log_context=f'topic_filter="{topic_filter}"',
                max_buffer_size=max_buffer_size,
            )
            try:
                self._client.message_callback_add(topic_filter, cb)
                # Back to the caller (run whatever is inside the with statement)
                yield generator
            finally:
                # We are exitting the with statement. Remove the topic filter.
                self._client.message_callback_remove(topic_filter)

    @asynccontextmanager
    async def unfiltered_messages(
        self, *, max_buffer_size: int = 0
    ) -> AsyncGenerator[AsyncGenerator[mqtt.MQTTMessage, None], None]:
        """Return async generator of all messages that are not caught in filters."""
        # Early out
        if self._client.on_message is not None:
            # TODO: This restriction can easily be removed.
            raise RuntimeError(
                "Only a single unfiltered_messages generator can be used at a time."
            )
        async with AsyncExitStack() as stack:
            cb, generator = await self._cb_and_generator(
                stack, log_context="unfiltered", max_buffer_size=max_buffer_size
            )
            try:
                self._client.on_message = cb
                # Back to the caller (run whatever is inside the with statement)
                yield generator
            finally:
                # We are exitting the with statement. Unset the callback.
                self._client.on_message = None

    async def _cb_and_generator(
        self, stack: AsyncExitStack, *, log_context: str, max_buffer_size: int = 0
    ) -> tuple[
        Callable[[mqtt.Client, Any, mqtt.MQTTMessage], None],
        AsyncGenerator[mqtt.MQTTMessage, None],
    ]:
        # Stream to hold the incoming messages
        send_stream, receive_stream = anyio.create_memory_object_stream(max_buffer_size)
        await stack.enter_async_context(send_stream)
        await stack.enter_async_context(receive_stream)

        # Callback for the underlying API
        def _put_in_stream(
            client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage
        ) -> None:
            try:
                send_stream.send_nowait(msg)
            except anyio.WouldBlock:
                MQTT_LOGGER.warning(
                    f"[{log_context}] Message queue is full. Discarding message."
                )

        # The generator that we give to the caller
        async def _message_generator() -> AsyncGenerator[mqtt.MQTTMessage, None]:
            # Forward all messages from the stream
            while True:
                yield await receive_stream.receive()

        return _put_in_stream, _message_generator()

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
        # self._connected twice (as it raises RuntimeError).
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
        self._stop_loops()
        # Return early if the disconnect is already acknowledged.
        # Sometimes (e.g., due to timeouts), paho-mqtt calls _on_disconnect
        # twice. We return early to avoid setting self._disconnected twice
        # (as it raises RuntimeError).
        if self._disconnected.done():
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
        reasonCodes: list[mqtt.ReasonCodes] | mqtt.ReasonCodes | None = None,
    ) -> None:
        try:
            self._pending_unsubscribes.pop(mid).set()
        except KeyError:
            MQTT_LOGGER.error(
                f'Unexpected message ID "{mid}" in on_unsubscribe callback'
            )

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
        client_socket = self._client.socket()
        _set_client_socket_defaults(client_socket, self._socket_options)

    def _on_socket_close(
        self, client: mqtt.Client, userdata: Any, sock: _PahoSocket
    ) -> None:
        pass

    def _on_socket_register_write(
        self, client: mqtt.Client, userdata: Any, sock: _PahoSocket
    ) -> None:
        self._event_write.set()

    def _on_socket_unregister_write(
        self, client: mqtt.Client, userdata: Any, sock: _PahoSocket
    ) -> None:
        # Will run out of the event loop if the task group is cancelled
        try:
            self._event_write = anyio.Event()
        except sniffio._impl.AsyncLibraryNotFoundError:
            pass

    def _start_loops(self) -> None:
        assert not self._cancel_scopes, "Loops already started"
        self._tg.start_soon(self._loop_read)
        self._tg.start_soon(self._loop_write)
        self._tg.start_soon(self._loop_misc)

    def _stop_loops(self) -> None:
        for cs in self._cancel_scopes:
            cs.cancel()
        self._cancel_scopes.clear()

    async def _loop_read(self) -> None:
        socket = self._client.socket()
        cs = anyio.CancelScope()
        self._cancel_scopes.add(cs)
        with cs:
            while True:
                await anyio.wait_socket_readable(socket)  # type: ignore[arg-type]
                self._client.loop_read()

    async def _loop_write(self) -> None:
        socket = self._client.socket()
        cs = anyio.CancelScope()
        self._cancel_scopes.add(cs)
        with cs:
            while True:
                await self._event_write.wait()
                await anyio.wait_socket_writable(socket)  # type: ignore[arg-type]
                self._client.loop_write()

    async def _loop_misc(self) -> None:
        cs = anyio.CancelScope()
        self._cancel_scopes.add(cs)
        with cs:
            while self._client.loop_misc() == mqtt.MQTT_ERR_SUCCESS:
                await anyio.sleep(1)

    async def __aenter__(self) -> "Client":
        """Connect to the broker."""
        await self._connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Disconnect from the broker."""
        # If we got here due to an exception, we want said exception to
        # propagate. Therefore (in this specific case), we suppress any
        # exception that _disconnect may raise.
        # If we got here due to a normal exit (no exceptions) then we
        # let _disconnect raise if it wants to.
        suppressed_exceptions = tuple() if exc_type is None else (Exception,)
        with suppress(*suppressed_exceptions):
            await self._disconnect()


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


class Promise(Generic[T], Awaitable[T]):
    def __init__(self) -> None:
        self._exception: Exception | None = None
        self._event = anyio.Event()

    def done(self) -> bool:
        return hasattr(self, "_result") or self._exception is not None

    def set_result(self, result: T) -> None:
        if self.done():
            raise RuntimeError("Promise already fulfilled with result")
        self._result = result
        self._event.set()

    def set_exception(self, exception: Exception) -> None:
        if self.done():
            raise RuntimeError("Promise already fulfilled with exception")
        self._exception = exception
        self._event.set()

    async def wait(self) -> None:
        await self._event.wait()

    async def get(self) -> T:
        await self.wait()
        assert self.done()
        if self._exception is not None:
            raise self._exception
        return self._result

    def __await__(self) -> Generator[Any, None, T]:
        return self.get().__await__()
