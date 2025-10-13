# Guides

This documentation aims to cover everything you need to know to use aiomqtt in your projects. If you get stuck, don’t hesitate to start a new discussion on GitHub. We’re happy to help!

## Publishing a message

This is a minimal example that connects to a broker and publishes a message:

```python
import asyncio
import aiomqtt


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        await client.publish("socks/right/status", payload=b"missing")


asyncio.run(main())
```

The connection to the broker is managed by the `Client` context manager. This context manager connects to the broker when we enter the `with` statement and disconnects when we exit it again.

Context managers make it easier to manage resources like network connections or files by ensuring that their teardown logic is always executed -- even in case of an exception.

> [!NOTE]
> The examples in this documentation are self-contained and runnable as-is. They connect to the [public mosquitto test broker](https://test.mosquitto.org/), which doesn't require authentication.

> [!TIP]
> If your use case does not allow you to use a context manager, you can use the client’s `__aenter__` and `__aexit__` methods directly as a workaround. With this approach you need to ensure that `__aexit__` is also called in case of an exception. Avoid this workaround if you can, it’s a bit tricky to get right.

### Quality of Service (QoS)

MQTT messages can be sent with different levels of reliability:

- **`0`** (“At most once”): The message is sent once, with no guarantee of delivery. This is the fastest option.
- **`1`** (“At least once”): The message is delivered at least once, possibly multiple times. The receiver acknowledges receipt with a PUBACK packet.
- **`2`** (“Exactly once”): The message is delivered exactly once, guaranteed through a four-part handshake (PUBLISH, PUBREC, PUBREL, PUBCOMP). This is the slowest option.

> [!IMPORTANT]
> MQTT runs over network protocols that already handle packet loss and retransmissions (typically: TCP). QoS therefore only matters when the connection is lost and the client reconnects with the same `identifier` and `clean_start=False`.

### Payload encoding

Message payloads are sent and received as `bytes`.

This is how you could encode and decode data as JSON to/from `bytes` with pydantic:

```python
import pydantic


class Measurement(pydantic.BaseModel):
    temperature: float
    humidity: float


measurement = Measurement(temperature=22.5, humidity=0.38)
# Encode to bytes
payload = measurement.model_dump_json().encode()
try:
    # Decode from bytes
    measurement = Measurement.model_validate_json(payload.decode())
except pydantic.ValidationError as e:
    print(e)
```

> [!TIP]
> aiomqtt (more specifically, the underlying [mqtt5](https://github.com/empicano/mqtt5) protocol library) serializes packets to minimal wire format. However, the number of bytes that are sent over the wire still depends a lot on how you encode your payloads. If you need to optimize for bandwidth, consider efficient schemes like Protobuf or MessagePack over JSON.

### TODO: Publishing with QoS=2

### Retained messages

Messages can be published with `retain=True`. The broker relays these messages to all subscribers as usual but also stores the most recent message for the topic. Each new subscriber receives the last retained message for a topic immediately after they subscribe.

> [!IMPORTANT]
> The broker stores only one retained message per topic. If you publish a new retained message for a topic, the previous retained message is overwritten.
> You can delete a retained message for a topic by publishing a retained message with an empty payload.

## Subscribing to a topic

To receive messages, we need to subscribe to topics. You can then use `Client.messages()` generator to iterate over incoming messages. This is a minimal example that listens for messages to the `socks/+/status` pattern:

```python
import asyncio
import aiomqtt


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        await client.subscribe("socks/#", max_qos=aiomqtt.QoS.AT_MOST_ONCE)
        async for message in client.messages():
            print(message.payload)


asyncio.run(main())
```

### Receiving messages with QoS=1

Messages sent with QoS=1 and QoS=2 must be acknowledged by the receiver. Unlike most other MQTT clients, aiomqtt gives you full control over message acknowledgments. This allows you to ensure that messages are processed and/or persisted before acknowledgment, and let's you fine-tune how your code applies backpressure.

> [!IMPORTANT]
> If you don't acknowledge QoS=1 and QoS=2 messages, the broker will stop sending new messages after reaching the `receive_max` limit (backpressure kicks in).

We acknowledge QoS=1 messages with PUBACK:

```python
import asyncio
import aiomqtt


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        await client.subscribe("socks/#", max_qos=aiomqtt.QoS.AT_LEAST_ONCE)
        async for message in client.messages():
            print(message.payload)
            if message.qos == aiomqtt.QoS.AT_LEAST_ONCE:
                await client.puback(message.packet_id)


asyncio.run(main())
```

> [!TIP]
> Setting the `max_qos` parameter in the subscription to `QoS.AT_MOST_ONCE` means that the broker downgrades all messages to your client to QoS=0. Setting it to `QoS.AT_LEAST_ONCE` means that the broker downgrades QoS=2 messages to QoS=1. Setting `max_qos` to `QoS.EXACTLY_ONCE` (the default) means that messages are delivered at the QoS level with which they were published.

### TODO: Receiving messages with QoS=2

### TODO: Routing messages

### Handling messages concurrently

The `Client.messages()` generator returns incoming messages sequentially. This can create a bottleneck if individual messages take a long time to handle (e.g. we write them to a database).

You can handle messages concurrently with multiple tasks like so:

```python
import asyncio
import aiomqtt
import random


async def consume(client):
    async for message in client.messages():
        await asyncio.sleep(random.random())  # Simulate some I/O-bound work
        print(message.payload)


async def main():
    async with aiomqtt.Client("test.mosquitto.org", receive_max=16) as client:
        await client.subscribe("socks/#", max_qos=aiomqtt.QoS.AT_MOST_ONCE)
        async with asyncio.TaskGroup() as tg:
            for _ in range(4):  # The number of consumer tasks
                tg.create_task(consume(client))


asyncio.run(main())
```

> [!IMPORTANT]
> Handling messages concurrently in multiple tasks only helps with I/O-bound code. If the message handling is CPU-bound, you should spawn multiple processes instead.

> [!WARNING]
> Messages might be processed in a different order than they arrive.

### TODO: Backpressure

### TODO: Listening without blocking

### Stop listening

If you have a consumer task running alongside other code, you can stop it with [`asyncio.Task.cancel()`](https://docs.python.org/3/library/asyncio-task.html#asyncio.Task.cancel) when you're done:

```python
import asyncio
import aiomqtt


async def consume(client):
    async for message in client.messages():
        print(message.payload)


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        await client.subscribe("socks/#", max_qos=aiomqtt.QoS.AT_MOST_ONCE)
        task = loop.create_task(consume())
        # Do something else for a while
        await asyncio.sleep(5)
        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


asyncio.run(main())
```

### Stop listening after timeout

If you want to listen to messages for a certain amount of time, you can use [`asyncio.timeout()`](https://docs.python.org/3/library/asyncio-task.html#timeouts):

```python
import asyncio
import aiomqtt


async def consume(client):
    async for message in client.messages():
        print(message.payload)


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        await client.subscribe("socks/#", max_qos=aiomqtt.QoS.AT_MOST_ONCE)
        try:
            # Cancel the consumer task after 5 seconds
            async with asyncio.timeout(5):
                await consume()
        except asyncio.TimeoutError:
            pass


asyncio.run(main())
```

## The connection to the broker

The connection to the broker is managed by the `Client` context manager. When we enter the `async with` block, the client connects to the broker (via TCP) and sends a CONNECT packet. The method returns once the broker responds with CONNACK.

Once we exit the context, the client sends a DISCONNECT packet and closes the connection gracefully.

> [!TIP]
> If your use case does not allow you to use a context manager, you can call the client's `__aenter__` and `__aexit__` methods manually as a workaround. With this approach you need to make sure that `__aexit__` is also called in case of an exception. Avoid this workaround if you can, it's a bit tricky to get right.

### TODO: Reconnection

### TODO: Persistent sessions

### TODO: Sharing the connection

### TODO: Will message

## TODO: Alongside FastAPI & Co.
