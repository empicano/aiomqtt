# Migration guide: v3.0.0 (alpha)

Version 3.0.0 is a major rewrite with a focus on more control and less magic. The underlying protocol library has been replaced, and many APIs have changed. This guide covers the breaking changes and how to migrate.

> [!NOTE]
> This is an alpha release. Things can still change based on feedback!

## New protocol library

aiomqtt no longer depends on paho-mqtt. The underlying protocol library is now [mqtt5](https://github.com/empicano/mqtt5). This means aiomqtt now **only supports MQTTv5**.

## Messages

`client.messages` has been renamed to `client.messages()` (a method call):

```python
# v2
async for message in client.messages:
    print(message.payload)

# v3
async for message in client.messages():
    print(message.payload)
```

Messages are now `mqtt5.PublishPacket` instances instead of `aiomqtt.Message`.

**Unchanged attributes:** `topic`, `payload`, `qos`, `retain`

**Changed attributes:**

`message.mid` is now named `message.packet_id`.

The opaque `message.properties` object has been replaced by individual attributes:

- `message.payload_format_indicator`
- `message.message_expiry_interval`
- `message.content_type`
- `message.response_topic`
- `message.correlation_data`
- `message.subscription_ids`
- `message.topic_alias`
- `message.user_properties`

**New attributes:** `message.duplicate`

**Removed:** `message.topic.matches(pattern)`

## Publishing

Payloads must now be `bytes`. This makes serialization and deserialization explicit. Passing `str`, `int`, `float`, etc. is no longer supported:

```python
# v2
await client.publish("topic", payload="hello")
await client.publish("topic", payload=42)

# v3
await client.publish("topic", b"hello")
await client.publish("topic", b"42")
```

Publishing with QoS>0 now requires a `packet_id`. This is because QoS>0 is really only useful if you retry failed publishes:

```python
# v2
await client.publish("topic", payload=b"hello", qos=1)

# v3
packet_id = next(client.packet_ids)
await client.publish(
    "topic", b"hello", qos=aiomqtt.QoS.AT_LEAST_ONCE, packet_id=packet_id
)
```

See the QoS=1 and QoS=2 guides for retry patterns.

## Subscribing

The `qos` parameter has been renamed to `max_qos`:

```python
# v2
await client.subscribe("topic", qos=1)

# v3
await client.subscribe("topic", max_qos=aiomqtt.QoS.AT_LEAST_ONCE)
```

## Manual acknowledgments

aiomqtt no longer acknowledges QoS=1 and QoS=2 messages automatically. You must acknowledge them yourself. This gives you control over *when* a message is considered delivered -- if processing fails before you acknowledge, the broker will redeliver the message on the next connection.

```python
# v3 -- QoS=1
async for message in client.messages():
    print(message.payload)
    if message.qos == aiomqtt.QoS.AT_LEAST_ONCE:
        await client.puback(message.packet_id)
```

For QoS=2, the `messages()` iterator yields both `PublishPacket` and `PubRelPacket`.

> [!IMPORTANT]
> If you don't acknowledge messages, the broker stops forwarding new QoS=1 and QoS=2 messages after reaching the `receive_max` limit.

## Flow control

Backpressure is now built in via `receive_max`. QoS=0 messages without a waiting consumer are dropped.

## Reconnection

Reconnection is now built into the client. Set `reconnect=True` to enable automatic reconnection with exponential backoff:

```python
# v2 -- manual reconnection
client = aiomqtt.Client("test.mosquitto.org")
while True:
    try:
        async with client:
            await client.subscribe("topic")
            async for message in client.messages:
                print(message.payload)
    except aiomqtt.MqttError:
        await asyncio.sleep(5)

# v3 -- built-in reconnection
async with aiomqtt.Client("test.mosquitto.org", reconnect=True) as client:
    ...
```

During disconnection, operations raise `ConnectError`. Use `await client.connected()` to wait for the client to reconnect.

## Topic matching

`message.topic.matches()` has been removed. aiomqtt no longer implements message routing. See the guides for routing example using regular expressions.

## Removed client arguments

The following `Client` arguments from v2 have been removed:

- `protocol`: v3 only supports MQTTv5
- `transport`: only TCP is supported (WebSocket support will be added later)
- `tls_context`: renamed to `ssl_context`
- `tls_params`, `tls_insecure`: use `ssl_context` directly
- `proxy`, `socket_options`: removed
- `queue_type`, `max_queued_incoming_messages`, `max_queued_outgoing_messages`: the internal queue has been removed
- `timeout`: removed, use `with asyncio.timeout(...)`
- `message_retry_set`: removed (was already deprecated in v2)

## Exceptions

- `MqttError` has been replaced by `ConnectError`, `ProtocolError`, and `NegativeAckError`
