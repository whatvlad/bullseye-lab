"""Paper trading for freshly graduated Pump coins on PumpSwap (research rule, paper only).

Rule from docs/GRADUATED_FIRST_LOOK_20261010.md, frozen: buy a fixed SOL size at the first
pool trade >= `latency` seconds after graduation, sell everything when the net result reaches
+take_profit% or -stop_loss% (after fees), or after `max_hold` seconds. Fills are simulated
on the PumpSwap constant-product pool using the reserves after the triggering trade and the
pool's own fee rate. Nothing here sends a transaction.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from memebot.providers.solana.encoding import BorshReader
from memebot.providers.solana.pump_idl import BUY_EVENT_DISCRIMINATOR, SELL_EVENT_DISCRIMINATOR

LAMPORTS_PER_SOL = 1_000_000_000
DEFAULT_FEE_BPS = 125  # fresh PumpSwap pools: LP 2 + protocol 93 + creator 30 (measured)
# A real Pump graduation opens the pool with ~62-80 SOL (30 of 84 "graduations" seen on
# 2026-10-09 had 50-100 SOL; the rest were dust pools < 2 SOL or old/large pools).
REAL_POOL_QUOTE_LAMPORTS = (50 * 1_000_000_000, 100 * 1_000_000_000)


def event_fee_bps(data: bytes) -> int | None:
    """Total LP + protocol + coin-creator fee (bps) from a PumpSwap buy/sell event."""
    if data[:8] not in (BUY_EVENT_DISCRIMINATOR, SELL_EVENT_DISCRIMINATOR):
        return None
    reader = BorshReader(data[8:])
    reader.i64()
    for _ in range(7):  # base, limit, user base, user quote, pool base, pool quote, quote
        reader.u64()
    lp_bps = reader.u64()
    reader.u64()
    protocol_bps = reader.u64()
    for _ in range(3):  # protocol fee, vault transfer, user quote amount
        reader.u64()
    for _ in range(7):  # pool, user, two user accounts, two fee accounts, coin creator
        reader.pubkey()
    creator_bps = reader.u64()
    total = lp_bps + protocol_bps + creator_bps
    return total if 0 <= total <= 1000 else None


def reserves_after(
    side: str, base_amount: int, quote_amount: int, pool_base: int, pool_quote: int
) -> tuple[int, int]:
    """Event reserves are pre-trade (checked on 191k consecutive events); apply the trade."""
    if side == "buy":
        return pool_base - base_amount, pool_quote + quote_amount
    return pool_base + base_amount, pool_quote - quote_amount


def buy_tokens(base: int, quote: int, sol_in: int, fee_bps: int) -> int:
    """Tokens out for `sol_in` lamports paid in total (fees charged on top of the swap)."""
    net = sol_in * 10_000 // (10_000 + fee_bps)
    return base * net // (quote + net)


def sell_lamports(base: int, quote: int, tokens: int, fee_bps: int) -> int:
    """Lamports received for selling `tokens` (fees taken from the output)."""
    gross = quote * tokens // (base + tokens)
    return gross * (10_000 - fee_bps) // 10_000


@dataclass
class _Pool:
    mint: str
    graduated_at: float
    buy_after: float | None
    base: int = 0
    quote: int = 0
    fee_bps: int = DEFAULT_FEE_BPS
    tokens: int = 0
    cost: int = 0
    opened_at: float | None = None
    exit_reason: str | None = None
    exit_after: float | None = None
    peak: float = 0.0
    closed: bool = False
    checked: bool = False


@dataclass
class GraduationPaperTrader:
    ledger: Path
    notify: Callable[[str], None] = lambda _text: None
    # Called once per real graduation (pool, mint, opening SOL in lamports): signal mode.
    signal: Callable[[str, str, int], None] | None = None
    size_sol: float = 0.1
    take_profit: float = 30.0
    stop_loss: float = 15.0
    max_hold: float = 1800.0
    latency: float = 0.8
    network_fee_lamports: int = 110_000  # base + priority fee per transaction
    pools: dict[str, _Pool] = field(default_factory=dict)
    closed_results: list[float] = field(default_factory=list)

    def on_graduation(
        self, pool: str, mint: str, graduated_at: float, *, now: float, fresh_seconds: float = 10.0
    ) -> bool:
        """Plan a buy only for coins we start watching right at graduation."""
        if pool in self.pools or now - graduated_at > fresh_seconds:
            return False
        self.pools[pool] = _Pool(mint, graduated_at, buy_after=now + self.latency)
        return True

    def busy(self, pool: str) -> bool:
        state = self.pools.get(pool)
        return state is not None and not state.closed

    def on_trade(
        self,
        pool: str,
        at: float,
        side: str,
        base_amount: int,
        quote_amount: int,
        pool_base: int,
        pool_quote: int,
        fee_bps: int | None,
    ) -> list[dict[str, Any]]:
        state = self.pools.get(pool)
        if state is None or state.closed:
            return []
        if not state.checked:
            state.checked = True
            low, high = REAL_POOL_QUOTE_LAMPORTS
            if not low <= pool_quote <= high:  # not a real graduation pool: never buy
                state.closed = True
                return []
            if self.signal is not None:
                self.signal(pool, state.mint, pool_quote)
        state.base, state.quote = reserves_after(
            side, base_amount, quote_amount, pool_base, pool_quote
        )
        if fee_bps is not None:
            state.fee_bps = fee_bps
        if state.base <= 0 or state.quote <= 0:
            return []
        if state.opened_at is None:
            if state.buy_after is not None and at >= state.buy_after:
                return [self._buy(pool, state, at)]
            return []
        if state.exit_after is not None:
            return [self._sell(pool, state, at)] if at >= state.exit_after else []
        result = self._net_percent(state)
        state.peak = max(state.peak, result)
        reason = None
        if result >= self.take_profit:
            reason = "take_profit"
        elif result <= -self.stop_loss:
            reason = "stop_loss"
        elif at - state.opened_at >= self.max_hold:
            reason = "max_hold"
        if reason:
            state.exit_reason, state.exit_after = reason, at + self.latency
        return []

    def _net_percent(self, state: _Pool) -> float:
        out = sell_lamports(state.base, state.quote, state.tokens, state.fee_bps)
        out -= self.network_fee_lamports
        return (out / state.cost - 1) * 100

    def _buy(self, pool: str, state: _Pool, at: float) -> dict[str, Any]:
        spend = int(self.size_sol * LAMPORTS_PER_SOL)
        state.tokens = buy_tokens(state.base, state.quote, spend, state.fee_bps)
        state.cost = spend + self.network_fee_lamports
        state.opened_at = at
        state.base -= state.tokens
        state.quote += spend * 10_000 // (10_000 + state.fee_bps)
        fill = {
            "event": "buy",
            "at": round(at, 3),
            "pool": pool,
            "mint": state.mint,
            "sol": self.size_sol,
            "tokens": state.tokens,
            "fee_bps": state.fee_bps,
            "seconds_after_graduation": round(at - state.graduated_at, 2),
        }
        self._record(
            fill,
            f"рџџў PAPER BUY graduated {state.mint}\n"
            f"{self.size_sol} SOL, {fill['seconds_after_graduation']} s after "
            f"graduation, fee {state.fee_bps / 100:.2f}%",
        )
        return fill

    def _sell(self, pool: str, state: _Pool, at: float) -> dict[str, Any]:
        out = sell_lamports(state.base, state.quote, state.tokens, state.fee_bps)
        out -= self.network_fee_lamports
        pnl = out - state.cost
        percent = (out / state.cost - 1) * 100
        state.closed = True
        self.closed_results.append(percent)
        assert state.opened_at is not None
        fill = {
            "event": "sell",
            "at": round(at, 3),
            "pool": pool,
            "mint": state.mint,
            "reason": state.exit_reason,
            "pnl_sol": round(pnl / LAMPORTS_PER_SOL, 6),
            "pnl_percent": round(percent, 2),
            "peak_percent": round(state.peak, 2),
            "held_seconds": round(at - state.opened_at, 1),
        }
        wins = sum(1 for r in self.closed_results if r > 0)
        total = sum(self.closed_results) * self.size_sol / 100
        self._record(
            fill,
            f"{'вњ…' if pnl > 0 else 'рџ”ґ'} PAPER SELL graduated {state.mint}\n"
            f"{percent:+.1f}% ({pnl / LAMPORTS_PER_SOL:+.4f} SOL), "
            f"{state.exit_reason}, held {fill['held_seconds']:.0f} s\n"
            f"Session: {len(self.closed_results)} trades, {wins} wins, "
            f"{total:+.4f} SOL",
        )
        return fill

    def _record(self, fill: dict[str, Any], message: str) -> None:
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(fill) + "\n")
        self.notify(message)
