# Examples

![license](https://img.shields.io/github/license/sbtinstruments/asyncio-mqtt)
![semver](https://img.shields.io/github/v/tag/sbtinstruments/asyncio-mqtt?sort=semver)

## Sending a JSON payload

### Subscriber

The following example describes a subscriber expecting to receive a JSON
payload, which, also, connects to the client using Basic Auth and specifying
the MQTT protocol to be used. Please beware that some MQTT brokers requires you
to specify the protocol to be used. For more arguments that the Client may
accept, please check [client.py](https://github.com/sbtinstruments/asyncio-mqtt/blob/f4736adf0d3c5b87a39ea27afd025ed58c7bb54c/asyncio_mqtt/client.py#L70)

Please observe that the content which is decoded is not the message received but
the content (payload) which is of the type [MQTTMessage](https://github.com/eclipse/paho.mqtt.python/blob/c339cea2652a957d47de68eafb2a76736c1514e6/src/paho/mqtt/client.py#L355)

```python
import json
from asyncio_mqtt import Client, ProtocolVersion

async with Client(
        "test.mosquitto.org",
        username="username",
        password="password",
        protocol=ProtocolVersion.V31
) as client:
    async with client.filtered_messages("floors/+/humidity") as messages:
        # subscribe is done afterwards so that we just start receiving messages
        # from this point on
        await client.subscribe("floors/#")
        async for message in messages:
            print(message.topic)
            print(json.loads(message.payload))
```

### Publisher

The publisher, besides specifying the Protocol and using also Basic Auth to
acess the broker, it also specifies the [QoS](https://www.hivemq.com/blog/mqtt-essentials-part-6-mqtt-quality-of-service-levels/) desired

```python
import json
from asyncio_mqtt import Client, ProtocolVersion

async with Client(
        "test.mosquitto.org",
        username="username",
        password="password",
        protocol=ProtocolVersion.V31
) as client:
    message = {"state": 3}
    await client.publish("floors/bed_room/humidity",
                         payload=json.dumps(message), qos=2, retain=False)
```

## License

![license](https://img.shields.io/github/license/sbtinstruments/asyncio-mqtt)

Note that the underlying paho-mqtt library is dual-licensed. One of the licenses is the so-called [Eclipse Distribution License v1.0](https://www.eclipse.org/org/documents/edl-v10.php). It is almost word-for-word identical to the [BSD 3-clause License](https://opensource.org/licenses/BSD-3-Clause). The only differences are:

- One use of "COPYRIGHT OWNER" (EDL) instead of "COPYRIGHT HOLDER" (BSD)
- One use of "Eclipse Foundation, Inc." (EDL) instead of "copyright holder" (BSD)
