"""Tests for the client."""

import asyncio
import socket
import ssl
import sys
import unittest.mock

import conftest
import mqtt5
import pytest

import aiomqtt

# This is the same as marking all tests in this file with @pytest.mark.asyncio
pytestmark = pytest.mark.asyncio


@pytest.mark.network
async def test_aenter_reusable() -> None:
    """Test that the client context manager is reusable."""
    client = aiomqtt.Client(hostname=conftest.HOSTNAME)
    topic = conftest.unique_topic()
    async with client:
        await client.publish(topic, b"")
    async with client:
        await client.publish(topic, b"")


@pytest.mark.network
async def test_aenter_reusable_invalid_hostname() -> None:
    """Test reusing the client after failure to connect in ``aenter``."""
    client = aiomqtt.Client(hostname="INVALID.HOSTNAME")
    with pytest.raises(socket.gaierror):
        await client.__aenter__()
    await client.__aexit__(None, None, None)
    # Second attempt should also fail but not raise reentry error
    with pytest.raises(socket.gaierror):
        await client.__aenter__()
    await client.__aexit__(None, None, None)


@pytest.mark.network
async def test_aenter_reusable_negative_connack() -> None:
    """Test reusing the client after negative CONNACK in ``aenter``."""
    client = aiomqtt.Client(hostname=conftest.HOSTNAME, authentication_method="INVALID")
    with pytest.raises(aiomqtt.NegativeAckError):
        await client.__aenter__()
    await client.__aexit__(None, None, None)
    # Second attempt should also fail but not raise reentry error
    with pytest.raises(aiomqtt.NegativeAckError):
        await client.__aenter__()
    await client.__aexit__(None, None, None)


@pytest.mark.network
async def test_aenter_not_reentrant() -> None:
    """Test that the client context manager is not reentrant."""
    client = aiomqtt.Client(hostname=conftest.HOSTNAME)
    async with client:
        with pytest.raises(RuntimeError):
            await client.__aenter__()


@pytest.mark.xfail(
    sys.version_info >= (3, 13) and conftest.HOSTNAME == "test.mosquitto.org",
    reason="test.mosquitto.org CA cert lacks key usage ext required by Python 3.13+",
)
@pytest.mark.network
async def test_aenter_tls() -> None:
    """Test connecting with TLS encryption."""
    async with aiomqtt.Client(
        hostname=conftest.HOSTNAME, port=8883, ssl_context=conftest.SSL_CONTEXT
    ):
        pass


@pytest.mark.network
async def test_aenter_tls_missing() -> None:
    """Test that connecting without TLS to an encrypted port fails."""
    client = aiomqtt.Client(hostname=conftest.HOSTNAME, port=8883)
    with pytest.raises(aiomqtt.ConnectError):
        await client.__aenter__()
    await client.__aexit__(None, None, None)


@pytest.mark.network
async def test_aenter_tls_untrusted_certificate() -> None:
    """Test that connecting with an untrusted certificate fails."""
    client = aiomqtt.Client(
        hostname=conftest.HOSTNAME, port=8883, ssl_context=ssl.create_default_context()
    )
    with pytest.raises(ssl.SSLCertVerificationError):
        await client.__aenter__()
    await client.__aexit__(None, None, None)


@pytest.mark.network
async def test_aenter_auth() -> None:
    """Test that the client can connect with username and password."""
    async with aiomqtt.Client(
        hostname=conftest.HOSTNAME,
        port=1884,
        username=conftest.USERNAME,
        password=conftest.PASSWORD,
    ):
        pass


@pytest.mark.network
async def test_aenter_auth_invalid_password() -> None:
    """Test that the client fails to connect with an invalid password."""
    client = aiomqtt.Client(
        hostname=conftest.HOSTNAME,
        port=1884,
        username=conftest.USERNAME,
        password=b"INVALID",
    )
    with pytest.raises(aiomqtt.NegativeAckError):
        await client.__aenter__()
    await client.__aexit__(None, None, None)


@pytest.mark.network
async def test_aexit_no_prior_aenter() -> None:
    """Test that aexit without prior (or unsuccessful) aenter runs cleanly."""
    client = aiomqtt.Client(hostname=conftest.HOSTNAME)
    await client.__aexit__(None, None, None)


@pytest.mark.network
async def test_aexit_consecutive_calls() -> None:
    """Test that aexit runs cleanly when it has already been called before."""
    async with aiomqtt.Client(hostname=conftest.HOSTNAME) as client:
        await client.__aexit__(None, None, None)


@pytest.mark.network
async def test_aexit_last_will() -> None:
    """Test that exiting with exception triggers disconnection with LWT."""
    topic = conftest.unique_topic()
    with pytest.raises(ProcessLookupError):
        async with aiomqtt.Client(
            hostname=conftest.HOSTNAME,
            will=aiomqtt.Will(
                topic, payload=b"foo", qos=aiomqtt.QoS.AT_LEAST_ONCE, retain=True
            ),
        ):
            # Simulate an exception that should trigger LWT
            raise ProcessLookupError
    # Check that will message was published (and retained)
    async with aiomqtt.Client(hostname=conftest.HOSTNAME) as client:
        await client.subscribe(aiomqtt.TopicFilter(topic))
        message = await anext(client.messages())
        assert isinstance(message, aiomqtt.PublishPacket)
        assert message.payload == b"foo"
        assert message.retain is True


@pytest.mark.parametrize("data", [b"", b"\x00\x02\x00\x00"], ids=["EOF", "malformed"])
@pytest.mark.network
async def test_background_reconnection(data: bytes) -> None:
    """Test that client reconnects after connection loss."""
    topic = conftest.unique_topic()
    first = True
    connect_count = 0

    async def connect_spy() -> None:
        nonlocal connect_count
        connect_count += 1
        return await original_connect()

    async def read_mock(n: int = -1) -> bytes:
        nonlocal first
        if first:
            first = False
            return data
        return await original_read(n)

    async with aiomqtt.Client(hostname=conftest.HOSTNAME, reconnect=True) as client:
        original_read = client._reader.read
        original_connect = client._connect
        # First operation should work
        await client.publish(topic, b"")
        with (
            unittest.mock.patch.object(client._reader, "read", side_effect=read_mock),
            unittest.mock.patch.object(client, "_connect", side_effect=connect_spy),
        ):
            await client.disconnected()
            # Buffer should be cleared after disconnection
            assert client._buffer_in.left == client._buffer_in.right
            await client.connected()
        # The client should reconnect on the first attempt
        assert connect_count == 1
        # The client should be connected again
        await client.publish(topic, b"")


@pytest.mark.network
async def test_message_iterator_concurrency() -> None:
    """Test that message iterator can be used concurrently by multiple tasks."""
    topic = conftest.unique_topic()
    r1, r2 = asyncio.Event(), asyncio.Event()
    async with (
        aiomqtt.Client(hostname=conftest.HOSTNAME) as client,
        asyncio.TaskGroup() as tg,
    ):

        async def consume(
            ready: asyncio.Event,
        ) -> aiomqtt.PublishPacket | aiomqtt.PubRelPacket:
            ready.set()
            return await anext(client.messages())

        t1 = tg.create_task(consume(r1))
        t2 = tg.create_task(consume(r2))
        await r1.wait()
        await r2.wait()
        await client.subscribe(aiomqtt.TopicFilter(topic))
        await client.publish(topic, b"foo")
        await client.publish(topic, b"bar")

    m1 = t1.result()
    m2 = t2.result()
    assert isinstance(m1, aiomqtt.PublishPacket)
    assert isinstance(m2, aiomqtt.PublishPacket)
    assert {m1.payload, m2.payload} == {b"foo", b"bar"}


@pytest.mark.network
async def test_message_iterator_disconnected() -> None:
    """Test that message iterator call fails when the client is not connected."""
    client = aiomqtt.Client(hostname=conftest.HOSTNAME)
    with pytest.raises(aiomqtt.ConnectError):
        await anext(client.messages())
    async with client:
        await client._close()
        with pytest.raises(aiomqtt.ConnectError):
            await anext(client.messages())
    with pytest.raises(aiomqtt.ConnectError):
        await anext(client.messages())


@pytest.mark.network
async def test_publish_qos0_no_matching_subscribers() -> None:
    """Test that QoS=0 publish to a topic with no subscribers succeeds."""
    topic = conftest.unique_topic()
    async with aiomqtt.Client(hostname=conftest.HOSTNAME) as client:
        await client.publish(topic, b"")


@pytest.mark.network
async def test_publish_qos1_no_matching_subscribers() -> None:
    """Test that QoS=1 publish to a topic with no subscribers succeeds."""
    topic = conftest.unique_topic()
    first = True
    client = aiomqtt.Client(hostname=conftest.HOSTNAME)
    packet_id = next(client.packet_ids)

    # The specification doesn't enforce notifying the client about no subscribers, but
    # we want to explicitely test this case here
    async def read_mock(n: int = -1) -> bytes:
        nonlocal first, packet_id
        if first:
            first = False
            return aiomqtt.PubAckPacket(
                packet_id=packet_id,
                reason_code=aiomqtt.PubAckReasonCode.NO_MATCHING_SUBSCRIBERS,
            ).write()
        return await original_read(n)

    async with client:
        original_read = client._reader.read
        with unittest.mock.patch.object(client._reader, "read", side_effect=read_mock):
            puback_packet = await client.publish(
                topic, b"", qos=aiomqtt.QoS.AT_LEAST_ONCE, packet_id=packet_id
            )
        assert (
            puback_packet.reason_code
            == aiomqtt.PubAckReasonCode.NO_MATCHING_SUBSCRIBERS
        )


@pytest.mark.network
async def test_publish_qos2_no_matching_subscribers() -> None:
    """Test that QoS=2 publish to a topic with no subscribers succeeds."""
    topic = conftest.unique_topic()
    first = True
    client = aiomqtt.Client(hostname=conftest.HOSTNAME)
    packet_id = next(client.packet_ids)

    # The specification doesn't enforce notifying the client about no subscribers, but
    # we want to explicitely test this case here
    async def read_mock(n: int = -1) -> bytes:
        nonlocal first, packet_id
        if first:
            first = False
            return aiomqtt.PubRecPacket(
                packet_id=packet_id,
                reason_code=aiomqtt.PubRecReasonCode.NO_MATCHING_SUBSCRIBERS,
            ).write()
        return await original_read(n)

    async with client:
        original_read = client._reader.read
        with unittest.mock.patch.object(client._reader, "read", side_effect=read_mock):
            pubrec_packet = await client.publish(
                topic, b"", qos=aiomqtt.QoS.EXACTLY_ONCE, packet_id=packet_id
            )
        assert (
            pubrec_packet.reason_code
            == aiomqtt.PubRecReasonCode.NO_MATCHING_SUBSCRIBERS
        )
        # Complete the QoS = 2 flow
        await client.pubrel(packet_id)


@pytest.mark.network
async def test_publish_disconnected_qos0() -> None:
    """Test that publish call fails when the client is not connected."""
    client = aiomqtt.Client(hostname=conftest.HOSTNAME)
    topic = conftest.unique_topic()
    with pytest.raises(aiomqtt.ConnectError):
        await client.publish(topic, b"")
    async with client:
        await client._close()
        with pytest.raises(aiomqtt.ConnectError):
            await client.publish(topic, b"")
    with pytest.raises(aiomqtt.ConnectError):
        await client.publish(topic, b"")


@pytest.mark.network
async def test_publish_disconnected_qos1() -> None:
    """Test that publish call fails when the client is not connected."""
    client = aiomqtt.Client(hostname=conftest.HOSTNAME)
    original_send = client._send
    topic = conftest.unique_topic()
    first = True

    async def send_mock(packet: mqtt5.Packet) -> None:
        nonlocal first
        await original_send(packet)
        # Disconnect after the first call
        if first:
            first = False
            await client._close()

    with pytest.raises(aiomqtt.ConnectError):
        await client.publish(
            topic, b"", qos=aiomqtt.QoS.AT_LEAST_ONCE, packet_id=next(client.packet_ids)
        )
    async with client:
        with (
            unittest.mock.patch.object(client, "_send", side_effect=send_mock),
            pytest.raises(aiomqtt.ConnectError),
        ):
            await client.publish(
                topic,
                b"",
                qos=aiomqtt.QoS.AT_LEAST_ONCE,
                packet_id=next(client.packet_ids),
            )
        with pytest.raises(aiomqtt.ConnectError):
            await client.publish(
                topic,
                b"",
                qos=aiomqtt.QoS.AT_LEAST_ONCE,
                packet_id=next(client.packet_ids),
            )
    with pytest.raises(aiomqtt.ConnectError):
        await client.publish(
            topic, b"", qos=aiomqtt.QoS.AT_LEAST_ONCE, packet_id=next(client.packet_ids)
        )


@pytest.mark.network
async def test_publish_disconnected_qos2() -> None:
    """Test that publish call fails when the client is not connected."""
    client = aiomqtt.Client(hostname=conftest.HOSTNAME)
    original_send = client._send
    topic = conftest.unique_topic()
    first = True

    async def send_mock(packet: mqtt5.Packet) -> None:
        nonlocal first
        await original_send(packet)
        # Disconnect after the first call
        if first:
            first = False
            await client._close()

    with pytest.raises(aiomqtt.ConnectError):
        await client.publish(
            topic, b"", qos=aiomqtt.QoS.EXACTLY_ONCE, packet_id=next(client.packet_ids)
        )
    async with client:
        with (
            unittest.mock.patch.object(client, "_send", side_effect=send_mock),
            pytest.raises(aiomqtt.ConnectError),
        ):
            await client.publish(
                topic,
                b"",
                qos=aiomqtt.QoS.EXACTLY_ONCE,
                packet_id=next(client.packet_ids),
            )
        with pytest.raises(aiomqtt.ConnectError):
            await client.publish(
                topic,
                b"",
                qos=aiomqtt.QoS.EXACTLY_ONCE,
                packet_id=next(client.packet_ids),
            )
    with pytest.raises(aiomqtt.ConnectError):
        await client.publish(
            topic, b"", qos=aiomqtt.QoS.EXACTLY_ONCE, packet_id=next(client.packet_ids)
        )


@pytest.mark.network
async def test_publish_retry_qos1() -> None:
    """Test QoS = 1 publish retry after disconnection."""
    topic = conftest.unique_topic()
    ready = asyncio.Event()

    async def send_mock(packet: mqtt5.Packet) -> None:
        await original_send(packet)
        if isinstance(packet, mqtt5.PublishPacket):
            ready.set()

    async def read_mock(_n: int = -1) -> bytes:
        await ready.wait()
        return b""

    async with aiomqtt.Client(
        hostname=conftest.HOSTNAME,
        clean_start=False,
        session_expiry_interval=600,
        reconnect=True,
    ) as client:
        original_send = client._send
        packet_id = next(client.packet_ids)
        # Block reads until PUBLISH is sent, then EOF to disconnect
        with (
            unittest.mock.patch.object(client, "_send", side_effect=send_mock),
            unittest.mock.patch.object(client._reader, "read", side_effect=read_mock),
            pytest.raises(aiomqtt.ConnectError),
        ):
            await client.publish(
                topic,
                b"hello",
                qos=aiomqtt.QoS.AT_LEAST_ONCE,
                packet_id=packet_id,
            )
        # Wait for automatic reconnection
        connack_packet = await client.connected()
        assert connack_packet.session_present is True
        # Retry with same packet_id and duplicate flag
        puback_packet = await client.publish(
            topic,
            b"hello",
            qos=aiomqtt.QoS.AT_LEAST_ONCE,
            packet_id=packet_id,
            duplicate=True,
        )
        assert puback_packet.reason_code in (
            aiomqtt.PubAckReasonCode.SUCCESS,
            aiomqtt.PubAckReasonCode.NO_MATCHING_SUBSCRIBERS,
        )


@pytest.mark.network
async def test_publish_retry_qos2() -> None:
    """Test QoS = 2 publish retry after disconnection."""
    topic = conftest.unique_topic()
    ready = asyncio.Event()

    async def send_mock(packet: mqtt5.Packet) -> None:
        await original_send(packet)
        if isinstance(packet, mqtt5.PublishPacket):
            ready.set()

    async def read_mock(_n: int = -1) -> bytes:
        await ready.wait()
        return b""

    async with aiomqtt.Client(
        hostname=conftest.HOSTNAME,
        clean_start=False,
        session_expiry_interval=600,
        reconnect=True,
    ) as client:
        original_send = client._send
        packet_id = next(client.packet_ids)
        # Block reads until PUBLISH is sent, then EOF to disconnect
        with (
            unittest.mock.patch.object(client, "_send", side_effect=send_mock),
            unittest.mock.patch.object(client._reader, "read", side_effect=read_mock),
            pytest.raises(aiomqtt.ConnectError),
        ):
            await client.publish(
                topic,
                b"hello",
                qos=aiomqtt.QoS.EXACTLY_ONCE,
                packet_id=packet_id,
            )
        # Wait for automatic reconnection
        connack_packet = await client.connected()
        assert connack_packet.session_present is True
        # Retry with same packet_id and duplicate flag
        pubrec_packet = await client.publish(
            topic,
            b"hello",
            qos=aiomqtt.QoS.EXACTLY_ONCE,
            packet_id=packet_id,
            duplicate=True,
        )
        assert pubrec_packet.reason_code == aiomqtt.PubRecReasonCode.SUCCESS
        # Complete the QoS = 2 flow
        pubcomp_packet = await client.pubrel(packet_id)
        assert pubcomp_packet.reason_code == aiomqtt.PubCompReasonCode.SUCCESS


@pytest.mark.network
async def test_publish_flow_control_qos1() -> None:
    """Test client backpressure for QoS = 1 PUBLISH (resolved by PUBACK)."""
    topic = conftest.unique_topic()
    ready = asyncio.Event()

    async def read_mock(n: int = -1) -> bytes:
        await ready.wait()
        return await original_read(n)

    async with aiomqtt.Client(hostname=conftest.HOSTNAME) as client:
        original_read = client._reader.read
        async with asyncio.TaskGroup() as tg:
            with unittest.mock.patch.object(
                client._reader, "read", side_effect=read_mock
            ):
                connack_packet = await client.connected()
                for _ in range(connack_packet.receive_max + 1):
                    tg.create_task(
                        client.publish(
                            topic,
                            b"",
                            qos=aiomqtt.QoS.AT_LEAST_ONCE,
                            packet_id=next(client.packet_ids),
                        )
                    )
                # Yield control so that other tasks can run
                await asyncio.sleep(0)
                assert client._send_semaphore._value == 0
                assert client._send_semaphore._waiters is not None
                assert len(client._send_semaphore._waiters) == 1
                # We can still send QoS = 0 PUBLISH
                await client.publish(topic, b"")
                # Resolve backpressure
                ready.set()
        assert client._send_semaphore._value == connack_packet.receive_max


@pytest.mark.network
async def test_publish_flow_control_qos2() -> None:
    """Test client backpressure for QoS = 2 PUBLISH (resolved by PUBCOMP)."""
    topic = conftest.unique_topic()
    ready = asyncio.Event()

    async def read_mock(n: int = -1) -> bytes:
        await ready.wait()
        return await original_read(n)

    async with aiomqtt.Client(hostname=conftest.HOSTNAME) as client:
        original_read = client._reader.read
        connack_packet = await client.connected()
        packet_ids = []
        for _ in range(connack_packet.receive_max):
            pubrec_packet = await client.publish(
                topic,
                b"",
                qos=aiomqtt.QoS.EXACTLY_ONCE,
                packet_id=next(client.packet_ids),
            )
            packet_ids.append(pubrec_packet.packet_id)
        async with asyncio.TaskGroup() as tg:
            with unittest.mock.patch.object(
                client._reader, "read", side_effect=read_mock
            ):
                for packet_id in packet_ids:
                    tg.create_task(client.pubrel(packet_id))
                # This next PUBLISH should block
                blocked = tg.create_task(
                    client.publish(
                        topic,
                        b"",
                        qos=aiomqtt.QoS.EXACTLY_ONCE,
                        packet_id=next(client.packet_ids),
                    )
                )
                # Yield control so that other tasks can run
                await asyncio.sleep(0)
                assert client._send_semaphore._value == 0
                assert client._send_semaphore._waiters is not None
                assert len(client._send_semaphore._waiters) == 1
                # We can still send QoS = 0 PUBLISH
                await client.publish(topic, b"")
                # Resolve backpressure
                ready.set()
        await client.pubrel(blocked.result().packet_id)
        assert client._send_semaphore._value == connack_packet.receive_max


@pytest.mark.parametrize(
    "packet_type",
    [
        aiomqtt.PubAckPacket,
        aiomqtt.PubRecPacket,
        aiomqtt.PubRelPacket,
        aiomqtt.PubCompPacket,
    ],
)
@pytest.mark.network
async def test_publish_unsolicited_ack(
    packet_type: type[
        aiomqtt.PubAckPacket
        | aiomqtt.PubRecPacket
        | aiomqtt.PubRelPacket
        | aiomqtt.PubCompPacket
    ],
) -> None:
    """Test that stray PUBLISH acknowledgment (e.g. after reconnection) is ignored."""
    topic = conftest.unique_topic()
    first = True

    async def read_mock(n: int = -1) -> bytes:
        data = await original_read(n)
        nonlocal first
        if first:
            first = False
            return packet_type(packet_id=999).write() + data
        return data

    async with aiomqtt.Client(hostname=conftest.HOSTNAME) as client:
        original_read = client._reader.read
        with unittest.mock.patch.object(client._reader, "read", side_effect=read_mock):
            await client.publish(
                topic,
                b"",
                qos=aiomqtt.QoS.AT_LEAST_ONCE,
                packet_id=next(client.packet_ids),
            )


@pytest.mark.network
async def test_puback_disconnected() -> None:
    """Test that puback call fails when the client is not connected."""
    client = aiomqtt.Client(hostname=conftest.HOSTNAME)
    with pytest.raises(aiomqtt.ConnectError):
        await client.puback(1)
    async with client:
        await client._close()
        with pytest.raises(aiomqtt.ConnectError):
            await client.puback(1)
    with pytest.raises(aiomqtt.ConnectError):
        await client.puback(1)


@pytest.mark.network
async def test_pubrec_disconnected() -> None:
    """Test that pubrec call fails when the client is not connected."""
    client = aiomqtt.Client(hostname=conftest.HOSTNAME)
    with pytest.raises(aiomqtt.ConnectError):
        await client.pubrec(1)
    async with client:
        await client._close()
        with pytest.raises(aiomqtt.ConnectError):
            await client.pubrec(1)
    with pytest.raises(aiomqtt.ConnectError):
        await client.pubrec(1)


@pytest.mark.network
async def test_pubrel_disconnected() -> None:
    """Test that pubrel call fails when the client is not connected."""
    client = aiomqtt.Client(hostname=conftest.HOSTNAME)
    original_send = client._send
    first = True

    async def send_mock(packet: mqtt5.Packet) -> None:
        nonlocal first
        await original_send(packet)
        # Disconnect after the first call
        if first:
            first = False
            await client._close()

    with pytest.raises(aiomqtt.ConnectError):
        await client.pubrel(1)
    async with client:
        with (
            unittest.mock.patch.object(client, "_send", side_effect=send_mock),
            pytest.raises(aiomqtt.ConnectError),
        ):
            await client.pubrel(1)
        with pytest.raises(aiomqtt.ConnectError):
            await client.pubrel(1)
    with pytest.raises(aiomqtt.ConnectError):
        await client.pubrel(1)


@pytest.mark.network
async def test_pubcomp_disconnected() -> None:
    """Test that pubcomp call fails when the client is not connected."""
    client = aiomqtt.Client(hostname=conftest.HOSTNAME)
    with pytest.raises(aiomqtt.ConnectError):
        await client.pubcomp(1)
    async with client:
        await client._close()
        with pytest.raises(aiomqtt.ConnectError):
            await client.pubcomp(1)
    with pytest.raises(aiomqtt.ConnectError):
        await client.pubcomp(1)


@pytest.mark.network
async def test_subscribe() -> None:
    """Test that subscribing to a topic receives messages published to it."""
    topic = conftest.unique_topic()
    async with aiomqtt.Client(hostname=conftest.HOSTNAME) as client:
        suback_packet = await client.subscribe(aiomqtt.TopicFilter(topic))
        assert len(suback_packet.reason_codes) == 1
        await client.publish(
            topic,
            b"foo",
            qos=aiomqtt.QoS.AT_LEAST_ONCE,
            packet_id=next(client.packet_ids),
        )
        message = await anext(client.messages())
        assert isinstance(message, aiomqtt.PublishPacket)
        assert message.payload == b"foo"
        assert message.packet_id is not None
        await client.puback(message.packet_id)


@pytest.mark.network
async def test_subscribe_multiple() -> None:
    """Test that multiple subscriptions can be sent in a single SUBSCRIBE packet."""
    topic = conftest.unique_topic()
    async with aiomqtt.Client(hostname=conftest.HOSTNAME) as client:
        await client.subscribe(
            aiomqtt.TopicFilter(topic + "/1"), aiomqtt.TopicFilter(topic + "/2")
        )
        await client.publish(
            topic + "/1",
            b"foo",
            qos=aiomqtt.QoS.AT_LEAST_ONCE,
            packet_id=next(client.packet_ids),
        )
        await client.publish(
            topic + "/2",
            b"bar",
            qos=aiomqtt.QoS.AT_LEAST_ONCE,
            packet_id=next(client.packet_ids),
        )
        payloads = set()
        for _ in range(2):
            message = await anext(client.messages())
            assert isinstance(message, aiomqtt.PublishPacket)
            assert message.packet_id is not None
            payloads.add(message.payload)
            await client.puback(message.packet_id)
        assert payloads == {b"foo", b"bar"}


@pytest.mark.network
async def test_subscribe_empty() -> None:
    """Test that subscribe() with no subscriptions is rejected client-side."""
    async with aiomqtt.Client(hostname=conftest.HOSTNAME) as client:
        with pytest.raises(ValueError):  # noqa: PT011
            await client.subscribe()


@pytest.mark.network
async def test_subscribe_disconnected() -> None:
    """Test that subscribe call fails when the client is not connected."""
    client = aiomqtt.Client(hostname=conftest.HOSTNAME)
    topic = conftest.unique_topic()
    original_send = client._send
    first = True

    async def send_mock(packet: mqtt5.Packet) -> None:
        nonlocal first
        await original_send(packet)
        # Disconnect after the first call
        if first:
            first = False
            await client._close()

    with pytest.raises(aiomqtt.ConnectError):
        await client.subscribe(aiomqtt.TopicFilter(topic))
    async with client:
        with (
            unittest.mock.patch.object(client, "_send", side_effect=send_mock),
            pytest.raises(aiomqtt.ConnectError),
        ):
            await client.subscribe(aiomqtt.TopicFilter(topic))
        with pytest.raises(aiomqtt.ConnectError):
            await client.subscribe(aiomqtt.TopicFilter(topic))
    with pytest.raises(aiomqtt.ConnectError):
        await client.subscribe(aiomqtt.TopicFilter(topic))


@pytest.mark.network
async def test_subscribe_unsolicited_ack() -> None:
    """Test that stray SUBACK (e.g. after reconnection) is ignored."""
    topic = conftest.unique_topic()
    first = True

    async def read_mock(n: int = -1) -> bytes:
        data = await original_read(n)
        nonlocal first
        if first:
            first = False
            packet = aiomqtt.SubAckPacket(
                packet_id=999,
                reason_codes=[aiomqtt.SubAckReasonCode.GRANTED_QOS_AT_MOST_ONCE],
            )
            return packet.write() + data
        return data

    async with aiomqtt.Client(hostname=conftest.HOSTNAME) as client:
        original_read = client._reader.read
        with unittest.mock.patch.object(client._reader, "read", side_effect=read_mock):
            await client.publish(topic, b"")


@pytest.mark.network
async def test_unsubscribe() -> None:
    """Test that messages are no longer received after unsubscribing from a topic."""
    topic = conftest.unique_topic()
    async with aiomqtt.Client(hostname=conftest.HOSTNAME) as client:
        await client.subscribe(aiomqtt.TopicFilter(topic))
        # QoS = 1 guarantees delivery before subscribe/unsubscribe takes effect
        await client.publish(
            topic,
            b"foo",
            qos=aiomqtt.QoS.AT_LEAST_ONCE,
            packet_id=next(client.packet_ids),
        )
        await client.unsubscribe(topic)
        await client.publish(
            topic,
            b"bar",
            qos=aiomqtt.QoS.AT_LEAST_ONCE,
            packet_id=next(client.packet_ids),
        )
        await client.subscribe(aiomqtt.TopicFilter(topic))
        await client.publish(
            topic,
            b"baz",
            qos=aiomqtt.QoS.AT_LEAST_ONCE,
            packet_id=next(client.packet_ids),
        )
        # We should only receive the first and last message
        payloads = set()
        for _ in range(2):
            message = await anext(client.messages())
            assert isinstance(message, aiomqtt.PublishPacket)
            assert message.packet_id is not None
            payloads.add(message.payload)
            await client.puback(message.packet_id)
        assert payloads == {b"foo", b"baz"}


@pytest.mark.network
async def test_unsubscribe_multiple() -> None:
    """Test that multiple patterns can be sent in a single UNSUBSCRIBE packet."""
    topic = conftest.unique_topic()
    async with aiomqtt.Client(hostname=conftest.HOSTNAME) as client:
        await client.subscribe(
            aiomqtt.TopicFilter(topic + "/1"), aiomqtt.TopicFilter(topic + "/2")
        )
        await client.unsubscribe(topic + "/1", topic + "/2")


@pytest.mark.network
async def test_unsubscribe_empty() -> None:
    """Test that unsubscribe() with no patterns is rejected client-side."""
    async with aiomqtt.Client(hostname=conftest.HOSTNAME) as client:
        with pytest.raises(ValueError):  # noqa: PT011
            await client.unsubscribe()


@pytest.mark.network
async def test_unsubscribe_nonexistent_subscription() -> None:
    """Test that unsubscribing from a topic that was never subscribed to succeeds."""
    topic = conftest.unique_topic()
    async with aiomqtt.Client(hostname=conftest.HOSTNAME) as client:
        unsuback_packet = await client.unsubscribe(topic)
        assert (
            unsuback_packet.reason_codes[0]
            == aiomqtt.UnsubAckReasonCode.NO_SUBSCRIPTION_EXISTED
        )


@pytest.mark.network
async def test_unsubscribe_disconnected() -> None:
    """Test that unsubscribe call fails when the client is not connected."""
    client = aiomqtt.Client(hostname=conftest.HOSTNAME)
    topic = conftest.unique_topic()
    original_send = client._send
    first = True

    async def send_mock(packet: mqtt5.Packet) -> None:
        nonlocal first
        await original_send(packet)
        # Disconnect after the first call
        if first:
            first = False
            await client._close()

    with pytest.raises(aiomqtt.ConnectError):
        await client.unsubscribe(topic)
    async with client:
        with (
            unittest.mock.patch.object(client, "_send", side_effect=send_mock),
            pytest.raises(aiomqtt.ConnectError),
        ):
            await client.unsubscribe(topic)
        with pytest.raises(aiomqtt.ConnectError):
            await client.unsubscribe(topic)
    with pytest.raises(aiomqtt.ConnectError):
        await client.unsubscribe(topic)


@pytest.mark.network
async def test_unsubscribe_unsolicited_ack() -> None:
    """Test that stray UNSUBACK (e.g. after reconnection) is ignored."""
    topic = conftest.unique_topic()
    first = True

    async def read_mock(n: int = -1) -> bytes:
        data = await original_read(n)
        nonlocal first
        if first:
            first = False
            packet = aiomqtt.UnsubAckPacket(
                packet_id=999,
                reason_codes=[aiomqtt.UnsubAckReasonCode.SUCCESS],
            )
            return packet.write() + data
        return data

    async with aiomqtt.Client(hostname=conftest.HOSTNAME) as client:
        original_read = client._reader.read
        with unittest.mock.patch.object(client._reader, "read", side_effect=read_mock):
            await client.publish(topic, b"")


@pytest.mark.network
async def test_broker_disconnect() -> None:
    """Test that receiving a DISCONNECT from the broker doesn't send one back."""
    first = True
    packets_sent: list[mqtt5.Packet] = []

    async def send_spy(packet: mqtt5.Packet) -> None:
        packets_sent.append(packet)
        return await original_send(packet)

    async def read_mock(n: int = -1) -> bytes:
        nonlocal first
        if first:
            first = False
            return mqtt5.DisconnectPacket(
                reason_code=mqtt5.DisconnectReasonCode.NORMAL_DISCONNECTION,
            ).write()
        return await original_read(n)

    async with aiomqtt.Client(hostname=conftest.HOSTNAME) as client:
        original_send = client._send
        original_read = client._reader.read
        with (
            unittest.mock.patch.object(client._reader, "read", side_effect=read_mock),
            unittest.mock.patch.object(client, "_send", side_effect=send_spy),
        ):
            await client.disconnected()
        assert not any(isinstance(p, mqtt5.DisconnectPacket) for p in packets_sent)
