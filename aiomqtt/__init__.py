# SPDX-License-Identifier: BSD-3-Clause
from .client import (
    Client,
    MessagesIterator,
    ProtocolVersion,
    ProxySettings,
    TLSParameters,
    Will,
)
from .exceptions import MqttCodeError, MqttError, MqttReentrantError
from .message import Message
from .topic import Topic, TopicLike, Wildcard, WildcardLike

__version__ = "2.4.0"
__version_tuple__ = (2, 4, 0)

__all__ = [
    "Client",
    "Message",
    "MessagesIterator",
    "MqttCodeError",
    "MqttError",
    "MqttReentrantError",
    "ProtocolVersion",
    "ProxySettings",
    "TLSParameters",
    "Topic",
    "TopicLike",
    "Wildcard",
    "WildcardLike",
    "Will",
    "__version__",
    "__version_tuple__",
]
