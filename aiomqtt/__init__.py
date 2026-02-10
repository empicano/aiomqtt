# SPDX-License-Identifier: BSD-3-Clause
"""The idiomatic asyncio MQTT client."""

import importlib.metadata

from mqtt5 import (
    ConnAckPacket,
    PubAckPacket,
    PubAckReasonCode,
    PubCompPacket,
    PubCompReasonCode,
    PublishPacket,
    PubRecPacket,
    PubRecReasonCode,
    PubRelPacket,
    PubRelReasonCode,
    QoS,
    RetainHandling,
    SubAckPacket,
    SubAckReasonCode,
    UnsubAckPacket,
    UnsubAckReasonCode,
    Will,
)

from ._client import (
    Client,
)
from ._exceptions import (
    ConnectError,
    NegativeAckError,
    ProtocolError,
)

__version__ = importlib.metadata.version(__name__)
__all__ = [
    "Client",
    "ConnAckPacket",
    "ConnectError",
    "NegativeAckError",
    "ProtocolError",
    "PubAckPacket",
    "PubAckReasonCode",
    "PubCompPacket",
    "PubCompReasonCode",
    "PubRecPacket",
    "PubRecReasonCode",
    "PubRelPacket",
    "PubRelReasonCode",
    "PublishPacket",
    "QoS",
    "RetainHandling",
    "SubAckPacket",
    "SubAckReasonCode",
    "UnsubAckPacket",
    "UnsubAckReasonCode",
    "Will",
    "__version__",
]
