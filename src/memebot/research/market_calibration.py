"""Bounded, passive calibration. No database, orders, worker or experiment imports.

Run separately: python -m memebot.research.market_calibration --seconds 180
The default PumpPortal subscriptions are FREE discovery only. Metered streams
are deliberately excluded: their remote billing cannot be capped by recv().
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, replace
from datetime import UTC, datetime
from decimal import Decimal
from itertools import pairwise
from pathlib import Path
from time import monotonic
from typing import Any
from urllib.parse import quote, urlsplit

import websockets

from memebot.core.config import Settings
from memebot.eligibility import entry_rejection
from memebot.models.common import ProviderProvenance
from memebot.models.market import LaunchVenue, MarketLifecycle
from memebot.models.paper import PositionEffect
from memebot.paper.execution import ExecutionPolicy, PaperFillSimulator
from memebot.paper.market_refresh import SolanaRpcMarketSnapshotRefresher
from memebot.paper.models import ExecutionMarketSnapshot
from memebot.providers.price.base import QuotePrice
from memebot.providers.pumpportal import _portal_error_code
from memebot.providers.solana.canonical import FEE_PROGRAM
from memebot.providers.solana.pump import extract_anchor_events
from memebot.providers.solana.pump_idl import (
    NATIVE_SOL_MINT,
    PUMP_PROGRAM_ID,
    WRAPPED_SOL_MINT,
    PumpCreate,
    PumpSwapPoolCreated,
    PumpSwapTrade,
    PumpTrade,
)
from memebot.providers.solana.rpc import JsonRpcSolanaClient, SolanaRpcError

SIZES = (Decimal("0.01"), Decimal("0.025"), Decimal("0.05"), Decimal("0.1"))
ROOT = Path(__file__).resolve().parents[3]
CHECKS = (
    "prospective_distributions",
    "timing_understood",
    "rpc_freshness_acceptable",
    "stream_reliability_acceptable",
    "execution_quotes_consistent",
    "fees_bounded",
    "cost_understood",
    "safety_bands_supported",
)


def utc() -> datetime:
    return datetime.now(UTC)


def identity(endpoint: str) -> str:
    """Identity without credential-bearing paths or queries."""
    return f"{urlsplit(endpoint).hostname}#{hashlib.sha256(endpoint.encode()).hexdigest()[:10]}"


def percent(value: Decimal | float | int, reference: Decimal | float | int) -> float | None:
    if reference <= 0:
        return None
    return float((Decimal(str(value)) / Decimal(str(reference)) - 1) * 100)


def distribution(values: list[float]) -> dict[str, int | float | None]:
    values = sorted(x for x in values if math.isfinite(x))

    def quantile(q: float) -> float | None:
        if not values:
            return None
        pos = (len(values) - 1) * q
        lower = math.floor(pos)
        return values[lower] + (values[math.ceil(pos)] - values[lower]) * (pos - lower)

    return {
        "N": len(values),
        "median": quantile(0.5),
        "p75": quantile(0.75),
        "p90": quantile(0.9),
        "p95": quantile(0.95),
        "p99": quantile(0.99),
        "max": max(values) if values else None,
    }


class RequestBudget:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.used = 0

    def take(self) -> None:
        if self.used >= self.limit:
            raise SolanaRpcError("calibration_request_cap")
        self.used += 1


class CalibrationRpc(JsonRpcSolanaClient):
    """Whitelist prevents accidentally converting this collector into execution."""

    METHODS = frozenset({"getSlot", "getAccountInfo", "getMultipleAccounts"})

    def __init__(self, endpoint: str, budget: RequestBudget) -> None:
        super().__init__(endpoint, timeout_seconds=8)
        self.identity = identity(endpoint)
        self.budget = budget
        self.calls: list[dict[str, Any]] = []

    async def _call(self, method: str, params: list[object] | None = None) -> object:
        if method not in self.METHODS:
            raise ValueError("calibration RPC method forbidden")
        if not self.available:
            raise SolanaRpcError("circuit_open")
        self.budget.take()
        started = monotonic()
        row: dict[str, Any] = {
            "method": method,
            "requested_at": utc().isoformat(),
            "monotonic_started": started,
            "endpoint": self.identity,
        }
        self.calls.append(row)
        try:
            result = await super()._call(method, params)
            if method == "getSlot":
                row["slot"] = result
            elif isinstance(result, dict):
                row["slot"] = result.get("context", {}).get("slot")
            row["status"] = "ok"
            return result
        except SolanaRpcError as error:
            row["status"] = error.code
            raise
        finally:
            row["received_at"] = utc().isoformat()
            row["latency_ms"] = (monotonic() - started) * 1000


def local_quotes(market: ExecutionMarketSnapshot) -> list[dict[str, Any]]:
    """Pure calculations; 'fill' objects never leave this process as orders.

    Buy research size is gross SOL; sell size is token quantity with the same
    marginal SOL notional, NOT a buy/sell round trip. Zero slippage is a model
    scenario, not an estimate inferred from market data.
    """
    simulator = PaperFillSimulator(
        ExecutionPolicy(
            venue_fee_bps=Decimal(125),
            latency_slippage_bps=Decimal(0),
            network_fee_sol=Decimal(0),
            priority_fee_sol=Decimal(0),
            compute_latency_ms=0,
            submission_latency_ms=0,
            max_market_staleness_seconds=5,
            max_quote_price_staleness_seconds=5,
            execution_provider_fee_bps=Decimal(0),
        )
    )
    now = market.observed_at
    unit = QuotePrice(
        quote_asset=market.quote_asset,
        portfolio_currency="SOL",
        price=Decimal(1),
        provenance=ProviderProvenance(provider="unit_sol_no_fx_request", observed_at=now),
    )
    rows = []
    for size in SIZES:
        buy = simulator.simulate_buy(
            market, unit, requested_portfolio_amount=size, signal_at=now, decision_at=now
        )
        sell = simulator.simulate_sell(
            market,
            unit,
            token_amount_raw=size * Decimal(10**9) / market.observed_price_raw,
            position_effect=PositionEffect.CLOSE,
            exit_reason="calibration_only",
            signal_at=now,
            decision_at=now,
        )
        row: dict[str, Any] = {
            "research_size_sol": str(size),
            "quality": "ESTIMATED",
            "slippage_scenario_bps": 0,
            "estimated_slippage_bps": None,
            "network_and_service_costs_included": False,
        }
        for side, outcome in (("buy", buy), ("sell", sell)):
            fill = outcome.fill
            row[side] = (
                fill.model_dump(mode="json") if fill else {"rejection": outcome.rejection_reason}
            )
            row[f"rpc_mark_to_local_{side}_quote_percent"] = (
                percent(fill.executable_quote, market.observed_price_raw)
                if fill and fill.executable_quote
                else None
            )
            row[f"{side}_impact_percent"] = float(fill.price_impact_bps / 100) if fill else None
            # Sell executable_quote is gross; fees must be subtracted for net proceeds.
            row[f"{side}_net_unit_price_raw"] = (
                str(
                    (fill.gross_quote_amount_raw - fill.venue_fee_quote_raw) / fill.token_amount_raw
                )
                if fill and side == "sell"
                else None
            )
        rows.append(row)
    return rows


def grouped_distributions(samples: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = (
        "stream_rpc_price_disagreement_percent",
        "buy_impact_percent",
        "sell_impact_percent",
        "rpc_mark_to_local_buy_quote_percent",
        "rpc_mark_to_local_sell_quote_percent",
        "stream_price_to_local_buy_quote_percent",
        "stream_price_to_local_sell_quote_percent",
    )
    dimensions = (
        "venue",
        "liquidity_bucket",
        "token_age_bucket",
        "volatility_bucket",
        "research_size_sol",
        "market_activity_state",
    )
    groups: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for sample in samples:
        for quote_index, quote_row in enumerate(sample["quotes"]):
            row = {**sample, **quote_row}
            for dimension in dimensions:
                group = f"{dimension}={row[dimension]}"
                for metric in metrics:
                    if (
                        metric == "stream_rpc_price_disagreement_percent"
                        and dimension != "research_size_sol"
                        and quote_index != 0
                    ):
                        continue  # quote sizes must not inflate independent pair N
                    value = row.get(metric)
                    if value is not None:
                        groups[group][metric].append(abs(float(value)))
    return {
        "absolute_percent_metrics": True,
        "groups": {
            key: {m: distribution(vals[m]) for m in metrics} for key, vals in groups.items()
        },
        "overall_stream_rpc": distribution(
            [abs(s["stream_rpc_price_disagreement_percent"]) for s in samples]
        ),
        "bands": {"NORMAL": None, "ELEVATED": None, "SEVERE": None},
        "band_status": "INSUFFICIENT_EVIDENCE_REQUIRES_REVIEW",
    }


class Collector:
    def __init__(self, settings: Settings, *, seconds: int, max_requests: int) -> None:
        self.settings = settings
        self.native_message_cap = 25000
        self.native_programs: tuple[str, ...] = (PUMP_PROGRAM_ID, FEE_PROGRAM)
        self.seconds = seconds
        self.budget = RequestBudget(max_requests)
        endpoints = [str(settings.solana_rpc_http_url), str(settings.solana_exit_rpc_http_url)]
        self.rpcs = [CalibrationRpc(url, self.budget) for url in dict.fromkeys(endpoints)]
        self.samples: list[dict[str, Any]] = []
        self.failures: list[dict[str, Any]] = []
        self.markets: dict[str, dict[str, Any]] = {}
        self.activity: Counter[str] = Counter()
        self.previous: dict[str, Decimal] = {}
        self.candidates: set[str] = set()
        self.deep: set[str] = set()
        self.seen: set[str] = set()
        self.launches: set[str] = set()
        self.pool_launches: set[str] = set()
        self.queue: asyncio.Queue[tuple[ExecutionMarketSnapshot, dict[str, Any]]] = asyncio.Queue(
            maxsize=64
        )
        self.streams: dict[str, dict[str, Any]] = {}
        self.stop = asyncio.Event()
        self.started = utc()
        self.fee_configuration: dict[str, Any] = {"status": "UNKNOWN"}
        self.pending_markets: set[str] = set()
        self.market_pair_attempts: Counter[str] = Counter()
        self.last_pair_monotonic: dict[str, float] = {}

    def stream_state(self, name: str) -> dict[str, Any]:
        state = {
            "connections_attempted": 0,
            "reconnects": 0,
            "messages": 0,
            "events": 0,
            "subscription_requests": 0,
            "acknowledgments": 0,
            "missing_slots": 0,
            "estimated_timestamps": 0,
            "duplicates": 0,
            "out_of_order": 0,
            "errors": [],
            "receipt_gaps_ms": [],
            "max_observed_slot": None,
            "last_event_monotonic": None,
            "first_event_at": None,
            "last_event_at": None,
        }
        self.streams[name] = state
        return state

    async def native_stream(self) -> None:
        name = "native_logs"
        state = self.stream_state(name)
        state["connections_attempted"] += 1
        state["endpoint"] = identity(str(self.settings.solana_rpc_ws_url))
        try:
            async with websockets.connect(
                str(self.settings.solana_rpc_ws_url), open_timeout=8, max_queue=64
            ) as ws:
                for idx, program in enumerate(self.native_programs, 1):
                    await ws.send(
                        json.dumps(
                            {
                                "jsonrpc": "2.0",
                                "id": idx,
                                "method": "logsSubscribe",
                                "params": [{"mentions": [program]}, {"commitment": "confirmed"}],
                            }
                        )
                    )
                    state["subscription_requests"] += 1
                async for raw in ws:
                    state["messages"] += 1
                    if state["messages"] > self.native_message_cap:
                        state["errors"].append("calibration_native_message_cap")
                        self.stop.set()
                        return
                    message = json.loads(raw)
                    if "id" in message:
                        if "result" in message:
                            state["acknowledgments"] += 1
                        else:
                            state["errors"].append("subscription_rejected")
                            return
                        continue
                    result = message.get("params", {}).get("result", {})
                    value = result.get("value", {})
                    if value.get("err") is not None:
                        continue
                    slot = result.get("context", {}).get("slot")
                    state["current_log_messages"] = value.get("logs", [])
                    self.native_transaction(value.get("signature"), slot, state)
                    for ordinal, (_, event) in enumerate(
                        extract_anchor_events(value.get("logs", []))
                    ):
                        key = f"{value.get('signature')}:{ordinal}"
                        if key in self.seen:
                            state["duplicates"] += 1
                            continue
                        self.seen.add(key)
                        state["current_event_id"] = key
                        self.native_event(event, slot, state)
                    if self.stop.is_set():
                        return
        except Exception as error:
            # Never log an exception URL or raw provider error containing secrets.
            response = getattr(error, "response", None)
            state["errors"].append(
                {
                    "type": type(error).__name__,
                    "http_status": getattr(response, "status_code", None),
                }
            )

    def native_transaction(
        self, signature: str | None, slot: int | None, state: dict[str, Any]
    ) -> None:
        """Optional passive consumer of mutation-only transactions."""

    def native_event(self, event: Any, slot: int | None, state: dict[str, Any]) -> None:
        now = utc()
        if isinstance(event, PumpCreate):
            self.launches.add(event.mint)
            if event.quote_mint in {WRAPPED_SOL_MINT, NATIVE_SOL_MINT} and not event.is_mayhem_mode:
                self.markets[event.mint] = {
                    "mint": event.mint,
                    "market": event.bonding_curve,
                    "venue": LaunchVenue.PUMP_FUN,
                    "created": event.timestamp,
                    "quote": event.quote_mint,
                    "created_time_kind": "token_creation",
                }
        elif isinstance(event, PumpSwapPoolCreated):
            return  # Excluded from standard calibration; no queue or enrichment.
        elif isinstance(event, (PumpTrade, PumpSwapTrade)):
            key = event.mint if isinstance(event, PumpTrade) else event.pool
            context = self.markets.get(key)
            if context is None:
                return  # no account lookup for unknown markets
            if isinstance(event, PumpTrade):
                vq, vt = event.virtual_quote_reserves, event.virtual_token_reserves
                rq, rt = event.real_quote_reserves, event.real_token_reserves
                quote_amount, token_amount = event.quote_amount, event.token_amount
                if event.quote_mint not in {WRAPPED_SOL_MINT, NATIVE_SOL_MINT}:
                    return
            else:
                rq, rt = event.pool_quote_token_reserves, event.pool_base_token_reserves
                vq, vt = rq + event.virtual_quote_reserves, rt
                quote_amount, token_amount = event.quote_amount, event.base_amount
            self.observe(
                context,
                slot,
                event.timestamp,
                now,
                state,
                vq,
                vt,
                rq,
                rt,
                quote_amount,
                token_amount,
            )

    def observe(
        self,
        context: dict[str, Any],
        slot: int | None,
        source_time: int | None,
        now: datetime,
        state: dict[str, Any],
        vq: int,
        vt: int,
        rq: int | None,
        rt: int | None,
        qa: int,
        ta: int,
    ) -> None:
        if context["venue"] != LaunchVenue.PUMP_FUN:
            return
        if vq <= 0 or vt <= 0:
            return
        stamp = monotonic()
        if state["last_event_monotonic"] is not None:
            state["receipt_gaps_ms"].append((stamp - state["last_event_monotonic"]) * 1000)
        state["last_event_monotonic"] = stamp
        state["first_event_at"] = state["first_event_at"] or now.isoformat()
        state["last_event_at"] = now.isoformat()
        state["events"] += 1
        if slot is None:
            state["missing_slots"] += 1
        elif state["max_observed_slot"] is not None and slot < state["max_observed_slot"]:
            state["out_of_order"] += 1
        if slot is not None:
            state["max_observed_slot"] = max(slot, state["max_observed_slot"] or slot)
        if source_time is None:
            state["estimated_timestamps"] += 1
        market_key = context["market"]
        self.activity[market_key] += 1
        mark = Decimal(vq) / Decimal(vt)
        volatility = abs(percent(mark, self.previous.get(market_key, mark)) or 0)
        self.previous[market_key] = mark
        # Research-only cheap activity filter. No strategy threshold is referenced.
        if self.activity[market_key] < 2 or qa <= 0 or ta <= 0:
            return
        self.candidates.add(context["mint"])
        # Fair sampling and one pending request per market, entirely local.
        # These are capture quotas, not entry/exit strategy thresholds.
        if (
            market_key in self.pending_markets
            or self.market_pair_attempts[market_key] >= 10
            or stamp - self.last_pair_monotonic.get(market_key, 0) < 1
        ):
            state["local_sampling_skips"] = state.get("local_sampling_skips", 0) + 1
            return
        age = (
            max(0, (source_time or now.timestamp()) - context["created"])
            if context.get("created") is not None
            else None
        )
        details: dict[str, Any] = {
            "provider": "native_logs" if slot is not None else "pumpportal",
            "stream_event_id": state.get("current_event_id"),
            "stream_receipt_timestamp": now.isoformat(),
            "stream_monotonic_timestamp": stamp,
            "stream_source_timestamp": source_time,
            "stream_source_slot": slot,
            # Anchor timestamp is decoded chain-origin data, not verified blockTime.
            "stream_timing": "SLOT_ONLY" if slot is not None else "RECEIPT_ESTIMATE",
            "stream_chain_timestamp_verified": False,
            "stream_virtual_quote_reserves": vq,
            "stream_virtual_token_reserves": vt,
            "stream_real_quote_reserves": rq,
            "stream_real_token_reserves": rt,
            "stream_trade_quote_amount": qa,
            "stream_trade_token_amount": ta,
            "stream_marginal_mark": str(mark),
            "stream_reserve_state_semantics": "PROGRAM_EVENT_NOT_END_OF_SLOT_STATE",
            "liquidity_bucket": "lt10SOL"
            if vq < 10**10
            else ("10to100SOL" if vq < 10**11 else "gte100SOL"),
            "token_age_bucket": "UNKNOWN"
            if age is None
            else ("lt60s" if age < 60 else ("60to300s" if age < 300 else "gte300s")),
            "volatility_bucket": "lt1pct"
            if volatility < 1
            else ("1to5pct" if volatility < 5 else "gte5pct"),
            "market_activity_state": "two_or_more_observed_trades",
            "token_age_seconds": age,
        }
        snapshot = ExecutionMarketSnapshot(
            mint=context["mint"],
            market=market_key,
            venue=context["venue"],
            lifecycle=MarketLifecycle.BONDING_CURVE
            if context["venue"] == LaunchVenue.PUMP_FUN
            else MarketLifecycle.POST_GRADUATION,
            observed_at=now,
            source_slot=slot,
            observed_price_raw=mark,
            quote_asset=context["quote"],
            real_token_reserves_raw=rt,
            real_quote_reserves_raw=rq,
            virtual_token_reserves_raw=vt if context["venue"] == LaunchVenue.PUMP_FUN else None,
            virtual_quote_reserves_raw=vq
            if context["venue"] == LaunchVenue.PUMP_FUN
            else vq - (rq or 0),
            price_source=details["provider"],
            feed_timestamp=now,
            feed_reference_price=mark,
        )
        try:
            self.queue.put_nowait((snapshot, details))
            self.pending_markets.add(market_key)
            self.market_pair_attempts[market_key] += 1
            self.last_pair_monotonic[market_key] = stamp
        except asyncio.QueueFull:
            state["queue_drops"] = state.get("queue_drops", 0) + 1

    async def portal_discovery(self) -> None:
        state = self.stream_state("pumpportal")
        state["scope"] = "free_launch_and_migration_only_no_metered_trades"
        state["connections_attempted"] += 1
        endpoint = str(self.settings.pumpportal_ws_url)
        if self.settings.pumpportal_api_key:
            endpoint += (
                ("&" if "?" in endpoint else "?")
                + "api-key="
                + quote(self.settings.pumpportal_api_key.get_secret_value())
            )
        try:
            async with websockets.connect(endpoint, open_timeout=8, max_queue=64) as ws:
                for method in ("subscribeNewToken", "subscribeMigration"):
                    await ws.send(json.dumps({"method": method}))
                    state["subscription_requests"] += 1
                async for raw in ws:
                    state["messages"] += 1
                    message = json.loads(raw)
                    if not isinstance(message, dict):
                        continue
                    error = _portal_error_code(message)
                    if error:
                        state["errors"].append(error)
                        return
                    if "message" in message and "mint" not in message:
                        state["acknowledgments"] += 1
                    if message.get("txType") == "create":
                        mint = message.get("mint")
                        if isinstance(mint, str):
                            self.launches.add(mint)
                            state["events"] += 1
                            state["missing_slots"] += 1
                            state["estimated_timestamps"] += 1
                            now = utc()
                            stamp = monotonic()
                            if state["last_event_monotonic"] is not None:
                                state["receipt_gaps_ms"].append(
                                    (stamp - state["last_event_monotonic"]) * 1000
                                )
                            state["last_event_monotonic"] = stamp
                            state["first_event_at"] = state["first_event_at"] or now.isoformat()
                            state["last_event_at"] = now.isoformat()
                    if self.stop.is_set():
                        return
        except Exception as error:
            response = getattr(error, "response", None)
            state["errors"].append(
                {
                    "type": type(error).__name__,
                    "http_status": getattr(response, "status_code", None),
                }
            )

    async def slot_probes(self) -> None:
        for _ in range(4):

            async def probe(rpc: CalibrationRpc) -> None:
                try:
                    await rpc._call("getSlot", [{"commitment": "confirmed"}])
                except SolanaRpcError:
                    pass

            await asyncio.gather(*(probe(rpc) for rpc in self.rpcs))
            try:
                await asyncio.wait_for(self.stop.wait(), timeout=10)
                return
            except TimeoutError:
                pass

    async def fee_probe(self) -> None:
        # Config enrichment requires an eligible synchronized standard candidate.
        self.fee_configuration = {"status": "UNKNOWN", "reason": "STANDARD_PREREQUISITE_UNMET"}

    async def pair_worker(self) -> None:
        refresher = SolanaRpcMarketSnapshotRefresher(self.rpcs[0], commitment="confirmed")
        while not self.stop.is_set():
            market, details = await self.queue.get()
            self.pending_markets.discard(market.market)
            reason = entry_rejection(
                market.normalized_state.evidence() if market.normalized_state else {},
                venue=market.venue.value,
                lifecycle=market.lifecycle.value,
                mayhem=market.is_mayhem_mode,
                complete=market.curve_complete,
            )
            if reason:
                self.failures.append({"mint": market.mint, "reason": reason})
                continue
            if self.budget.used >= self.budget.limit:
                self.stop.set()
                return
            # Backlogged stream data is recorded as a failure, never as synchronized.
            if (utc() - market.observed_at).total_seconds() > 2:
                self.failures.append({"mint": market.mint, "reason": "queue_receipt_age_above_2s"})
                continue
            self.deep.add(market.mint)
            rpc = self.rpcs[0]
            first_call = len(rpc.calls)
            result = await refresher.refresh_with_diagnostics(market)
            if result.status != "refreshed":
                self.failures.append({"mint": market.mint, "reason": result.detail})
                continue
            fresh = replace(
                result.market,
                price_source="rpc_primary_reserves",
                source_timestamp=None,
                received_timestamp=result.market.observed_at,
                data_quality="rpc_slot_known_source_time_unknown",
                rpc_state="healthy",
                decision_price=market.observed_price_raw,
            )
            calls = rpc.calls[first_call:]
            slots = [c.get("slot") for c in calls if c.get("slot") is not None]
            # PumpSwap pool metadata and vault reads may occupy distinct slots.
            coherent = len(set(slots)) == 1
            quotes = local_quotes(fresh)
            for q in quotes:
                for side in ("buy", "sell"):
                    price = q[side].get("executable_quote")
                    q[f"stream_price_to_local_{side}_quote_percent"] = (
                        percent(Decimal(price), market.observed_price_raw) if price else None
                    )
            row = {
                **details,
                "mint": market.mint,
                "market": market.market,
                "venue": market.venue.value,
                "rpc_endpoint": rpc.identity,
                "rpc_response_slot": fresh.source_slot,
                "rpc_receipt_timestamp": fresh.observed_at.isoformat(),
                "rpc_monotonic_timestamp": monotonic(),
                "rpc_timing": "SLOT_ONLY",
                "rpc_source_timestamp": None,
                "rpc_component_slots": slots,
                "rpc_component_slots_coherent": coherent,
                "rpc_reserves": {k: v for k, v in asdict(fresh).items() if "reserves_raw" in k},
                "rpc_marginal_mark": str(fresh.observed_price_raw),
                "receipt_time_delta_ms": (fresh.observed_at - market.observed_at).total_seconds()
                * 1000,
                "slot_delta": fresh.source_slot - market.source_slot
                if fresh.source_slot is not None and market.source_slot is not None
                else None,
                "stream_rpc_price_disagreement_percent": percent(
                    fresh.observed_price_raw, market.observed_price_raw
                ),
                "stream_rpc_reserve_delta": {
                    k: getattr(fresh, k) - getattr(market, k)
                    if getattr(fresh, k) is not None and getattr(market, k) is not None
                    else None
                    for k in (
                        "real_token_reserves_raw",
                        "real_quote_reserves_raw",
                        "virtual_token_reserves_raw",
                        "virtual_quote_reserves_raw",
                    )
                },
                "quotes": quotes,
                "local_quote_state": "RPC_CAPTURED_RESERVES",
                "data_quality": "ESTIMATED" if coherent else "MIXED_RPC_SLOTS",
            }
            self.samples.append(row)
            if len(self.samples) >= 1000 and len({s["mint"] for s in self.samples}) >= 100:
                self.stop.set()

    async def run(self) -> None:
        tasks = [
            asyncio.create_task(fn())
            for fn in (
                self.native_stream,
                self.portal_discovery,
                self.slot_probes,
                self.fee_probe,
                self.pair_worker,
            )
        ]
        try:
            await asyncio.wait_for(self.stop.wait(), timeout=self.seconds)
        except TimeoutError:
            pass
        finally:
            self.stop.set()
            for task in tasks:
                task.cancel()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    self.failures.append(
                        {"reason": "collector_task_error", "type": type(result).__name__}
                    )
            for rpc in self.rpcs:
                await rpc.close()
            self.write_outputs()

    def write_outputs(self) -> None:
        ended = utc()
        elapsed = (ended - self.started).total_seconds()
        run = {
            "started_at": self.started.isoformat(),
            "ended_at": ended.isoformat(),
            "elapsed_seconds": elapsed,
            "mode": "PASSIVE_NO_ORDERS_NO_DATABASE",
            "max_rpc_requests": self.budget.limit,
            "metered_trade_subscriptions": 0,
            "native_message_cap": 25000,
            "max_pairs_per_market": 10,
            "min_pair_interval_seconds": 1,
            "source_file_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        }
        for state in self.streams.values():
            state["event_rate_per_second"] = state["events"] / elapsed
            state["receipt_gap_distribution_ms"] = distribution(state["receipt_gaps_ms"])
            state["trailing_silence_ms"] = (
                (monotonic() - state["last_event_monotonic"]) * 1000
                if state["last_event_monotonic"] is not None
                else elapsed * 1000
            )
        endpoints = {}
        for rpc in self.rpcs:
            slots = [c["slot"] for c in rpc.calls if c["method"] == "getSlot" and "slot" in c]
            endpoints[rpc.identity] = {
                "requests": len(rpc.calls),
                "calls": rpc.calls,
                "metrics": rpc.metrics(),
                "slot_sequence": slots,
                "duplicate_slots": sum(a == b for a, b in pairwise(slots)),
                "regressions": sum(b < a for a, b in pairwise(slots)),
                "chain_tip_lag_slots": None,
                "latency_distribution_ms": distribution([c["latency_ms"] for c in rpc.calls]),
            }
        paired_tokens = len({s["mint"] for s in self.samples})
        funnel: dict[str, Any] = {
            "launches_observed": len(self.launches),
            "observed_launch_mints": sorted(self.launches),
            "candidate_mints": sorted(self.candidates),
            "pool_creations_observed": len(self.pool_launches),
            "cheap_filter_survivors": len(self.candidates),
            "paired_calibration_candidates": paired_tokens,
            "deeply_inspected_candidates": len(self.deep),
            "paired_snapshots": len(self.samples),
        }
        funnel["conversion_percent"] = {
            "launch_to_filter": 100 * len(self.candidates & self.launches) / len(self.launches)
            if self.launches
            else None,
            "filter_to_pair": 100 * paired_tokens / len(self.candidates)
            if self.candidates
            else None,
        }
        costs = {
            "run": run,
            "rpc_endpoints": endpoints,
            "streams": self.streams,
            "funnel": funnel,
            "rpc_requests": self.budget.used,
            "requests_per_sampled_token": self.budget.used / paired_tokens
            if paired_tokens
            else None,
            "requests_per_paired_snapshot": self.budget.used / len(self.samples)
            if self.samples
            else None,
            "requests_per_launch_including_probes": self.budget.used / len(self.launches)
            if self.launches
            else None,
            "credits_consumed": None,
            "compute_units_consumed": None,
            "currency_cost": None,
            "metered_pumpportal_events": 0,
            "estimated_cost_per_1000_candidates": None,
            "estimated_cost_per_100_serious_candidates": None,
            "estimated_monthly_cost": None,
            "fee_configuration": self.fee_configuration,
            "projection_formula": (
                "R_month = launches_month * filter_conversion * deep_conversion "
                "* pairs_per_deep * requests_per_pair + health_and_config_reads; "
                "provider charge requires measured method CU schedule and billing plan. "
                "PumpPortal optional trade charge = events_sent / 10000 * 0.01 SOL"
            ),
            "cost_limitations": [
                "No billing/CU response data",
                "No purchased metered streams",
                "Insufficient conversion/launch-volume history for extrapolation",
            ],
        }
        checks = dict.fromkeys(CHECKS, False)
        checks["timing_understood"] = True
        gate = {
            "status": "BLOCKED",
            "runner-edge-prospective-v1": "BLOCKED",
            "checks": checks,
            "run": run,
            "paired_snapshots": len(self.samples),
            "paired_tokens": paired_tokens,
            "target_snapshots": 1000,
            "target_tokens": 100,
            "blockers": [k for k, passed in checks.items() if not passed],
            "automatically_activates_experiment": False,
        }
        output = ROOT / "analysis"
        output.mkdir(exist_ok=True)
        for name, payload in (
            (
                "market_data_samples.json",
                {"run": run, "samples": self.samples, "failed_pair_attempts": self.failures},
            ),
            ("disagreement_distribution.json", grouped_distributions(self.samples)),
            ("provider_costs.json", costs),
            ("calibration_gate.json", gate),
        ):
            (output / name).write_text(
                json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8"
            )
        columns = [
            "mint",
            "market",
            "venue",
            "provider",
            "stream_source_slot",
            "stream_source_timestamp",
            "stream_receipt_timestamp",
            "stream_monotonic_timestamp",
            "rpc_response_slot",
            "rpc_receipt_timestamp",
            "receipt_time_delta_ms",
            "slot_delta",
            "stream_rpc_price_disagreement_percent",
            "research_size_sol",
            "data_quality",
        ]
        with (output / "market_data_samples.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            for sample in self.samples:
                for q in sample["quotes"]:
                    writer.writerow({k: ({**sample, **q}).get(k) for k in columns})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, default=180)
    parser.add_argument("--max-rpc-requests", type=int, default=200)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 3600 or not 8 <= args.max_rpc_requests <= 2000:
        parser.error("bounded limits: seconds 1..3600, RPC requests 8..2000")
    asyncio.run(
        Collector(Settings(), seconds=args.seconds, max_requests=args.max_rpc_requests).run()
    )


if __name__ == "__main__":
    main()
