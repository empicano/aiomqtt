# The idiomatic asyncio MQTT client 🙌

<a href="https://github.com/empicano/aiomqtt/actions/workflows/test.yml"><img alt="test" src="https://github.com/empicano/aiomqtt/actions/workflows/test.yml/badge.svg"></a> <a href="https://pypi.org/project/aiomqtt"><img alt="PyPI downloads" src="https://img.shields.io/pypi/dm/aiomqtt"></a> <a href="https://pypi.org/project/aiomqtt"><img alt="PyPI version" src="https://img.shields.io/pypi/v/aiomqtt"></a> <a href="https://pypi.org/project/aiomqtt"><img alt="Supported Python versions" src="https://img.shields.io/pypi/pyversions/aiomqtt.svg"></a> <a href="https://codecov.io/gh/sbtinstruments/aiomqtt"><img alt="Coverage" src="https://img.shields.io/codecov/c/github/sbtinstruments/aiomqtt"></a> <a href="https://github.com/empicano/aiomqtt"><img alt="Typing: strict" src="https://img.shields.io/badge/typing-strict-green.svg"></a> <a href="https://github.com/astral-sh/ruff"><img alt="Ruff" src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json"></a> <a href="https://github.com/empicano/aiomqtt/blob/main/LICENSE"><img alt="License: BSD-3-Clause" src="https://img.shields.io/github/license/empicano/aiomqtt"></a>

**Documentation:** [https://aiomqtt.felixboehm.dev](https://aiomqtt.felixboehm.dev)

---

<!-- documentation start -->

Write code like this:

**Publish**

```python
async with Client("test.mosquitto.org") as client:
    await client.publish("temperature/outside", payload=28.4)
```

**Subscribe**

```python
async with Client("test.mosquitto.org") as client:
    await client.subscribe("temperature/#")
    async for message in client.messages:
        print(message.payload)
```

## Key features

- Based on the time-proven [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) library
  with an idiomatic async interface
- No more callbacks! 👍
- No more return codes (welcome to `MqttError`)
- Graceful disconnection (forget about `on_unsubscribe`, `on_disconnect`, etc.)
- Supports MQTT versions 5.0, 3.1.1 and 3.1
- Optionally: separate queues per subscription. No more overhead for dispatching.
- Fully type-hinted
- Did we mention no more callbacks?
- Works with asyncio *and* trio! No workarounds required!

## Installation

```
pip install aiomqtt
```

The only dependency is [paho-mqtt](https://github.com/eclipse/paho.mqtt.python).

If you can't wait for the latest version, install directly from GitHub with:

```
pip install git+https://github.com/empicano/aiomqtt
```

## License

This project is licensed under the [BSD 3-clause License](https://opensource.org/licenses/BSD-3-Clause).

Note that the underlying paho-mqtt library is dual-licensed. One of the licenses is the [Eclipse Distribution License v1.0](https://www.eclipse.org/org/documents/edl-v10.php), which is almost identical to the BSD 3-clause License. The only differences are:

- One use of "COPYRIGHT OWNER" (EDL) instead of "COPYRIGHT HOLDER" (BSD)
- One use of "Eclipse Foundation, Inc." (EDL) instead of "copyright holder" (BSD)

## Contributing

We're happy about contributions to aiomqtt! 🎉 You can get started by reading [CONTRIBUTING.md](https://github.com/empicano/aiomqtt/blob/main/CONTRIBUTING.md).

## Versioning

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Breaking changes will only occur in major `X.0.0` releases.

## Changelog

See [CHANGELOG.md](https://github.com/empicano/aiomqtt/blob/main/CHANGELOG.md), which follows the principles of [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
