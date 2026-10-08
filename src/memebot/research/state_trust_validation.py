"""Matched passive scope experiment; read-only RPC, no database or order imports."""

from __future__ import annotations

import asyncio
import json
from collections import Counter
from dataclasses import asdict, replace
from time import monotonic
from typing import Any, cast

from memebot.core.config import Settings
from memebot.market_state import MarketStateTracker
from memebot.paper.market_refresh import SolanaRpcMarketSnapshotRefresher
from memebot.providers.solana.bootstrap import ReadOnlyConfigCache
from memebot.providers.solana.canonical import FEE_PROGRAM, curve_address
from memebot.providers.solana.invalidation import scope_native_mutations
from memebot.providers.solana.pump import extract_anchor_events, unsupported_native_mutation
from memebot.providers.solana.pump_idl import PumpMayhemUpdate, PumpSwapTrade, PumpTrade
from memebot.research.market_calibration import ROOT, Collector, utc


class StateTrustCollector(Collector):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings, seconds=65, max_requests=60)
        self.native_message_cap = 150000
        self.native_programs = (*self.native_programs, FEE_PROGRAM)
        self.arms = {
            name: MarketStateTracker(capacity=20000)
            for name in ("legacy_global", "scoped", "scoped_mutations")
        }
        self.tracker = MarketStateTracker(capacity=100000)
        self.config_cache = ReadOnlyConfigCache(self.rpcs[0], "confirmed")
        self.refresher = SolanaRpcMarketSnapshotRefresher(
            self.rpcs[0],
            commitment="confirmed",
            state_tracker=self.tracker,
            config_cache=self.config_cache,
        )
        self.transactions: set[str] = set()
        self.observations: list[dict[str, Any]] = []
        self.counts: dict[str, Counter[str]] = {name: Counter() for name in self.arms}
        self.reconciliations: list[dict[str, Any]] = []
        self.started_mono = monotonic()
        self.attempted: set[str] = set()
        self.scope_only_unknown_reduction = 0
        self.scope_unknown_added = 0

    def native_transaction(
        self, signature: str | None, slot: int | None, state: dict[str, Any]
    ) -> None:
        if signature is None or signature in self.transactions:
            return
        self.transactions.add(signature)
        logs = state["current_log_messages"]
        legacy = unsupported_native_mutation(logs)
        if legacy:
            self.arms["legacy_global"].invalidate(None, legacy, signature=signature, slot=slot)
        for tracker in (self.arms["scoped"], self.arms["scoped_mutations"], self.tracker):
            scope_native_mutations(logs, tracker, signature=signature, slot=slot)

    def native_event(self, event: Any, slot: int | None, state: dict[str, Any]) -> None:
        signature, _, ordinal_text = state.get("current_event_id", "UNKNOWN:0").rpartition(":")
        ordinal = int(ordinal_text or 0)
        logs = state["current_log_messages"]
        if isinstance(event, PumpMayhemUpdate):
            if slot is not None:
                for tracker in (self.arms["scoped_mutations"], self.tracker):
                    tracker.apply_mayhem_update(
                        event,
                        market=curve_address(event.mint),
                        signature=signature,
                        slot=slot,
                        ordinal=ordinal,
                    )
            return
        if isinstance(event, (PumpTrade, PumpSwapTrade)):
            market = curve_address(event.mint) if isinstance(event, PumpTrade) else event.pool
            multi = (
                isinstance(event, PumpTrade)
                and sum(
                    isinstance(e, PumpTrade) and e.mint == event.mint
                    for _, e in extract_anchor_events(logs)
                )
                > 1
            )
            normalized = {}
            for name, tracker in (*self.arms.items(), ("production", self.tracker)):
                result = tracker.observe(
                    event,
                    market=market,
                    slot=slot,
                    signature=signature,
                    ordinal=ordinal,
                    multi_event_unknown=multi,
                )
                normalized[name] = result
                if name != "production":
                    self.counts[name][result.continuity_status] += 1
            a, b = normalized["legacy_global"], normalized["scoped"]
            self.scope_only_unknown_reduction += (
                a.continuity_status == "UNKNOWN" and b.continuity_status != "UNKNOWN"
            )
            self.scope_unknown_added += (
                a.continuity_status != "UNKNOWN" and b.continuity_status == "UNKNOWN"
            )
            current = normalized["production"]
            self.observations.append(
                {
                    "venue": "pump_fun" if isinstance(event, PumpTrade) else "pump_swap",
                    **current.model_dump(mode="json"),
                    "raw_event": asdict(event),
                    "received_at": utc().isoformat(),
                    "multi_event": multi,
                    "queue_depth": self.queue.qsize(),
                    "log_truncated": any("Log truncated" in line for line in logs),
                    "matched_status": {
                        name: item.continuity_status for name, item in normalized.items()
                    },
                }
            )
            if current.reserve_semantics.value == "UNKNOWN":
                return
            # This collector queues account reconciliation, never an entry. A
            # broken history must not prevent candidate-specific reserve repair.
            if isinstance(event, PumpSwapTrade):
                assert current.token_reserve is not None and current.quote_reserve is not None
                event = replace(
                    event,
                    pool_base_token_reserves=current.token_reserve,
                    pool_quote_token_reserves=current.quote_reserve,
                )
        super().native_event(event, slot, state)

    async def pair_worker(self) -> None:
        await self.config_cache.ensure(self.tracker.config_generation)
        while not self.stop.is_set():
            market, _ = await self.queue.get()
            self.pending_markets.discard(market.market)
            if market.market in self.attempted or len(self.attempted) >= 12:
                continue
            if self.budget.used > self.budget.limit - 5:
                continue  # Continue free passive collection; do not shorten the capture.
            self.attempted.add(market.market)
            self.deep.add(market.mint)
            before = self.budget.used
            result = await self.refresher.refresh(market)
            self.reconciliations.append(
                {
                    "market": market.market,
                    "mint": market.mint,
                    "rpc_calls": self.budget.used - before,
                    "rpc_state": result.rpc_state,
                    "quality": result.data_quality,
                    "normalized_state": result.normalized_state.model_dump(mode="json")
                    if result.normalized_state
                    else None,
                    "synchronization": "SLOT_ONLY",
                    "threshold_eligible": False,
                }
            )

    async def run(self) -> None:
        tasks = [
            asyncio.create_task(fn())
            for fn in (self.native_stream, self.portal_discovery, self.pair_worker)
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
            self.failures.extend(
                {"reason": type(r).__name__} for r in results if isinstance(r, Exception)
            )
            for rpc in self.rpcs:
                await rpc.close()
            self.write_outputs()

    def write_outputs(self) -> None:
        def save(name: str, report: Any) -> None:
            (ROOT / "analysis" / name).write_text(
                json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8"
            )

        ledger = [row.model_dump(mode="json") for row in self.tracker.invalidations]
        active = [row for row in ledger if row["dimensions"]]
        single = [
            row
            for row in active
            if row["scope"] in {"MARKET", "POOL"} and len(row["affected_markets"]) == 1
        ]
        unknown = [row for row in self.observations if row["continuity_status"] == "UNKNOWN"]
        identities = {key: asdict(value) for key, value in self.tracker.identities.items()}
        bootstrap = {
            key: asdict(cast(Any, value)) if hasattr(value, "__dataclass_fields__") else value
            for key, value in self.refresher.bootstrap_evidence.items()
        }
        calls = [call for rpc in self.rpcs for call in rpc.calls]
        report = {
            "mode": "PASSIVE_NO_DATABASE_NO_ORDERS",
            "started_at": self.started.isoformat(),
            "ended_at": utc().isoformat(),
            "elapsed_seconds": monotonic() - self.started_mono,
            "native_message_cap": self.native_message_cap,
            "rpc_cap": self.budget.limit,
            "rpc_calls": self.budget.used,
            "total_observations": len(self.observations),
            "continuity": dict(Counter(row["continuity_status"] for row in self.observations)),
            "markets": len({row["market"] for row in self.observations}),
            "unknown_by_scope": dict(
                Counter(row["invalidation_scope"] or "UNATTRIBUTED" for row in unknown)
            ),
            "unknown_by_reason": dict(
                Counter(
                    row["invalidation_reason"] or row["reason"] or "UNATTRIBUTED" for row in unknown
                )
            ),
            "reconciliation_requests": len(self.tracker.reconciliation_requests),
            "reconciliations": self.reconciliations,
            "reconciliation_success": sum(
                row["rpc_state"] == "healthy" for row in self.reconciliations
            ),
            "canonical_verified_markets": sum(
                row["canonical_verified"] for row in identities.values()
            ),
            "config_verified_markets": sum(row["config_verified"] for row in identities.values()),
            "launches": sorted(self.launches),
            "cheap_candidates": sorted(self.candidates),
            "serious_candidates": sorted(self.deep),
            "rpc_reads_per_launch": self.budget.used / len(self.launches)
            if self.launches
            else None,
            "rpc_reads_per_candidate": self.budget.used / len(self.attempted)
            if self.attempted
            else None,
            "rpc_duties": {
                "config_bootstrap": self.config_cache.reads,
                "identity_reserve_bootstrap": self.budget.used - self.config_cache.reads,
                "per_event": 0,
            },
            "provider_requests": calls,
            "matched_counterfactual": {
                "arms": {name: dict(counts) for name, counts in self.counts.items()},
                "scope_only_unknown_removed": self.scope_only_unknown_reduction,
                "scope_only_unknown_added": self.scope_unknown_added,
                "net_unknown_reduction_due_to_scope": self.scope_only_unknown_reduction
                - self.scope_unknown_added,
                "rpc_reconciliation_in_arms": False,
                "same_incoming_events": True,
                "prior_capture_replay_possible": False,
                "prior_capture_limitation": (
                    "Native mutation frames not retained; matched arms isolate scope effects "
                    "without claiming improved feed reliability."
                ),
            },
            "streams": self.streams,
            "failures": self.failures,
            "observations": self.observations,
            "runner_status": "BLOCKED",
            "calibration_status": "SLOT_ONLY_NOT_TRANSACTION_SYNCHRONIZED",
        }
        save("state_trust_validation.json", report)
        save(
            "invalidation_scope.json",
            {
                "ledger": ledger,
                "active_invalidations": len(active),
                "scope_counts": dict(Counter(row["scope"] for row in active)),
                "reason_counts": dict(Counter(row["reason"] for row in active)),
                "single_market_invalidations": len(single),
                "single_market_fraction": len(single) / len(active) if active else None,
                "matched_counterfactual": report["matched_counterfactual"],
            },
        )
        save(
            "identity_bootstrap.json",
            {
                "identities": identities,
                "bootstrap_checks": bootstrap,
                "canonical_by_venue": dict(
                    Counter(
                        row["venue"] for row in identities.values() if row["canonical_verified"]
                    )
                ),
                "execution_assumptions_verified": False,
                "slot_alignment": "SLOT_ONLY",
                "reserved_inventory_context": (
                    "Vault amount minus earlier curve real reserve; exact invariant requires "
                    "coherent historical context."
                ),
            },
        )
        save(
            "fee_config_bootstrap.json",
            {
                "accounts": self.config_cache.records,
                "reads": self.config_cache.reads,
                "cache_generation": self.config_cache.generation,
                "versions": {
                    venue: self.config_cache.version(venue) for venue in ("pump_fun", "pump_swap")
                },
                "execution_fee_model": "STATIC_ASSUMPTION",
                "exact_fee_application_verified": False,
                "remaining_unknown": [
                    "transaction-specific fee tier and sharing routing",
                    "Token-2022 transfer extensions",
                    "priority and network fee at historical instant",
                    "Mayhem/boost execution behavior",
                    "integer rounding parity with executable provider",
                ],
            },
        )
        print(
            json.dumps(
                {
                    key: value
                    for key, value in report.items()
                    if key
                    in {
                        "elapsed_seconds",
                        "total_observations",
                        "continuity",
                        "rpc_calls",
                        "canonical_verified_markets",
                        "config_verified_markets",
                        "rpc_reads_per_candidate",
                        "failures",
                    }
                }
            )
        )


def main() -> None:
    asyncio.run(StateTrustCollector(Settings()).run())


if __name__ == "__main__":
    main()
