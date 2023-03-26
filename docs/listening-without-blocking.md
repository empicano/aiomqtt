# Listening without blocking

When you run the minimal example for subscribing and listening for messages, you'll notice that the program doesn't finish until you stop it. Waiting for messages through the `messages()` generator blocks the execution of everything that comes afterward.

In case you want to run other code after starting your listener, this is not practical.

You can use `asyncio.TaskGroup` (or `asyncio.gather` for Python `<3.11`) to safely run other tasks alongside the MQTT listener:

```python
import asyncio
import asyncio_mqtt as aiomqtt


async def sleep(seconds):
    await asyncio.sleep(seconds)
    print(f"Slept for {seconds} seconds!")


async def listen():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        async with client.messages() as messages:
            await client.subscribe("humidity/#")
            async for message in messages:
                print(message.payload)


async def main():
    async with asyncio.TaskGroup() as group:
        group.create_task(sleep(2))
        group.create_task(listen())  # Start listening
        group.create_task(sleep(3))
        group.create_task(sleep(1))


asyncio.run(main())
```

## Fire and forget

Another way to avoid blocking is to start the listener in a fire-and-forget way.

This is especially useful if you're using asyncio-mqtt alongside an async web framework. The framework usually runs in an endless loop, so `await`ing the listener task is not possible.

The idea is to use asyncio's `create_task` without `await`ing the created task:

```{caution}
You need to be a bit careful with this approach. Exceptions raised in asyncio tasks are propagated only if we `await` the task. In this case, we explicitly don't.

This means that you need to handle all possible exceptions _inside_ the fire-and-forget task. If you don't, the exception will be silently ignored until the program exits.
```

```python
import asyncio
import asyncio_mqtt as aiomqtt


async def listen():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        async with client.messages() as messages:
            await client.subscribe("humidity/#")
            async for message in messages:
                print(message.payload)


background_tasks = set()


async def main():
    loop = asyncio.get_event_loop()
    # Listen for mqtt messages in an (unawaited) asyncio task
    task = loop.create_task(listen())
    # Save a reference to the task so it doesn't get garbage collected
    background_tasks.add(task)
    task.add_done_callback(background_tasks.remove)

    # Infinitely do something else (e.g. handling HTTP requests)
    while True:
        await asyncio.sleep(2)


asyncio.run(main())
```

```{important}
You [need to keep a reference to the task](https://docs.python.org/3/library/asyncio-task.html#creating-tasks) so it doesn't get garbage collected mid-execution. That's what we're using the `background_tasks` set in our example for.
```
