from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from time import monotonic
from typing import Any

from memebot.core.clock import utc_now

from .client import BirdeyeClient, BirdeyeError


@dataclass(frozen=True, slots=True)
class BirdeyeMarketSnapshot:
    mint: str
    price_usd: Decimal | None
    liquidity_usd: Decimal | None
    market_cap_usd: Decimal | None
    volume_24h_usd: Decimal | None
    observed_at: str
    provider: str = "birdeye_official_rest"


class BirdeyeMarketDataProvider:
    """On-demand, cached enrichment to preserve the limited Standard CU budget."""

    def __init__(self, client: BirdeyeClient, *, cache_seconds: int = 300) -> None:
        self._client = client
        self._cache_seconds = cache_seconds
        self._cache: dict[str, tuple[float, BirdeyeMarketSnapshot]] = {}

    async def token_snapshot(self, mint: str) -> BirdeyeMarketSnapshot:
        cached = self._cache.get(mint)
        if cached is not None and monotonic() - cached[0] < self._cache_seconds:
            return cached[1]
        try:
            payload = await self._client.market_data(mint)
        except BirdeyeError as error:
            if error.status_code not in {400, 403, 404}:
                raise
            payload = await self._client.price(mint)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise BirdeyeError("birdeye_market_data_missing")
        snapshot = BirdeyeMarketSnapshot(
            mint=mint,
            price_usd=_decimal(data, "price", "price_usd", "value"),
            liquidity_usd=_decimal(data, "liquidity", "liquidity_usd"),
            market_cap_usd=_decimal(data, "market_cap", "marketcap", "mc"),
            volume_24h_usd=_decimal(data, "volume_24h_usd", "volume24h", "v24hUSD"),
            observed_at=utc_now().isoformat(),
        )
        self._cache[mint] = (monotonic(), snapshot)
        return snapshot

    async def close(self) -> None:
        await self._client.close()


def _decimal(data: dict[str, Any], *keys: str) -> Decimal | None:
    for key in keys:
        value = data.get(key)
        if value is not None:
            try:
                return Decimal(str(value))
            except ValueError:
                return None
    return None
