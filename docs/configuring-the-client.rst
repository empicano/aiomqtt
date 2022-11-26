Configuring the client
======================

You can configure quite a few things when initializing the client. These are all the possible parameters together with their default values. See `paho-mqtt's documentation <https://github.com/eclipse/paho.mqtt.python>`_ for more information about the individual parameters.

.. code-block:: python

   import asyncio_mqtt as aiomqtt
   import paho.mqtt as mqtt

   aiomqtt.Client(
       hostname="test.mosquitto.org",  # The only non-optional parameter
       port=1883,
       username=None,
       password=None,
       logger=None,
       client_id=None,
       tls_context=None,
       tls_params=None,
       proxy=None,
       protocol=None,
       will=None,
       clean_session=None,
       transport="tcp",
       keepalive=60,
       bind_address="",
       bind_port=0,
       clean_start=mqtt.client.MQTT_CLEAN_START_FIRST_ONLY,
       properties=None,
       message_retry_set=20,
       socket_options=(),
       max_concurrent_outgoing_calls=None,
       websocket_path=None,
       websocket_headers=None,
   )
