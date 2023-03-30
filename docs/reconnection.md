# Reconnection

Network connections are inherently unstable and can fail at any time. Especially for long-running applications, this can be a problem.

The first challenge in making an application resilient to connection failures is to detect them in the first place. The second challenge is to recover from them.

A simple way to detect connection failures and recover from them is to wrap your code in a `try`/`except`-block and listen for `MqttError`s:

```python
import asyncio
import asyncio_mqtt as aiomqtt


async def main():
    interval = 5  # Seconds
    while True:
        try:
            async with aiomqtt.Client("test.mosquitto.org") as client:
                async with client.messages() as messages:
                    await client.subscribe("humidity/#")
                    async for message in messages:
                        print(message.payload)
        except aiomqtt.MqttError:
            print(f'Connection lost; Reconnecting in {interval} seconds ...')
            await asyncio.sleep(interval)


asyncio.run(main())
```
