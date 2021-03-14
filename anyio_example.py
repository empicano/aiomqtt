#!/usr/bin/python3.8
import anyio
from contextlib import AsyncExitStack, asynccontextmanager
from random import randrange
from asyncio_mqtt import Client, MqttError


async def advanced_example(client):
    async with anyio.create_task_group() as tg:
        # You can create any number of topic filters
        topic_filters = (
            "floors/+/humidity",
            "floors/rooftop/#"
            # 👉 Try to add more filters!
        )
        for topic_filter in topic_filters:
            # Log all messages that matches the filter
            manager = client.filtered_messages(topic_filter)
            template = f'[topic_filter="{topic_filter}"] {{}}'
            tg.spawn(log_messages, manager, template)

        # Messages that doesn't match a filter will get logged here
        tg.spawn(log_messages, client.unfiltered_messages(), "[unfiltered] {}")

        # Subscribe to topic(s)
        # 🤔 Note that we subscribe *after* starting the message
        # loggers. Otherwise, we may miss retained messages.
        await client.subscribe("my_floors/#")

        # Publish a random value to each of these topics
        topics = (
            "my_floors/basement/humidity",
            "my_floors/rooftop/humidity",
            "my_floors/rooftop/illuminance",
            # 👉 Try to add more topics!
        )
        tg.spawn(post_to_topics, client, topics)
        # End of scope. Wait for everything to complete (or fail due
        # to, e.g., network errors). All of this happens inside tg.__aexit__.

        # Alternatively, you can cancel the task group after a while.
        # await anyio.sleep(8)
        # tg.cancel_scope.cancel()


async def post_to_topics(client, topics):
    while True:
        for topic in topics:
            # Send some large packets to test the write loop as well
            message_len = randrange(10 * 1024 ** 2)  # At most 10 MiB
            message = bytes(message_len)
            print(
                f'[topic="{topic}"] Publishing message of length {len(message) / 1024**2:0.1f} MiB'
            )
            await client.publish(topic, message, qos=1)
            await anyio.sleep(2)


async def log_messages(cm, template):
    async with cm as messages:
        async for message in messages:
            print(template.format(len(message.payload)))


async def reconnect_indefinitely(client):
    # Run the advanced_example indefinitely. Reconnect automatically
    # if the connection is lost.
    reconnect_interval = 3  # [seconds]
    while True:
        try:
            # Note that we can reuse the client over and over.
            # This fixes issue #27 and (partly) #48
            async with client:
                print("Connected to server.")
                await advanced_example(client)
            print("Disconnected from server.")
        except MqttError as error:
            print(f'Error "{error}". Reconnecting in {reconnect_interval} seconds.')
        finally:
            await anyio.sleep(reconnect_interval)


async def main():
    tg = anyio.create_task_group()
    async with tg:
        client = Client(tg, "localhost")
        await reconnect_indefinitely(client)


try:
    anyio.run(main)
except KeyboardInterrupt:
    print("User interrupted the program")
