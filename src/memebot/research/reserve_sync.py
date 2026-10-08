"""Research-only state semantics and bounded native transaction correlation."""

from __future__ import annotations

import argparse
import asyncio
import base64
import gzip
import hashlib
import json
import random
import re
from dataclasses import asdict
from itertools import pairwise
from pathlib import Path
from time import monotonic
from typing import Any, cast

from memebot.core.config import Settings
from memebot.providers.solana.pump import extract_anchor_events
from memebot.providers.solana.pump_idl import (
    PUMP_AMM_PROGRAM_ID,
    PumpSwapTrade,
    PumpTrade,
    decode_anchor_event,
)
from memebot.providers.solana.rpc import SolanaRpcError
from memebot.research.market_calibration import (
    ROOT,
    CalibrationRpc,
    Collector,
    RequestBudget,
    utc,
)


class ForensicRpc(CalibrationRpc):
    METHODS = CalibrationRpc.METHODS | {"getBlock", "getTransaction"}

    def __init__(self, endpoint: str, budget: RequestBudget) -> None:
        super().__init__(endpoint, budget)

        async def inspect_error(response: Any) -> None:
            await response.aread()
            try:
                error = response.json().get("error", {})
                if error and self.calls:
                    message = re.sub(
                        r"https?://\S+", "[REDACTED_URL]", str(error.get("message", ""))
                    )
                    self.calls[-1]["rpc_diagnostic"] = message[:300]
            except (ValueError, AttributeError):
                pass

        self._client.event_hooks["response"].append(inspect_error)


def event_state(event: PumpTrade | PumpSwapTrade) -> dict[str, int]:
    if isinstance(event, PumpTrade):
        return {
            "virtual_quote": event.virtual_quote_reserves,
            "virtual_token": event.virtual_token_reserves,
            "real_quote": event.real_quote_reserves,
            "real_token": event.real_token_reserves,
        }
    return {
        "real_quote": event.pool_quote_token_reserves,
        "real_token": event.pool_base_token_reserves,
        "virtual_offset": event.virtual_quote_reserves,
    }


def swap_mutation(event: PumpSwapTrade, logs: list[str]) -> dict[str, int] | None:
    matches = []
    for line in logs:
        if not line.startswith("Program data: "):
            continue
        try:
            data = base64.b64decode(line[14:], validate=True)
            if decode_anchor_event(PUMP_AMM_PROGRAM_ID, data) != event:
                continue
            # IDL field12: actual pool quote transfer, including/excluding LP fee.
            transfer = int.from_bytes(data[104:112], "little")
            matches.append(
                {
                    "real_token": event.pool_base_token_reserves
                    + (-event.base_amount if event.is_buy else event.base_amount),
                    "real_quote": event.pool_quote_token_reserves
                    + (transfer if event.is_buy else -transfer),
                    "virtual_offset": event.virtual_quote_reserves,
                }
            )
        except ValueError:
            continue
    return matches[0] if len(matches) == 1 else None


class LocalReserveTracker:
    """Observed mutation sequence, never an assertion of complete chain state."""

    def __init__(self) -> None:
        self.latest: dict[str, dict[str, Any]] = {}
        self.events: list[dict[str, Any]] = []
        self.seen: set[str] = set()

    def update(
        self,
        event: PumpTrade | PumpSwapTrade,
        *,
        event_id: str,
        slot: int | None,
        received_at: str,
        transaction_index: int | None = None,
        mutation: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        key = event.mint if isinstance(event, PumpTrade) else event.pool
        state = event_state(event)
        previous = self.latest.get(key)
        row: dict[str, Any] = {
            "event_id": event_id,
            "signature": event_id.rsplit(":", 1)[0],
            "slot": slot,
            "transaction_index": transaction_index,
            "event_ordinal": event_id.rsplit(":", 1)[-1],
            "received_at": received_at,
            "local_monotonic_timestamp": monotonic(),
            "market_key": key,
            "venue": "pump_fun" if isinstance(event, PumpTrade) else "pump_swap",
            "event": asdict(event),
            "reported_reserves": state,
            "known_reserves_before": previous["reported_reserves"] if previous else None,
            "expected_reserves_after": None,
            "semantic": "UNKNOWN",
            "synchronization": "SLOT_ONLY" if slot is not None else "RECEIPT_ONLY",
            "coverage_complete": False,
        }
        if event_id in self.seen:
            row["status"] = "DUPLICATE"
            return row
        self.seen.add(event_id)
        if (
            previous
            and slot is not None
            and previous["slot"] is not None
            and slot < previous["slot"]
        ):
            row["status"] = "OUT_OF_ORDER_IGNORED"
            self.events.append(row)
            return row
        if previous and isinstance(event, PumpTrade):
            before = previous["reported_reserves"]
            direction = 1 if event.is_buy else -1
            expected = {
                "virtual_quote": before["virtual_quote"] + direction * event.quote_amount,
                "virtual_token": before["virtual_token"] - direction * event.token_amount,
                "real_quote": before["real_quote"] + direction * event.quote_amount,
                "real_token": before["real_token"] - direction * event.token_amount,
            }
            row["expected_reserves_after"] = expected
            row["post_trade_transition_matches"] = expected == state
            # Matching adjacent events supports a hypothesis, not complete capture proof.
            row["semantic"] = "POST_TRADE_SUPPORTED" if expected == state else "UNKNOWN"
        if isinstance(event, PumpSwapTrade) and mutation is not None:
            row["known_reserves_before"] = state
            row["expected_reserves_after"] = mutation
            row["semantic"] = "PRE_TRADE_RECONSTRUCTION_HYPOTHESIS"
            row["sequence_matches_previous_post"] = (
                previous["expected_reserves_after"] == state
                if previous and previous["expected_reserves_after"]
                else None
            )
        row["status"] = "OBSERVED_INCOMPLETE_COVERAGE"
        self.latest[key] = row
        self.events.append(row)
        return row


def transaction_events(block: dict[str, Any], slot: int) -> list[dict[str, Any]]:
    rows = []
    for tx_index, tx in enumerate(block.get("transactions", [])):
        meta = tx.get("meta") or {}
        if meta.get("err") is not None:
            continue
        transaction = tx.get("transaction", {})
        signatures = transaction.get("signatures", [])
        signature = signatures[0] if signatures else "UNKNOWN"
        message = transaction.get("message", {})
        keys = message.get("accountKeys", [])
        loaded = meta.get("loadedAddresses", {})
        keys = keys + loaded.get("writable", []) + loaded.get("readonly", [])
        keys = [k.get("pubkey") if isinstance(k, dict) else k for k in keys]
        events = extract_anchor_events(meta.get("logMessages") or [])
        for ordinal, (program, event) in enumerate(events):
            if not isinstance(event, (PumpTrade, PumpSwapTrade)):
                continue
            row = {
                "slot": slot,
                "transaction_index": tx_index,
                "signature": signature,
                "event_ordinal": ordinal,
                "program": program,
                "event": asdict(event),
                "venue": "pump_fun" if isinstance(event, PumpTrade) else "pump_swap",
                "reported_reserves": event_state(event),
                "account_keys": keys,
                "instructions": message.get("instructions", []),
                "inner_instructions": meta.get("innerInstructions", []),
                "pre_token_balances": meta.get("preTokenBalances", []),
                "post_token_balances": meta.get("postTokenBalances", []),
                "pre_balances": meta.get("preBalances", []),
                "post_balances": meta.get("postBalances", []),
                "semantic": "UNKNOWN",
                "instruction_index": None,
            }
            # Sole AMM trade event + pool-owned base/quote token balances can
            # establish PRE/POST without assuming event field names imply either.
            if isinstance(event, PumpSwapTrade):
                related = [
                    e for _, e in events if isinstance(e, PumpSwapTrade) and e.pool == event.pool
                ]
                pre = {
                    b["accountIndex"]: b
                    for b in row["pre_token_balances"]
                    if b.get("owner") == event.pool
                }
                post = {
                    b["accountIndex"]: b
                    for b in row["post_token_balances"]
                    if b.get("owner") == event.pool
                }
                matching = []
                for idx, balance in pre.items():
                    amount = int(balance["uiTokenAmount"]["amount"])
                    if amount == event.pool_base_token_reserves and idx in post:
                        matching.append(
                            {
                                "vault": keys[idx],
                                "mint": balance["mint"],
                                "pre": amount,
                                "post": int(post[idx]["uiTokenAmount"]["amount"]),
                            }
                        )
                if len(related) == 1 and len(matching) == 1:
                    base = matching[0]
                    signed = -event.base_amount if event.is_buy else event.base_amount
                    if base["post"] - base["pre"] == signed:
                        row["semantic"] = "PRE_TRADE"
                        row["base_vault_evidence"] = base
                        row["post_base_reserves"] = base["post"]
                quote_matches = [
                    {
                        "vault": keys[idx],
                        "mint": b["mint"],
                        "pre": int(b["uiTokenAmount"]["amount"]),
                        "post": int(post[idx]["uiTokenAmount"]["amount"]),
                    }
                    for idx, b in pre.items()
                    if idx in post
                    and int(b["uiTokenAmount"]["amount"]) == event.pool_quote_token_reserves
                ]
                row["quote_vault_candidates"] = quote_matches
                if row["semantic"] == "PRE_TRADE" and len(quote_matches) == 1:
                    row["post_quote_reserves"] = quote_matches[0]["post"]
                    row["post_state_from_metadata"] = {
                        "real_token": row["post_base_reserves"],
                        "real_quote": row["post_quote_reserves"],
                    }
            if isinstance(event, PumpSwapTrade):
                row["expected_post_from_event_fields"] = swap_mutation(
                    event, meta.get("logMessages") or []
                )
            rows.append(row)
    return rows


async def block_read(rpc: ForensicRpc, slot: int, cache: Path) -> dict[str, Any] | None:
    path = cache / f"block-{slot}.json.gz"
    if path.exists():
        return cast(dict[str, Any], json.loads(gzip.decompress(path.read_bytes())))
    try:
        result = await rpc._call(
            "getBlock",
            [
                slot,
                {
                    "commitment": "finalized",
                    "encoding": "json",
                    "transactionDetails": "full",
                    "rewards": False,
                    "maxSupportedTransactionVersion": 127,
                },
            ],
        )
        if isinstance(result, dict):
            path.write_bytes(gzip.compress(json.dumps(result).encode()))
            return result
    except SolanaRpcError:
        pass
    return None


def verify_semantics(rows: list[dict[str, Any]], market_by_mint: dict[str, str]) -> None:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        e = row["event"]
        key = e.get("pool", e.get("mint"))
        groups.setdefault((row["signature"], key), []).append(row)
    for (_, key), events in groups.items():
        events.sort(key=lambda r: r["event_ordinal"])
        first, last = events[0], events[-1]
        if first["venue"] == "pump_swap":
            pre = [b for b in first["pre_token_balances"] if b.get("owner") == key]
            post = {
                b["accountIndex"]: b for b in last["post_token_balances"] if b.get("owner") == key
            }
            vaults = {}
            for name in ("real_token", "real_quote"):
                matches = [
                    b
                    for b in pre
                    if int(b["uiTokenAmount"]["amount"]) == first["reported_reserves"][name]
                ]
                if len(matches) == 1 and matches[0]["accountIndex"] in post:
                    b = matches[0]
                    vaults[name] = {
                        "address": first["account_keys"][b["accountIndex"]],
                        "mint": b["mint"],
                        "owner": key,
                        "pre": int(b["uiTokenAmount"]["amount"]),
                        "post": int(post[b["accountIndex"]]["uiTokenAmount"]["amount"]),
                    }
            continuous = all(
                a.get("expected_post_from_event_fields") == b["reported_reserves"]
                for a, b in pairwise(events)
            )
            final = last.get("expected_post_from_event_fields")
            verified = (
                len(vaults) == 2
                and continuous
                and final
                and all(final[k] == vaults[k]["post"] for k in vaults)
            )
            instruction_indices = [
                i
                for i, ix in enumerate(first["instructions"])
                if first["account_keys"][ix["programIdIndex"]] == PUMP_AMM_PROGRAM_ID
                and key in [first["account_keys"][idx] for idx in ix["accounts"]]
            ]
            for i, row in enumerate(events):
                row["vault_identity"] = vaults
                row["transaction_state_sequence_verified"] = bool(verified)
                if verified:
                    row["semantic"] = "PRE_TRADE"
                if len(instruction_indices) == len(events):
                    row["instruction_index"] = instruction_indices[i]
        else:
            market = market_by_mint.get(key)
            if len(events) != 1 or market not in first["account_keys"]:
                continue
            index = first["account_keys"].index(market)
            if index >= len(first["pre_balances"]) or index >= len(first["post_balances"]):
                continue
            e = first["event"]
            delta = e["quote_amount"] * (1 if e["is_buy"] else -1)
            pre, post = first["pre_balances"][index], first["post_balances"][index]
            # Offset (rent etc.) is inferred, not assumed; equal before/after
            # with actual curve-account movement corroborates POST quote state.
            offset = post - e["real_quote_reserves"]
            first["curve_account_transition"] = {
                "market": market,
                "pre_lamports": pre,
                "post_lamports": post,
                "quote_delta": delta,
                "inferred_non_reserve_offset": offset,
            }
            if post - pre == delta and offset >= 0:
                first["semantic"] = "POST_TRADE_QUOTE_VERIFIED_TOKEN_SEQUENCE_REQUIRED"
                base = [
                    b
                    for b in first["pre_token_balances"]
                    if b.get("owner") == market and b.get("mint") == key
                ]
                post_base = {
                    b["accountIndex"]: b
                    for b in first["post_token_balances"]
                    if b.get("owner") == market and b.get("mint") == key
                }
                if len(base) == 1 and base[0]["accountIndex"] in post_base:
                    b = base[0]
                    pre_amount = int(b["uiTokenAmount"]["amount"])
                    post_amount = int(post_base[b["accountIndex"]]["uiTokenAmount"]["amount"])
                    first["token_vault_transition"] = {
                        "vault": first["account_keys"][b["accountIndex"]],
                        "pre": pre_amount,
                        "post": post_amount,
                        "inferred_reserved_inventory_offset": post_amount
                        - e["real_token_reserves"],
                    }
                    if post_amount - pre_amount == e["token_amount"] * (-1 if e["is_buy"] else 1):
                        first["semantic"] = "POST_TRADE"
                        first["offset_independently_bootstrapped"] = False


def select_anomalies(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def rank(s: dict[str, Any]) -> float:
        return abs(float(s["stream_rpc_price_disagreement_percent"]))

    fun = sorted([s for s in samples if s["venue"] == "pump_fun"], key=rank, reverse=True)[:10]
    swap = [s for s in samples if s["venue"] == "pump_swap" and rank(s) > 25]
    same = sorted([s for s in samples if s["slot_delta"] == 0], key=rank, reverse=True)[:10]
    return list(
        {f"{s['mint']}:{s['stream_monotonic_timestamp']}": s for s in fun + swap + same}.values()
    )


async def historical(settings: Settings, budget: RequestBudget) -> dict[str, Any]:
    previous_path = ROOT / "analysis/reserve_anomalies.json"
    previous_calls = (
        json.loads(previous_path.read_text()).get("provider_requests", [])
        if previous_path.exists()
        else []
    )
    samples = json.loads((ROOT / "analysis/market_data_samples.json").read_text())["samples"]
    selected = select_anomalies(samples)
    controls = random.Random(20261001).sample([s for s in samples if s not in selected], 3)
    cache = ROOT / "research_sessions/reserve-sync-20261001"
    cache.mkdir(parents=True, exist_ok=True)
    rpc = ForensicRpc(str(settings.solana_rpc_http_url), budget)
    # Maximum sixteen full block requests, prioritized by anomalies then controls.
    priority = sorted(
        selected, key=lambda s: abs(s["stream_rpc_price_disagreement_percent"]), reverse=True
    )
    slots = list(
        dict.fromkeys(
            s[field]
            for s in priority + controls
            for field in ("stream_source_slot", "rpc_response_slot")
        )
    )[:16]
    rows = []
    unavailable = []
    try:
        for slot in slots:
            block = await block_read(rpc, slot, cache)
            if block is None:
                unavailable.append(slot)
                # Stop on provider 429/auth; no blind retries.
                if not rpc.available:
                    break
            else:
                rows.extend(transaction_events(block, slot))
    finally:
        await rpc.close()
    results = []
    verify_semantics(rows, {s["mint"]: s["market"] for s in samples if s["venue"] == "pump_fun"})
    for sample in selected + controls:
        matching = []
        for row in rows:
            e = row["event"]
            if row["slot"] != sample["stream_source_slot"] or row["venue"] != sample["venue"]:
                continue
            if sample["venue"] == "pump_fun":
                matches = (
                    e["mint"] == sample["mint"]
                    and e["virtual_quote_reserves"] == sample["stream_virtual_quote_reserves"]
                    and e["virtual_token_reserves"] == sample["stream_virtual_token_reserves"]
                )
            else:
                matches = (
                    e["pool"] == sample["market"]
                    and e["pool_base_token_reserves"] == sample["stream_virtual_token_reserves"]
                    and e["pool_quote_token_reserves"] == sample["stream_real_quote_reserves"]
                )
            if matches:
                matching.append(row)
        target = matching[0] if len(matching) == 1 else None
        key = "mint" if sample["venue"] == "pump_fun" else "pool"
        address = sample["mint"] if key == "mint" else sample["market"]
        timeline = sorted(
            [
                r
                for r in rows
                if r["event"].get(key) == address
                and sample["stream_source_slot"] <= r["slot"] <= sample["rpc_response_slot"]
            ],
            key=lambda r: (r["slot"], r["transaction_index"], r["event_ordinal"]),
        )
        latest_exact = []
        for r in timeline:
            if sample["venue"] == "pump_swap":
                expected = r.get("expected_post_from_event_fields")
                actual = sample["rpc_reserves"]
                if (
                    expected
                    and expected["real_token"] == actual["real_token_reserves_raw"]
                    and expected["real_quote"] == actual["real_quote_reserves_raw"]
                    and expected["virtual_offset"] == actual["virtual_quote_reserves_raw"]
                ):
                    latest_exact.append(r)
            else:
                state = r["reported_reserves"]
                actual = sample["rpc_reserves"]
                if (
                    state["virtual_quote"] == actual["virtual_quote_reserves_raw"]
                    and state["virtual_token"] == actual["virtual_token_reserves_raw"]
                    and state["real_quote"] == actual["real_quote_reserves_raw"]
                    and state["real_token"] == actual["real_token_reserves_raw"]
                ):
                    latest_exact.append(r)
        results.append(
            {
                "sample": {
                    k: v for k, v in sample.items() if k not in {"quotes", "stream_state_quotes"}
                },
                "selection": "ANOMALY" if sample in selected else "RANDOM_CONTROL",
                "matching_transaction_count": len(matching),
                "target_trade": target,
                "preceding_trade": timeline[timeline.index(target) - 1]
                if target in timeline and timeline.index(target) > 0
                else None,
                "following_trade": timeline[timeline.index(target) + 1]
                if target in timeline and timeline.index(target) + 1 < len(timeline)
                else None,
                "timeline": timeline,
                "intermediate_slots_complete": all(
                    (cache / f"block-{s}.json.gz").exists()
                    for s in range(sample["stream_source_slot"], sample["rpc_response_slot"] + 1)
                ),
                "synchronization": "TRANSACTION_CORRELATED" if target else "SLOT_ONLY",
                "same_state_as_rpc_proven": False,
                "cause": "DIFFERENT_VALID_STATES_SUPPORTED" if latest_exact else "UNKNOWN",
                "rpc_state_matching_native_trade": latest_exact[-1] if latest_exact else None,
                "original_comparison_eligible_for_threshold": False,
            }
        )
    report = {
        "selected_anomalies": len(selected),
        "random_controls": 3,
        "requested_slots": slots,
        "unavailable_slots": unavailable,
        "provider_requests": previous_calls + rpc.calls,
        "results": results,
        "native_events": rows,
        "cache_manifest": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in cache.glob("*.gz")
        },
    }
    (ROOT / "analysis/reserve_anomalies.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


class SyncCollector(Collector):
    def __init__(self, settings: Settings, budget: RequestBudget) -> None:
        super().__init__(settings, seconds=120, max_requests=budget.limit)
        self.budget = budget
        for rpc in self.rpcs:
            rpc.budget = budget
        self.tracker = LocalReserveTracker()
        self.reconcile_at: dict[str, float] = {}
        self.reconciliations: list[dict[str, Any]] = []
        path = ROOT / "analysis/reserve_live_pilot.json"
        self.prior_calls = (
            json.loads(path.read_text()).get("provider_requests", []) if path.exists() else []
        )

    def native_event(self, event: Any, slot: int | None, state: dict[str, Any]) -> None:
        if isinstance(event, (PumpTrade, PumpSwapTrade)):
            self.tracker.update(
                event,
                event_id=state.get("current_event_id", "UNKNOWN:0"),
                slot=slot,
                received_at=utc().isoformat(),
                mutation=swap_mutation(event, state.get("current_log_messages", []))
                if isinstance(event, PumpSwapTrade)
                else None,
            )
        super().native_event(event, slot, state)

    async def pair_worker(self) -> None:
        from memebot.paper.market_refresh import SolanaRpcMarketSnapshotRefresher

        refresher = SolanaRpcMarketSnapshotRefresher(self.rpcs[0], commitment="confirmed")
        while not self.stop.is_set():
            market, details = await self.queue.get()
            self.pending_markets.discard(market.market)
            if len(self.deep) >= 30 and market.mint not in self.deep:
                continue
            # Bootstrap and periodic reconciliation, at most 3 reads/market in this pilot.
            if monotonic() - self.reconcile_at.get(market.market, 0) < 10:
                continue
            if sum(r["market"] == market.market for r in self.reconciliations) >= 3:
                continue
            if self.budget.used >= self.budget.limit:
                self.stop.set()
                return
            self.deep.add(market.mint)
            self.reconcile_at[market.market] = monotonic()
            result = await refresher.refresh_with_diagnostics(market)
            latest_key = market.mint if market.venue.value == "pump_fun" else market.market
            latest = self.tracker.latest.get(latest_key)
            self.reconciliations.append(
                {
                    "mint": market.mint,
                    "market": market.market,
                    "venue": market.venue.value,
                    "rpc_status": result.status,
                    "rpc_detail": result.detail,
                    "rpc_snapshot": asdict(result.market),
                    "queued_stream": details,
                    "latest_local_event_at_rpc_receipt": latest,
                    "synchronization": "SLOT_ONLY",
                    "eligible_for_threshold": False,
                }
            )

    def write_outputs(self) -> None:
        report = {
            "started_at": self.started.isoformat(),
            "ended_at": utc().isoformat(),
            "policy": "bootstrap + 10s periodic; <=3 checks/market; <=30 tokens",
            "events": self.tracker.events,
            "reconciliations": self.reconciliations,
            "launches": sorted(self.launches),
            "cheap_survivors": sorted(self.candidates),
            "serious_candidates": sorted(self.deep),
            "streams": self.streams,
            "provider_requests": self.prior_calls + [c for rpc in self.rpcs for c in rpc.calls],
            "current_run_provider_requests": [c for rpc in self.rpcs for c in rpc.calls],
            "total_phase_budget_used": self.budget.used,
            "max_rpc_requests": self.budget.limit,
        }
        (ROOT / "analysis/reserve_live_pilot.json").write_text(
            json.dumps(report, indent=2, default=str) + "\n"
        )


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical-only", action="store_true")
    parser.add_argument("--live-only", action="store_true")
    parser.add_argument("--investigate-live-breaks", action="store_true")
    args = parser.parse_args()
    settings = Settings()
    budget = RequestBudget(300)
    # Keep the phase budget across all research invocations, including default mode.
    for name in (
        "reserve_anomalies.json",
        "reserve_live_pilot.json",
        "live_transition_forensics.json",
    ):
        path = ROOT / "analysis" / name
        if path.exists():
            budget.used += len(json.loads(path.read_text()).get("provider_requests", []))
    if args.investigate_live_breaks:
        live = json.loads((ROOT / "analysis/reserve_live_pilot.json").read_text())
        signatures = {e["event_id"] for e in live["events"]}
        latest: dict[str, dict[str, Any]] = {}
        selected = []
        for e in live["events"]:
            if e.get("sequence_matches_previous_post") is False:
                selected.append((latest[e["market_key"]], e))
            latest[e["market_key"]] = e
        rpc = ForensicRpc(str(settings.solana_rpc_http_url), budget)
        cache = ROOT / "research_sessions/reserve-sync-20261001"
        results = []
        prior_path = ROOT / "analysis/live_transition_forensics.json"
        prior_calls = (
            json.loads(prior_path.read_text()).get("provider_requests", [])
            if prior_path.exists()
            else []
        )
        try:
            for previous, current in selected[:3]:
                slots = (
                    list(range(previous["slot"], current["slot"] + 1))
                    if 0 <= current["slot"] - previous["slot"] <= 2
                    else [previous["slot"], current["slot"]]
                )
                rows = []
                for slot in slots[:3]:
                    block = await block_read(rpc, slot, cache)
                    if block:
                        rows.extend(transaction_events(block, slot))
                rows.sort(key=lambda r: (r["slot"], r["transaction_index"], r["event_ordinal"]))
                matching = [r for r in rows if r["event"].get("pool") == current["market_key"]]
                verify_semantics(matching, {})
                indexes = {
                    r["signature"] + ":" + str(r["event_ordinal"]): i
                    for i, r in enumerate(matching)
                }
                p, c = indexes.get(previous["event_id"]), indexes.get(current["event_id"])
                between = matching[p + 1 : c] if p is not None and c is not None and c > p else []
                results.append(
                    {
                        "previous_event_id": previous["event_id"],
                        "current_event_id": current["event_id"],
                        "market": current["market_key"],
                        "slot": current["slot"],
                        "previous_transaction_order": p,
                        "current_transaction_order": c,
                        "native_intervening_events": between,
                        "absent_from_passive_capture": [
                            r["signature"] + ":" + str(r["event_ordinal"])
                            for r in between
                            if r["signature"] + ":" + str(r["event_ordinal"]) not in signatures
                        ],
                        "all_market_native_events": matching,
                        "cause": "SAME_SLOT_RECEIPT_ORDER_DIFFERS"
                        if p is not None and c is not None and c < p
                        else ("INTERVENING_NATIVE_EVENTS" if between else "UNKNOWN"),
                    }
                )
        finally:
            await rpc.close()
        (ROOT / "analysis/live_transition_forensics.json").write_text(
            json.dumps({"provider_requests": prior_calls + rpc.calls, "results": results}, indent=2)
            + "\n"
        )
        return
    if args.live_only:
        await SyncCollector(settings, budget).run()
        return
    report = await historical(settings, budget)
    print(
        json.dumps(
            {
                "anomalies": report["selected_anomalies"],
                "block_requests": budget.used,
                "transaction_matches": sum(bool(r["target_trade"]) for r in report["results"]),
            }
        )
    )
    if not args.historical_only:
        await SyncCollector(settings, budget).run()


if __name__ == "__main__":
    asyncio.run(main())
