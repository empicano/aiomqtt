# Stop listening

You might want to have a listener task running alongside other code, and then stop it when you're done. You can use [`Task.cancel()`](https://docs.python.org/3/library/asyncio-task.html#asyncio.Task.cancel) for this.

Here's a minimal working example:

```python
import asyncio
import asyncio_mqtt as aiomqtt


async def listen():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        async with client.messages() as messages:
            await client.subscribe("humidity/#")
            async for message in messages:
                print(message.payload)


async def main():
    loop = asyncio.get_event_loop()
    # Listen for mqtt messages in an (unawaited) asyncio task
    task = loop.create_task(listen())
    # Do something else for a while
    await asyncio.sleep(5)
    # Cancel the task
    task.cancel()
    # Wait for the task to be cancelled
    try:
        await task
    except asyncio.CancelledError:
        pass


asyncio.run(main())
```

## Stop listening after a certain amount of time

For use cases where you only want to listen to messages for a certain amount of time, Python 3.11 introduced a neat feature called [timeouts](https://docs.python.org/3/library/asyncio-task.html#timeouts):

```python
import asyncio
import asyncio_mqtt as aiomqtt


async def listen():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        async with client.messages() as messages:
            await client.subscribe("humidity/#")
            async for message in messages:
                print(message.payload)


async def main():
    try:
        # Cancel the listener task after 5 seconds
        async with asyncio.timeout(5):
            await listen()
    # Ignore the resulting TimeoutError
    except asyncio.TimeoutError:
        pass


asyncio.run(main())
```
