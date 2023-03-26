# Reconnecting

You can reconnect when the connection to the broker is lost by wrapping your code in a `try/except`-block and listening for `MqttError`s.

```python
import asyncio
import asyncio_mqtt as aiomqtt


async def main():
    reconnect_interval = 5  # In seconds
    while True:
        try:
            async with aiomqtt.Client("test.mosquitto.org") as client:
                async with client.messages() as messages:
                    await client.subscribe("humidity/#")
                    async for message in messages:
                        print(message.payload.decode())
        except aiomqtt.MqttError as error:
            print(f'Error "{error}". Reconnecting in {reconnect_interval} seconds.')
            await asyncio.sleep(reconnect_interval)



asyncio.run(main())
```

## Why can't I `connect`/`disconnect` manually?

Managing connections directly by calling `connect` and `disconnect` can be a bit tricky. For instance, when disconnecting the client, you have to ensure that no other task depends on the connection. There are many other similar situations where it's easy to make mistakes. Context managers handle all connection and disconnection logic for you, making them easier and less error-prone than `connect`/`disconnect`.

Supporting both would add a lot of complexity to asyncio-mqtt. To keep the maintainer burden manageable, we only focus on context managers.
