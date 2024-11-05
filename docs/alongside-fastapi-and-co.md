# Alongside FastAPI & Co.

Many web frameworks take control over the main function, which can make it tricky to figure out where to create the `Client` and how to share this connection.

With [FastAPI](https://github.com/tiangolo/fastapi) (`0.93+`) and [Starlette](https://github.com/encode/starlette) you can use lifespan context managers to safely set up a global client instance. This is a minimal working example of FastAPI side by side with an aiomqtt listener task and message publication on `GET /`:

```python
import asyncio
from typing import Annotated
import aiomqtt
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI


async def listen(client):
    async for message in client.messages:
        print(message.payload)


client = None


async def get_mqtt():
    yield client


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    async with aiomqtt.Client("test.mosquitto.org") as c:
        # Make client globally available
        client = c
        # Listen for MQTT messages in (unawaited) asyncio task
        await client.subscribe("humidity/#")
        loop = asyncio.get_event_loop()
        task = loop.create_task(listen(client))
        yield
        # Cancel the task
        task.cancel()
        # Wait for the task to be cancelled
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def publish(client: Annotated[aiomqtt.Client, Depends(get_mqtt)]):
    await client.publish("humidity/outside", 0.38)
```

```{note}
This is a combination of some concepts addressed in more detail in other sections: The connection is shared between the listener task and the routes, as explained in [](connecting-to-the-broker.md#sharing-the-connection). We don't immediately await the listener task in order to avoid blocking other code, as explained in [](subscribing-to-a-topic.md#listening-without-blocking).
```

```{tip}
With Starlette you can yield the initialized client to [the lifespan's state](https://www.starlette.io/lifespan/) instead of using global variables and dependency injection.
```
