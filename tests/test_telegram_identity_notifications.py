import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from memebot.events.models import PaperActionExpired
from memebot.telegram.notifications import TelegramTradeNotifier


@pytest.mark.asyncio
@pytest.mark.parametrize("lookup_failure", [False, True])
async def test_dispatch_enriches_names_and_keeps_full_mint_when_lookup_fails(
    monkeypatch, lookup_failure
):
    sent = []

    class FakeBot:
        def __init__(self, **kwargs):
            self.session = self

        async def close(self):
            pass

        async def send_message(self, user_id, message):
            sent.append(message)

    async def lookup(mint):
        if lookup_failure:
            raise RuntimeError("metadata unavailable")
        return {"name": "AnsemWideWeb", "symbol": "AWW"}

    monkeypatch.setattr("memebot.telegram.notifications.Bot", FakeBot)
    notifier = TelegramTradeNotifier(
        "unused", frozenset({1}), minimum_interval_seconds=0, token_lookup=lookup
    )
    mint = "So11111111111111111111111111111111111111112"
    event = PaperActionExpired(
        provider="test",
        source_event_at=datetime.now(UTC),
        portfolio_id=uuid4(),
        mint=mint,
        action="entry",
        reason="stale",
    )
    await notifier.start()
    notifier.enqueue_event(event)
    await asyncio.wait_for(notifier._queue.join(), 2)
    await notifier.close()
    assert mint in sent[-1] and f"solscan.io/token/{mint}" in sent[-1]
    assert f"dexscreener.com/solana/{mint}" in sent[-1]
    if not lookup_failure:
        assert "AnsemWideWeb (AWW)" in sent[-1]
