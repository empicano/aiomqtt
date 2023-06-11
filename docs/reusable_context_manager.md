# Reusable context manager

The client object will now support reusable (but not reentrant!), Related[#212](https://github.com/sbtinstruments/asyncio-mqtt/issues/212)

```python
import asyncio
import asyncio_mqtt as aiomqtt

client = aiomqtt.Client("test.mosquitto.org")

async def main():
    interval = 5  # Seconds
    while True:
        try:
            async with client:  # This is reusable
                async with client.messages() as messages:
                    await client.subscribe("humidity/#")
                    async for message in messages:
                        print(message.payload)
        except aiomqtt.MqttError:
            print(f'Connection lost; Reconnecting in {interval} seconds ...')
            await asyncio.sleep(interval)


asyncio.run(main())
```
