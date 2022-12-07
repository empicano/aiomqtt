# Filtering messages

Imagine you're measuring temperature and humidity on the outside and inside, and our topics look like this: `temperature/outside`. You want to receive all types of measurements but handle them differently. _asyncio-mqtt_ provides `Topic.matches()` to make this easy:

```python
import asyncio
import asyncio_mqtt as aiomqtt


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        async with client.messages() as messages:
            await client.subscribe("#")
            async for message in messages:
                if message.topic.matches("humidity/outside"):
                    print(f"[humidity/outside] {message.payload}")
                if message.topic.matches("+/inside"):
                    print(f"[+/inside] {message.payload}")
                if message.topic.matches("temperature/#"):
                    print(f"[temperature/#] {message.payload}")


asyncio.run(main())
```

Note that in our example, messages to `temperature/inside` are handled twice!
