from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from decimal import Decimal
from time import monotonic
from typing import Any, cast

import httpx
from pydantic import SecretStr

from memebot.core.clock import utc_now

_MAX_RESPONSE_BYTES = 1_000_000


class BirdeyeError(RuntimeError):
    def __init__(self, code: str, *, status_code: int | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class BirdeyeCapabilityReport:
    authenticated: bool
    available: frozenset[str]
    unavailable: dict[str, str]
    credits: dict[str, Any] | None
    probed_at: str


class BirdeyeClient:
    """Bounded official BDS REST client. API keys are header-only and never logged."""

    def __init__(
        self,
        base_url: str,
        api_key: SecretStr,
        *,
        timeout_seconds: float = 10,
        minimum_interval_seconds: float = 1,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds),
            transport=transport,
            headers={
                "X-API-KEY": api_key.get_secret_value(),
                "x-chain": "solana",
                "accept": "application/json",
            },
        )
        self._minimum_interval_seconds = minimum_interval_seconds
        self._last_request_at = 0.0
        self._rate_lock = asyncio.Lock()

    async def credits(self) -> dict[str, Any]:
        return await self.get("/utils/v1/credits")

    async def price(self, mint: str) -> dict[str, Any]:
        return await self.get("/defi/price", params={"address": mint})

    async def market_data(self, mint: str) -> dict[str, Any]:
        return await self.get("/defi/v3/token/market-data", params={"address": mint})

    async def new_listings(self, *, limit: int = 1) -> dict[str, Any]:
        return await self.get(
            "/defi/v2/tokens/new_listing",
            params={"limit": limit, "meme_platform_enabled": "true"},
        )

    async def holder_profile(self, mint: str) -> dict[str, Any]:
        return await self.get(
            "/token/v1/holder-profile",
            params={
                "token_address": mint,
                "interval": "1h",
                "ui_amount_mode": "raw",
                "include_zero_balance": "false",
            },
        )

    async def probe(self, reference_mint: str) -> BirdeyeCapabilityReport:
        checks: dict[str, tuple[str, dict[str, str | int] | None]] = {
            "account_credits": ("/utils/v1/credits", None),
            "supported_networks": ("/defi/networks", None),
            "token_price": ("/defi/price", {"address": reference_mint}),
            "token_market_data": (
                "/defi/v3/token/market-data",
                {"address": reference_mint},
            ),
            "new_listings": (
                "/defi/v2/tokens/new_listing",
                {"limit": 1, "meme_platform_enabled": "true"},
            ),
        }
        available: set[str] = set()
        unavailable: dict[str, str] = {"token_exit_liquidity": "unsupported_chain_base_only"}
        credits: dict[str, Any] | None = None
        for capability, (path, params) in checks.items():
            try:
                payload = await self.get(path, params=params)
            except BirdeyeError as error:
                unavailable[capability] = error.code
            else:
                available.add(capability)
                if capability == "account_credits":
                    credits = _safe_credit_summary(payload)
        return BirdeyeCapabilityReport(
            authenticated="account_credits" in available,
            available=frozenset(available),
            unavailable=unavailable,
            credits=credits,
            probed_at=utc_now().isoformat(),
        )

    async def get(self, path: str, *, params: dict[str, str | int] | None = None) -> dict[str, Any]:
        response: httpx.Response | None = None
        for attempt in range(2):
            await self._wait_for_rate_slot()
            try:
                response = await self._client.get(f"{self._base_url}{path}", params=params)
            except httpx.HTTPError as error:
                raise BirdeyeError("birdeye_transport_error") from error
            if response.status_code != 429 or attempt == 1:
                break
            await asyncio.sleep(1.1)
        assert response is not None
        if len(response.content) > _MAX_RESPONSE_BYTES:
            raise BirdeyeError("birdeye_response_too_large", status_code=response.status_code)
        if response.status_code == 401:
            raise BirdeyeError("birdeye_unauthorized", status_code=401)
        if response.status_code == 403:
            raise BirdeyeError("birdeye_plan_forbidden", status_code=403)
        if response.status_code == 429:
            raise BirdeyeError("birdeye_rate_limited", status_code=429)
        if response.status_code >= 400:
            raise BirdeyeError("birdeye_http_error", status_code=response.status_code)
        try:
            payload = json.loads(response.content, parse_float=Decimal, parse_int=Decimal)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise BirdeyeError("birdeye_invalid_json") from error
        if not isinstance(payload, dict):
            raise BirdeyeError("birdeye_invalid_payload")
        if payload.get("success") is False:
            raise BirdeyeError("birdeye_unsuccessful_response")
        return cast(dict[str, Any], payload)

    async def _wait_for_rate_slot(self) -> None:
        async with self._rate_lock:
            elapsed = monotonic() - self._last_request_at
            delay = self._minimum_interval_seconds - elapsed
            if delay > 0:
                await asyncio.sleep(delay)
            self._last_request_at = monotonic()

    async def close(self) -> None:
        await self._client.aclose()


def _safe_credit_summary(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    if not isinstance(data, dict):
        return {"available": True}
    allowed = {
        "plan",
        "package",
        "total",
        "used",
        "remaining",
        "overage_usage",
        "overage_cost",
        "start_time",
        "end_time",
    }
    return {key: value for key, value in data.items() if key in allowed}
