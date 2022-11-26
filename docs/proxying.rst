Proxying
========

You can configure proxying via the ``ProxySettings`` class. The parameters are directly passed through to paho-mqtt's ``proxy_set`` functionality. Both SOCKS and HTTP proxies are supported. Note that proxying is an extra feature (even in paho-mqtt) that requires the ``PySocks`` dependency. See `paho-mqtt's documentation <https://github.com/eclipse/paho.mqtt.python>`_ for more information about the individual parameters.

.. code-block:: python

   import asyncio
   import asyncio_mqtt as aiomqtt
   import socks


   proxy_params = aiomqtt.ProxySettings(
       proxy_type=socks.HTTP,
       proxy_addr="www.example.com",
       proxy_rdns=True,
       proxy_username=None,
       proxy_password=None,
   )

   async def main():
       async with aiomqtt.Client("test.mosquitto.org", proxy=proxy_params) as client:
           await client.publish("measurements/humidity", payload=0.38)


   asyncio.run(main())
