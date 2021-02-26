# SPDX-License-Identifier: BSD-3-Clause


from typing import Any, Dict


class MqttError(Exception):
    """Base exception for all asyncio-mqtt exceptions."""

    pass


class MqttCodeError(MqttError):
    def __init__(self, rc: int, *args: Any):
        super().__init__(*args)
        self.rc = rc

    def __str__(self) -> str:
        return f"[code:{self.rc}] {super().__str__()}"


class MqttConnectError(MqttCodeError):
    def __init__(self, rc: int):
        msg = "Connection refused"
        try:
            msg += f": {_CONNECT_RC_STRINGS[rc]}"
        except KeyError:
            pass
        super().__init__(rc, msg)


_CONNECT_RC_STRINGS: Dict[int, str] = {
    # Reference: https://github.com/eclipse/paho.mqtt.python/blob/v1.5.0/src/paho/mqtt/client.py#L1898
    # 0: Connection successful
    # 1: Connection refused - incorrect protocol version
    1: "Incorrect protocol version",
    # 2: Connection refused - invalid client identifier
    2: "Invalid client identifier",
    # 3: Connection refused - server unavailable
    3: "Server unavailable",
    # 4: Connection refused - bad username or password
    4: "Bad username or password",
    # 5: Connection refused - not authorised
    5: "Not authorised"
    # 6-255: Currently unused.
}
