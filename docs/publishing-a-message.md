# Publishing a message

Let's see a minimal working example of publishing a message to the `temperature/outside` topic:

```python
import asyncio
import aiomqtt


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        await client.publish("temperature/outside", payload=28.4)


asyncio.run(main())
```

## Payload encoding

MQTT message payloads are transmitted as byte streams.

aiomqtt accepts payloads of types `int`, `float`, `str`, `bytes`, `bytearray`, and `None`. `int` and `float` payloads are automatically converted to `str` (which is then converted to `bytes`). If you want to send a true `int` or `float`, you can use [`struct.pack()`](https://docs.python.org/3/library/struct.html) to encode it as a `bytes` object. When no payload is specified or when it's set to `None`, a zero-length payload is sent.

```{note}
If you want to send non-standard types, you have to implement the encoding yourself. For example, to send a `dict` as JSON, you can use `json.dumps()` (which returns a `str`). On the receiving end, you can then use `json.loads()` to decode the JSON string back into a `dict`.
```

## Quality of Service (QoS)

MQTT messages can be sent with different levels of reliability. When publishing a message and when subscribing to a topic you can set the `qos` parameter to one of the three Quality of Service levels:

- QoS 0 (**"At most once"**): The message is sent once, with no guarantee of delivery. This is the fastest and least reliable option. This is the default of aiomqtt.
- QoS 1 (**"At least once"**): The message is delivered at least once to the receiver, possibly multiple times. The sender stores messages until the receiver acknowledges receipt.
- QoS 2 (**"Exactly once"**): The message is delivered exactly once to the receiver, guaranteed through a four-part handshake. This is the slowest and most reliable option.

```{important}
The QoS levels of the publisher and the subscriber are two different things and don't have to be the same!

The publisher's QoS level defines the reliability of the communication between the publisher and the broker. The subscriber's QoS level defines the reliability of the communication between the broker and the subscriber.
```

## Retained messages

Messages can be published with the `retain` parameter set to `True`. The broker relays these messages to all subscribers as usual but also stores the most recent message for the topic. Each new subscriber receives the last retained message for a topic immediately after they subscribe.

```{important}
The broker stores only one retained message per topic. If you publish a new retained message on a topic, the previous retained message is overwritten.
```

```{note}
To delete a retained message, you can send a message with an empty payload to the topic. However, it’s usually not useful or necessary to delete retained messages, as new retained messages overwrite the previous ones.
```
