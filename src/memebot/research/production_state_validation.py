"""Bounded passive capture using production normalization. No database or orders."""

from __future__ import annotations

import asyncio
import json
from collections import Counter
from dataclasses import asdict, replace
from time import monotonic
from typing import Any

from memebot.core.config import Settings
from memebot.market_state import MarketStateTracker
from memebot.paper.market_refresh import SolanaRpcMarketSnapshotRefresher
from memebot.providers.solana.pump import unsupported_native_mutation
from memebot.providers.solana.pump_idl import PumpSwapTrade, PumpTrade
from memebot.research.market_calibration import ROOT, Collector, utc


class ProductionValidationCollector(Collector):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings, seconds=60, max_requests=30)
        self.production_tracker = MarketStateTracker()
        self.observations: list[dict[str, Any]] = []
        self.reconciliations: list[dict[str, Any]] = []
        self.reconciled_markets: set[str] = set()
        self.inspected_transactions: set[str] = set()
        self.mutations: Counter[str] = Counter()
        self.started_mono = monotonic()

    def native_event(self, event: Any, slot: int | None, state: dict[str, Any]) -> None:
        event_id = state.get("current_event_id", "UNKNOWN:0")
        signature, _, ordinal_text = event_id.rpartition(":")
        logs = state.get("current_log_messages", [])
        if signature not in self.inspected_transactions:
            self.inspected_transactions.add(signature)
            unsupported = unsupported_native_mutation(logs)
            if unsupported:
                self.mutations[unsupported] += 1
                self.production_tracker.invalidate(None, unsupported)
        if isinstance(event, (PumpTrade, PumpSwapTrade)):
            from memebot.providers.solana.pump import extract_anchor_events

            context = self.markets.get(event.mint) if isinstance(event, PumpTrade) else None
            market = (
                context["market"]
                if context
                else (
                    "unbootstrapped:" + event.mint if isinstance(event, PumpTrade) else event.pool
                )
            )
            multi = (
                isinstance(event, PumpTrade)
                and sum(
                    isinstance(e, PumpTrade) and e.mint == event.mint
                    for _, e in extract_anchor_events(logs)
                )
                > 1
            )
            normalized = self.production_tracker.observe(
                event,
                market=market,
                slot=slot,
                signature=signature,
                ordinal=int(ordinal_text or 0),
                multi_event_unknown=multi,
            )
            self.observations.append(
                {
                    "venue": "pump_fun" if isinstance(event, PumpTrade) else "pump_swap",
                    **normalized.model_dump(mode="json"),
                }
            )
            self.mutations["buy" if event.is_buy else "sell"] += 1
            # Candidate filtering must see production POST, not original PRE.
            if isinstance(event, PumpSwapTrade):
                if normalized.observational_price is None:
                    return
                assert normalized.token_reserve is not None and normalized.quote_reserve is not None
                super().native_event(
                    replace(
                        event,
                        pool_base_token_reserves=normalized.token_reserve,
                        pool_quote_token_reserves=normalized.quote_reserve,
                    ),
                    slot,
                    state,
                )
                return
            if normalized.observational_price is None:
                return
        else:
            self.mutations[type(event).__name__] += 1
        super().native_event(event, slot, state)

    async def pair_worker(self) -> None:
        refresher = SolanaRpcMarketSnapshotRefresher(
            self.rpcs[0], commitment="confirmed", state_tracker=self.production_tracker
        )
        while not self.stop.is_set():
            market, _details = await self.queue.get()
            self.pending_markets.discard(market.market)
            # Diversity: one bootstrap per candidate, no periodic or per-tick reads.
            if market.market in self.reconciled_markets or len(self.deep) >= 15:
                continue
            if self.budget.used >= self.budget.limit - 2:
                self.stop.set()
                return
            self.reconciled_markets.add(market.market)
            self.deep.add(market.mint)
            before = self.budget.used
            refreshed = await refresher.refresh(market)
            self.reconciliations.append(
                {
                    "market": market.market,
                    "mint": market.mint,
                    "duty": "bootstrap",
                    "rpc_calls": self.budget.used - before,
                    "rpc_state": refreshed.rpc_state,
                    "quality": refreshed.data_quality,
                    "snapshot": asdict(refreshed),
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
            for result in results:
                if isinstance(result, Exception):
                    self.failures.append({"reason": type(result).__name__})
            for rpc in self.rpcs:
                await rpc.close()
            self.write_outputs()

    def write_outputs(self) -> None:
        statuses = Counter(row["continuity_status"] for row in self.observations)
        success = sum(r["rpc_state"] == "healthy" for r in self.reconciliations)
        report = {
            "started_at": self.started.isoformat(),
            "ended_at": utc().isoformat(),
            "elapsed_seconds": monotonic() - self.started_mono,
            "mode": "PASSIVE_NO_DATABASE_NO_ORDERS",
            "max_rpc_requests": self.budget.limit,
            "markets_tracked": len({row["market"] for row in self.observations}),
            "trade_observations": len(self.observations),
            "mutations": dict(self.mutations),
            "continuity": dict(statuses),
            "unknown_occurrences": sum(
                row["reserve_semantics"] == "UNKNOWN" or row["continuity_status"] == "UNKNOWN"
                for row in self.observations
            ),
            "launches": sorted(self.launches),
            "cheap_candidates": sorted(self.candidates),
            "serious_candidates": sorted(self.deep),
            "reconciliations": self.reconciliations,
            "reconciliation_success_count": success,
            "reconciliation_success_rate": success / len(self.reconciliations)
            if self.reconciliations
            else None,
            "rpc_reads_per_candidate": self.budget.used / len(self.deep) if self.deep else None,
            "rpc_duties": {
                "bootstrap": self.budget.used,
                "periodic": 0,
                "divergence_repair": 0,
                "pre_entry": 0,
                "exit": 0,
            },
            "provider_requests": [call for rpc in self.rpcs for call in rpc.calls],
            "observations": self.observations,
            "streams": self.streams,
            "failures": self.failures,
            "percentage_threshold_derived": False,
        }
        (ROOT / "analysis/production_state_passive.json").write_text(
            json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8"
        )


def main() -> None:
    asyncio.run(ProductionValidationCollector(Settings()).run())


if __name__ == "__main__":
    main()
