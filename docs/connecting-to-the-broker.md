# Connecting to the broker

To publish messages and subscribe to topics, we need to connect to a broker. A minimal working example that publishes a message to the `temperature/outside` topic looks like this:

```python
import asyncio
import asyncio_mqtt as aiomqtt


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        await client.publish("temperature/outside", payload=28.4)


asyncio.run(main())
```

The connection to the broker is managed by the `Client` context manager. Context managers handle all connection and disconnection logic for you. asyncio-mqtt doesn't support manual calls to `connect` and `disconnect`.

```{tip}
The above example uses the public [mosquitto test broker](https://test.mosquitto.org/). You can connect to this broker without any credentials. Please use the mosquitto test broker in issues or discussions (if possible) to make it easier for others to run your code.
```

## The client in detail

You can configure quite a few things when initializing the client. These are all the possible parameters together with their default values. See [paho-mqtt's documentation](https://github.com/eclipse/paho.mqtt.python) for more information about the individual parameters.

```python
import asyncio_mqtt as aiomqtt
import paho.mqtt as mqtt


aiomqtt.Client(
    hostname="test.mosquitto.org",  # The only non-optional parameter
    port=1883,
    username=None,
    password=None,
    logger=None,
    client_id=None,
    tls_context=None,
    tls_params=None,
    proxy=None,
    protocol=None,
    will=None,
    clean_session=None,
    transport="tcp",
    timeout=None,
    keepalive=60,
    bind_address="",
    bind_port=0,
    clean_start=mqtt.client.MQTT_CLEAN_START_FIRST_ONLY,
    properties=None,
    message_retry_set=20,
    socket_options=(),
    max_concurrent_outgoing_calls=None,
    websocket_path=None,
    websocket_headers=None,
    max_inflight_messages=None,
    max_queued_messages=None,
)
```

### Persistent sessions

Connections to the MQTT broker can be persistent or non-persistent. Persistent sessions are kept alive when the client is offline. This means that the broker stores the client's subscriptions and queues any messages of [QoS 1 and 2](publishing-a-message.md#quality-of-service-qos) that the client misses or has not yet acknowledged. The broker will then retransmit the messages when the client reconnects.

To create a persistent session, set the `clean_session` parameter to `False` when initializing the client. For a non-persistent session, set `clean_session` to `True`.

```{note}
The amount of messages that can be queued is limited by the broker's memory. If a client with a persistent session does not come back online for a long time, the broker will eventually run out of memory and start discarding messages.
```

### TLS

You can configure TLS via the `TLSParameters` class. The parameters are directly passed through to paho-mqtt's `tls_set` function. See [paho-mqtt's documentation](https://github.com/eclipse/paho.mqtt.python) for more information about the individual parameters.

```python
import asyncio
import asyncio_mqtt as aiomqtt
import ssl


tls_params = aiomqtt.TLSParameters(
    ca_certs=None,
    certfile=None,
    keyfile=None,
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLS,
    ciphers=None,
)


async def main():
    async with aiomqtt.Client("test.mosquitto.org", tls_params=tls_params) as client:
        await client.publish("temperature/outside", payload=28.4)


asyncio.run(main())
```

### Proxying

You can configure proxying via the `ProxySettings` class. The parameters are directly passed through to paho-mqtt's `proxy_set` functionality. Both SOCKS and HTTP proxies are supported. Note that proxying is an extra feature (even in paho-mqtt) that requires the `PySocks` dependency. See [paho-mqtt's documentation](https://github.com/eclipse/paho.mqtt.python) for more information about the individual parameters.

```python
import asyncio
import asyncio_mqtt as aiomqtt
import socks


proxy_params = aiomqtt.ProxySettings(
    proxy_type=socks.HTTP,
    proxy_addr="www.example.com",
    proxy_rdns=True,
    proxy_username=None,
    proxy_password=None,
)

async def main():
    async with aiomqtt.Client("test.mosquitto.org", proxy=proxy_params) as client:
        await client.publish("temperature/outside", payload=28.4)


asyncio.run(main())
```

## Sharing the connection

In many cases, you'll want to send and receive messages in different locations in your code. You could create a new client each time, but:

1. this is not very performant, and
2. you'll use more network bandwidth.

You can share the connection by passing the `Client` instance to all functions that need it:

```python
import asyncio
import asyncio_mqtt as aiomqtt


async def publish_temperature(client):
    await client.publish("temperature/outside", payload=28.4)


async def publish_humidity(client):
    await client.publish("humidity/inside", payload=0.38)


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        await publish_temperature(client)
        await publish_humidity(client)


asyncio.run(main())
```
