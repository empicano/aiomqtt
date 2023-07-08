# Connecting to the broker

To publish messages and subscribe to topics, we need to connect to a broker. A minimal working example that connects to a broker and then publishes a message looks like this:

```python
import asyncio
import aiomqtt


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        await client.publish("temperature/outside", payload=28.4)


asyncio.run(main())
```

The connection to the broker is managed by the `Client` context manager.

This context manager connects to the broker when you enter the `with` statement and disconnects when you exit it again. Similar to e.g. the `with open(file)` context manager, this ensures that the teardown logic is always executed at least, and at most, once -- even in case of an exception.

```{tip}
If you're used to calling something like `connect` and `disconnect` explicitly, working with the client via a context manager might feel a bit strange at first. We will see a few examples which will hopefully clear this up.

In case your use case does not allow you to use a context manager, you can use the context manager's `__aenter__` and `__aexit__` methods directly, similar to something like `connect` and `disconnect`. Note that you loose the benefits of context managers in this case. We do not recommend this approach; It's a workaround and a bit tricky to get right.
```

```{note}
Examples use the public [mosquitto test broker](https://test.mosquitto.org/). You can connect to this broker without any credentials. Please use this broker in issues or discussions (if possible) to make it easier for others to test your code.
```

For a list of all available arguments to the client, see the [API reference](#developer-interface).

## Sharing the connection

In many cases, you'll want to send and receive messages in different locations in your code. You could create a new client each time, but:

1. This is not very performant, and
2. You'll use more network bandwidth.

You can share the connection by passing the `Client` instance to all functions that need it:

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

Connections to the MQTT broker can be persistent or non-persistent. Persistent sessions are kept alive when the client is offline. This means that the broker stores the client's subscriptions and queues any messages of [QoS 1 and 2](publishing-a-message.md#quality-of-service-qos) that the client misses or has not yet acknowledged. The broker will then retransmit the messages when the client reconnects.

To create a persistent session, set the `clean_session` parameter to `False` when initializing the client. For a non-persistent session, set `clean_session` to `True`.

```{note}
The amount of messages that can be queued is limited by the broker's memory. If a client with a persistent session does not come back online for a long time, the broker will eventually run out of memory and start discarding messages.
```
