# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import socket
import ssl
import sys
from typing import Any, Callable, TypeVar

import paho.mqtt.client as mqtt

if sys.version_info >= (3, 10):
    from typing import ParamSpec, TypeAlias
else:
    from typing_extensions import ParamSpec, TypeAlias


T = TypeVar("T")
P = ParamSpec("P")

PayloadType: TypeAlias = "str | bytes | bytearray | int | float | None"
SubscribeTopic: TypeAlias = "str | tuple[str, mqtt.SubscribeOptions] | list[tuple[str, mqtt.SubscribeOptions]] | list[tuple[str, int]]"
WebSocketHeaders: TypeAlias = (
    "dict[str, str] | Callable[[dict[str, str]], dict[str, str]]"
)
_PahoSocket: TypeAlias = "socket.socket | ssl.SSLSocket | mqtt.WebsocketWrapper | Any"
# See the overloads of `socket.setsockopt` for details.
SocketOption: TypeAlias = "tuple[int, int, int | bytes] | tuple[int, int, None, int]"
