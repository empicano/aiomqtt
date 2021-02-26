import asyncio
from typing import Any, Awaitable, Generator, Optional, TypeVar, Union
from paho.mqtt import client as paho  # type: ignore

T = TypeVar("T")

ProtocolType = Union[paho.MQTTv31, paho.MQTTv311, paho.MQTTv5]
PayloadType = Optional[Union[str, bytes, bytearray, int, float]]
