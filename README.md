<h1 align="center">The idiomatic asyncio MQTT client 🙌</h1>
<p align="center"><em>(formerly known as asyncio-mqtt)</em></p>
<p align="center">
    <a href="https://github.com/sbtinstruments/aiomqtt/blob/main/LICENSE"><img alt="License: BSD-3-Clause" src="https://img.shields.io/github/license/sbtinstruments/aiomqtt"></a>
    <a href="https://pypi.org/project/aiomqtt"><img alt="PyPI version" src="https://img.shields.io/pypi/v/aiomqtt"></a>
    <a href="https://pypi.org/project/aiomqtt"><img alt="Supported Python versions" src="https://img.shields.io/pypi/pyversions/aiomqtt.svg"></a>
    <a href="https://pypi.org/project/aiomqtt"><img alt="PyPI downloads" src="https://img.shields.io/pypi/dm/aiomqtt"></a>
    <a href="https://github.com/sbtinstruments/aiomqtt/actions/workflows/test.yml"><img alt="test" src="https://github.com/sbtinstruments/aiomqtt/actions/workflows/test.yml/badge.svg"></a>
    <a href="https://github.com/sbtinstruments/aiomqtt/actions/workflows/docs.yml"><img alt="docs" src="https://github.com/sbtinstruments/aiomqtt/actions/workflows/docs.yml/badge.svg"></a>
    <a href="https://codecov.io/gh/sbtinstruments/aiomqtt"><img alt="Coverage" src="https://img.shields.io/codecov/c/github/sbtinstruments/aiomqtt"></a>
    <a href="https://github.com/sbtinstruments/aiomqtt"><img alt="Typing: strict" src="https://img.shields.io/badge/typing-strict-green.svg"></a>
    <a href="https://github.com/sbtinstruments/aiomqtt"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-black"></a>
    <a href="https://github.com/charliermarsh/ruff"><img alt="Ruff" src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v1.json"></a>
</p>

<!-- pitch start -->

Write code like this:

**Publish**

```python
async with Client("test.mosquitto.org") as client:
    await client.publish("humidity/outside", payload=0.38)
```

**Subscribe**

```python
async with Client("test.mosquitto.org") as client:
    async with client.messages() as messages:
        await client.subscribe("humidity/#")
        async for message in messages:
            print(message.payload)
```

aiomqtt combines the stability of the time-proven [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) library with an intuitive, idiomatic asyncio interface:

- No more callbacks! 👍
- No more return codes (welcome to the `MqttError`)
- Graceful disconnection (forget about `on_unsubscribe`, `on_disconnect`, etc.)
- Supports MQTT versions 5.0, 3.1.1 and 3.1
- Fully type-hinted
- Did we mention no more callbacks?

<!-- pitch end -->

---

**[Read the documentation at sbtinstruments.github.io/aiomqtt](https://sbtinstruments.github.io/aiomqtt)**

---

<!-- documentation start -->

## Installation

aiomqtt can be installed via `pip install aiomqtt`. It requires Python `3.8+` to run. The only dependency is [paho-mqtt](https://github.com/eclipse/paho.mqtt.python).

If you can't wait for the latest version and want to install directly from GitHub, use:

`pip install git+https://github.com/sbtinstruments/aiomqtt`

### Note for Windows users

Since Python `3.8`, the default asyncio event loop is the `ProactorEventLoop`. Said loop [doesn't support the `add_reader` method](https://docs.python.org/3/library/asyncio-platforms.html#windows) that is required by aiomqtt. Please switch to an event loop that supports the `add_reader` method such as the built-in `SelectorEventLoop`:

```python
# Change to the "Selector" event loop if platform is Windows
if sys.platform.lower() == "win32" or os.name.lower() == "nt":
    from asyncio import set_event_loop_policy, WindowsSelectorEventLoopPolicy
    set_event_loop_policy(WindowsSelectorEventLoopPolicy())
# Run your async application as usual
asyncio.run(main())
```

## License

This project is licensed under the [BSD 3-clause License](https://opensource.org/licenses/BSD-3-Clause).

Note that the underlying paho-mqtt library is dual-licensed. One of the licenses is the so-called [Eclipse Distribution License v1.0](https://www.eclipse.org/org/documents/edl-v10.php). It is almost word-for-word identical to the BSD 3-clause License. The only differences are:

- One use of "COPYRIGHT OWNER" (EDL) instead of "COPYRIGHT HOLDER" (BSD)
- One use of "Eclipse Foundation, Inc." (EDL) instead of "copyright holder" (BSD)

## Contributing

We're very happy about contributions to the project! You can get started by reading [CONTRIBUTING.md](https://github.com/sbtinstruments/aiomqtt/blob/main/CONTRIBUTING.md).

## Versioning

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Breaking changes will only occur in major `X.0.0` releases.

## Changelog

The changelog lives in [CHANGELOG.md](https://github.com/sbtinstruments/aiomqtt/blob/main/CHANGELOG.md). It follows the principles of [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## Related projects

Is aiomqtt not what you're looking for? There are a few other clients you can try:

- [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) — Own protocol implementation. Synchronous.<br>![GitHub stars](https://img.shields.io/github/stars/eclipse/paho.mqtt.python) ![license](https://img.shields.io/github/license/eclipse/paho.mqtt.python)
- [gmqtt](https://github.com/wialon/gmqtt) — Own protocol implementation. Asynchronous.<br>![GitHub stars](https://img.shields.io/github/stars/wialon/gmqtt) ![license](https://img.shields.io/github/license/wialon/gmqtt)
- [fastapi-mqtt](https://github.com/sabuhish/fastapi-mqtt) — Asynchronous wrapper around gmqtt. Simplifies integration in your FastAPI application.<br>![GitHub stars](https://img.shields.io/github/stars/sabuhish/fastapi-mqtt) ![license](https://img.shields.io/github/license/sabuhish/fastapi-mqtt)
- [amqtt](https://github.com/Yakifo/amqtt) — Own protocol implementation. Asynchronous. Includes a broker.<br>![GitHub stars](https://img.shields.io/github/stars/Yakifo/amqtt) ![license](https://img.shields.io/github/license/Yakifo/amqtt)
- [mqttools](https://github.com/eerimoq/mqttools) — Own protocol implementation. Asynchronous.<br>![GitHub stars](https://img.shields.io/github/stars/eerimoq/mqttools) ![license](https://img.shields.io/github/license/eerimoq/mqttools)
- [trio-paho-mqtt](https://github.com/bkanuka/trio-paho-mqtt) — Asynchronous wrapper around paho-mqtt (similar to aiomqtt). Based on trio instead of asyncio.<br>![GitHub stars](https://img.shields.io/github/stars/bkanuka/trio-paho-mqtt) ![license](https://img.shields.io/github/license/bkanuka/trio-paho-mqtt)
