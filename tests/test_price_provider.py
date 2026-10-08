import json
from decimal import Decimal

import httpx
import pytest

from memebot.providers.price.coingecko import CoinGeckoQuotePriceProvider


@pytest.mark.asyncio
async def test_coingecko_keyless_sol_usdt_conversion_is_decimal_and_cached() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert "api-key" not in str(request.url)
        return httpx.Response(
            200,
            text=json.dumps(
                {
                    "solana": {"usd": 150.25, "last_updated_at": 1_777_000_000},
                    "tether": {"usd": 1.001, "last_updated_at": 1_777_000_001},
                }
            ),
        )

    provider = CoinGeckoQuotePriceProvider(
        "https://price.invalid/api/v3",
        transport=httpx.MockTransport(handler),
    )
    try:
        first = await provider.quote_price("USDT")
        second = await provider.quote_price("USDT")
    finally:
        await provider.close()

    assert first.price == Decimal("150.25") / Decimal("1.001")
    assert second == first
    assert calls == 1
