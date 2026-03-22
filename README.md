# aiomqtt

<a href="https://pypi.org/project/aiomqtt"><img alt="PyPI downloads" src="https://img.shields.io/pypi/dm/aiomqtt"></a> <a href="https://pypi.org/project/aiomqtt"><img alt="PyPI version" src="https://img.shields.io/pypi/v/aiomqtt"></a> <a href="https://pypi.org/project/aiomqtt"><img alt="Supported Python versions" src="https://img.shields.io/pypi/pyversions/aiomqtt.svg"></a>

The idiomatic asyncio MQTT client. Write code like this:

**Publish**

```python
async with aiomqtt.Client("test.mosquitto.org") as client:
    await client.publish("ducks/louie/status", payload=b"quack")
```

**Subscribe**

```python
async with aiomqtt.Client("test.mosquitto.org") as client:
    await client.subscribe("ducks/#", max_qos=aiomqtt.QoS.AT_MOST_ONCE)
    async for message in client.messages():
        print(message.payload)
```

## Key features

- No callbacks! 👍
- Complete MQTTv5 support (flow control, user properties, ...)
- Automatic reconnection
- Fine-grained control over acknowledgments
- Fully type-hinted

## Installation

```
pip install aiomqtt
```

The only dependency is [mqtt5](https://github.com/empicano/mqtt5).

## Documentation

To get started, see [the guides](https://github.com/empicano/aiomqtt/tree/main/docs).

If you're new to MQTT, we recommend reading [HiveMQ's MQTT essentials](https://www.hivemq.com/mqtt/) as an introduction. Afterward, the [MQTTv5 specification](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html) is a great reference.

The [RealPython walkthrough](https://realpython.com/async-io-python/) is a nice introduction to Python's asyncio.

## Contributing

We're happy about contributions! See [CONTRIBUTING.md](https://github.com/empicano/aiomqtt/blob/main/CONTRIBUTING.md) to get started.

## Versioning

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Changelog

See [CHANGELOG.md](https://github.com/empicano/aiomqtt/blob/main/CHANGELOG.md), which follows the principles of [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
