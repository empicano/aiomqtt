import anyio
import anyio.abc
import pytest

from asyncio_mqtt import Client
from asyncio_mqtt.client import ProtocolVersion, Will

pytestmark = pytest.mark.anyio


async def test_client_filtered_messages() -> None:
    topic_header = "tests/asyncio_mqtt/filtered_messages/"
    good_topic = topic_header + "good"
    bad_topic = topic_header + "bad"

    async def handle_messages(tg: anyio.abc.TaskGroup) -> None:
        async with client.filtered_messages(good_topic) as messages:
            async for message in messages:
                assert message.topic == good_topic
                tg.cancel_scope.cancel()

    async with Client("test.mosquitto.org") as client:
        async with anyio.create_task_group() as tg:
            await client.subscribe(topic_header + "#")
            tg.start_soon(handle_messages, tg)
            await client.publish(bad_topic)
            await client.publish(good_topic)


async def test_client_unfiltered_messages() -> None:
    topic_header = "tests/asyncio_mqtt/unfiltered_messages/"
    topic_filtered = topic_header + "filtered"
    topic_unfiltered = topic_header + "unfiltered"

    async def handle_unfiltered_messages(tg: anyio.abc.TaskGroup) -> None:
        async with client.unfiltered_messages() as messages:
            async for message in messages:
                assert message.topic == topic_unfiltered
                tg.cancel_scope.cancel()

    async def handle_filtered_messages() -> None:
        async with client.filtered_messages(topic_filtered) as messages:
            async for message in messages:
                assert message.topic == topic_filtered

    async with Client("test.mosquitto.org") as client:
        async with anyio.create_task_group() as tg:
            await client.subscribe(topic_header + "#")
            tg.start_soon(handle_filtered_messages)
            tg.start_soon(handle_unfiltered_messages, tg)
            await client.publish(topic_filtered)
            await client.publish(topic_unfiltered)


async def test_client_unsubscribe() -> None:
    topic_header = "tests/asyncio_mqtt/unsubscribe/"
    topic1 = topic_header + "1"
    topic2 = topic_header + "2"

    async def handle_messages(tg: anyio.abc.TaskGroup) -> None:
        async with client.unfiltered_messages() as messages:
            i = 0
            async for message in messages:
                if i == 0:
                    assert message.topic == topic1
                elif i == 1:
                    assert message.topic == topic2
                    tg.cancel_scope.cancel()
                i += 1

    async with Client("test.mosquitto.org") as client:
        async with anyio.create_task_group() as tg:
            await client.subscribe(topic1)
            await client.subscribe(topic2)
            tg.start_soon(handle_messages, tg)
            await client.publish(topic1)
            await client.unsubscribe(topic1)
            await client.publish(topic1)
            await client.publish(topic2)


@pytest.mark.parametrize(
    "protocol, length",
    ((ProtocolVersion.V31, 22), (ProtocolVersion.V311, 0), (ProtocolVersion.V5, 0)),
)
async def test_client_id(protocol: ProtocolVersion, length: int) -> None:
    client = Client("test.mosquitto.org", protocol=protocol)
    assert len(client.id) == length


async def test_client_will() -> None:
    topic = "tests/asyncio_mqtt/will"
    event = anyio.Event()

    async def launch_client() -> None:
        with anyio.CancelScope(shield=True) as cs:
            async with Client("test.mosquitto.org") as client:
                await client.subscribe(topic)
                event.set()
                async with client.filtered_messages(topic) as messages:
                    async for message in messages:
                        assert message.topic == topic
                        cs.cancel()

    async with anyio.create_task_group() as tg:
        tg.start_soon(launch_client)
        await event.wait()
        async with Client("test.mosquitto.org", will=Will(topic)) as client:
            client._client._sock_close()  # type: ignore[attr-defined]
