# Listening without blocking

If you run the basic example for subscribing and listening for messages, you'll notice that the program doesn't finish until you stop it. Waiting for messages blocks the execution of everything that comes afterward. If you want to run other code after starting your listener (e.g. handling HTTP requests in a web framework) you don't want this.

To solve this, you can use asyncio's `create_task` without `await`ing the created task. The concept is similar to starting a new thread without `join`ing it in a multithreaded application.

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
    # Wait for messages in (unawaited) asyncio task
    loop = asyncio.get_event_loop()
    task = loop.create_task(listen())
    # This will still run!
    print("Magic!")
    # If you don't await the task here the program will simply finish.
    # However, if you're using an async web framework you usually don't have to await
    # the task, as the framework runs in an endless loop.
    await task


asyncio.run(main())
```
