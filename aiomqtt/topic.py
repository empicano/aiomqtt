# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import attrs
import sys

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias


MAX_TOPIC_LENGTH = 65535


def _split_topic(self):
    if not isinstance(self.value, str):
        return ()
    return tuple(self.value.split("/"))


@attrs.frozen
class Topic:
    """MQTT topic that can be published and subscribed to.

    Args:
        value: The topic string.

    Attributes:
        value: The topic string.
    """

    value: str = attrs.field()
    levels: List[str] = attrs.field(
        repr=False, hash=False, default=attrs.Factory(_split_topic, takes_self=True)
    )

    @value.validator
    def check(self, attribute, value) -> None:
        """Validate the topic."""
        if not isinstance(value, str):
            msg = "Wildcard must be of type str"
            raise TypeError(msg)
        if (
            len(value) == 0
            or len(value) > MAX_TOPIC_LENGTH
            or "+" in value or "#" in value
        ):
            msg = f"Invalid topic: {self.value}"
            raise ValueError(msg)

    def matches(self, wildcard: WildcardLike) -> bool:
        """Check if the topic matches a given wildcard.

        Args:
            wildcard: The wildcard to match against.

        Returns:
            True if the topic matches the wildcard, False otherwise.
        """
        if not isinstance(wildcard, Wildcard):
            wildcard = Wildcard(wildcard)

        topic_levels = self.levels
        wildcard_levels = wildcard.levels
        if len(wildcard_levels) > 0 and wildcard_levels[0] == "$share":
            # Shared subscriptions use the topic structure: $share/<group_id>/<topic>
            wildcard_levels = wildcard_levels[2:]

        # If the topic is shorter than the wildcard it can't match
        if len(topic_levels) < len(wildcard_levels):
            return False

        # Unless the wildcard has a trailing '#', if it is longer than the
        # wildcard it can't match either
        if not wildcard.prefix and len(wildcard_levels) < len(topic_levels):
            return False

        # now compare the individual pieces
        for t, w in zip(topic_levels, wildcard_levels):
            if t != w and w != "+":
                return False
        return True


TopicLike: TypeAlias = "str | Topic"



def _split_wildcard(self):
    if not isinstance(self.value, str):
        return ()
    res = self.value.split("/")
    if res[-1] == '#':
        res.pop()
    return tuple(res)

def _has_hash(self):
    if not isinstance(self.value, str):
        return False
    return self.value == '#' or self.value.endswith('/#')


@attrs.frozen
class Wildcard(Topic):
    """MQTT wildcard that can be subscribed to, but not published to.

    A wildcard is similar to a topic, but can optionally contain ``+`` and ``#``
    placeholders. You can access the ``value`` attribute directly to perform ``str``
    operations on a wildcard.

    Args:
        value: The wildcard string.

    Attributes:
        value: The wildcard string.
        levels: The wildcard string, pre-split, without trailing '#' if any.
        prefix: indicates that the wildcard has a trailing '#'.
    """

    value: str = attrs.field()
    levels: List[str] = attrs.field(
        repr=False, hash=False, default=attrs.Factory(_split_wildcard, takes_self=True)
    )
    prefix: bool = attrs.field(default=attrs.Factory(_has_hash, takes_self=True))

    def __str__(self) -> str:
        return self.value

    @value.validator
    def _check_value(self, attribute, value) -> None:
        """Validate the wildcard."""
        if not isinstance(value, str):
            msg = "Wildcard must be of type str"
            raise TypeError(msg)
        if (
            len(value) == 0
            or len(value) > MAX_TOPIC_LENGTH
            or "#/" in value
            or any(
                "+" in level or "#" in level for level in self.levels if len(level) > 1
            )
        ):
            msg = f"Invalid wildcard: {self.value}"
            raise ValueError(msg)


WildcardLike: TypeAlias = "str | Wildcard"
