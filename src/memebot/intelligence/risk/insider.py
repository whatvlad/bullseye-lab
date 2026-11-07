"""Who holds the supply: big holders, who funded them, and fresh wallets.

The wallet-cluster part of a "bubble map": holders funded by the same wallet are
probably one operator. Facts are logged as shadow evidence first; they do not affect
risk decisions until backtested and turned into rules.
"""

from __future__ import annotations

import asyncio
import base64
from collections import Counter, OrderedDict
from dataclasses import dataclass
from decimal import Decimal
from time import time
from typing import Any, Protocol

from memebot.core.logging import get_logger
from memebot.providers.solana.pump_idl import decode_token_account

# Fixed thresholds are reported side by side so rules can be chosen from backtests.
HOLDER_THRESHOLDS = (Decimal(1), Decimal(2), Decimal(3), Decimal(5))
FRESH_WALLET_SECONDS = 24 * 3600
# A funder seen behind this many distinct wallets is a hub (exchange, router, faucet),
# not evidence that its wallets belong to one operator.
HUB_FUNDER_WALLETS = 25
_SIGNATURE_PAGE = 100


class RawRpc(Protocol):
    async def _call(self, method: str, params: list[object] | None = None) -> object: ...


@dataclass(frozen=True, slots=True)
class WalletOrigin:
    funder: str | None  # first SOL sender into the wallet; None for aged/unknown
    first_seen: int | None  # unix time of the wallet's first transaction, if reachable
    aged: bool  # more than one page of history: not a fresh wallet


@dataclass(frozen=True, slots=True)
class InsiderFacts:
    holders: tuple[tuple[str, Decimal], ...]  # (owner, % of circulating), curve excluded
    holders_over: dict[str, tuple[int, Decimal]]  # threshold -> (count, combined %)
    linked_supply_percent: Decimal  # held by holders sharing a funder with another holder
    linked_cluster_count: int
    largest_cluster_percent: Decimal
    fresh_holder_count: int
    fresh_supply_percent: Decimal
    resolved_holders: int


class WalletFunderResolver:
    """Resolve a wallet's funder and age with at most two RPC calls, cached forever."""

    def __init__(
        self,
        rpc: RawRpc,
        *,
        concurrency: int = 4,
        requests_per_second: float = 8,
        cache_size: int = 100_000,
    ) -> None:
        # Use a dedicated RPC client: a 429 here must never trip the trading client's
        # circuit breaker (that pauses entries).
        self._rpc = rpc
        self._limit = asyncio.Semaphore(concurrency)
        self._interval = 1 / requests_per_second
        self._pace = asyncio.Lock()
        self._next_at = 0.0
        self._cache: OrderedDict[str, WalletOrigin] = OrderedDict()
        self._cache_size = cache_size
        self.calls: Counter[str] = Counter()
        self.funder_wallets: Counter[str] = Counter()
        self._logger = get_logger("memebot.insider")

    async def origin(self, wallet: str) -> WalletOrigin | None:
        cached = self._cache.get(wallet)
        if cached is not None:
            return cached
        try:
            async with self._limit:
                result = await self._resolve(wallet)
        except Exception as error:  # an unresolved wallet is reported, never fatal
            self.calls["errors"] += 1
            self.calls[f"error:{getattr(error, 'code', type(error).__name__)}"] += 1
            self._logger.debug("wallet_origin_failed", error_type=type(error).__name__)
            return None
        self._cache[wallet] = result
        if result.funder:
            self.funder_wallets[result.funder] += 1
        if len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)
        return result

    async def _call(self, method: str, params: list[object]) -> object:
        for attempt in range(4):
            async with self._pace:
                delay = self._next_at - asyncio.get_running_loop().time()
                if delay > 0:
                    await asyncio.sleep(delay)
                self._next_at = asyncio.get_running_loop().time() + self._interval
            self.calls[method] += 1
            try:
                return await self._rpc._call(method, params)
            except Exception as error:
                code = getattr(error, "code", "")
                if attempt == 3 or not (
                    getattr(error, "rate_limited", False) or code == "circuit_open"
                ):
                    raise
                await asyncio.sleep(2 * (attempt + 1))
        raise RuntimeError("unreachable")

    async def _resolve(self, wallet: str) -> WalletOrigin:
        signatures = await self._call(
            "getSignaturesForAddress", [wallet, {"limit": _SIGNATURE_PAGE}]
        )
        if not isinstance(signatures, list) or not signatures:
            return WalletOrigin(None, None, aged=False)
        if len(signatures) >= _SIGNATURE_PAGE:
            return WalletOrigin(None, None, aged=True)
        first = signatures[-1]
        transaction = await self._call(
            "getTransaction",
            [
                first["signature"],
                {
                    "encoding": "jsonParsed",
                    "commitment": "confirmed",
                    "maxSupportedTransactionVersion": 1,
                },
            ],
        )
        return WalletOrigin(
            first_sol_sender(transaction, wallet), first.get("blockTime"), aged=False
        )


def first_sol_sender(transaction: Any, wallet: str) -> str | None:
    """Source of the first System transfer/createAccount into `wallet` in a parsed tx."""
    if not isinstance(transaction, dict):
        return None
    meta = transaction.get("meta") or {}
    message = (transaction.get("transaction") or {}).get("message") or {}
    instructions = list(message.get("instructions") or [])
    for group in meta.get("innerInstructions") or []:
        instructions.extend(group.get("instructions") or [])
    for item in instructions:
        parsed = item.get("parsed") if isinstance(item, dict) else None
        if not isinstance(parsed, dict) or item.get("program") != "system":
            continue
        info = parsed.get("info") or {}
        kind = parsed.get("type")
        if kind in {"transfer", "transferWithSeed"} and info.get("destination") == wallet:
            return str(info.get("source")) if info.get("source") else None
        if kind in {"createAccount", "createAccountWithSeed"} and info.get("newAccount") == wallet:
            return str(info.get("source")) if info.get("source") else None
    return None


async def insider_facts(
    resolver: WalletFunderResolver,
    holders: list[tuple[str, Decimal]],
    *,
    now: float | None = None,
    max_holders: int = 20,
) -> InsiderFacts:
    holders = sorted(holders, key=lambda item: item[1], reverse=True)[:max_holders]
    origins = await asyncio.gather(*(resolver.origin(owner) for owner, _ in holders))
    hubs = {
        funder for funder, count in resolver.funder_wallets.items() if count >= HUB_FUNDER_WALLETS
    }
    return summarize(holders, list(origins), now=now if now is not None else time(), hubs=hubs)


def summarize(
    holders: list[tuple[str, Decimal]],
    origins: list[WalletOrigin | None],
    *,
    now: float,
    hubs: set[str] | frozenset[str] = frozenset(),
) -> InsiderFacts:
    over = {
        str(threshold): (
            sum(1 for _, share in holders if share >= threshold),
            sum((share for _, share in holders if share >= threshold), start=Decimal(0)),
        )
        for threshold in HOLDER_THRESHOLDS
    }
    by_funder: dict[str, list[Decimal]] = {}
    fresh_count, fresh_share, resolved = 0, Decimal(0), 0
    for (_owner, share), origin in zip(holders, origins, strict=True):
        if origin is None:
            continue
        resolved += 1
        if origin.funder and origin.funder not in hubs:
            by_funder.setdefault(origin.funder, []).append(share)
        if (
            not origin.aged
            and origin.first_seen is not None
            and now - origin.first_seen < FRESH_WALLET_SECONDS
        ):
            fresh_count += 1
            fresh_share += share
    clusters = [shares for shares in by_funder.values() if len(shares) >= 2]
    return InsiderFacts(
        holders=tuple(holders),
        holders_over=over,
        linked_supply_percent=sum((sum(c, Decimal(0)) for c in clusters), start=Decimal(0)),
        linked_cluster_count=len(clusters),
        largest_cluster_percent=max((sum(c, Decimal(0)) for c in clusters), default=Decimal(0)),
        fresh_holder_count=fresh_count,
        fresh_supply_percent=fresh_share,
        resolved_holders=resolved,
    )


class HolderRpc(Protocol):
    async def get_token_largest_accounts(self, mint: str, commitment: Any) -> Any: ...

    async def get_multiple_accounts(self, addresses: list[str], commitment: Any) -> Any: ...


async def current_holders(
    rpc: HolderRpc, mint: str, curve: str | None, *, supply_raw: int = 10**15
) -> list[tuple[str, Decimal]]:
    """Largest holders now, as % of the fixed 1B supply, bonding curve excluded."""
    largest = await rpc.get_token_largest_accounts(mint, "confirmed")
    addresses = [balance.address for balance in largest.balances]
    accounts = await rpc.get_multiple_accounts(addresses, "confirmed")
    shares: dict[str, Decimal] = {}
    for balance, account in zip(largest.balances, accounts, strict=True):
        if account is None:
            continue
        owner = decode_token_account(base64.b64decode(account.data_base64)).owner
        if owner == curve or balance.amount_raw <= 0:
            continue
        share = Decimal(balance.amount_raw) * 100 / Decimal(supply_raw)
        shares[owner] = shares.get(owner, Decimal(0)) + share
    return sorted(shares.items(), key=lambda item: item[1], reverse=True)


class InsiderShadow:
    """Background, log-only insider facts per assessed token (never blocks trading)."""

    def __init__(
        self, holder_rpc: HolderRpc, resolver: WalletFunderResolver, *, refresh_seconds: float = 120
    ) -> None:
        self._holder_rpc = holder_rpc
        self._resolver = resolver
        self._refresh = refresh_seconds
        self._last: OrderedDict[str, float] = OrderedDict()
        self._queue: asyncio.Queue[tuple[str, str | None]] = asyncio.Queue(maxsize=200)
        self._logger = get_logger("memebot.insider")

    def request(self, mint: str, curve: str | None) -> None:
        now = time()
        if now - self._last.get(mint, 0) < self._refresh:
            return
        self._last[mint] = now
        self._last.move_to_end(mint)
        if len(self._last) > 20_000:
            self._last.popitem(last=False)
        try:
            self._queue.put_nowait((mint, curve))
        except asyncio.QueueFull:
            self._logger.debug("insider_queue_full")

    async def run(self) -> None:
        while True:
            mint, curve = await self._queue.get()
            try:
                holders = await current_holders(self._holder_rpc, mint, curve)
                facts = await insider_facts(self._resolver, holders)
                self._logger.info(
                    "insider_facts",
                    mint=mint,
                    holders_over={k: [v[0], str(v[1])] for k, v in facts.holders_over.items()},
                    top10_percent=str(sum((s for _, s in facts.holders[:10]), Decimal(0))),
                    linked_supply_percent=str(facts.linked_supply_percent),
                    linked_clusters=facts.linked_cluster_count,
                    largest_cluster_percent=str(facts.largest_cluster_percent),
                    fresh_holders=facts.fresh_holder_count,
                    fresh_supply_percent=str(facts.fresh_supply_percent),
                    resolved_holders=facts.resolved_holders,
                    rpc_calls=dict(self._resolver.calls),
                )
            except Exception as error:
                self._logger.warning("insider_facts_failed", error_type=type(error).__name__)
            finally:
                self._queue.task_done()
