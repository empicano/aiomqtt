![license](https://img.shields.io/github/license/sbtinstruments/asyncio-mqtt)
![semver](https://img.shields.io/github/v/tag/sbtinstruments/asyncio-mqtt?sort=semver)
[![PyPI](https://img.shields.io/pypi/v/asyncio-mqtt)](https://pypi.org/project/asyncio-mqtt/)

# MQTT client with idiomatic asyncio interface 🙌

Write code like this:

##### Subscriber

```python
async with Client("test.mosquitto.org") as client:
    async with client.filtered_messages("floors/+/humidity") as messages:
        await client.subscribe("floors/#")
        async for message in messages:
            print(message.payload.decode())
```

##### Publisher

```python
async with Client("test.mosquitto.org") as client:
    message = "10%"
    await client.publish(
            "floors/bed_room/humidity",
             payload=message.encode()
          )
```

asyncio-mqtt combines the stability of the time-proven [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) library with a modern, asyncio-based interface.

- No more callbacks! 👍
- No more return codes (welcome to the `MqttError`)
- Graceful disconnection (forget about `on_unsubscribe`, `on_disconnect`, etc.)
- Compatible with `async` code
- Fully type-hinted
- Did we mention no more callbacks?

The whole thing is less than [700 lines of code](https://github.com/sbtinstruments/asyncio-mqtt/blob/master/asyncio_mqtt/client.py).

## Installation 📚

`pip install asyncio-mqtt`

## Advanced use ⚡

Let's make the example from before more interesting:

```python
import asyncio
from contextlib import AsyncExitStack, asynccontextmanager
from random import randrange
from asyncio_mqtt import Client, MqttError


async def advanced_example():
    # We 💛 context managers. Let's create a stack to help
    # us manage them.
    async with AsyncExitStack() as stack:
        # Keep track of the asyncio tasks that we create, so that
        # we can cancel them on exit
        tasks = set()
        stack.push_async_callback(cancel_tasks, tasks)

        # Connect to the MQTT broker
        client = Client("test.mosquitto.org")
        await stack.enter_async_context(client)

        # You can create any number of topic filters
        topic_filters = (
            "floors/+/humidity",
            "floors/rooftop/#"
            # 👉 Try to add more filters!
        )
        for topic_filter in topic_filters:
            # Log all messages that matches the filter
            manager = client.filtered_messages(topic_filter)
            messages = await stack.enter_async_context(manager)
            template = f'[topic_filter="{topic_filter}"] {{}}'
            task = asyncio.create_task(log_messages(messages, template))
            tasks.add(task)

        # Messages that doesn't match a filter will get logged here
        messages = await stack.enter_async_context(client.unfiltered_messages())
        task = asyncio.create_task(log_messages(messages, "[unfiltered] {}"))
        tasks.add(task)

        # Subscribe to topic(s)
        # 🤔 Note that we subscribe *after* starting the message
        # loggers. Otherwise, we may miss retained messages.
        await client.subscribe("floors/#")

        # Publish a random value to each of these topics
        topics = (
            "floors/basement/humidity",
            "floors/rooftop/humidity",
            "floors/rooftop/illuminance",
            # 👉 Try to add more topics!
        )
        task = asyncio.create_task(post_to_topics(client, topics))
        tasks.add(task)

        # Wait for everything to complete (or fail due to, e.g., network
        # errors)
        await asyncio.gather(*tasks)

async def post_to_topics(client, topics):
    while True:
        for topic in topics:
            message = randrange(100)
            print(f'[topic="{topic}"] Publishing message={message}')
            await client.publish(topic, message, qos=1)
            await asyncio.sleep(2)

async def log_messages(messages, template):
    async for message in messages:
        # 🤔 Note that we assume that the message paylod is an
        # UTF8-encoded string (hence the `bytes.decode` call).
        print(template.format(message.payload.decode()))

async def cancel_tasks(tasks):
    for task in tasks:
        if task.done():
            continue
        try:
            task.cancel()
            await task
        except asyncio.CancelledError:
            pass

async def main():
    # Run the advanced_example indefinitely. Reconnect automatically
    # if the connection is lost.
    reconnect_interval = 3  # [seconds]
    while True:
        try:
            await advanced_example()
        except MqttError as error:
            print(f'Error "{error}". Reconnecting in {reconnect_interval} seconds.')
        finally:
            await asyncio.sleep(reconnect_interval)


asyncio.run(main())
```

## TLS configuration for MQTT client

asyncio-mqtt also exposes paho-mqtt's `tls_set` functionality for the users. The following minimal example explains how to enable SSL/TLS support for asyncio-mqtt client

```python
import ssl
from asyncio_mqtt import Client, TLSParameters, ProtocolVersion

"""
ca_certs          : a string path to the Certificate Authority certificate files
                    that are to be treated as trusted by this client
certfile & keyfile: strings pointing to the PEM encoded client certificate and
                    private keys respectively
cert_reqs         : allows the certificate requirements that the client imposes on
                    the broker to be changed. By default this is ssl.CERT_REQUIRED
tls_version       : allows the version of the SSL/TLS protocol used to be specified.
                    By default TLS v1 is used
ciphers           : string specifying which encryption ciphers are allowable for this
                    connection, or None to use the defaults
keyfile_password  : if either certfile or keyfile is encrypted and needs a password to
                    decrypt it, then this can be passed using the keyfile_password
                    argument. If you do not provide keyfile_password, the password will
                    be requested to be typed in at a terminal window
"""
tls_params = TLSParameters(
    ca_certs="/path/to/certificates",
    certfile="/path/to/certfile",
    keyfile="/path/to/keyfile",
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLSv2,
    ciphers=None,
    keyfile_password=None,
)

async with Client(
    "test.mosquitto.org",
    username="username",
    password="password",
    protocol=ProtocolVersion.V31,
    tls_params=tls_params,
) as client:
    async with client.filtered_messages("floors/+/humidity") as messages:
        # subscribe is done afterwards so that we just start receiving messages
        # from this point on
        await client.subscribe("floors/#")
        async for message in messages:
            print(message.topic)
            print(json.loads(message.payload))
```

## Proxy settings for asyncio-mqtt client

asyncio-mqtt allows the user to configure proxing of MQTT connection and enables the support for SOCKS or HTTP proxies. asyncio-mqtt uses the paho-mqtt `proxy_set` functionality to allow setting up the proxy. One thing to note here is that setting up a proxy is an extra feature (even in paho-mqtt) that requires the `PySocks` dependency.

The following minimal example depicts how to configure proxing of the MQTT connection

```python
import socks
from asyncio_mqtt import Client, ProxySettings

proxy_params = ProxySettings(
    proxy_type=socks.HTTP,
    proxy_addr="example.com",
    proxy_rdns=True,
    proxy_username="username",
    proxy_password="password",
)

async with Client(
    "test.mosquitto.org",
    username="username",
    password="password",
    protocol=ProtocolVersion.V31,
    procxy=proxy_params,
) as client:
    ...
    ...
```

## Related projects

Is asyncio-mqtt not what you are looking for? Try another client:

- [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) — Own protocol implementation. Synchronous.<br>![GitHub stars](https://img.shields.io/github/stars/eclipse/paho.mqtt.python) ![license](https://img.shields.io/github/license/eclipse/paho.mqtt.python)
- [gmqtt](https://github.com/wialon/gmqtt) — Own protocol implementation. Asynchronous.<br>![GitHub stars](https://img.shields.io/github/stars/wialon/gmqtt) ![license](https://img.shields.io/github/license/wialon/gmqtt)
- [fastapi-mqtt](https://github.com/sabuhish/fastapi-mqtt) — Asynchronous wrapper around gmqtt. Simplifies integration in your FastAPI application.<br>![GitHub stars](https://img.shields.io/github/stars/sabuhish/fastapi-mqtt) ![license](https://img.shields.io/github/license/sabuhish/fastapi-mqtt)
- [amqtt](https://github.com/Yakifo/amqtt) — Own protocol implementation. Asynchronous. Includes a broker.<br>![GitHub stars](https://img.shields.io/github/stars/Yakifo/amqtt) ![license](https://img.shields.io/github/license/Yakifo/amqtt)
- [mqttools](https://github.com/eerimoq/mqttools) — Own protocol implementation. Asynchronous.<br>![GitHub stars](https://img.shields.io/github/stars/eerimoq/mqttools) ![license](https://img.shields.io/github/license/eerimoq/mqttools)
- [trio-paho-mqtt](https://github.com/bkanuka/trio-paho-mqtt) — Asynchronous wrapper around paho-mqtt (similar to asyncio-mqtt). Based on trio instead of asyncio.<br>![GitHub stars](https://img.shields.io/github/stars/bkanuka/trio-paho-mqtt) ![license](https://img.shields.io/github/license/bkanuka/trio-paho-mqtt)

## Requirements

Python 3.7 or later. The only dependency is [paho-mqtt](https://github.com/eclipse/paho.mqtt.python).

## Note for Windows Users

Since Python 3.8, the default asyncio event loop is the `ProactorEventLoop`. Said loop [doesn't support the `add_reader` method](https://docs.python.org/3/library/asyncio-platforms.html#windows) that is required by asyncio-mqtt. To use asyncio-mqtt, please switch to an event loop that supports the `add_reader` method such as the built-in `SelectorEventLoop`. E.g:

```python
# Change to the "Selector" event loop
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# Run your async application as usual
asyncio.run(main())
```

## Changelog

Please refer to the [CHANGELOG](https://github.com/sbtinstruments/asyncio-mqtt/blob/master/CHANGELOG.md) document. It adheres to the principles of [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## Versioning

![semver](https://img.shields.io/github/v/tag/sbtinstruments/asyncio-mqtt?sort=semver)

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Expect API changes until we reach version `1.0.0`. After `1.0.0`, breaking changes will only occur in major release (e.g., `2.0.0`, `3.0.0`, etc.).

## License

![license](https://img.shields.io/github/license/sbtinstruments/asyncio-mqtt)

Note that the underlying paho-mqtt library is dual-licensed. One of the licenses is the so-called [Eclipse Distribution License v1.0](https://www.eclipse.org/org/documents/edl-v10.php). It is almost word-for-word identical to the [BSD 3-clause License](https://opensource.org/licenses/BSD-3-Clause). The only differences are:

- One use of "COPYRIGHT OWNER" (EDL) instead of "COPYRIGHT HOLDER" (BSD)
- One use of "Eclipse Foundation, Inc." (EDL) instead of "copyright holder" (BSD)
