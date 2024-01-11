# Reconnection

Network connections are inherently unstable and can fail at any time. Especially for long-running applications, this can be a challenge.

To make an application resilient against connection failures, we have to be able to detect failures and recover from them.

The `Client` context is designed to be [reusable (but not reentrant)](https://docs.python.org/3/library/contextlib.html#reusable-context-managers). This means that we can wrap our code in a `try`/`except`-block, listen for `MqttError`s, and reconnect like so:

```python
import asyncio
import aiomqtt


async def main():
    client = aiomqtt.Client("test.mosquitto.org")
    interval = 5  # Seconds
    while True:
        try:
            async with client:
                await client.subscribe("humidity/#")
                async for message in client.messages:
                    print(message.payload)
        except aiomqtt.MqttError:
            print(f"Connection lost; Reconnecting in {interval} seconds ...")
            await asyncio.sleep(interval)


asyncio.run(main())
```
