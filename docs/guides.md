# Guides

This documentation aims to cover everything you need to know to use aiomqtt in your projects. If you get stuck, don’t hesitate to start a new discussion on GitHub. We’re happy to help!

## Publishing a message

This is a minimal example that connects to a broker and publishes a message:

```python
import asyncio
import aiomqtt


async def main() -> None:
    async with aiomqtt.Client(hostname="test.mosquitto.org") as client:
        await client.publish("ducks/louie/status", b"quack")


asyncio.run(main())
```

The connection to the broker is managed by the `Client` context manager. This context manager connects to the broker when we enter the `with` statement and disconnects when we exit it again.

Context managers make it easy to manage resources like network connections or files by ensuring that their teardown logic is always executed – even in case of an exception.

> [!NOTE]
> The examples in this documentation are self-contained and runnable as-is. They connect to the [public mosquitto test broker](https://test.mosquitto.org/), which doesn't require authentication.

### Quality of Service (QoS)

MQTT messages can be sent with different levels of reliability:

- **`0`** (“At most once”): The message is sent once, with no guarantee of delivery. This is the fastest option.
- **`1`** (“At least once”): The message is delivered at least once, possibly multiple times. The receiver acknowledges receipt with a PUBACK packet.
- **`2`** (“Exactly once”): The message is delivered exactly once, guaranteed through a four-part handshake (PUBLISH, PUBREC, PUBREL, PUBCOMP). This is the slowest option.

> [!IMPORTANT]
> MQTT runs over network protocols that already handle packet loss and retransmissions (typically: TCP). QoS mainly matters in two scenarios: reconnection (retransmitting unacknowledged messages when `clean_start=False`) and flow control (limiting in-flight QoS=1 and QoS=2 messages). Additionally, QoS=0 messages may be dropped by any participant under load.

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

### Publishing with QoS=1

Unlike QoS=0, publishing with QoS=1 and QoS=2 requires a `packet_id`. QoS=1 and QoS=2 guarantee delivery through retransmission. If the connection is lost before the broker acknowledges the message, we have to resend it with the same `packet_id` and `duplicate=True`:

```python
import asyncio
import aiomqtt


async def main() -> None:
    async with aiomqtt.Client(
        hostname="test.mosquitto.org",
        clean_start=False,
        session_expiry_interval=600,
        reconnect=True,
    ) as client:
        packet_id = next(client.packet_ids)
        duplicate = False
        while True:
            try:
                await client.publish(
                    "ducks/louie/status",
                    b"quack",
                    qos=aiomqtt.QoS.AT_LEAST_ONCE,
                    packet_id=packet_id,
                    duplicate=duplicate,
                )
                break
            except aiomqtt.ConnectError:
                duplicate = True
                await client.connected()


asyncio.run(main())
```

> [!IMPORTANT]
> For retries to work correctly, the client's session must be persistent. Set `clean_start=False` and a non-zero `session_expiry_interval`; Use a consistent `identifier` if you recreate the client.

### Publishing with QoS=2

QoS=2 is a four-part handshake: PUBLISH, PUBREC, PUBREL, PUBCOMP. Both the PUBLISH and the PUBREL need to be retried if the connection is lost before their respective acknowledgments:

```python
import asyncio
import aiomqtt


async def main() -> None:
    async with aiomqtt.Client(
        hostname="test.mosquitto.org",
        clean_start=False,
        session_expiry_interval=600,
        reconnect=True,
    ) as client:
        packet_id = next(client.packet_ids)
        duplicate = False
        while True:
            try:
                await client.publish(
                    "ducks/louie/status",
                    b"quack",
                    qos=aiomqtt.QoS.EXACTLY_ONCE,
                    packet_id=packet_id,
                    duplicate=duplicate,
                )
                break
            except aiomqtt.ConnectError:
                duplicate = True
                await client.connected()
        while True:
            try:
                await client.pubrel(packet_id)
                break
            except aiomqtt.ConnectError:
                await client.connected()


asyncio.run(main())
```

### Retained messages

Messages can be published with `retain=True`. The broker relays these messages to all subscribers as usual but also stores the most recent message for the topic. Each new subscriber receives the last retained message for a topic immediately after they subscribe.

> [!IMPORTANT]
> The broker stores only one retained message per topic. If you publish a new retained message for a topic, the previous retained message is overwritten.
> You can delete a retained message for a topic by publishing a retained message with an empty payload.

## Subscribing to a topic

To receive messages, we need to subscribe to topics. You can then use `Client.messages()` generator to iterate over incoming messages. This is a minimal example that listens for messages to the `ducks/#` pattern:

```python
import asyncio
import aiomqtt


async def main() -> None:
    async with aiomqtt.Client(hostname="test.mosquitto.org") as client:
        await client.subscribe("ducks/#", max_qos=aiomqtt.QoS.AT_MOST_ONCE)
        async for message in client.messages():
            print(message.payload)


asyncio.run(main())
```

> [!TIP]
> MQTT supports two types of wildcards in subscription patterns: `+` matches exactly one topic level (e.g., `ducks/+/status` matches `ducks/louie/status` but not `ducks/status`); `#` matches zero or more levels and must be the last character (e.g., `ducks/#` matches `ducks`, `ducks/louie`, and `ducks/louie/status`).

> [!WARNING]
> Try to avoid overlapping subscriptions (e.g., subscribing to both `ducks/#` and `ducks/louie/status`). Some brokers deliver matching messages once, others deliver them once per matching subscription. If overlap is unavoidable, subscription identifiers can help you route messages reliably.

> [!NOTE]
> Setting the `max_qos` parameter in the subscription to `QoS.AT_MOST_ONCE` means that the broker downgrades all messages to your client to QoS=0. Setting it to `QoS.AT_LEAST_ONCE` means that the broker downgrades QoS=2 messages to QoS=1. Setting `max_qos` to `QoS.EXACTLY_ONCE` (the default) means that messages are delivered at the QoS level with which they were published.

### Receiving messages with QoS=1

Messages sent with QoS=1 and QoS=2 must be acknowledged by the receiver. aiomqtt gives you full control over message acknowledgments. This allows you to ensure that messages are processed and/or persisted before acknowledgment, and lets you fine-tune how your code applies backpressure.

> [!IMPORTANT]
> If you don't acknowledge QoS=1 and QoS=2 messages, the broker will stop sending new messages after reaching the `receive_max` limit (flow control).

We acknowledge QoS=1 messages with PUBACK:

```python
import asyncio
import aiomqtt


async def main() -> None:
    async with aiomqtt.Client(hostname="test.mosquitto.org") as client:
        await client.subscribe("ducks/#", max_qos=aiomqtt.QoS.AT_LEAST_ONCE)
        async for message in client.messages():
            print(message.payload)
            if message.qos == aiomqtt.QoS.AT_LEAST_ONCE:
                await client.puback(message.packet_id)


asyncio.run(main())
```

> [!NOTE]
> The specification requires acknowledgments to be sent in-order per topic. In practice, most brokers (e.g. EMQX, VerneMQ) don't enforce this. If you need strict compliance, make sure to acknowledge messages in-order per topic.

### Receiving messages with QoS=2

QoS=2 is a two-step acknowledgment. The `messages()` iterator yields both `PublishPacket` and `PubRelPacket`. We acknowledge `PublishPacket` with PUBREC, and `PubRelPacket` with PUBCOMP. To guarantee exactly-once delivery across reconnections, you have to persist the message before sending PUBREC:

```python
import asyncio
import aiomqtt


async def main() -> None:
    async with aiomqtt.Client(hostname="test.mosquitto.org") as client:
        await client.subscribe("ducks/#")
        async for message in client.messages():
            match message:
                case aiomqtt.PublishPacket(qos=aiomqtt.QoS.EXACTLY_ONCE):
                    # TODO: Persist the message here (e.g. write to database)
                    await client.pubrec(message.packet_id)
                case aiomqtt.PubRelPacket():
                    # TODO: Retrieve the PUBLISH packet based on the packet ID
                    # TODO: Process the message
                    await client.pubcomp(message.packet_id)
                case aiomqtt.PublishPacket(qos=aiomqtt.QoS.AT_LEAST_ONCE):
                    print(message.payload)
                    await client.puback(message.packet_id)
                case _:
                    print(message.payload)


asyncio.run(main())
```

> [!IMPORTANT]
> QoS=2 only guarantees exactly-once delivery if you persist messages before sending PUBREC. Without persistence, a crash after PUBREC but before processing would lose the message.

### Routing messages

aiomqtt doesn't implement message routing. You can implement a basic router with regular expressions:

```python
import re


pattern = "ducks/+/status/#"
pattern = re.compile(pattern.replace('+', '[^/]*').replace('/#', '(|/.*)'))
cases = [
    ("ducks/louie/status", True),
    ("ducks/louie/status/", True),
    ("ducks/louie/status/foo", True),
    ("ducks/louie/location", False),
    ("dogs/louie/status", False),
    ("ducks/louie/location/status", False),
    ("ducks//louie/status", False),
    ("ducks/louie////status", False),
    ("ducks//status", True),
    ("ducks/status", False),
    ("/ducks/louie/status", False),
]
for topic, result in cases:
    assert bool(pattern.fullmatch(topic)) == result
```

> [!TIP]
> Message routing can be optimized by using subscription identifiers. Note that subscription identifiers are part of the session state and thus need to be persisted across connections.

### Handling messages concurrently

The `Client.messages()` generator returns incoming messages sequentially. This can create a bottleneck if individual messages take a long time to handle (e.g. we write them to a database).

You can handle messages concurrently with multiple tasks like so:

```python
import asyncio
import aiomqtt
import random


async def consume(client: aiomqtt.Client) -> None:
    async for message in client.messages():
        await asyncio.sleep(random.random())  # Simulate some I/O-bound work
        print(message.payload)


async def main() -> None:
    async with aiomqtt.Client("test.mosquitto.org", receive_max=16) as client:
        await client.subscribe("ducks/#", max_qos=aiomqtt.QoS.AT_MOST_ONCE)
        async with asyncio.TaskGroup() as tg:
            for _ in range(4):  # The number of consumer tasks
                tg.create_task(consume(client))


asyncio.run(main())
```

> [!IMPORTANT]
> Handling messages concurrently in multiple tasks only helps with I/O-bound code. If the message handling is CPU-bound, you should spawn multiple processes instead.

> [!WARNING]
> Messages might be processed in a different order than they arrive.

### Backpressure

You can apply backpressure to the broker by setting the Client's `receive_max` parameter. The broker queues QoS=1 and QoS=2 messages to your client when `receive_max` messages are unacknowledged. This prevents the broker from overwhelming your client with more messages than it can process.

> [!NOTE]
> Backpressure only applies to QoS=1 and QoS=2 messages. QoS=0 messages are still sent regardless of `receive_max`.

### Listening without blocking

The `async for message in client.messages()` loop runs indefinitely, waiting for new messages. Any code after it never executes. You can use `asyncio.TaskGroup` to run other code alongside the listener:

```python
import asyncio
import aiomqtt


async def consume(client: aiomqtt.Client) -> None:
    async for message in client.messages():
        print(message.payload)


async def main() -> None:
    async with aiomqtt.Client(hostname="test.mosquitto.org") as client:
        await client.subscribe("ducks/#", max_qos=aiomqtt.QoS.AT_MOST_ONCE)
        async with asyncio.TaskGroup() as tg:
            tg.create_task(consume(client))
            tg.create_task(asyncio.sleep(5))  # Some other task


asyncio.run(main())
```

### Stop listening

If you have a consumer task running alongside other code, you can stop it with [`asyncio.Task.cancel()`](https://docs.python.org/3/library/asyncio-task.html#asyncio.Task.cancel) when you're done:

```python
import asyncio
import aiomqtt


async def consume(client: aiomqtt.Client) -> None:
    async for message in client.messages():
        print(message.payload)


async def main() -> None:
    async with aiomqtt.Client(hostname="test.mosquitto.org") as client:
        await client.subscribe("ducks/#", max_qos=aiomqtt.QoS.AT_MOST_ONCE)
        task = asyncio.create_task(consume(client))
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


async def consume(client: aiomqtt.Client) -> None:
    async for message in client.messages():
        print(message.payload)


async def main() -> None:
    async with aiomqtt.Client(hostname="test.mosquitto.org") as client:
        await client.subscribe("ducks/#", max_qos=aiomqtt.QoS.AT_MOST_ONCE)
        try:
            # Cancel the consumer task after 5 seconds
            async with asyncio.timeout(5):
                await consume(client)
        except asyncio.TimeoutError:
            pass


asyncio.run(main())
```

## The connection to the broker

When we enter the context manager, the `Client` sends a CONNECT packet to the broker. The `__aenter__` method returns once the broker responds with CONNACK. When we exit the context, the client sends a DISCONNECT packet and closes the connection.

> [!TIP]
> If your use case does not allow you to use a context manager, you can call the client's `__aenter__` and `__aexit__` methods manually as a workaround. With this approach you need to make sure that `__aexit__` is also called in case of an exception. Avoid this workaround if you can, it's a bit tricky to get right.

### Reconnection

Set `reconnect=True` to automatically reconnect in the background when the connection is lost. The client uses exponential backoff with jitter between attempts.

While the client is disconnected, publish, subscribe, etc. raise `ConnectError`. You can use `await client.connected()` to wait for the the client to reconnect.

> [!IMPORTANT]
> By default, the broker discards the client's session (e.g. subscriptions, unacknowledged QoS=1 and QoS=2 messages) on disconnection. To keep the session alive across reconnections, set `clean_start=False` and a non-zero `session_expiry_interval` (in seconds). With a persistent session, the broker queues messages while the client is offline and delivers them when the client reconnects.

> [!TIP]
> `session_expiry_interval` controls how long the broker keeps the session after disconnection. Set `session_expiry_interval` to `2**32 - 1` for a session that does not expire.

### Sharing the connection

You can share a single connection by passing the `Client` instance to all functions that need it:

```python
import asyncio
import aiomqtt


async def publish_status(client: aiomqtt.Client) -> None:
    await client.publish("ducks/louie/status", b"quack")


async def publish_location(client: aiomqtt.Client) -> None:
    await client.publish("ducks/louie/location", b"sky")


async def main() -> None:
    async with aiomqtt.Client(hostname="test.mosquitto.org") as client:
        await publish_status(client)
        await publish_location(client)


asyncio.run(main())
```

### Will message

The broker can publish a Will message on behalf of the client when the connection is lost unexpectedly. You can use this to let other subscribers know that the client has gone offline:

```python
import asyncio
import aiomqtt


async def main() -> None:
    async with aiomqtt.Client(
        hostname="test.mosquitto.org", will=aiomqtt.Will("ducks/louie/status", payload=b"zzzz")
    ) as client:
        await client.subscribe("ducks/#", max_qos=aiomqtt.QoS.AT_MOST_ONCE)
        async for message in client.messages():
            print(message.payload)


asyncio.run(main())
```

> [!NOTE]
> The broker sends the Will message when the connection closes without a DISCONNECT packet (e.g. network failure). It's also sent when the `Client` context manager exits with an exception. The Will message is not sent when the client disconnects normally.

## Alongside FastAPI & Co.

Most web frameworks take control over the main function, which can make it tricky to figure out where to create the `Client` and how to share the connection.

With [FastAPI](https://github.com/fastapi/fastapi), you can use a lifespan context manager to set up a `Client` instance that lives for the duration of the application. Store it in `app.state` and access it via dependency injection:

```python
import asyncio
import collections.abc
import contextlib
from typing import Annotated

import aiomqtt
import fastapi


async def consume(client: aiomqtt.Client) -> None:
    async for message in client.messages():
        print(message.payload)


@contextlib.asynccontextmanager
async def lifespan(app: fastapi.FastAPI) -> collections.abc.AsyncIterator[None]:
    async with aiomqtt.Client(hostname="test.mosquitto.org") as client:
        app.state.mqtt = client
        await client.subscribe("ducks/#", max_qos=aiomqtt.QoS.AT_MOST_ONCE)
        task = asyncio.create_task(consume(client))
        yield
        # Cancel the task
        task.cancel()
        # Wait for the task to be cancelled
        try:
            await task
        except asyncio.CancelledError:
            pass


app = fastapi.FastAPI(lifespan=lifespan)


async def get_mqtt(request: fastapi.Request) -> aiomqtt.Client:
    return request.app.state.mqtt


@app.get("/")
async def publish(client: Annotated[aiomqtt.Client, fastapi.Depends(get_mqtt)]) -> None:
    await client.publish("ducks/louie/status", b"quack")
```
