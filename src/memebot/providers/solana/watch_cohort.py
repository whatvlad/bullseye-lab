"""Small dynamic evidence watch set; no RPC enrichment or strategy changes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from memebot.providers.solana.canonical import associated_address, curve_address
from memebot.providers.solana.pump_idl import (
    NATIVE_SOL_MINT,
    TOKEN_2022_PROGRAM_ID,
    TOKEN_PROGRAM_ID,
    WRAPPED_SOL_MINT,
)


@dataclass(frozen=True)
class WatchedMarket:
    mint: str
    curve: str
    vaults: tuple[str, ...]
    added_at: datetime
    expires_at: datetime
    last_activity_at: datetime

    @property
    def accounts(self) -> tuple[str, ...]:
        return (self.mint, self.curve, *self.vaults)


class WatchCohort:
    def __init__(
        self, *, capacity: int = 8, ttl_seconds: int = 120, idle_seconds: int = 30
    ) -> None:
        if min(capacity, ttl_seconds, idle_seconds) <= 0:
            raise ValueError("invalid bounded watch policy")
        self.capacity = capacity
        self.ttl = timedelta(seconds=ttl_seconds)
        self.idle = timedelta(seconds=idle_seconds)
        self.markets: dict[str, WatchedMarket] = {}
        self.removals: list[dict[str, str]] = []

    def observe(
        self,
        mint: str,
        *,
        now: datetime,
        standard: bool,
        quote_mint: str,
        continuity: str,
        multi_event: bool,
        cashback: bool = False,
        complete: bool = False,
        migrated: bool = False,
        supported_fee_route: bool = True,
    ) -> bool:
        self.expire(now)
        if (
            not standard
            or quote_mint not in {NATIVE_SOL_MINT, WRAPPED_SOL_MINT}
            or continuity != "EXACT"
            or multi_event
            or cashback
            or complete
            or migrated
            or not supported_fee_route
        ):
            self.remove(mint, "OUT_OF_SCOPE", now)
            return False
        current = self.markets.get(mint)
        if current is not None:
            self.markets[mint] = WatchedMarket(
                current.mint,
                current.curve,
                current.vaults,
                current.added_at,
                current.expires_at,
                now,
            )
            return True
        if len(self.markets) >= self.capacity:
            return False  # No eviction of active proof evidence to admit more launches.
        curve = curve_address(mint)
        vaults = tuple(
            associated_address(curve, mint, program)
            for program in (TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID)
        )
        self.markets[mint] = WatchedMarket(mint, curve, vaults, now, now + self.ttl, now)
        return True

    def remove(self, mint: str, reason: str, now: datetime) -> None:
        if self.markets.pop(mint, None) is not None:
            self.removals.append({"mint": mint, "reason": reason, "at": now.isoformat()})
            self.removals = self.removals[-128:]

    def expire(self, now: datetime) -> None:
        for mint, market in list(self.markets.items()):
            if now >= market.expires_at:
                self.remove(mint, "TTL_EXPIRED", now)
            elif now - market.last_activity_at >= self.idle:
                self.remove(mint, "CANDIDATE_IDLE", now)

    def accounts(self) -> list[str]:
        return sorted({a for market in self.markets.values() for a in market.accounts})
