Topic filters
=============

Let's take the example from the beginning again, but this time with messages in both ``measurements/humidity`` and ``measurements/temperature``. You want to receive both types of measurements but handle them differently. *asyncio-mqtt* has topic filters to make this easy:

.. code-block:: python

   import asyncio
   import asyncio_mqtt as aiomqtt
   import contextlib


   async def print_messages(messages, template):
       async for message in messages:
           print(template.format(message.payload))


   async def cancel_tasks(tasks):
       for task in tasks:
           if task.done():
               continue
           try:
               task.cancel()
               await task
           except asyncio.CancelledError:
               pass


   async def main():
       # We 💛 context managers. Let's create a stack to help us manage them.
       async with contextlib.AsyncExitStack() as stack:
           # Keep track of the asyncio tasks that we create, so that
           # we can cancel them on exit
           tasks = set()
           stack.push_async_callback(cancel_tasks, tasks)

           # Connect to MQTT broker
           client = aiomqtt.Client("test.mosquitto.org")
           await stack.enter_async_context(client)

           # You can create any number of topic filters
           topic_filters = (
               "measurements/humidity",
               "measurements/temperature"
               # 👉 Try to add more complex filters!
           )

           for topic_filter in topic_filters:
               # Print all messages that match the filter
               manager = client.filtered_messages(topic_filter)
               messages = await stack.enter_async_context(manager)
               template = f'[topic_filter="{topic_filter}"] {{}}'
               task = asyncio.create_task(print_messages(messages, template))
               tasks.add(task)

           # Handle messages that don't match a filter
           messages = await stack.enter_async_context(client.unfiltered_messages())
           task = asyncio.create_task(print_messages(messages, "[unfiltered] {}"))
           tasks.add(task)

           # Subscribe to topic(s)
           # 🤔 Note that we subscribe *after* starting the message
           # loggers. Otherwise, we may miss retained messages.
           await client.subscribe("measurements/#")

           # Wait for everything to complete (or fail due to, e.g., network errors)
           await asyncio.gather(*tasks)


   asyncio.run(main())
