[license](https://img.shields.io/github/license/sbtinstruments/asyncio-mqtt)

# MQTT client with idiomatic asyncio interface

Write code like this:

```python
async with Client('test.mosquitto.org') as client:
    await client.subscribe('floors/#')

    async with client.filtered_messages('floors/+/humidity') as messages:
        async for message in messages:
            print(message.decode())
```

* No more callbacks! 👍
* No more return codes (welcome to the `MqttError`)
* Graceful disconnection (forget about `on_unsubscribe`, `on_disconnect`, etc.)
* Compatible with `async` code
* Did we mention no more callbacks?

We combine the stability of the time-proven [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) library with a modern, asyncio-based interface.

The whole thing is less than [250 lines of code](https://github.com/sbtinstruments/asyncio-mqtt/blob/master/asyncio_mqtt/client.py).

## Alternative asyncio-based MQTT clients:

Is asyncio-mqtt not what you are looking for? Try another client:

 * [hbmqtt](https://github.com/beerfactory/hbmqtt) - Includes a broker  
   ![GitHub stars](https://img.shields.io/github/stars/beerfactory/hbmqtt) ![license](https://img.shields.io/github/license/beerfactory/hbmqtt)
 * [aiomqtt](https://github.com/mossblaser/aiomqtt) - Direct wrapper around paho-mqtt  
   ![GitHub stars](https://img.shields.io/github/stars/mossblaser/aiomqtt) ![license](https://img.shields.io/github/license/mossblaser/aiomqtt)
 * [aio-mqtt](https://github.com/NotJustAToy/aio-mqtt) - Written from scratch  
   ![GitHub stars](https://img.shields.io/github/stars/NotJustAToy/aio-mqtt) ![license](https://img.shields.io/github/license/NotJustAToy/aio-mqtt)

This is not an exhaustive list.

## Dependencies

There is only a single dependency:

 * [paho-mqtt](https://github.com/eclipse/paho.mqtt.python)  
   ![GitHub stars](https://img.shields.io/github/stars/eclipse/paho.mqtt.python) ![license](https://img.shields.io/github/license/eclipse/paho.mqtt.python)

## License

[license](https://img.shields.io/github/license/sbtinstruments/asyncio-mqtt)

Note that paho-mqtt is dual-licensed. One of the licenses is the so-called [Eclipse Distribution License v1.0](https://www.eclipse.org/org/documents/edl-v10.php). It is almost word-for-word identical to the [BSD 3-clause License](https://opensource.org/licenses/BSD-3-Clause). There only differences are:
 * One use of "COPYRIGHT OWNER" (EDL) instead of "COPYRIGHT HOLDER" (BSD)
 * One use of "Eclipse Foundation, Inc." (EDL) instead of "copyright holder" (bsd)