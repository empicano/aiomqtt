# Connecting to the broker

To publish messages and subscribe to topics, we first need to connect to a broker. This is a minimal working example that connects to a broker and then publishes a message:

```python
import asyncio
import aiomqtt


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        await client.publish("temperature/outside", payload=28.4)


asyncio.run(main())
```

The connection to the broker is managed by the `Client` context manager. This context manager connects to the broker when we enter the `with` statement and disconnects when we exit it again.

Context managers make it easy to manage resources like network connections or files by ensuring that their teardown logic is always executed -- even in case of an exception.

```{tip}
If your use case does not allow you to use a context manager, you can use the client's `__aenter__` and `__aexit__` methods manually as a workaround. With this approach you need to ensure that `___aexit___` is also called in case of an exception. Avoid this workaround if you can, it's a bit tricky to get right.
```

```{note}
Examples use the public [mosquitto test broker](https://test.mosquitto.org/). You can connect to this broker without any credentials. Alternatively, our [contribution guide](https://github.com/empicano/aiomqtt/blob/main/CONTRIBUTING.md) contains an explanation of how to spin up a local mosquitto broker with Docker.

All examples in this documentation are self-contained and runnable as-is.
```

For a list of all available arguments to the client, see the [API reference](#developer-interface).

## Sharing the connection

We often want to send and receive messages in multiple different locations in our code. We could create a new client each time, but:

1. This is not very performant, and
2. We'll use more network bandwidth.

You can share the connection to the broker by passing the `Client` instance to all functions that need it:

```python
import asyncio
import aiomqtt


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

## Persistent sessions

Connections to the MQTT broker can be persistent or non-persistent. Persistent sessions are kept alive when the client goes offline. This means that the broker stores the client's subscriptions and queues any messages of [QoS 1 and 2](publishing-a-message.md#quality-of-service-qos) that the client misses or has not yet acknowledged. The broker will then retransmit the messages when the client reconnects.

To create a persistent session, set the `clean_session` parameter to `False` when initializing the client. For a non-persistent session, set `clean_session` to `True`.

```{note}
The amount of messages that can be queued is limited by the broker's memory. If a client with a persistent session does not come back online for a long time, the broker will eventually run out of memory and start discarding messages.
```
