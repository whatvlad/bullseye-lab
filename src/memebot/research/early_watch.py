"""Cheap coverage admission, bounded hysteresis and per-market window evidence."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

from memebot.providers.solana.canonical import associated_address, curve_address
from memebot.providers.solana.pump_idl import TOKEN_2022_PROGRAM_ID, TOKEN_PROGRAM_ID


class ResearchStage(StrEnum):
    DISCOVERED = "DISCOVERED"
    CHEAP_FILTERED = "CHEAP_FILTERED"
    EARLY_WATCH = "EARLY_WATCH"
    SERIOUS_CANDIDATE = "SERIOUS_CANDIDATE"
    PROOF_PENDING = "PROOF_PENDING"
    REJECTED = "REJECTED"


@dataclass
class EarlyMarket:
    mint: str
    accounts: tuple[str, ...]
    started: datetime
    expires: datetime
    activity: datetime
    state: str = "WATCH_START"
    cooldown_until: datetime | None = None
    acknowledged: datetime | None = None


class EarlyWatch:
    def __init__(
        self,
        capacity: int,
        *,
        ttl_seconds: int = 120,
        idle_seconds: int = 30,
        grace_seconds: int = 5,
    ) -> None:
        if capacity not in {8, 16, 32} or min(ttl_seconds, idle_seconds, grace_seconds) <= 0:
            raise ValueError("invalid bounded early watch policy")
        self.capacity = capacity
        self.ttl = timedelta(seconds=ttl_seconds)
        self.idle = timedelta(seconds=idle_seconds)
        self.grace = timedelta(seconds=grace_seconds)
        self.markets: dict[str, EarlyMarket] = {}
        self.history: dict[str, EarlyMarket] = {}
        self.stages: dict[str, ResearchStage] = {}
        self.removals: list[dict[str, Any]] = []
        self.transitions: list[dict[str, Any]] = []
        self.metrics: Counter[str] = Counter()
        self.active_samples: Counter[int] = Counter()
        self.capacity_missed: set[str] = set()
        self.rejected: set[str] = set()

    def admit(self, mint: str, now: datetime) -> bool:
        if mint in self.rejected:
            return False
        self.stages[mint] = ResearchStage.DISCOVERED
        self.stages[mint] = ResearchStage.CHEAP_FILTERED
        if mint in self.markets:
            self.touch(mint, now)
            return True
        if len(self.markets) >= self.capacity:
            self.metrics["capacity_admission_rejects"] += 1
            self.capacity_missed.add(mint)
            return False
        curve = curve_address(mint)
        accounts = (
            mint,
            curve,
            *(
                associated_address(curve, mint, program)
                for program in (TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID)
            ),
        )
        market = EarlyMarket(mint, accounts, now, now + self.ttl, now)
        self.markets[mint] = market
        self.history[mint] = market
        self.stages[mint] = ResearchStage.EARLY_WATCH
        self.transition(market, "WATCH_START", now)
        self.metrics["watch_starts"] += 1
        return True

    def transition(self, market: EarlyMarket, state: str, now: datetime) -> None:
        market.state = state
        self.transitions.append({"mint": market.mint, "state": state, "at": now.isoformat()})

    def touch(self, mint: str, now: datetime, *, favorable: bool = True) -> None:
        market = self.markets.get(mint)
        if market is None:
            return
        if favorable:
            market.activity = now
            market.cooldown_until = None
            if market.state == "WATCH_COOLDOWN":
                self.transition(market, "WATCH_ACTIVE", now)
        elif market.cooldown_until is None:
            market.cooldown_until = now + self.grace
            self.transition(market, "WATCH_COOLDOWN", now)

    def acknowledge(self, accounts: list[str], now: datetime) -> None:
        covered = set(accounts)
        for market in self.markets.values():
            if set(market.accounts).issubset(covered) and market.acknowledged is None:
                market.acknowledged = now
                self.transition(market, "WATCH_ACTIVE", now)

    def remove(self, mint: str, reason: str, now: datetime) -> None:
        market = self.markets.pop(mint, None)
        self.rejected.add(mint)
        self.stages[mint] = ResearchStage.REJECTED
        if market is not None:
            self.transition(market, "WATCH_REMOVED", now)
            self.removals.append({"mint": mint, "reason": reason, "at": now.isoformat()})

    def expire(self, now: datetime) -> None:
        for mint, market in list(self.markets.items()):
            if now >= market.expires:
                self.remove(mint, "TTL_EXPIRED", now)
            elif market.cooldown_until is not None and now >= market.cooldown_until:
                self.remove(mint, "COOLDOWN_EXPIRED", now)
            elif now - market.activity >= self.idle and market.cooldown_until is None:
                self.touch(mint, now, favorable=False)
        self.active_samples[len(self.markets)] += 1

    def accounts(self) -> list[str]:
        return sorted({account for market in self.markets.values() for account in market.accounts})

    def serious(self, mint: str, at: datetime) -> dict[str, Any]:
        market = self.history.get(mint)
        self.stages[mint] = ResearchStage.SERIOUS_CANDIDATE
        earlier = market is not None and market.started < at and mint in self.markets
        return {
            "mint": mint,
            "serious_at": at.isoformat(),
            "early_watch_before_serious": earlier,
            "ack_before_serious": bool(
                earlier and market and market.acknowledged and market.acknowledged < at
            ),
            "early_watch_at": market.started.isoformat() if market else None,
            "watch_ack_at": market.acknowledged.isoformat()
            if market and market.acknowledged
            else None,
            "watch_to_serious_ms": (at - market.started).total_seconds() * 1000 if market else None,
            "capacity_rejected_before_serious": mint in self.capacity_missed,
        }

    def report(self) -> dict[str, Any]:
        return {
            "capacity": self.capacity,
            "ttl_seconds": self.ttl.total_seconds(),
            "idle_seconds": self.idle.total_seconds(),
            "grace_seconds": self.grace.total_seconds(),
            "metrics": dict(self.metrics),
            "active_count_distribution": dict(self.active_samples),
            "transitions": self.transitions,
            "removals": self.removals,
            "stages": {m: str(s) for m, s in self.stages.items()},
        }
