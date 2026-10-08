from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from time import monotonic
from typing import Any, cast

import httpx

from memebot.core.clock import utc_now
from memebot.models.common import DataConfidence, ProviderProvenance
from memebot.providers.solana.pump_idl import WRAPPED_SOL_MINT

from .base import QuotePrice


class QuotePriceError(RuntimeError):
    pass


class CoinGeckoQuotePriceProvider:
    """Small cached adapter for CoinGecko's official keyless public endpoint."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 10,
        cache_seconds: float = 20,
        retry_after_failure_seconds: float = 15,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._endpoint = f"{base_url.rstrip('/')}/simple/price"
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds), transport=transport
        )
        self._cache_seconds = cache_seconds
        self._cached_at = 0.0
        self._failed_at = float("-inf")
        self._retry_after_failure_seconds = retry_after_failure_seconds
        self._cache: dict[str, QuotePrice] = {}

    async def quote_price(self, portfolio_currency: str) -> QuotePrice:
        currency = portfolio_currency.upper()
        if currency not in {"USD", "USDT"}:
            raise QuotePriceError("unsupported_portfolio_currency")
        now = monotonic()
        cached = self._cache.get(currency)
        if cached is not None and now - self._cached_at <= self._cache_seconds:
            return cached
        if cached is not None and now - self._failed_at < self._retry_after_failure_seconds:
            return cached
        try:
            await self._refresh()
        except QuotePriceError:
            # The keyless endpoint rate-limits. Keep the last good price; execution
            # enforces its own maximum quote age from the provenance timestamp.
            self._failed_at = monotonic()
            if cached is None:
                raise
            return cached
        result = self._cache.get(currency)
        if result is None:
            raise QuotePriceError("quote_price_unavailable")
        return result

    async def _refresh(self) -> None:
        try:
            response = await self._client.get(
                self._endpoint,
                params={
                    "ids": "solana,tether",
                    "vs_currencies": "usd",
                    "include_last_updated_at": "true",
                    "precision": "full",
                },
                headers={"accept": "application/json"},
            )
            response.raise_for_status()
            if len(response.content) > 64_000:
                raise QuotePriceError("price_response_too_large")
            body = cast(
                dict[str, Any],
                json.loads(response.text, parse_float=Decimal, parse_int=int),
            )
            solana = cast(dict[str, Any], body["solana"])
            tether = cast(dict[str, Any], body["tether"])
            sol_usd = Decimal(solana["usd"])
            tether_usd = Decimal(tether["usd"])
            timestamp = min(int(solana["last_updated_at"]), int(tether["last_updated_at"]))
            observed_at = datetime.fromtimestamp(timestamp, tz=UTC)
            if sol_usd <= 0 or tether_usd <= 0:
                raise QuotePriceError("non_positive_quote_price")
        except QuotePriceError:
            raise
        except (httpx.HTTPError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise QuotePriceError("price_provider_error") from error

        received_at = utc_now()
        common = {
            "provider": "coingecko_keyless_public",
            "observed_at": observed_at,
            "received_at": received_at,
            "confidence": DataConfidence.HIGH,
            "source_reference": "simple/price:solana,tether:usd",
        }
        self._cache = {
            "USD": QuotePrice(
                quote_asset=WRAPPED_SOL_MINT,
                portfolio_currency="USD",
                price=sol_usd,
                provenance=ProviderProvenance(**common),
            ),
            "USDT": QuotePrice(
                quote_asset=WRAPPED_SOL_MINT,
                portfolio_currency="USDT",
                price=sol_usd / tether_usd,
                provenance=ProviderProvenance(**common),
            ),
        }
        self._cached_at = monotonic()

    async def close(self) -> None:
        await self._client.aclose()
