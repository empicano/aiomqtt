import paho.mqtt.client as mqtt
import pytest
from paho.mqtt.packettypes import PacketTypes

from asyncio_mqtt.error import _CONNECT_RC_STRINGS, MqttCodeError, MqttConnectError


@pytest.mark.parametrize(
    "rc",
    (
        mqtt.MQTT_ERR_SUCCESS,
        mqtt.MQTT_ERR_NOMEM,
        mqtt.MQTT_ERR_PROTOCOL,
        mqtt.MQTT_ERR_INVAL,
        mqtt.MQTT_ERR_NO_CONN,
        mqtt.MQTT_ERR_CONN_REFUSED,
        mqtt.MQTT_ERR_NOT_FOUND,
        mqtt.MQTT_ERR_CONN_LOST,
        mqtt.MQTT_ERR_TLS,
        mqtt.MQTT_ERR_PAYLOAD_SIZE,
        mqtt.MQTT_ERR_NOT_SUPPORTED,
        mqtt.MQTT_ERR_AUTH,
        mqtt.MQTT_ERR_ACL_DENIED,
        mqtt.MQTT_ERR_UNKNOWN,
        mqtt.MQTT_ERR_ERRNO,
        mqtt.MQTT_ERR_QUEUE_SIZE,
        mqtt.MQTT_ERR_KEEPALIVE,
        -1,
    ),
)
def test_mqtt_code_error_int(rc: int) -> None:
    assert str(MqttCodeError(rc)) == f"[code:{rc}] {mqtt.error_string(rc)}"


@pytest.mark.parametrize(
    "packetType, aName",
    (
        (PacketTypes.CONNACK, "Success"),
        (PacketTypes.PUBACK, "Success"),
        (PacketTypes.SUBACK, "Granted QoS 1"),
    ),
)
def test_mqtt_code_error_reason_codes(packetType: int, aName: str) -> None:
    rc = mqtt.ReasonCodes(packetType, aName)
    assert str(MqttCodeError(rc)) == f"[code:{rc.value}] {str(rc)}"


def test_mqtt_code_error_none() -> None:
    assert str(MqttCodeError(None)) == "[code:None] "


@pytest.mark.parametrize("rc, message", list(_CONNECT_RC_STRINGS.items()) + [(0, "")])
def test_mqtt_connect_error_int(rc: int, message: str) -> None:
    error = MqttConnectError(rc)
    arg = "Connection refused"
    if rc in _CONNECT_RC_STRINGS:
        arg += f": {message}"
    assert error.args[0] == arg
    assert str(error) == f"[code:{rc}] {mqtt.error_string(rc)}"


@pytest.mark.parametrize(
    "packetType, aName",
    (
        (PacketTypes.CONNACK, "Success"),
        (PacketTypes.PUBACK, "Success"),
        (PacketTypes.SUBACK, "Granted QoS 1"),
    ),
)
def test_mqtt_connect_error_reason_codes(packetType: int, aName: str) -> None:
    rc = mqtt.ReasonCodes(packetType, aName)
    assert str(MqttConnectError(rc)) == f"[code:{rc.value}] {str(rc)}"
