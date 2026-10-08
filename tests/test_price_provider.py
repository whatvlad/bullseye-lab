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


@pytest.mark.asyncio
async def test_rate_limited_refresh_keeps_last_good_price_and_backs_off() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls > 1:
            return httpx.Response(429)
        return httpx.Response(
            200,
            text=json.dumps(
                {
                    "solana": {"usd": 150, "last_updated_at": 1_777_000_000},
                    "tether": {"usd": 1, "last_updated_at": 1_777_000_000},
                }
            ),
        )

    provider = CoinGeckoQuotePriceProvider(
        "https://price.invalid/api/v3",
        cache_seconds=0,
        transport=httpx.MockTransport(handler),
    )
    try:
        first = await provider.quote_price("USDT")
        assert await provider.quote_price("USDT") == first  # 429: last good price kept
        assert await provider.quote_price("USDT") == first  # within backoff: no request
    finally:
        await provider.close()
    assert calls == 2


@pytest.mark.asyncio
async def test_failure_without_any_good_price_still_raises() -> None:
    from memebot.providers.price.coingecko import QuotePriceError

    provider = CoinGeckoQuotePriceProvider(
        "https://price.invalid/api/v3",
        transport=httpx.MockTransport(lambda request: httpx.Response(429)),
    )
    try:
        with pytest.raises(QuotePriceError):
            await provider.quote_price("USDT")
    finally:
        await provider.close()
