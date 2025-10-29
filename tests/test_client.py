"""Tests for the client."""

import asyncio
import logging
import unittest.mock

import conftest
import pytest

import aiomqtt

logging.basicConfig(level=logging.DEBUG)

# This is the same as marking all tests in this file with @pytest.mark.asyncio
pytestmark = pytest.mark.asyncio

_HOSTNAME = "test.mosquitto.org"


@pytest.mark.network
async def test_aenter_reusable() -> None:
    """Test that the client context manager is reusable."""
    topic = conftest.unique_topic()
    client = aiomqtt.Client(_HOSTNAME)
    async with client:
        await client.publish(topic)
    async with client:
        await client.publish(topic)


@pytest.mark.network
async def test_aenter_not_reentrant() -> None:
    """Test that the client context manager is not reentrant."""
    client = aiomqtt.Client(_HOSTNAME)
    async with client:
        with pytest.raises(RuntimeError):
            async with client:
                pass


@pytest.mark.network
async def test_aenter_invalid_hostname() -> None:
    """Test reusing the client after failure to connect in ``aenter``."""
    client = aiomqtt.Client("INVALID.HOSTNAME")
    with pytest.raises(OSError):
        await client.__aenter__()
    # Second attempt should also fail but not raise reentry error
    with pytest.raises(OSError):
        await client.__aenter__()


@pytest.mark.network
async def test_aenter_negative_connack() -> None:
    """Test reusing the client after negative CONNACK in ``aenter``."""
    client = aiomqtt.Client(_HOSTNAME, authentication_method="INVALID")
    with pytest.raises(aiomqtt.NegativeAckError):
        await client.__aenter__()
    # Second attempt should also fail but not raise reentry error
    with pytest.raises(aiomqtt.NegativeAckError):
        await client.__aenter__()


@pytest.mark.network
async def test_background_reconnection() -> None:
    """Test that client reconnects after connection loss."""
    topic = conftest.unique_topic()
    first = True

    async def read_mock(n: int = -1) -> bytes:
        nonlocal first
        if first:
            first = False
            return b""  # EOF
        return await original_read(n)

    async with aiomqtt.Client(_HOSTNAME, reconnect=True) as client:
        original_read = client._reader.read
        # First operation should work
        await client.publish(topic)
        with unittest.mock.patch.object(client._reader, "read", side_effect=read_mock):
            await client.disconnected()
        async with asyncio.timeout(5):
            await client.connected()
        # The client should be connected again
        await client.publish(topic)


@pytest.mark.parametrize(
    "qos",
    [aiomqtt.QoS.AT_MOST_ONCE, aiomqtt.QoS.AT_LEAST_ONCE, aiomqtt.QoS.EXACTLY_ONCE],
)
async def test_publish_not_connected(qos: aiomqtt.QoS) -> None:
    """Test that publish call fails when the client is not connected."""
    topic = conftest.unique_topic()
    client = aiomqtt.Client(_HOSTNAME)
    with pytest.raises(aiomqtt.ConnectError):
        await client.publish(topic, qos=qos)


@pytest.mark.network
async def test_publish_flow_control_qos1() -> None:
    """Test client backpressure for QoS=1 PUBLISH (resolved by PUBACK)."""
    topic = conftest.unique_topic()
    ready = asyncio.Event()

    async def read_mock(n: int = -1) -> bytes:
        await ready.wait()
        return await original_read(n)

    async with aiomqtt.Client(_HOSTNAME) as client:
        original_read = client._reader.read
        async with asyncio.TaskGroup() as tg:
            with unittest.mock.patch.object(
                client._reader, "read", side_effect=read_mock
            ):
                connack_packet = await client.connected()
                for _ in range(connack_packet.receive_max + 1):
                    tg.create_task(client.publish(topic, qos=aiomqtt.QoS.AT_LEAST_ONCE))
                # Yield control so that other tasks can run
                await asyncio.sleep(0)
                assert client._send_semaphore._value == 0
                assert client._send_semaphore._waiters is not None
                assert len(client._send_semaphore._waiters) == 1
                # We can still send QoS=0 PUBLISH
                await client.publish(topic)
                # Resolve backpressure
                ready.set()
        assert client._send_semaphore._value == connack_packet.receive_max


@pytest.mark.network
async def test_publish_flow_control_qos2() -> None:
    """Test client backpressure for QoS=2 PUBLISH (resolved by PUBCOMP)."""
    topic = conftest.unique_topic()
    ready = asyncio.Event()

    async def read_mock(n: int = -1) -> bytes:
        await ready.wait()
        return await original_read(n)

    async with aiomqtt.Client(_HOSTNAME) as client:
        original_read = client._reader.read
        connack_packet = await client.connected()
        packet_ids = []
        for _ in range(connack_packet.receive_max):
            pubrec_packet = await client.publish(topic, qos=aiomqtt.QoS.EXACTLY_ONCE)
            packet_ids.append(pubrec_packet.packet_id)
        async with asyncio.TaskGroup() as tg:
            with unittest.mock.patch.object(
                client._reader, "read", side_effect=read_mock
            ):
                for packet_id in packet_ids:
                    tg.create_task(client.pubrel(packet_id))
                # This next PUBLISH should block
                blocked = tg.create_task(
                    client.publish(topic, qos=aiomqtt.QoS.EXACTLY_ONCE)
                )
                # Yield control so that other tasks can run
                await asyncio.sleep(0)
                assert client._send_semaphore._value == 0
                assert client._send_semaphore._waiters is not None
                assert len(client._send_semaphore._waiters) == 1
                # We can still send QoS=0 PUBLISH
                await client.publish(topic)
                # Resolve backpressure
                ready.set()
        await client.pubrel(blocked.result().packet_id)
        assert client._send_semaphore._value == connack_packet.receive_max


async def test_puback_not_connected() -> None:
    """Test that puback call fails when the client is not connected."""
    client = aiomqtt.Client(_HOSTNAME)
    with pytest.raises(aiomqtt.ConnectError):
        await client.puback(1)


async def test_pubrec_not_connected() -> None:
    """Test that pubrec call fails when the client is not connected."""
    client = aiomqtt.Client(_HOSTNAME)
    with pytest.raises(aiomqtt.ConnectError):
        await client.pubrec(1)


async def test_pubrel_not_connected() -> None:
    """Test that pubrel call fails when the client is not connected."""
    client = aiomqtt.Client(_HOSTNAME)
    with pytest.raises(aiomqtt.ConnectError):
        await client.pubrel(1)


async def test_pubcomp_not_connected() -> None:
    """Test that pubcomp call fails when the client is not connected."""
    client = aiomqtt.Client(_HOSTNAME)
    with pytest.raises(aiomqtt.ConnectError):
        await client.pubcomp(1)


async def test_subscribe_not_connected() -> None:
    """Test that subscribe call fails when the client is not connected."""
    topic = conftest.unique_topic()
    client = aiomqtt.Client(_HOSTNAME)
    with pytest.raises(aiomqtt.ConnectError):
        await client.subscribe(topic)


@pytest.mark.network
async def test_unsubscribe() -> None:
    """Test that messages are no longer received after unsubscribing from a topic."""
    topic = conftest.unique_topic()
    async with aiomqtt.Client(_HOSTNAME) as client:
        await client.subscribe(topic)
        await client.publish(topic, payload=b"foo", qos=aiomqtt.QoS.AT_LEAST_ONCE)
        await client.unsubscribe(topic)
        await client.publish(topic, payload=b"bar", qos=aiomqtt.QoS.AT_LEAST_ONCE)
        await client.subscribe(topic)
        await client.publish(topic, payload=b"baz", qos=aiomqtt.QoS.AT_LEAST_ONCE)
        # We should only receive the first and last message
        async with asyncio.timeout(5):
            message = await anext(client.messages())
        assert message.payload == b"foo"
        await client.puback(message.packet_id)  # type: ignore[arg-type]
        async with asyncio.timeout(5):
            message = await anext(client.messages())
        assert message.payload == b"baz"
        await client.puback(message.packet_id)  # type: ignore[arg-type]


async def test_unsubscribe_not_connected() -> None:
    """Test that unsubscribe call fails when the client is not connected."""
    topic = conftest.unique_topic()
    client = aiomqtt.Client(_HOSTNAME)
    with pytest.raises(aiomqtt.ConnectError):
        await client.unsubscribe(topic)


@pytest.mark.network
async def test_message_iterator_concurrency() -> None:
    """Test that message iterator can be used concurrently by multiple tasks."""
    topic = conftest.unique_topic()
    r1, r2 = asyncio.Event(), asyncio.Event()
    async with aiomqtt.Client(_HOSTNAME) as client, asyncio.TaskGroup() as tg:

        async def consume(ready: asyncio.Event) -> aiomqtt.PublishPacket:
            ready.set()
            async with asyncio.timeout(5):
                return await anext(client.messages())

        t1 = tg.create_task(consume(r1))
        t2 = tg.create_task(consume(r2))
        await r1.wait()
        await r2.wait()
        await client.subscribe(topic)
        await client.publish(topic, payload=b"foo")
        await client.publish(topic, payload=b"bar")

    assert {t1.result().payload, t2.result().payload} == {b"foo", b"bar"}


async def test_message_iterator_not_connected() -> None:
    """Test that message iterator call fails when the client is not connected."""
    client = aiomqtt.Client(_HOSTNAME)
    messages = client.messages()
    with pytest.raises(aiomqtt.ConnectError):
        await anext(messages)


@pytest.mark.network
async def test_aexit_no_prior_aenter() -> None:
    """Test that aexit without prior (or unsuccessful) aenter runs cleanly."""
    client = aiomqtt.Client(_HOSTNAME)
    await client.__aexit__(None, None, None)


@pytest.mark.network
async def test_aexit_consecutive_calls() -> None:
    """Test that aexit runs cleanly when it has already been called before."""
    async with aiomqtt.Client(_HOSTNAME) as client:
        await client.__aexit__(None, None, None)


@pytest.mark.network
async def test_aexit_last_will() -> None:
    """Test that exiting with exception triggers disconnection with LWT."""
    topic = conftest.unique_topic()
    with pytest.raises(ProcessLookupError):
        async with aiomqtt.Client(
            _HOSTNAME,
            will=aiomqtt.Will(
                topic, payload=b"foo", qos=aiomqtt.QoS.AT_LEAST_ONCE, retain=True
            ),
        ):
            # Simulate an exception that should trigger LWT
            raise ProcessLookupError
    # Check that will message was published (and retained)
    async with aiomqtt.Client(_HOSTNAME) as client:
        await client.subscribe(topic)
        async with asyncio.timeout(5):
            puback_packet = await anext(client.messages())
        assert puback_packet.payload == b"foo"
        assert puback_packet.retain is True
