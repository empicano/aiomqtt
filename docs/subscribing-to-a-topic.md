# Subscribing to a topic

To receive messages for a topic, we need to subscribe to it and listen for messages. A minimal working example that listens for messages to the `temperature/#` wildcard looks like this:

```python
import asyncio
import aiomqtt


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        async with client.messages() as messages:
            await client.subscribe("temperature/#")
            async for message in messages:
                print(message.payload)


asyncio.run(main())
```

Now you can use the [minimal publisher example](publishing-a-message.md) to publish a message to `temperature/outside` and see it appear in the console.

````{important}
Messages are handled _one after another_. If a message takes a long time to handle, other [messages are queued](#the-message-queue) and handled only after the first one is done.

You can handle messages in parallel by using an `asyncio.TaskGroup` like so:

```python
import asyncio
import aiomqtt


async def handle(message):
    await asyncio.sleep(5)  # Simulate some I/O-bound work
    print(message.payload)


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        async with client.messages() as messages:
            await client.subscribe("temperature/#")
            async with asyncio.TaskGroup() as tg:
                async for message in messages:
                    tg.create_task(process(message))


asyncio.run(main())
```

Note that this only makes sense if your message handling is I/O-bound. If it's CPU-bound, you should spawn multiple processes instead.
````

```{tip}
You can set the [Quality of Service](publishing-a-message.md#quality-of-service-qos) of the subscription by passing the `qos` parameter to `subscribe()`.
```

## Filtering messages

Imagine we measure temperature and humidity on the outside and inside, and our topics look like this: `temperature/outside`. We want to receive all types of measurements but handle them differently.

aiomqtt provides `Topic.matches()` to make this easy:

```python
import asyncio
import aiomqtt


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        async with client.messages() as messages:
            await client.subscribe("temperature/#")
            await client.subscribe("humidity/#")
            async for message in messages:
                if message.topic.matches("humidity/inside"):
                    print(f"[humidity/outside] {message.payload}")
                if message.topic.matches("+/outside"):
                    print(f"[+/inside] {message.payload}")
                if message.topic.matches("temperature/#"):
                    print(f"[temperature/#] {message.payload}")


asyncio.run(main())
```

```{note}
In our example, messages to `temperature/outside` are handled twice!
```

## The message queue

Messages are buffered in a queue internally. The default queue is `asyncio.Queue` which returns messages on a FIFO ("first in first out") basis. You can pass [other asyncio queues](https://docs.python.org/3/library/asyncio-queue.html) as `queue_class` to `messages()` to modify the order in which messages are returned, e.g. `asyncio.LifoQueue`.

If you want to queue based on priority, you can subclass `asyncio.PriorityQueue`. This queue returns messages in priority order (lowest priority first). In case of ties, messages with lower message identifiers are returned first.

Let's say we measure temperature and humidity again, but we want to prioritize humidity messages:

```python
import asyncio
import aiomqtt


class CustomPriorityQueue(asyncio.PriorityQueue):
    def _put(self, item):
        priority = 2
        if item.topic.matches("humidity/#"):  # Assign priority
            priority = 1
        super()._put((priority, item))

    def _get(self):
        return super()._get()[1]


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        async with client.messages(queue_class=CustomPriorityQueue) as messages:
            await client.subscribe("temperature/#")
            await client.subscribe("humidity/#")
            async for message in messages:
                print(message.payload)


asyncio.run(main())
```

```{note}
By default, the size of the queue is unlimited. You can limit it by passing the `queue_maxsize` parameter to `messages()`.
```

## Listening without blocking

When you run the minimal example for subscribing and listening for messages, you'll notice that the program doesn't finish. Waiting for messages through the `messages()` generator blocks the execution of everything that comes afterward.

In case you want to run other code after starting your listener, this is not practical.

You can use `asyncio.TaskGroup` (or `asyncio.gather` for Python `<3.11`) to safely run other tasks alongside the MQTT listener:

```python
import asyncio
import aiomqtt


async def sleep(seconds):
    await asyncio.sleep(seconds)
    print(f"Slept for {seconds} seconds!")


async def listen():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        async with client.messages() as messages:
            await client.subscribe("temperature/#")
            async for message in messages:
                print(message.payload)


async def main():
    async with asyncio.TaskGroup() as tg:
        tg.create_task(sleep(2))
        tg.create_task(listen())  # Start the listener task
        tg.create_task(sleep(3))
        tg.create_task(sleep(1))


asyncio.run(main())
```

In case task groups are not an option (e.g. because you run aiomqtt [side by side with a web framework](side-by-side-with-web-frameworks.md)) you can start the listener in a fire-and-forget way. The idea is to use asyncio's `create_task` but not `await` the created task:

```{caution}
You need to be a bit careful with this approach. Exceptions raised in asyncio tasks are propagated only when we `await` the task. In this case, we explicitly don't.

This means that you need to handle all possible exceptions _inside_ the fire-and-forget task. Any unhandled exceptions will be silently ignored until the program exits.
```

```python
import asyncio
import aiomqtt


async def listen():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        async with client.messages() as messages:
            await client.subscribe("temperature/#")
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
        await asyncio.sleep(1)


asyncio.run(main())
```

```{important}
You [need to keep a reference to the task](https://docs.python.org/3/library/asyncio-task.html#creating-tasks) so it doesn't get garbage collected mid-execution. That's what we're using the `background_tasks` set in our example for.
```

## Stop listening

You might want to have a listener task running alongside other code, and then stop it when you're done. You can use [`Task.cancel()`](https://docs.python.org/3/library/asyncio-task.html#asyncio.Task.cancel) for this:

```python
import asyncio
import aiomqtt


async def listen():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        async with client.messages() as messages:
            await client.subscribe("temperature/#")
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

## Stop listening after timeout

For use cases where you only want to listen to messages for a certain amount of time, Python `3.11` introduced a neat feature called [timeouts](https://docs.python.org/3/library/asyncio-task.html#timeouts):

```python
import asyncio
import aiomqtt


async def listen():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        async with client.messages() as messages:
            await client.subscribe("temperature/#")
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
