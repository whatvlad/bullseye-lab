from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import cast

from memebot.events.models import DomainEvent

type EventHandler[EventT: DomainEvent] = Callable[[EventT], Awaitable[None]]


class EventBus:
    """Deterministic, in-process async event dispatch.

    Handlers are awaited in subscription order. The bus deliberately does not
    create background tasks: failures propagate to the publisher and there is no
    hidden concurrency or loss. A durable transport can replace this boundary if
    measurement justifies it in a later phase.
    """

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler[DomainEvent]]] = defaultdict(list)

    def subscribe[EventT: DomainEvent](
        self,
        event_class: type[EventT],
        handler: EventHandler[EventT],
    ) -> None:
        registered = cast(EventHandler[DomainEvent], handler)
        if registered not in self._handlers[event_class]:
            self._handlers[event_class].append(registered)

    def unsubscribe[EventT: DomainEvent](
        self,
        event_class: type[EventT],
        handler: EventHandler[EventT],
    ) -> None:
        registered = cast(EventHandler[DomainEvent], handler)
        handlers = self._handlers.get(event_class, [])
        if registered in handlers:
            handlers.remove(registered)

    async def publish(self, event: DomainEvent) -> int:
        handlers = [*self._handlers.get(type(event), [])]
        if type(event) is not DomainEvent:
            handlers.extend(self._handlers.get(DomainEvent, []))
        for handler in tuple(handlers):
            await handler(event)
        return len(handlers)
