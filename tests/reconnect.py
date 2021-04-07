import asyncio
import logging
from asyncio_mqtt import Client, MqttError


logger = logging.getLogger(__name__)


async def tick():
    while True:
        logger.info("Tick")
        await asyncio.sleep(1)


async def test():
    while True:
        try:
            logger.info("Connecting to MQTT")
            async with Client("localhost") as client:
                logger.info("Connection to MQTT open")
                async with client.unfiltered_messages() as messages:
                    await client.subscribe("#")
                    async for message in messages:
                        logger.info(
                            "Message %s %s", message.topic, message.payload.decode()
                        )
                # await asyncio.sleep(2)
        except MqttError as e:
            logger.error("Connection to MQTT closed: " + str(e))
        except Exception:
            logger.exception("Connection to MQTT closed")
        await asyncio.sleep(3)


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    asyncio.get_event_loop().run_until_complete(asyncio.wait([test(), tick()]))


if __name__ == "__main__":
    main()
