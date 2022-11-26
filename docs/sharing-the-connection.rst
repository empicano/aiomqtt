Sharing the connection
======================

In many cases, you'll want to send and receive messages in different locations in your code. You could create a new client each time, but

#. this is not very performant, and
#. you'll use a lot more network bandwidth.

You can share the connection by passing the ``Client`` instance to all functions that need it:

.. code-block:: python

   import asyncio
   import asyncio_mqtt as aiomqtt


   async def publish_humidity(client):
       await client.publish("measurements/humidity", payload=0.38)


   async def publish_temperature(client):
       await client.publish("measurements/temperature", payload=28.3)


   async def main():
       async with aiomqtt.Client("test.mosquitto.org") as client:
           await publish_humidity(client)
           await publish_temperature(client)


   asyncio.run(main())

Side by side with web frameworks
--------------------------------

Most web frameworks take control over the "main" function, which makes it difficult to figure out where to create and connect the ``Client`` and how to share this connection.

Some frameworks like `Starlette <https://github.com/encode/starlette>`_ directly support lifespan context managers, with which you can safely set up a global client instance that you can then pass to functions that need it, just like before:

.. code-block:: python

    import asyncio
    import asyncio_mqtt as aiomqtt
    import starlette.applications
    import contextlib


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

FastAPI (which is built upon Starlette) doesn't expose that API yet, but there are `multiple <https://github.com/tiangolo/fastapi/pull/5503>`_ `open PRs <https://github.com/tiangolo/fastapi/pull/2944>`_ to add it. In the meantime, you can work around it via FastAPI's dependency injection.

Why can't I ``connect`` / ``disconnect`` manually?
--------------------------------------------------

Managing a connection by calling ``connect`` and ``disconnect`` directly is a bit tricky. For example, when you're disconnecting the client, you'd have to make sure that there's no other task that still relies on the connection. There are many similar situations where something can easily go wrong.

Context managers take care of all connection and disconnection logic for you, in a way that makes it very difficult to shoot yourself in the foot. They are a lot easier and less error-prone to use than ``connect`` / ``disconnect`` .

Supporting both context managers and manual ``connect`` / ``disconnect`` would add a lot of complexity to *asyncio-mqtt*. To keep the maintainer burden manageable, we focus only on the preferred option: context managers.
