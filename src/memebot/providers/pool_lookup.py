"""Pool-address discovery only; every suggested address must be verified over RPC."""

from __future__ import annotations

from time import monotonic
from typing import Protocol

import httpx

from memebot.models.common import is_solana_address
from memebot.providers.solana.pump_idl import WRAPPED_SOL_MINT


class PoolLookup(Protocol):
    async def pools(self, mint: str) -> tuple[str, ...]: ...


class DexScreenerPoolLookup:
    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport
        self._cache: dict[str, tuple[float, tuple[str, ...]]] = {}

    async def pools(self, mint: str) -> tuple[str, ...]:
        if not is_solana_address(mint):
            return ()
        cached = self._cache.get(mint)
        if cached and monotonic() - cached[0] < 60:
            return cached[1]
        result = ()
        try:
            async with httpx.AsyncClient(timeout=6, transport=self._transport) as client:
                response = await client.get(
                    f"https://api.dexscreener.com/token-pairs/v1/solana/{mint}"
                )
                response.raise_for_status()
                rows = response.json()
            if isinstance(rows, list):
                result = tuple(
                    dict.fromkeys(
                        row["pairAddress"]
                        for row in rows
                        if isinstance(row, dict)
                        and row.get("chainId") == "solana"
                        and row.get("dexId") == "pumpswap"
                        and isinstance(row.get("baseToken"), dict)
                        and isinstance(row.get("quoteToken"), dict)
                        and isinstance(row.get("pairAddress"), str)
                        and (row.get("baseToken") or {}).get("address") == mint
                        and (row.get("quoteToken") or {}).get("address") == WRAPPED_SOL_MINT
                        and is_solana_address(row.get("pairAddress", ""))
                    )
                )[:4]
        except (httpx.HTTPError, ValueError, TypeError):
            pass
        if len(self._cache) >= 256:
            self._cache.pop(next(iter(self._cache)))
        self._cache[mint] = (monotonic(), result)
        return result
