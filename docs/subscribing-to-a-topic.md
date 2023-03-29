# Subscribing to a topic

To receive messages for a topic, we need to subscribe to it and listen for messages. A minimal working example looks like this:

```python
import asyncio
import asyncio_mqtt as aiomqtt


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        async with client.messages() as messages:
            await client.subscribe("humidity/#")
            async for message in messages:
                print(message.payload)


asyncio.run(main())
```

```{tip}
You can set the [Quality of Service](publishing-a-message.md#quality-of-service-qos) of the subscription by passing the `qos` parameter to `subscribe()`.
```

## Filtering messages

Imagine you're measuring temperature and humidity on the outside and inside, and our topics look like this: `temperature/outside`. You want to receive all types of measurements but handle them differently.

asyncio-mqtt provides `Topic.matches()` to make this easy:

```python
import asyncio
import asyncio_mqtt as aiomqtt


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        async with client.messages() as messages:
            await client.subscribe("#")
            async for message in messages:
                if message.topic.matches("humidity/outside"):
                    print(f"[humidity/outside] {message.payload}")
                if message.topic.matches("+/inside"):
                    print(f"[+/inside] {message.payload}")
                if message.topic.matches("temperature/#"):
                    print(f"[temperature/#] {message.payload}")


asyncio.run(main())
```

```{note}
In our example, messages to `temperature/inside` are handled twice!
```

## Listening without blocking

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

### Fire and forget

Another way to avoid blocking the execution is to start the listener in a fire-and-forget way. The idea is to use asyncio's `create_task` without `await`ing the created task:

```{caution}
You need to be a bit careful with this approach. Exceptions raised in asyncio tasks are propagated only if we `await` the task. In this case, we explicitly don't.

This means that you need to handle all possible exceptions _inside_ the fire-and-forget task. If you don't, any exceptions will be silently ignored until the program exits.
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

## Stop listening

You might want to have a listener task running alongside other code, and then stop it when you're done. You can use [`Task.cancel()`](https://docs.python.org/3/library/asyncio-task.html#asyncio.Task.cancel) for this:

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
    # Listen for MQTT messages in (unawaited) asyncio task
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

### Stop listening after a certain amount of time

For use cases where you only want to listen to messages for a certain amount of time, Python `3.11` introduced a neat feature called [timeouts](https://docs.python.org/3/library/asyncio-task.html#timeouts):

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
