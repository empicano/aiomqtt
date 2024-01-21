# Migration guide: v2.0.0

Version 2.0.0 introduces some breaking changes. This page aims to help you migrate to this new major version. The relevant changes are:

- The deprecated `connect` and `disconnect` methods have been removed
- The deprecated `filtered_messages` and `unfiltered_messages` methods have been removed
- User-managed queues for incoming messages have been replaced with a single client-wide queue
- Some arguments to the `Client` have been renamed or removed

## Changes to the client lifecycle

The deprecated `connect` and `disconnect` methods have been removed. The best way to connect and disconnect from the broker is through the client's context manager:

```python
import asyncio
import aiomqtt


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        await client.publish("temperature/outside", payload=28.4)


asyncio.run(main())
```

If your use case does not allow you to use a context manager, you can use the client’s `__aenter__` and `__aexit__` methods almost interchangeably in place of the removed `connect` and `disconnect` methods.

The `__aenter__` and `__aexit__` methods are designed to be called by the `async with` statement when the execution enters and exits the context manager. However, we can also execute them manually:

```python
import asyncio
import aiomqtt


async def main():
    client = aiomqtt.Client("test.mosquitto.org")
    await client.__aenter__()
    try:
        await client.publish("temperature/outside", payload=28.4)
    finally:
        await client.__aexit__(None, None, None)


asyncio.run(main())
```

`__aenter__` is equivalent to `connect`. `__aexit__` is equivalent to `disconnect` except that it forces disconnection instead of throwing an exception in case the client cannot disconnect cleanly.

```{note}
`__aexit__` expects three arguments: `exc_type`, `exc`, and `tb`. These arguments describe the exception that caused the context manager to exit, if any. You can pass `None` to all of these arguments in a manual call to `__aexit__`.
```

## Changes to the message queue

The `filtered_messages`, `unfiltered_messages`, and `messages` methods have been removed and replaced with a single client-wide message queue.

For previous versions, a minimal example of printing all messages (unfiltered) looked like this:

```python
import asyncio
import aiomqtt


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        await client.subscribe("temperature/#")
        async with client.messages() as messages:
            async for message in messages:
                print(message.payload)


asyncio.run(main())
```

We now no longer need the line `async with client.messages() as messages:`, but instead access the message generator directly with `client.messages`:

```python
import asyncio
import aiomqtt


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        await client.subscribe("temperature/#")
        async for message in client.messages:
            print(message.payload)


asyncio.run(main())
```

To handle messages from different topics differently, we can use `Topic.matches()`:

```python
import asyncio
import aiomqtt


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        await client.subscribe("temperature/#")
        await client.subscribe("humidity/#")
        async for message in client.messages:
            if message.topic.matches("humidity/inside"):
                print(f"[humidity/inside] {message.payload}")
            if message.topic.matches("+/outside"):
                print(f"[+/outside] {message.payload}")
            if message.topic.matches("temperature/#"):
                print(f"[temperature/#] {message.payload}")


asyncio.run(main())
```

```{note}
In our example, messages to `temperature/outside` are handled twice!
```

The `filtered_messages`, `unfiltered_messages`, and `messages` methods created isolated message queues underneath, such that you could invoke them multiple times. From Version 2.0.0 on, the client maintains a single queue that holds all incoming messages, accessible via `Client.messages`.

If you continue to need multiple queues (e.g. because you have special concurrency requirements), you can build a "distributor" on top:

```python
import asyncio
import aiomqtt


async def temperature_consumer():
    while True:
        message = await temperature_queue.get()
        print(f"[temperature/#] {message.payload}")


async def humidity_consumer():
    while True:
        message = await humidity_queue.get()
        print(f"[humidity/#] {message.payload}")


temperature_queue = asyncio.Queue()
humidity_queue = asyncio.Queue()


async def distributor(client):
    # Sort messages into the appropriate queues
    async for message in client.messages:
        if message.topic.matches("temperature/#"):
            temperature_queue.put_nowait(message)
        elif message.topic.matches("humidity/#"):
            humidity_queue.put_nowait(message)


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        await client.subscribe("temperature/#")
        await client.subscribe("humidity/#")
        # Use a task group to manage and await all tasks
        async with asyncio.TaskGroup() as tg:
            tg.create_task(distributor(client))
            tg.create_task(temperature_consumer())
            tg.create_task(humidity_consumer())


asyncio.run(main())
```

## Changes to client arguments

- The `queue_class` and `queue_maxsize` arguments to `filtered_messages`, `unfiltered_messages`, and `messages` have been moved to the `Client` and have been renamed to `queue_type` and `max_queued_incoming_messages`
- The `max_queued_messages` client argument has been renamed to `max_queued_outgoing_messages`
- The deprecated `message_retry_set` client argument has been removed
