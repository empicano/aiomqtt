![license](https://img.shields.io/github/license/sbtinstruments/asyncio-mqtt)
![semver](https://img.shields.io/github/v/tag/sbtinstruments/asyncio-mqtt?sort=semver)
[![PyPI](https://img.shields.io/pypi/v/asyncio-mqtt)](https://pypi.org/project/asyncio-mqtt/)

# Idiomatic asyncio MQTT client 🙌

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

asyncio-mqtt combines the stability of the time-proven [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) library with a modern, asyncio-based interface.

- No more callbacks! 👍
- No more return codes (welcome to the `MqttError`)
- Graceful disconnection (forget about `on_unsubscribe`, `on_disconnect`, etc.)
- Compatible with `async` code
- Fully type-hinted
- Did we mention no more callbacks?

The whole thing is less than [700 lines of code](asyncio-mqtt/client.py).

## Contents

- [Installation](#installation-📚)
- [Advanced usage](#advanced-usage-⚡)
  - [Configuring the client](#configuring-the-client)
  - [Reconnecting](#reconnecting)
  - [Sharing the connection](#sharing-the-connection)
  - [Topic filters](#topic-filters)
  - [TLS](#tls)
  - [Proxying](#proxying)
- [Related projects](#related-projects)
- [Requirements](#requirements)
- [Note for Windows users](#note-for-windows-users)
- [Changelog](#changelog)
- [Versioning](#versioning)
- [License](#license)

## Installation 📚

`pip install asyncio-mqtt`

## Advanced usage ⚡

Let's make the example from before more interesting:

### Configuring the client

You can configure quite a few things when initializing the client. These are all the possible parameters together with their default values. See [paho-mqtt's documentation](https://github.com/eclipse/paho.mqtt.python) for more information about the individual parameters.

```python
import asyncio_mqtt as aiomqtt
import paho.mqtt as mqtt

aiomqtt.Client(
    hostname="test.mosquitto.org",  # the only non-optional parameter
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
    reconnect_interval = 5  # in seconds
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

Let's take the example from the beginning again, but this time with messages in both `measurements/humidity` and `measurements/temperature`. You want to receive both types of measurements, but handle them differently. asyncio-mqtt has topic filters to make this easy:

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
    # we 💛 context managers. Let's create a stack to help us manage them.
    async with contextlib.AsyncExitStack() as stack:
        # keep track of the asyncio tasks that we create, so that
        # we can cancel them on exit
        tasks = set()
        stack.push_async_callback(cancel_tasks, tasks)

        # connect to MQTT broker
        client = aiomqtt.Client("test.mosquitto.org")
        await stack.enter_async_context(client)

        # you can create any number of topic filters
        topic_filters = (
            "measurements/humidity",
            "measurements/temperature"
            # 👉 try to add more complex filters!
        )

        for topic_filter in topic_filters:
            # print all messages that match the filter
            manager = client.filtered_messages(topic_filter)
            messages = await stack.enter_async_context(manager)
            template = f'[topic_filter="{topic_filter}"] {{}}'
            task = asyncio.create_task(log_messages(messages, template))
            tasks.add(task)

        # handle messages that don't match a filter
        messages = await stack.enter_async_context(client.unfiltered_messages())
        task = asyncio.create_task(log_messages(messages, "[unfiltered] {}"))
        tasks.add(task)

        # subscribe to topic(s)
        # 🤔 note that we subscribe *after* starting the message
        # loggers. Otherwise, we may miss retained messages.
        await client.subscribe("measurements/#")

        # wait for everything to complete (or fail due to, e.g., network errors)
        await asyncio.gather(*tasks)


asyncio.run(main())
```

### Sharing the connection

In many cases you'll want to send and receive messages in different locations in your code. You could create a new client each time, but firstly this not very performant, and secondly you'll use a lot more network bandwith.

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

**Caveats:**

Most web frameworks take control over the "main" function, which makes it difficult to figure out where to create and connect to the `Client`. With e.g. FastAPI you can share a connection via its dependency injection.

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

## Alternative asyncio-based MQTT clients

Is asyncio-mqtt not what you are looking for? Try another client:

- [hbmqtt](https://github.com/beerfactory/hbmqtt) - Own protocol implementation. Includes a broker.
  ![GitHub stars](https://img.shields.io/github/stars/beerfactory/hbmqtt)
  ![license](https://img.shields.io/github/license/beerfactory/hbmqtt)
- [gmqtt](https://github.com/wialon/gmqtt) - Own protocol implementation. No dependencies.
  ![GitHub stars](https://img.shields.io/github/stars/wialon/gmqtt)
  ![license](https://img.shields.io/github/license/wialon/gmqtt)
- [aiomqtt](https://github.com/mossblaser/aiomqtt) - Wrapper around paho-mqtt.
  ![GitHub stars](https://img.shields.io/github/stars/mossblaser/aiomqtt)
  ![license](https://img.shields.io/github/license/mossblaser/aiomqtt)
- [mqttools](https://github.com/eerimoq/mqttools) - Own protocol implementation. No dependencies.
  ![GitHub stars](https://img.shields.io/github/stars/eerimoq/mqttools)
  ![license](https://img.shields.io/github/license/eerimoq/mqttools)
- [aio-mqtt](https://github.com/NotJustAToy/aio-mqtt) - Own protocol implementation. No dependencies.
  ![GitHub stars](https://img.shields.io/github/stars/NotJustAToy/aio-mqtt)
  ![license](https://img.shields.io/github/license/NotJustAToy/aio-mqtt)

This is not an exhaustive list.

### Honorable mentions

- [trio-paho-mqtt](https://github.com/bkanuka/trio-paho-mqtt) - Trio-based. Wrapper around paho-mqtt.
  ![GitHub stars](https://img.shields.io/github/stars/bkanuka/trio-paho-mqtt)
  ![license](https://img.shields.io/github/license/bkanuka/trio-paho-mqtt)

## Requirements

Python 3.7 or later.

There is only a single dependency:

- [paho-mqtt](https://github.com/eclipse/paho.mqtt.python)
  ![GitHub stars](https://img.shields.io/github/stars/eclipse/paho.mqtt.python) ![license](https://img.shields.io/github/license/eclipse/paho.mqtt.python)

## Note for Windows users

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
