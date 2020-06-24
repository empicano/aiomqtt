# SPDX-License-Identifier: BSD-3-Clause
import asyncio
import logging
import socket
from contextlib import contextmanager, suppress
try:
    from contextlib import asynccontextmanager
except ImportError:
    from async_generator import asynccontextmanager
import paho.mqtt.client as mqtt
from .error import MqttError, MqttCodeError


MQTT_LOGGER = logging.getLogger('mqtt')
MQTT_LOGGER.setLevel(logging.WARNING)


class Client:
    def __init__(self, hostname, port=1883, *, username=None, password=None,
                 logger=None, client_id=None, tls_context=None):
        self._hostname = hostname
        self._port = port
        self._loop = asyncio.get_event_loop()
        self._connected = asyncio.Future()
        self._disconnected = asyncio.Future()
        self._pending_calls = {}  # Pending subscribe, unsubscribe, and publish calls
        self._pending_calls_threshold = 10
        self._misc_task = None

        self._client = mqtt.Client(client_id=client_id)
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
        
        if username is not None and password is not None:
            self._client.username_pw_set(username=username, password=password)

        if tls_context is not None:
            self._client.tls_set_context(tls_context)

    async def connect(self, *, timeout=10):
        try:
            self._client.connect(self._hostname, self._port, 60)
        except ConnectionError as error:
            raise MqttError(str(error))
        await self._wait_for(self._connected, timeout=timeout)
        self._client.socket().setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2048)

    async def disconnect(self, *, timeout=10):
        rc = self._client.disconnect()
        # Early out on error
        if rc != mqtt.MQTT_ERR_SUCCESS:
            raise MqttCodeError(rc, "Could not disconnect")
        # Wait for acknowledgement
        await self._wait_for(self._disconnected, timeout=timeout)

    async def force_disconnect(self):
        self._disconnected.set_result(None)

    async def subscribe(self, *args, timeout=10, **kwargs):
        result, mid = self._client.subscribe(*args, **kwargs)
        # Early out on error
        if result != mqtt.MQTT_ERR_SUCCESS:
            raise MqttCodeError(result, 'Could not subscribe to topic')
        # Create future for when the on_subscribe callback is called
        cb_result = asyncio.Future()
        with self._pending_call(mid, cb_result):
            # Wait for cb_result
            return await self._wait_for(cb_result, timeout=timeout)

    async def unsubscribe(self, *args, timeout=10):
        result, mid = self._client.unsubscribe(*args)
        # Early out on error
        if result != mqtt.MQTT_ERR_SUCCESS:
            raise MqttCodeError(result, 'Could not unsubscribe from topic')
        # Create event for when the on_unsubscribe callback is called
        confirmation = asyncio.Event()
        with self._pending_call(mid, confirmation):
            # Wait for confirmation
            await self._wait_for(confirmation.wait(), timeout=timeout)

    async def publish(self, *args, timeout=10, **kwargs):
        info = self._client.publish(*args, **kwargs)  # [2]
        # Early out on error
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise MqttCodeError(info.rc, 'Could not publish message')
        # Early out on immediate success
        if info.is_published():
            return
        # Create event for when the on_publish callback is called
        confirmation = asyncio.Event()
        with self._pending_call(info.mid, confirmation):
            # Wait for confirmation
            await self._wait_for(confirmation.wait(), timeout=timeout)

    @asynccontextmanager
    async def filtered_messages(self, topic_filter, *, queue_maxsize=0):
        """Return async generator of messages that match the given filter.

        Use queue_maxsize to restrict the queue size. If the queue is full,
        incoming messages will be discarded (and a warning is logged).
        If queue_maxsize is less than or equal to zero, the queue size is infinite.
        
        Example use:
            async with client.filtered_messages('floors/+/humidity') as messages:
                async for message in messages:
                    print(f'Humidity reading: {message.payload.decode()}')
        """
        cb, generator = self._cb_and_generator(log_context=f'topic_filter="{topic_filter}"',
                                               queue_maxsize=queue_maxsize)
        try:
            self._client.message_callback_add(topic_filter, cb)
            # Back to the caller (run whatever is inside the with statement)
            yield generator
        finally:
            # We are exitting the with statement. Remove the topic filter.
            self._client.message_callback_remove(topic_filter)

    @asynccontextmanager
    async def unfiltered_messages(self, *, queue_maxsize=0):
        """Return async generator of all messages that are not caught in filters."""
        # Early out
        if self._client.on_message is not None:
            # TODO: This restriction can easily be removed.
            raise RuntimeError('Only a single unfiltered_messages generator can be used at a time.')
        cb, generator = self._cb_and_generator(log_context='unfiltered',
                                               queue_maxsize=queue_maxsize)
        try:
            self._client.on_message = cb
            # Back to the caller (run whatever is inside the with statement)
            yield generator
        finally:
            # We are exitting the with statement. Unset the callback.
            self._client.on_message = None

    def _cb_and_generator(self, *, log_context, queue_maxsize=0):
        # Queue to hold the incoming messages
        messages = asyncio.Queue(maxsize=queue_maxsize)
        # Callback for the underlying API
        def _put_in_queue(client, userdata, msg):
            try:
                messages.put_nowait(msg)
            except asyncio.QueueFull:
                MQTT_LOGGER.warning(f'[{log_context}] Message queue is full. Discarding message.')
        # The generator that we give to the caller
        async def _message_generator():
            # Forward all messages from the queue
            while True:
                # Wait until we either:
                #  1. Receive a message
                #  2. Disconnect from the broker
                get = asyncio.create_task(messages.get())
                done, _ = await asyncio.wait(
                    (get, self._disconnected),
                    return_when=asyncio.FIRST_COMPLETED
                )
                if get in done:
                    # We received a message. Return the result.
                    yield get.result()
                else:
                    # We got disconnected from the broker. Cancel the "get" task.
                    get.cancel()
                    # Await the "_disconnected" future to propagate the cause.
                    # If an exception is the cause of the disconnect, it will be raised.
                    await self._disconnected
                    # Exception or not, the generator stops here.
                    return
        return _put_in_queue, _message_generator()

    async def _wait_for(self, *args, **kwargs):
        try:
            return await asyncio.wait_for(*args, **kwargs)
        except asyncio.TimeoutError:
            raise MqttError('Operation timed out')

    @contextmanager
    def _pending_call(self, mid, value):
        if mid in self._pending_calls:
            raise RuntimeError(f'There already exists a pending call for message ID "{mid}"')
        self._pending_calls[mid] = value  # [1]
        try:
            # Log a warning if there is a concerning number of pending calls
            pending = len(self._pending_calls)
            if pending > self._pending_calls_threshold:
                MQTT_LOGGER.warning(f'There are {pending} pending publish calls.')
            # Back to the caller (run whatever is inside the with statement)
            yield
        finally:
            # The normal procedure is:
            #  * We add the item at [1]
            #  * A callback will remove the item
            #
            # However, if the callback doesn't get called (e.g., due to a
            # network error) we still need to remove the item from the dict.
            self._pending_calls.pop(mid, None)
                
    def _on_connect(self, client, userdata, flags, rc):
        if rc == mqtt.CONNACK_ACCEPTED:
            self._connected.set_result(rc)
        else:
            self._connected.set_exception(MqttCodeError(rc, 'Could not connect'))

    def _on_disconnect(self, client, userdata, rc):
        if rc == mqtt.MQTT_ERR_SUCCESS:
            self._disconnected.set_result(rc)
        else:
            self._disconnected.set_exception(MqttCodeError(rc, 'Unexpected disconnect'))

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        try:
            self._pending_calls.pop(mid).set_result(granted_qos)
        except KeyError:
            MQTT_LOGGER.error(f'Unexpected message ID "{mid}" in on_subscribe callback')

    def _on_unsubscribe(self, client, userdata, mid):
        try:
            self._pending_calls.pop(mid).set()
        except KeyError:
            MQTT_LOGGER.error(f'Unexpected message ID "{mid}" in on_unsubscribe callback')

    def _on_publish(self, client, userdata, mid):
        try:
            self._pending_calls.pop(mid).set()
        except KeyError:
            # Do nothing since [2] may call on_publish before it even returns.
            # That is, the message may already be published before we even get a
            # chance to set up the 'pending_call' logic.
            pass

    def _on_socket_open(self, client, userdata, sock):
        def cb():
            client.loop_read()
        self._loop.add_reader(sock, cb)
        self._misc_task = self._loop.create_task(self._misc_loop())

    def _on_socket_close(self, client, userdata, sock):
        self._loop.remove_reader(sock)
        with suppress(asyncio.CancelledError):
            self._misc_task.cancel()

    def _on_socket_register_write(self, client, userdata, sock):
        def cb():
            client.loop_write()
        self._loop.add_writer(sock, cb)

    def _on_socket_unregister_write(self, client, userdata, sock):
        self._loop.remove_writer(sock)

    async def _misc_loop(self):
        while self._client.loop_misc() == mqtt.MQTT_ERR_SUCCESS:
            await asyncio.sleep(1)

    async def __aenter__(self):
        """Connect to the broker."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Disconnect from the broker."""
        # Early out if already disconnected
        if self._disconnected.done():
            return
        # Try to gracefully disconnect from the broker
        try:
            await self.disconnect()
        except MqttError as error:
            # We tried to be graceful. Now there is no mercy.
            MQTT_LOGGER.warning(f'Could not gracefully disconnect due to "{error}". Forcing disconnection.')
            await self.force_disconnect()
