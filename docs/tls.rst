TLS
===

You can configure TLS via the ``TLSParameters`` class. The parameters are directly passed through to paho-mqtt's ``tls_set`` function. See `paho-mqtt's documentation <https://github.com/eclipse/paho.mqtt.python>`_ for more information about the individual parameters.

.. code-block:: python

   import asyncio
   import asyncio_mqtt as aiomqtt
   import ssl


   tls_params = aiomqtt.TLSParameters(
       ca_certs=None,
       certfile=None,
       keyfile=None,
       cert_reqs=ssl.CERT_REQUIRED,
       tls_version=ssl.PROTOCOL_TLS,
       ciphers=None,
   )


   async def main():
       async with aiomqtt.Client("test.mosquitto.org", tls_params=tls_params) as client:
           await client.publish("measurements/humidity", payload=0.38)


   asyncio.run(main())
