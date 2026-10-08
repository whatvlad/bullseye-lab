from datetime import UTC, datetime

import pytest

from memebot.events.bus import EventBus
from memebot.events.models import DomainEvent, TokenDiscovered

MINT = "So11111111111111111111111111111111111111112"


@pytest.mark.asyncio
async def test_event_bus_awaits_handlers_in_registration_order() -> None:
    bus = EventBus()
    calls: list[str] = []

    async def first(_event: TokenDiscovered) -> None:
        calls.append("first")

    async def second(_event: TokenDiscovered) -> None:
        calls.append("second")

    async def all_events(_event: DomainEvent) -> None:
        calls.append("all")

    bus.subscribe(TokenDiscovered, first)
    bus.subscribe(TokenDiscovered, second)
    bus.subscribe(DomainEvent, all_events)
    event = TokenDiscovered(
        provider="test",
        source_event_at=datetime(2026, 8, 22, tzinfo=UTC),
        mint=MINT,
    )

    handled = await bus.publish(event)

    assert handled == 3
    assert calls == ["first", "second", "all"]


@pytest.mark.asyncio
async def test_event_bus_propagates_handler_failures() -> None:
    bus = EventBus()

    async def broken(_event: TokenDiscovered) -> None:
        raise RuntimeError("persistence unavailable")

    bus.subscribe(TokenDiscovered, broken)
    event = TokenDiscovered(
        provider="test",
        source_event_at=datetime(2026, 8, 22, tzinfo=UTC),
        mint=MINT,
    )

    with pytest.raises(RuntimeError, match="persistence unavailable"):
        await bus.publish(event)
