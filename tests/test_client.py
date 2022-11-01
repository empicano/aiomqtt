from __future__ import annotations

import logging
import ssl
import sys
from pathlib import Path

import anyio
import anyio.abc
import paho.mqtt.client as mqtt
import pytest

from asyncio_mqtt import Client, ProtocolVersion, TLSParameters, Will
from asyncio_mqtt.types import PayloadType

pytestmark = pytest.mark.anyio

HOSTNAME = "test.mosquitto.org"
OS_PY_VERSION = sys.platform + "_" + ".".join(map(str, sys.version_info[:2]))
TOPIC_HEADER = OS_PY_VERSION + "/tests/asyncio_mqtt/"


async def test_client_filtered_messages() -> None:
    topic_header = TOPIC_HEADER + "filtered_messages/"
    good_topic = topic_header + "good"
    bad_topic = topic_header + "bad"

    async def handle_messages(tg: anyio.abc.TaskGroup) -> None:
        async with client.filtered_messages(good_topic) as messages:
            async for message in messages:
                assert message.topic == good_topic
                tg.cancel_scope.cancel()

    async with Client(HOSTNAME) as client:
        async with anyio.create_task_group() as tg:
            await client.subscribe(topic_header + "#")
            tg.start_soon(handle_messages, tg)
            await client.publish(bad_topic, 2)
            await client.publish(good_topic, 2)


async def test_client_unfiltered_messages() -> None:
    topic_header = TOPIC_HEADER + "unfiltered_messages/"
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

    async with Client(HOSTNAME) as client:
        async with anyio.create_task_group() as tg:
            await client.subscribe(topic_header + "#")
            tg.start_soon(handle_filtered_messages)
            tg.start_soon(handle_unfiltered_messages, tg)
            await client.publish(topic_filtered, 2)
            await client.publish(topic_unfiltered, 2)


async def test_client_unsubscribe() -> None:
    topic_header = TOPIC_HEADER + "unsubscribe/"
    topic1 = topic_header + "1"
    topic2 = topic_header + "2"

    async def handle_messages(tg: anyio.abc.TaskGroup) -> None:
        async with client.unfiltered_messages() as messages:
            is_first_message = True
            async for message in messages:
                if is_first_message:
                    assert message.topic == topic1
                    is_first_message = False
                else:
                    assert message.topic == topic2
                    tg.cancel_scope.cancel()

    async with Client(HOSTNAME) as client:
        async with anyio.create_task_group() as tg:
            await client.subscribe(topic1)
            await client.subscribe(topic2)
            tg.start_soon(handle_messages, tg)
            await client.publish(topic1, 2)
            await client.unsubscribe(topic1)
            await client.publish(topic1, 2)
            await client.publish(topic2, 2)


@pytest.mark.parametrize(
    "protocol, length",
    ((ProtocolVersion.V31, 22), (ProtocolVersion.V311, 0), (ProtocolVersion.V5, 0)),
)
async def test_client_id(protocol: ProtocolVersion, length: int) -> None:
    client = Client(HOSTNAME, protocol=protocol)
    assert len(client.id) == length


async def test_client_will() -> None:
    topic = TOPIC_HEADER + "will"
    event = anyio.Event()

    async def launch_client() -> None:
        with anyio.CancelScope(shield=True) as cs:
            async with Client(HOSTNAME) as client:
                await client.subscribe(topic)
                event.set()
                async with client.filtered_messages(topic) as messages:
                    async for message in messages:
                        assert message.topic == topic
                        cs.cancel()

    async with anyio.create_task_group() as tg:
        tg.start_soon(launch_client)
        await event.wait()
        async with Client(HOSTNAME, will=Will(topic)) as client:
            client._client._sock_close()  # type: ignore[attr-defined]


async def test_client_tls_context() -> None:
    topic = TOPIC_HEADER + "tls_context"

    async def handle_messages(tg: anyio.abc.TaskGroup) -> None:
        async with client.filtered_messages(topic) as messages:
            async for message in messages:
                assert message.topic == topic
                tg.cancel_scope.cancel()

    async with Client(
        HOSTNAME,
        8883,
        tls_context=ssl.SSLContext(protocol=ssl.PROTOCOL_TLS),
    ) as client:
        async with anyio.create_task_group() as tg:
            await client.subscribe(topic)
            tg.start_soon(handle_messages, tg)
            await client.publish(topic)


async def test_client_tls_params() -> None:
    topic = TOPIC_HEADER + "tls_params"

    async def handle_messages(tg: anyio.abc.TaskGroup) -> None:
        async with client.filtered_messages(topic) as messages:
            async for message in messages:
                assert message.topic == topic
                tg.cancel_scope.cancel()

    async with Client(
        HOSTNAME,
        8883,
        tls_params=TLSParameters(
            ca_certs=str(Path.cwd() / "tests" / "mosquitto.org.crt")
        ),
    ) as client:
        async with anyio.create_task_group() as tg:
            await client.subscribe(topic)
            tg.start_soon(handle_messages, tg)
            await client.publish(topic)


async def test_client_username_password() -> None:
    topic = TOPIC_HEADER + "username_password"

    async def handle_messages(tg: anyio.abc.TaskGroup) -> None:
        async with client.filtered_messages(topic) as messages:
            async for message in messages:
                assert message.topic == topic
                tg.cancel_scope.cancel()

    async with Client(HOSTNAME, username="asyncio-mqtt", password="012") as client:
        async with anyio.create_task_group() as tg:
            await client.subscribe(topic)
            tg.start_soon(handle_messages, tg)
            await client.publish(topic)


async def test_client_logger() -> None:
    logger = logging.getLogger("asyncio-mqtt")
    async with Client(HOSTNAME, logger=logger) as client:
        assert logger is client._client._logger  # type: ignore[attr-defined]


async def test_client_max_concurrent_outgoing_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    topic = TOPIC_HEADER + "max_concurrent_outgoing_calls"

    class MockPahoClient(mqtt.Client):
        def subscribe(
            self,
            topic: str
            | tuple[str, mqtt.SubscribeOptions]
            | list[tuple[str, mqtt.SubscribeOptions]]
            | list[tuple[str, int]],
            qos: int = 0,
            options: mqtt.SubscribeOptions | None = None,
            properties: mqtt.Properties | None = None,
        ) -> tuple[int, int]:
            assert client._outgoing_calls_sem is not None
            assert client._outgoing_calls_sem.locked()
            return super().subscribe(topic, qos, options, properties)

        def unsubscribe(
            self, topic: str | list[str], properties: mqtt.Properties | None = None
        ) -> tuple[int, int]:
            assert client._outgoing_calls_sem is not None
            assert client._outgoing_calls_sem.locked()
            return super().unsubscribe(topic, properties)

        def publish(
            self,
            topic: str,
            payload: PayloadType | None = None,
            qos: int = 0,
            retain: bool = False,
            properties: mqtt.Properties | None = None,
        ) -> mqtt.MQTTMessageInfo:
            assert client._outgoing_calls_sem is not None
            assert client._outgoing_calls_sem.locked()
            return super().publish(topic, payload, qos, retain, properties)

    monkeypatch.setattr(mqtt, "Client", MockPahoClient)

    async with Client(HOSTNAME, max_concurrent_outgoing_calls=1) as client:
        await client.subscribe(topic)
        await client.unsubscribe(topic)
        await client.publish(topic)


async def test_client_websockets() -> None:
    topic = TOPIC_HEADER + "websockets"

    async def handle_messages(tg: anyio.abc.TaskGroup) -> None:
        async with client.filtered_messages(topic) as messages:
            async for message in messages:
                assert message.topic == topic
                tg.cancel_scope.cancel()

    async with Client(
        HOSTNAME,
        8080,
        transport="websockets",
        websocket_path="/",
        websocket_headers={"foo": "bar"},
    ) as client:
        async with anyio.create_task_group() as tg:
            await client.subscribe(topic)
            tg.start_soon(handle_messages, tg)
            await client.publish(topic)


async def test_client_pending_calls_threshold(caplog: pytest.LogCaptureFixture) -> None:
    topic = TOPIC_HEADER + "pending_calls_threshold"

    async with Client(HOSTNAME) as client:
        nb_publish = client._pending_calls_threshold + 1

        async with anyio.create_task_group() as tg:
            for _ in range(nb_publish):
                tg.start_soon(client.publish, topic)

        assert caplog.record_tuples == [
            (
                "mqtt",
                logging.WARNING,
                f"There are {nb_publish} pending publish calls.",
            )
        ]


async def test_client_no_pending_calls_warnings_with_max_concurrent_outgoing_calls(
    caplog: pytest.LogCaptureFixture,
) -> None:
    topic = (
        TOPIC_HEADER + "no_pending_calls_warnings_with_max_concurrent_outgoing_calls"
    )

    async with Client(HOSTNAME, max_concurrent_outgoing_calls=1) as client:
        nb_publish = client._pending_calls_threshold + 1

        async with anyio.create_task_group() as tg:
            for _ in range(nb_publish):
                tg.start_soon(client.publish, topic)

        assert caplog.record_tuples == []
