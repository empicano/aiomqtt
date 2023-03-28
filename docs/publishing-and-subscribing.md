# Publishing and subscribing

Let's see a minimal working example of publishing a message:

```python
import asyncio
import asyncio_mqtt as aiomqtt


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        await client.publish("humidity/outside", payload=0.38)


asyncio.run(main())
```

For subscribing and listening to messages, a minimal working example looks like this:

```python
import asyncio
import asyncio_mqtt as aiomqtt


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        async with client.messages() as messages:
            await client.subscribe("humidity/#")
            async for message in messages:
                print(message.payload)


asyncio.run(main())
```

## Payload encoding

MQTT message payloads are transmitted as bytestreams.

asyncio-mqtt accepts payloads of types `int`, `float`, `str`, `bytes`, `bytearray`, and `None`. `int` and `float` payloads are automatically converted to `str` (which is then converted to `bytes`). If you want to send a true `int` or `float`, you can use [`struct.pack()`](https://docs.python.org/3/library/struct.html) to encode it as a `bytes` object. When no payload is specified or when it's set to `None`, a zero-length payload is sent.

```{important}
If you want to send non-standard types, you have to implement the encoding yourself. For example, to send a `dict` as JSON, you can use `json.dumps()` (which returns a `str`). On the receiving end, you can then use `json.loads()` to decode the JSON string back into a `dict`.
```

## Quality of Service (QoS)

MQTT messages can be sent with different levels of reliability. When publishing a message and when subscribing to a topic you can set the `qos` parameter to one of the three Quality of Service levels:

- QoS 0 (**"At most once"**): The message is sent once, with no guarantee of delivery. This is the fastest and least reliable option. This is the default of asyncio-mqtt.
- QoS 1 (**"At least once"**): The message is delivered at least once to the receiver, possibly multiple times. The sender stores messages until the receiver acknowledges receipt.
- QoS 2 (**"Exactly once"**): The message is delivered exactly once to the receiver, guaranteed through a four-part handshake. This is the slowest and most reliable option.

```{important}
The QoS levels of the publisher and the subscriber are two different things and don't have to be the same!

The publisher's QoS level defines the reliability of the communication between the publisher and the broker. The subscriber's QoS level defines the reliability of the communication between the broker and the subscriber.
```

## Persistent sessions

## Filtering messages

Imagine you're measuring temperature and humidity on the outside and inside, and our topics look like this: `temperature/outside`. You want to receive all types of measurements but handle them differently.

asyncio-mqtt provides `Topic.matches()` to make this easy:

```python
import asyncio
import asyncio_mqtt as aiomqtt


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        async with client.messages() as messages:
            await client.subscribe("#")
            async for message in messages:
                if message.topic.matches("humidity/outside"):
                    print(f"[humidity/outside] {message.payload}")
                if message.topic.matches("+/inside"):
                    print(f"[+/inside] {message.payload}")
                if message.topic.matches("temperature/#"):
                    print(f"[temperature/#] {message.payload}")


asyncio.run(main())
```

```{note}
In our example, messages to `temperature/inside` are handled twice!
```
