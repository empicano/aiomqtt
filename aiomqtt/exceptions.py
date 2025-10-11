# SPDX-License-Identifier: BSD-3-Clause
"""Custom exceptions raised by the library."""

from mqtt5 import (
    ConnAckPacket,
    PubAckPacket,
    PubCompPacket,
    PubRecPacket,
    PubRelPacket,
    SubAckPacket,
    UnsubAckPacket,
)


class ConnectError(Exception):
    """Raised when the connection to the broker fails or is lost."""


class ProtocolError(Exception):
    """Raised when the protocol is violated."""


class NegativeAckError(Exception):
    """Raised when we receive a negative acknowledgment."""

    def __init__(
        self,
        packet: ConnAckPacket
        | PubAckPacket
        | PubRecPacket
        | PubRelPacket
        | PubCompPacket
        | SubAckPacket
        | UnsubAckPacket,
    ) -> None:
        msg = f"Negative {packet.__class__.__name__}: "
        if isinstance(packet, SubAckPacket | UnsubAckPacket):
            msg += ", ".join([rc.name for rc in packet.reason_codes])
        else:
            msg += packet.reason_code.name
        super().__init__(msg)
        # Attach extra info as exception attributes
        self.packet_id = None if isinstance(packet, ConnAckPacket) else packet.packet_id
        self.reason_str = packet.reason_str
