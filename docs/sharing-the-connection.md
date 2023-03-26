# Sharing the connection

In many cases, you'll want to send and receive messages in different locations in your code. You could create a new client each time, but

1. this is not very performant, and
2. you'll use a lot more network bandwidth.

You can share the connection by passing the `Client` instance to all functions that need it:

```python
import asyncio
import asyncio_mqtt as aiomqtt


async def publish_humidity(client):
    await client.publish("humidity/outside", payload=0.38)


async def publish_temperature(client):
    await client.publish("temperature/outside", payload=28.3)


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        await publish_humidity(client)
        await publish_temperature(client)


asyncio.run(main())
```

## Side by side with web frameworks

Many web frameworks take control over the "main" function, which can make it tricky to figure out where to create and connect the `Client` and how to share this connection.

With [FastAPI](https://github.com/tiangolo/fastapi) (`0.93+`) and [Starlette](https://github.com/encode/starlette) you can use lifespan context managers to safely set up a global client instance. Here's a minimal working example of FastAPI side by side with an asyncio-mqtt listener task and message publication on `GET /`:

```{note}
We don't immediately await the listener task in order to avoid blocking the server code, as explained in [](../listening-without-blocking).
```

```python
import asyncio
import asyncio_mqtt as aiomqtt
import contextlib
import fastapi


async def listen(client):
    async with client.messages() as messages:
        await client.subscribe("humidity/#")
        async for message in messages:
            print(message.payload)


client = None


@contextlib.asynccontextmanager
async def lifespan(app):
    global client
    async with aiomqtt.Client("test.mosquitto.org") as c:
        # Make client globally available
        client = c
        # Start MQTT listener in (unawaited) asyncio task
        loop = asyncio.get_event_loop()
        task = loop.create_task(listen(client))
        yield
        task.cancel()
        # Wait for the MQTT listener task to be cancelled
        try:
            await task
        except asyncio.CancelledError:
            pass


app = fastapi.FastAPI(lifespan=lifespan)


@app.get("/")
async def publish():
    await client.publish("humidity/outside", 0.38)
```
