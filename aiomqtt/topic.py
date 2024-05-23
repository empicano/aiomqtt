# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import attrs
import sys
import functools
import anyio
from contextlib import contextmanager

from .queue import Queue

from typing import Iterable

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

    if len(res) > 2 and res[0] == "$share":
        # Shared subscriptions use the topic structure: $share/<group_id>/<topic>
        res = res[2:]
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
            msg = f"Wildcard must be of type str, not {type(value)}"
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

def _to_wild(w: WildcardLike):
    if isinstance(w,str):
        w = Wildcard(w)
    return w

@attrs.frozen(eq=False)
class Subscription:
    """
    One subscription.

    Usage::

        sub = Subscription()

        while True:
            try:
                with sub.subscribed_to(tree):
                    async for msg in sub:
                        process(msg)
            except anyio.IncompleteRead:
                # overflow. We've been dropped.
    """
    topic: WildcardLike = attrs.field(converter=_to_wild)
    queue: Queue = attrs.field(factory=functools.partial(Queue, 10))

    @contextmanager
    def subscribed_to(self, tree: SubscriptionTree):
        try:
            tree.attach(self)
            yield self
        finally:
            tree.detach(self)

    def close(self):
        """
        Close the queue's write side.

        This is called by the dispatcher when the queue is full, indicating
        lost messages.
        """
        self.queue.close_writer()

    def __iter__(self):
        return self

    async def __aiter__(self):
        """
        Read the next message.
        """
        try:
            return await self.queue.get()
        except StopAsyncIteration:
            raise anyio.IncompleteRead(self)


@attrs.frozen
class SubscriptionTree:
    """
    Remember wildcards per tree
    """
    subscriptions: set[Subscription] = attrs.field(factory=set)
    child: dict[str, SubscriptionTree] = attrs.field(factory=dict)

    def __getitem__(self, elem):
        # convenient for debugging, not used in code
        return self.child[elem]

    @property
    def empty(self):
        """Flag whether this subtree has no children or subscriptions"""
        if self.child:
            return False
        if not self.subscriptions:
            return False
        return True

    def _attach(self, sub:Subscription, topic:Iterable[str]):
        # attach on this level
        try:
            s = next(topic)

        except StopIteration:
            self.subscriptions.add(sub)

        else:
            sn = self.child.get(s)
            if sn is None:
                self.child[s] = sn = SubscriptionTree()
            sn._attach(sub, topic)

    def _detach(self, sub:Subscription, topic:Iterable[str]):
        # detach on this level
        try:
            s = next(topic)

        except StopIteration:
            self.subscriptions.discard(sub)

        else:
            try:
                sn = self.child[s]
            except KeyError:
                # This happens when the subscription was unlinked
                # by the tree's dispatcher, due to a full queue
                return
            sn._detach(sub, topic)

            if sn.empty:
                del self.child[s]


    def attach(self, sub: Subscription):
        """Add a subscription to this tree.

        Adding a subscription twice is a no-op.
        """
        self._attach(sub, iter(sub.topic.levels))

    def detach(self, sub: Subscription):
        """Remove a subscription from this tree.

        The tree is pruned if warranted. The subscription *must* have been
        attached.
        """
        self._detach(sub, iter(sub.topic.levels))


    def dispatch(self, message:Message):
        """Send a message to all subscribing queues.

        Returns the number of queues dispatched to.
        """
        return self._dispatch(message, iter(message.topic.levels))

    def _disp_here(self, message:Message, wild:bool = False):
        drop = []
        for sb in self.subscriptions:
            if wild and not sb.topic.prefix:
                continue
            try:
                sb.queue.put_nowait(message)
            except anyio.WouldBlock:
                drop.append(sb)
                sb.close()

        if drop:
            sb -= drop
        return len(drop)

    def _dispatch(self, message:Message, topic:Iterable[str]):
        try:
            s = next(topic)

        except StopIteration:
            # We are at the leaf. Feed to all subscribers.
            return self._disp_here(message)

        else:
            # Dispatch to the next level, either named …
            n = 0

            sb = self.child.get(s)
            if sb is not None:
                nn = sb._dispatch(message, topic)
                if nn:
                    # Some subscriptions were dropped.
                    # Clean them up if necessary.
                    if sb.empty:
                        del self.child[s]
                    n += nn

            # … or via '+' wildcard.
            sb = self.child.get('+')
            if sb is not None:
                nn = sb._dispatch(message, topic)
                if nn:
                    if sb.empty:
                        del self.child['+']
                    n += nn

            # Finally, send to any '#' wildcard topics.
            n += self._disp_here(message, wild=True)

            return n
