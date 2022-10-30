<h1 align="center">Idiomatic asyncio MQTT Client 🙌</h1>
<p align="center">
    <a href="https://github.com/sbtinstruments/asyncio-mqtt/blob/main/LICENSE"><img alt="License: BSD-3-Clause" src="https://img.shields.io/github/license/sbtinstruments/asyncio-mqtt"></a>
    <a href="https://pypi.org/project/asyncio-mqtt"><img alt="PyPI version" src="https://img.shields.io/pypi/v/asyncio-mqtt"></a>
    <a href="https://pypi.org/project/asyncio-mqtt"><img alt="Supported Python versions" src="https://img.shields.io/pypi/pyversions/asyncio-mqtt.svg"></a>
    <a href="https://pypi.org/project/asyncio-mqtt"><img alt="PyPI downloads" src="https://img.shields.io/pypi/dm/asyncio-mqtt"></a>
    <a href="https://github.com/sbtinstruments/asyncio-mqtt/actions/workflows/test.yml"><img alt="Coverage" src="https://github.com/sbtinstruments/asyncio-mqtt/actions/workflows/test.yml/badge.svg"></a>
    <a href="https://codecov.io/gh/sbtinstruments/asyncio-mqtt"><img alt="Coverage" src="https://img.shields.io/codecov/c/github/sbtinstruments/asyncio-mqtt"></a>
    <a href="https://results.pre-commit.ci/latest/github/sbtinstruments/asyncio-mqtt/master"><img alt="pre-commit.ci status" src="https://results.pre-commit.ci/badge/github/sbtinstruments/asyncio-mqtt/master.svg"></a>
    <a href="https://github.com/sbtinstruments/asyncio-mqtt"><img alt="Typing: strict" src="https://img.shields.io/badge/typing-strict-green.svg"></a>
    <a href="https://github.com/sbtinstruments/asyncio-mqtt"><img alt="Code Style: Black" src="https://img.shields.io/badge/code%20style-black-black"></a>
</p>

Write code like this:

**Subscriber**

```python
async with Client("test.mosquitto.org") as client:
    async with client.unfiltered_messages() as messages:
        await client.subscribe("measurements/#")
        async for message in messages:
            print(message.payload)
```

**Publisher**

```python
async with Client("test.mosquitto.org") as client:
    await client.publish("measurements/humidity", payload=0.38)
```

_asyncio-mqtt_ combines the stability of the time-proven [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) library with a modern, asyncio-based interface.

- No more callbacks! 👍
- No more return codes (welcome to the `MqttError`)
- Graceful disconnection (forget about `on_unsubscribe`, `on_disconnect`, etc.)
- Compatible with `async` code
- Fully type-hinted
- Did we mention no more callbacks?

The whole thing is less than [700 lines of code](asyncio-mqtt/client.py).

## Contents 🔍

- [Installation](#installation-)
  - [Note for Windows users](#note-for-windows-users)
- [Advanced usage](#advanced-usage-)
  - [Configuring the client](#configuring-the-client)
  - [Reconnecting](#reconnecting)
  - [Sharing the connection](#sharing-the-connection)
    - [Side by side with web frameworks](#side-by-side-with-web-frameworks)
    - [Why can't I `connect`/`disconnect` manually?](#why-cant-i-connectdisconnect-manually)
  - [Listening without blocking](#listening-without-blocking)
  - [Topic filters](#topic-filters)
  - [TLS](#tls)
  - [Proxying](#proxying)
- [License](#license-)
- [Versioning](#versioning-)
- [Changelog](#changelog-)
- [Related projects](#related-projects-)

## Installation 📚

_asyncio-mqtt_ can be installed via `pip install asyncio-mqtt`. It requires Python 3.7+ to run. The only dependency is [_paho-mqtt_](https://github.com/eclipse/paho.mqtt.python).

If you can't wait for the latest version and want to install directly from GitHub, use:

`pip install git+https://github.com/sbtinstruments/asyncio-mqtt`

### Note for Windows users

Since Python 3.8, the default asyncio event loop is the `ProactorEventLoop`. Said loop [doesn't support the `add_reader` method](https://docs.python.org/3/library/asyncio-platforms.html#windows) that is required by _asyncio-mqtt_. Please switch to an event loop that supports the `add_reader` method such as the built-in `SelectorEventLoop`:

```python
# Change to the "Selector" event loop
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# Run your async application as usual
asyncio.run(main())
```

## Advanced usage ⚡

Let's make the example from before more interesting:

### Configuring the client

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
)
```

### Reconnecting

You can reconnect when the connection to the broker is lost by wrapping your code in a `try/except`-block and listening for `MqttError`s.

```python
import asyncio
import asyncio_mqtt as aiomqtt


async def main():
    reconnect_interval = 5  # In seconds
    while True:
        try:
            async with aiomqtt.Client("test.mosquitto.org") as client:
                async with client.filtered_messages('/measurements/humidity') as messages:
                    await client.subscribe("measurements/#")
                    async for message in messages:
                        print(message.payload.decode())
        except aiomqtt.MqttError as error:
            print(f'Error "{error}". Reconnecting in {reconnect_interval} seconds.')
            await asyncio.sleep(reconnect_interval)



asyncio.run(main())
```

### Topic filters

Let's take the example from the beginning again, but this time with messages in both `measurements/humidity` and `measurements/temperature`. You want to receive both types of measurements but handle them differently. _asyncio-mqtt_ has topic filters to make this easy:

```python
import asyncio
import asyncio_mqtt as aiomqtt
import contextlib


async def print_messages(messages, template):
    async for message in messages:
        print(template.format(message.payload))


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
    # We 💛 context managers. Let's create a stack to help us manage them.
    async with contextlib.AsyncExitStack() as stack:
        # Keep track of the asyncio tasks that we create, so that
        # we can cancel them on exit
        tasks = set()
        stack.push_async_callback(cancel_tasks, tasks)

        # Connect to MQTT broker
        client = aiomqtt.Client("test.mosquitto.org")
        await stack.enter_async_context(client)

        # You can create any number of topic filters
        topic_filters = (
            "measurements/humidity",
            "measurements/temperature"
            # 👉 Try to add more complex filters!
        )

        for topic_filter in topic_filters:
            # Print all messages that match the filter
            manager = client.filtered_messages(topic_filter)
            messages = await stack.enter_async_context(manager)
            template = f'[topic_filter="{topic_filter}"] {{}}'
            task = asyncio.create_task(print_messages(messages, template))
            tasks.add(task)

        # Handle messages that don't match a filter
        messages = await stack.enter_async_context(client.unfiltered_messages())
        task = asyncio.create_task(print_messages(messages, "[unfiltered] {}"))
        tasks.add(task)

        # Subscribe to topic(s)
        # 🤔 Note that we subscribe *after* starting the message
        # loggers. Otherwise, we may miss retained messages.
        await client.subscribe("measurements/#")

        # Wait for everything to complete (or fail due to, e.g., network errors)
        await asyncio.gather(*tasks)


asyncio.run(main())
```

### Sharing the connection

In many cases, you'll want to send and receive messages in different locations in your code. You could create a new client each time, but

1. this is not very performant, and
2. you'll use a lot more network bandwidth.

You can share the connection by passing the `Client` instance to all functions that need it:

```python
import asyncio
import asyncio_mqtt as aiomqtt


async def publish_humidity(client):
    await client.publish("measurements/humidity", payload=0.38)


async def publish_temperature(client):
    await client.publish("measurements/temperature", payload=28.3)


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        await publish_humidity(client)
        await publish_temperature(client)


asyncio.run(main())
```

#### Side by side with web frameworks

Most web frameworks take control over the "main" function, which makes it difficult to figure out where to create and connect the `Client` and how to share this connection.

Some frameworks like [Starlette](https://github.com/encode/starlette) directly support lifespan context managers, with which you can safely set up a global client instance that you can than pass to functions that need it, just like before:

```python
import asyncio
import asyncio_mqtt as aiomqtt
import starlette.applications
import contextlib


client = None


@contextlib.asynccontextmanager
async def lifespan(app):
    global client
    async with aiomqtt.Client("test.mosquitto.org") as c:
        client = c
        yield


app = starlette.applications.Starlette(
    routes=[],
    lifespan=lifespan,
)
```

FastAPI (which is built upon Starlette) doesn't expose that API yet, but there are [multiple](https://github.com/tiangolo/fastapi/pull/5503) [open PRs](https://github.com/tiangolo/fastapi/pull/2944) to add it. In the meantime, you can work around it via FastAPI's dependency injection.

#### Why can't I `connect`/`disconnect` manually?

Managing a connection by calling `connect` and `disconnect` directly is a bit tricky. For example, when you're disconnecting the client, you'd have to make sure that there's no other task that still relies on the connection. There are many similar situations where something can easily go wrong.

Context managers take care of all connection and disconnection logic for you, in a way that makes it very difficult to shoot yourself in the foot. They are a lot easier and less error-prone to use than `connect`/`disconnect`.

Supporting both context managers and manual `connect`/`disconnect` would add a lot of complexity to _asyncio-mqtt_. To keep maintainer burden manageable, we (the _asyncio-mqtt_ maintainers) decided to focus only on the better option: context managers.

### Listening without blocking

If you run the basic example for subscribing and listening for messages, you'll notice that the program doesn't finish until you stop it. If you want to run other code after starting your listener (e.g. handling HTTP requests in a web framework) you don't want the execution to block.

You can use asyncio's `create_task` for this. The concept is similar to starting a new thread without `join`ing it in a multithreaded application.

```python
import asyncio
import asyncio_mqtt as aiomqtt


async def listen():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        async with client.unfiltered_messages() as messages:
            await client.subscribe("measurements/#")
            async for message in messages:
                print(message.payload)


async def main():
    # Wait for messages in (unawaited) asyncio task
    loop = asyncio.get_event_loop()
    task = loop.create_task(listen())
    # This will still run!
    print("Magic!")
    # If you don't await the task here the program will simply finish.
    # However, if you're using an async web framework you usually don't have to await
    # the task, as the framework runs in an endless loop.
    await task


asyncio.run(main())
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
        await client.publish("measurements/humidity", payload=0.38)


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
        await client.publish("measurements/humidity", payload=0.38)


asyncio.run(main())
```

## License 📋

<a href="https://github.com/sbtinstruments/asyncio-mqtt/blob/main/LICENSE"><img alt="License: BSD-3-Clause" src="https://img.shields.io/github/license/sbtinstruments/asyncio-mqtt"></a>

Note that the underlying paho-mqtt library is dual-licensed. One of the licenses is the so-called [Eclipse Distribution License v1.0](https://www.eclipse.org/org/documents/edl-v10.php). It is almost word-for-word identical to the [BSD 3-clause License](https://opensource.org/licenses/BSD-3-Clause). The only differences are:

- One use of "COPYRIGHT OWNER" (EDL) instead of "COPYRIGHT HOLDER" (BSD)
- One use of "Eclipse Foundation, Inc." (EDL) instead of "copyright holder" (BSD)

## Versioning 🎯

<a href="https://pypi.org/project/asyncio-mqtt"><img alt="PyPI" src="https://img.shields.io/pypi/v/asyncio-mqtt"></a>

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Expect API changes until we reach version `1.0.0`. After `1.0.0`, breaking changes will only occur in major release (e.g., `2.0.0`, `3.0.0`, etc.).

## Changelog 🚧

Please refer to the [CHANGELOG](https://github.com/sbtinstruments/asyncio-mqtt/blob/master/CHANGELOG.md) document. It adheres to the principles of [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## Related projects 🌟

Is _asyncio-mqtt_ not what you are looking for? Try another client:

- [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) — Own protocol implementation. Synchronous.<br>![GitHub stars](https://img.shields.io/github/stars/eclipse/paho.mqtt.python) ![license](https://img.shields.io/github/license/eclipse/paho.mqtt.python)
- [gmqtt](https://github.com/wialon/gmqtt) — Own protocol implementation. Asynchronous.<br>![GitHub stars](https://img.shields.io/github/stars/wialon/gmqtt) ![license](https://img.shields.io/github/license/wialon/gmqtt)
- [fastapi-mqtt](https://github.com/sabuhish/fastapi-mqtt) — Asynchronous wrapper around gmqtt. Simplifies integration in your FastAPI application.<br>![GitHub stars](https://img.shields.io/github/stars/sabuhish/fastapi-mqtt) ![license](https://img.shields.io/github/license/sabuhish/fastapi-mqtt)
- [amqtt](https://github.com/Yakifo/amqtt) — Own protocol implementation. Asynchronous. Includes a broker.<br>![GitHub stars](https://img.shields.io/github/stars/Yakifo/amqtt) ![license](https://img.shields.io/github/license/Yakifo/amqtt)
- [mqttools](https://github.com/eerimoq/mqttools) — Own protocol implementation. Asynchronous.<br>![GitHub stars](https://img.shields.io/github/stars/eerimoq/mqttools) ![license](https://img.shields.io/github/license/eerimoq/mqttools)
- [trio-paho-mqtt](https://github.com/bkanuka/trio-paho-mqtt) — Asynchronous wrapper around paho-mqtt (similar to _asyncio-mqtt_). Based on trio instead of asyncio.<br>![GitHub stars](https://img.shields.io/github/stars/bkanuka/trio-paho-mqtt) ![license](https://img.shields.io/github/license/bkanuka/trio-paho-mqtt)
