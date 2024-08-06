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

# These are placeholders that are managed by poetry-dynamic-versioning
__version__ = "0.0.0"
__version_tuple__ = (0, 0, 0)

__all__ = [
    "__version__",
    "__version_tuple__",
    "MessagesIterator",
    "Client",
    "Message",
    "ProtocolVersion",
    "ProxySettings",
    "TLSParameters",
    "Topic",
    "TopicLike",
    "Wildcard",
    "WildcardLike",
    "Will",
    "MqttCodeError",
    "MqttReentrantError",
    "MqttError",
]
