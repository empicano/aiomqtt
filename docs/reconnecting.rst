Reconnecting
============

You can reconnect when the connection to the broker is lost by wrapping your code in a ``try/except``-block and listening for ``MqttError`` s.

.. code-block:: python

   import asyncio
   import asyncio_mqtt as aiomqtt


   async def main():
       reconnect_interval = 5  # In seconds
       while True:
           try:
               async with aiomqtt.Client("test.mosquitto.org") as client:
                   async with client.filtered_messages('/measurements/humidity') as messages:
                       await client.subscribe("measurements/#")
                       async for message in messages:
                           print(message.payload.decode())
           except aiomqtt.MqttError as error:
               print(f'Error "{error}". Reconnecting in {reconnect_interval} seconds.')
               await asyncio.sleep(reconnect_interval)



   asyncio.run(main())
