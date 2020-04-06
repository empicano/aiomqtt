![license](https://img.shields.io/github/license/sbtinstruments/asyncio-mqtt)
![semver](https://img.shields.io/github/v/tag/sbtinstruments/asyncio-mqtt?sort=semver)

# MQTT client with idiomatic asyncio interface 🙌

Write code like this:

```python
async with Client('test.mosquitto.org') as client:
    await client.subscribe('floors/#')

    async with client.filtered_messages('floors/+/humidity') as messages:
        async for message in messages:
            print(message.decode())
```

asyncio-mqtt combines the stability of the time-proven [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) library with a modern, asyncio-based interface.

* No more callbacks! 👍
* No more return codes (welcome to the `MqttError`)
* Graceful disconnection (forget about `on_unsubscribe`, `on_disconnect`, etc.)
* Compatible with `async` code
* Did we mention no more callbacks?

The whole thing is less than [250 lines of code](https://github.com/sbtinstruments/asyncio-mqtt/blob/master/asyncio_mqtt/client.py).

## Installation 📚

`pip install asyncio-mqtt`

## Advanced use ⚡

Let's make the example from before more interesting:

```python
import asyncio
from random import randrange
from asyncio_mqtt import Client

async def log_filtered_messages(client, topic_filter):
    async with client.filtered_messages(topic_filter) as messages:
        async for message in messages:
            print(f'[topic_filter="{topic_filter}"]: {message.decode()}')

async def log_unfiltered_messages(client):
    async with client.unfiltered_messages() as messages:
        async for message in messages:
            print(f'[unfiltered]: {message.decode()}')

async def main():
    async with Client('test.mosquitto.org') as client:
        await client.subscribe('floors/#')

        # You can create any number of message filters
        asyncio.create_task(log_filtered_messages(client, 'floors/+/humidity'))
        asyncio.create_task(log_filtered_messages(client, 'floors/rooftop/#'))
        # 👉 Try to add more filters!

        # All messages that doesn't match a filter will get logged here
        asyncio.create_task(log_unfiltered_messages(client))

        # Publish a random value to each of these topics
        topics = [
            'floors/basement/humidity',
            'floors/rooftop/humidity',
            'floors/rooftop/illuminance',
            # 👉 Try to add more topics!
        ]
        while True:
            for topic in topics:
                message = randrange(100)
                print(f'[topic="{topic}"] Publishing message={message}')
                await client.publish(topic, message, qos=1)
                await asyncio.sleep(2)

asyncio.run(main())
```

## Alternative asyncio-based MQTT clients:

Is asyncio-mqtt not what you are looking for? Try another client:

 * [hbmqtt](https://github.com/beerfactory/hbmqtt) - Own protocol implementation. Includes a broker.  
   ![GitHub stars](https://img.shields.io/github/stars/beerfactory/hbmqtt)
   ![license](https://img.shields.io/github/license/beerfactory/hbmqtt)
 * [gmqtt](https://github.com/wialon/gmqtt) - Own protocol implementation. No dependencies.  
   ![GitHub stars](https://img.shields.io/github/stars/wialon/gmqtt)
   ![license](https://img.shields.io/github/license/wialon/gmqtt)
 * [aiomqtt](https://github.com/mossblaser/aiomqtt) - Wrapper around paho-mqtt.  
   ![GitHub stars](https://img.shields.io/github/stars/mossblaser/aiomqtt)
   ![license](https://img.shields.io/github/license/mossblaser/aiomqtt)
 * [mqttools](https://github.com/eerimoq/mqttools) - Own protocol implementation. No dependencies.  
   ![GitHub stars](https://img.shields.io/github/stars/eerimoq/mqttools)
   ![license](https://img.shields.io/github/license/eerimoq/mqttools)
 * [aio-mqtt](https://github.com/NotJustAToy/aio-mqtt) - Own protocol implementation. No dependencies.  
   ![GitHub stars](https://img.shields.io/github/stars/NotJustAToy/aio-mqtt)
   ![license](https://img.shields.io/github/license/NotJustAToy/aio-mqtt)

This is not an exhaustive list.

### Honorable mentions

 * [trio-paho-mqtt](https://github.com/bkanuka/trio-paho-mqtt) - Trio-based. Wrapper around paho-mqtt.  
   ![GitHub stars](https://img.shields.io/github/stars/bkanuka/trio-paho-mqtt)
   ![license](https://img.shields.io/github/license/bkanuka/trio-paho-mqtt)

## Requirements

Python 3.7 or later.

There is only a single dependency:

 * [paho-mqtt](https://github.com/eclipse/paho.mqtt.python)  
   ![GitHub stars](https://img.shields.io/github/stars/eclipse/paho.mqtt.python) ![license](https://img.shields.io/github/license/eclipse/paho.mqtt.python)

## License

![license](https://img.shields.io/github/license/sbtinstruments/asyncio-mqtt)

Note that the underlying paho-mqtt library is dual-licensed. One of the licenses is the so-called [Eclipse Distribution License v1.0](https://www.eclipse.org/org/documents/edl-v10.php). It is almost word-for-word identical to the [BSD 3-clause License](https://opensource.org/licenses/BSD-3-Clause). The only differences are:
 * One use of "COPYRIGHT OWNER" (EDL) instead of "COPYRIGHT HOLDER" (BSD)
 * One use of "Eclipse Foundation, Inc." (EDL) instead of "copyright holder" (BSD)