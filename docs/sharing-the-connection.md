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

With [FastAPI](https://github.com/tiangolo/fastapi) (`0.93.0+`) and [Starlette](https://github.com/encode/starlette) you can use lifespan context managers to safely set up a global client instance that you can then pass to functions that need it, just like before:

```python
import asyncio
import asyncio_mqtt as aiomqtt
import contextlib
import starlette.applications


client = None


@contextlib.asynccontextmanager
async def lifespan(app):
    global client
    async with aiomqtt.Client("test.mosquitto.org") as c:
        client = c
        yield


app = starlette.applications.Starlette(
    routes=[],
    lifespan=lifespan,
)
```

## Why can't I `connect`/`disconnect` manually?

Managing connections directly by calling `connect` and `disconnect` can be a bit tricky. For instance, when disconnecting the client, you have to ensure that no other task depends on the connection. There are many other similar situations where it's easy to make mistakes. Context managers handle all connection and disconnection logic for you, making them easier and less error-prone than `connect`/`disconnect`.

Supporting both would add a lot of complexity to `asyncio-mqtt`. To keep the maintainer burden manageable, we only focus on context managers.
