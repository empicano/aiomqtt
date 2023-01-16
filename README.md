<h1 align="center">The idiomatic asyncio MQTT Client 🙌</h1>
<p align="center">
    <a href="https://github.com/sbtinstruments/asyncio-mqtt/blob/main/LICENSE"><img alt="License: BSD-3-Clause" src="https://img.shields.io/github/license/sbtinstruments/asyncio-mqtt"></a>
    <a href="https://pypi.org/project/asyncio-mqtt"><img alt="PyPI version" src="https://img.shields.io/pypi/v/asyncio-mqtt"></a>
    <a href="https://pypi.org/project/asyncio-mqtt"><img alt="Supported Python versions" src="https://img.shields.io/pypi/pyversions/asyncio-mqtt.svg"></a>
    <a href="https://pypi.org/project/asyncio-mqtt"><img alt="PyPI downloads" src="https://img.shields.io/pypi/dm/asyncio-mqtt"></a>
    <a href="https://github.com/sbtinstruments/asyncio-mqtt/actions/workflows/test.yml"><img alt="test suite" src="https://github.com/sbtinstruments/asyncio-mqtt/actions/workflows/test.yml/badge.svg"></a>
    <a href="https://github.com/sbtinstruments/asyncio-mqtt/actions/workflows/docs.yml"><img alt="docs" src="https://github.com/sbtinstruments/asyncio-mqtt/actions/workflows/docs.yml/badge.svg"></a>
    <a href="https://codecov.io/gh/sbtinstruments/asyncio-mqtt"><img alt="Coverage" src="https://img.shields.io/codecov/c/github/sbtinstruments/asyncio-mqtt"></a>
    <a href="https://results.pre-commit.ci/latest/github/sbtinstruments/asyncio-mqtt/main"><img alt="pre-commit.ci status" src="https://results.pre-commit.ci/badge/github/sbtinstruments/asyncio-mqtt/main.svg"></a>
    <a href="https://github.com/sbtinstruments/asyncio-mqtt"><img alt="Typing: strict" src="https://img.shields.io/badge/typing-strict-green.svg"></a>
    <a href="https://github.com/sbtinstruments/asyncio-mqtt"><img alt="Code Style: Black" src="https://img.shields.io/badge/code%20style-black-black"></a>
</p>

<!-- pitch start -->

Write code like this:

**Publisher**

```python
async with Client("test.mosquitto.org") as client:
    await client.publish("humidity/outside", payload=0.38)
```

**Subscriber**

```python
async with Client("test.mosquitto.org") as client:
    async with client.messages() as messages:
        await client.subscribe("humidity/#")
        async for message in messages:
            print(message.payload)
```

asyncio-mqtt combines the stability of the time-proven [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) library with a modern, asyncio-based interface.

- No more callbacks! 👍
- No more return codes (welcome to the `MqttError`)
- Graceful disconnection (forget about `on_unsubscribe`, `on_disconnect`, etc.)
- Compatible with `async` code
- Fully type-hinted
- Did we mention no more callbacks?

The whole thing is less than [900 lines of code](https://github.com/sbtinstruments/asyncio-mqtt/blob/main/asyncio_mqtt/client.py).

<!-- pitch end -->

---

**[Read the documentation at sbtinstruments.github.io/asyncio-mqtt](https://sbtinstruments.github.io/asyncio-mqtt)**

---

<!-- documentation start -->

## Installation

asyncio-mqtt can be installed via `pip install asyncio-mqtt`. It requires Python 3.7+ to run. The only dependency is [paho-mqtt](https://github.com/eclipse/paho.mqtt.python).

If you can't wait for the latest version and want to install directly from GitHub, use:

`pip install git+https://github.com/sbtinstruments/asyncio-mqtt`

### Note for Windows users

Since Python 3.8, the default asyncio event loop is the `ProactorEventLoop`. Said loop [doesn't support the `add_reader` method](https://docs.python.org/3/library/asyncio-platforms.html#windows) that is required by asyncio-mqtt. Please switch to an event loop that supports the `add_reader` method such as the built-in `SelectorEventLoop`:

```python
# Change to the "Selector" event loop
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# Run your async application as usual
asyncio.run(main())
```

## License

This project is licensed under the [BSD 3-clause License](https://opensource.org/licenses/BSD-3-Clause).

Note that the underlying paho-mqtt library is dual-licensed. One of the licenses is the so-called [Eclipse Distribution License v1.0](https://www.eclipse.org/org/documents/edl-v10.php). It is almost word-for-word identical to the BSD 3-clause License. The only differences are:

- One use of "COPYRIGHT OWNER" (EDL) instead of "COPYRIGHT HOLDER" (BSD)
- One use of "Eclipse Foundation, Inc." (EDL) instead of "copyright holder" (BSD)

## Contributing

We're happy about your contributions to the project!

You can get started by reading the [CONTRIBUTING.md](https://github.com/sbtinstruments/asyncio-mqtt/blob/main/CHANGELOG.md).

## Versioning

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Expect API changes until we reach version `1.0.0`. After `1.0.0`, breaking changes will only occur in a major release (e.g., `2.0.0`, `3.0.0`, etc.).

## Changelog

The changelog lives in the [CHANGELOG.md](https://github.com/sbtinstruments/asyncio-mqtt/blob/main/CHANGELOG.md) document. It adheres to the principles of [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## Related projects

Is asyncio-mqtt not what you're looking for? There are a few other clients you can try:

- [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) — Own protocol implementation. Synchronous.<br>![GitHub stars](https://img.shields.io/github/stars/eclipse/paho.mqtt.python) ![license](https://img.shields.io/github/license/eclipse/paho.mqtt.python)
- [gmqtt](https://github.com/wialon/gmqtt) — Own protocol implementation. Asynchronous.<br>![GitHub stars](https://img.shields.io/github/stars/wialon/gmqtt) ![license](https://img.shields.io/github/license/wialon/gmqtt)
- [fastapi-mqtt](https://github.com/sabuhish/fastapi-mqtt) — Asynchronous wrapper around gmqtt. Simplifies integration in your FastAPI application.<br>![GitHub stars](https://img.shields.io/github/stars/sabuhish/fastapi-mqtt) ![license](https://img.shields.io/github/license/sabuhish/fastapi-mqtt)
- [amqtt](https://github.com/Yakifo/amqtt) — Own protocol implementation. Asynchronous. Includes a broker.<br>![GitHub stars](https://img.shields.io/github/stars/Yakifo/amqtt) ![license](https://img.shields.io/github/license/Yakifo/amqtt)
- [mqttools](https://github.com/eerimoq/mqttools) — Own protocol implementation. Asynchronous.<br>![GitHub stars](https://img.shields.io/github/stars/eerimoq/mqttools) ![license](https://img.shields.io/github/license/eerimoq/mqttools)
- [trio-paho-mqtt](https://github.com/bkanuka/trio-paho-mqtt) — Asynchronous wrapper around paho-mqtt (similar to asyncio-mqtt). Based on trio instead of asyncio.<br>![GitHub stars](https://img.shields.io/github/stars/bkanuka/trio-paho-mqtt) ![license](https://img.shields.io/github/license/bkanuka/trio-paho-mqtt)
