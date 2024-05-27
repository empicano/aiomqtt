# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import attrs
import sys
import functools
import anyio
from contextlib import contextmanager, ExitStack

from .queue import Queue
from .types import extract_topics

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
        if len(wildcard_levels) < len(topic_levels):
            # The topic is longer than the wildcard: this requires a prefix
            # match
            if not wildcard.prefix:
                return False
            # wildcards must not match on '$subtopic'
            if topic_levels[len(wildcard_levels)].startswith('$'):
                return False

        # now compare the individual pieces
        for t, w in zip(topic_levels, wildcard_levels):
            if t != w:
                if w != "+":
                    return False
                if t.startswith('$'):
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
        # Shared subscriptions use the topic structure '$share/<group_id>/<topic>'
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
        value (str):
            The wildcard topic.

    Attributes:
        value (str):
            The wildcard topic.
        levels (tuple[str]):
            The topic, pre-split on '/'.

            Leading shared topics '$share/XXX/' or trailing multi-level
            wildcards '/#' are not included in this attribute.
        prefix (bool):
            indicates that the wildcard has a trailing multi-level wildcard '#'.
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


@attrs.define(eq=False)
class Subscriptions:
    """
    A handler for possibly-multiple subscriptions.

    Args:
        topics (SubscribeTopic):
            The topic(s) we want to subscribe to.
        queue (Queue):
            The queue to send messages to. If `None` a transient queue will
            be created.
    """
    topics: SubscribeTopic
    queue: Queue = None

    @contextmanager
    def subscribed_to(self, tree: SubscriptionTree, queue_len:int =10):
        """
        Add our subscription(s) to this tree.

        Args:
            tree (SubscriptionTree):
                The tree to hook our subscription(s) into.
            queue_len (int):
                If using a transient queue, its maximum length.

        This is a context manager. It yields an iterator for the queue
        which raises `anyio.IncompleteRead` if/when the queue overflows.

        """
        do_close = False
        if self.queue is None:
            self.queue = Queue(queue_len)
            do_close = True

        try:
            with ExitStack() as s:
                for top in extract_topics(self.topics):
                    sub = Subscription(top, self.queue)
                    s.enter_context(sub.subscribed_to(tree))
                yield self
        finally:
            if do_close:
                self.queue.close_reader()
                self.queue.close_writer()

    def __aiter__(self):
        return self

    async def __anext__(self):
        """
        Read the next message.
        """
        try:
            return await self.queue.get()
        except StopAsyncIteration:
            raise anyio.IncompleteRead(self)


@attrs.define(eq=False)
class Subscription:
    """
    One subscription.

    Usage::

        sub = Subscription()

        while True:
            try:
                with sub.subscribed_to(tree):
                    async for msg in sub:
                        await process(msg)
            except anyio.IncompleteRead:
                # The subscription has been dropped because
                # our processing was too slow.
                # 
                # Recovering from this error typically involves
                # re-subscribing to the topic(s), to get the server to
                # resend any persistent messages that we might have missed.
                ...

        # in some other task
        tree.dispatch(Message("/some/topic", ...))

    """
    topic: WildcardLike = attrs.field(converter=_to_wild)
    queue: Queue = None

    @contextmanager
    def subscribed_to(self, tree: SubscriptionTree):
        do_close = False
        if self.queue is None:
            self.queue = Queue()
            do_close = True

        try:
            tree.attach(self)
            yield self
        finally:
            tree.detach(self)

            if do_close:
                self.queue.close_reader()
                self.queue.close_writer()

    def close(self):
        """
        Close the queue's write side.

        Called by the dispatcher when the queue is full,
        indicating lost messages.
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
    Collect subscriptions and dispatch to them efficiently.

    Attributes:
        subscriptions (set[Subscription]):
            The subscriptions on this topic, or its multi-level wildcard (trailing '#').
        child (dict[str, SubscriptionTree]):
            Subscriptions on the next level of the topic hierarchy,
            indexed by its name or the single-level wildcard('+')
    """
    subscriptions: set[Subscription] = attrs.field(factory=set)
    child: dict[str, SubscriptionTree] = attrs.field(factory=dict)

    def __getitem__(self, elem):
        # convenient for debugging, not used in code
        return self.child[elem]

    @property
    def empty(self):
        """Flag. True iff this (sub)tree has no children or subscriptions"""
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


    def attach(self, sub: Subscription) -> None:
        """Add a subscription to this tree.

        Adding a subscription twice is a no-op.

        Args:
            sub (Subscription): The subscription to add.
        """
        self._attach(sub, iter(sub.topic.levels))

    def detach(self, sub: Subscription) -> None:
        """Remove a subscription from this tree.

        The tree is pruned if warranted.

        Detaching an unattached subscription is a no-op.

        Args:
            sub (Subscription): The subscription to remove.
        """
        self._detach(sub, iter(sub.topic.levels))


    def dispatch(self, message: Message) -> int:
        """Send a message to all subscribing queues.

        Args:
            message (Message): The message to send.
            
        Returns:
            the number of queues dropped.

        """
        return self._dispatch(message, iter(message.topic.levels))

    def _disp_here(self, message:Message, multi:bool = False):
        # local dispatch. If @multi is set, only multi-level
        # wildcard (trailing '#') subscriptions are processed.
        drop = []
        for sb in self.subscriptions:
            if multi and not sb.topic.prefix:
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

            if not s.startswith('$'):  # MQTT-4.7.2-1
                # … or via '+' wildcard.
                sb = self.child.get('+')
                if sb is not None:
                    nn = sb._dispatch(message, topic)
                    if nn:
                        if sb.empty:
                            del self.child['+']
                        n += nn

                # Finally, send to multi-level ('#') wildcard topics
                n += self._disp_here(message, multi=True)

            return n
