"""Bounded passive standard-only funnel. No transaction reconstruction or orders."""

from __future__ import annotations

import asyncio
import json
from collections import Counter
from dataclasses import asdict
from time import monotonic
from typing import Any

from memebot.core.config import Settings
from memebot.eligibility import research_rejection
from memebot.market_state import MarketStateTracker
from memebot.providers.solana.canonical import FEE_PROGRAM, curve_address
from memebot.providers.solana.invalidation import scope_native_mutations
from memebot.providers.solana.pump import extract_anchor_events
from memebot.providers.solana.pump_idl import (
    NATIVE_SOL_MINT,
    PUMP_PROGRAM_ID,
    WRAPPED_SOL_MINT,
    PumpComplete,
    PumpCreate,
    PumpMigration,
    PumpTrade,
)
from memebot.research.market_calibration import ROOT, Collector, utc


class StandardUniverseCollector(Collector):
    def __init__(self, settings: Settings, *, seconds: int = 60) -> None:
        super().__init__(settings, seconds=seconds, max_requests=0)
        self.native_programs = (PUMP_PROGRAM_ID, FEE_PROGRAM)
        self.native_message_cap = 150000
        self.trusted = MarketStateTracker(capacity=20000)
        self.arithmetic = MarketStateTracker(capacity=20000)
        self.transactions: set[str] = set()
        self.launch_modes: dict[str, bool] = {}
        self.migrated: set[str] = set()
        self.rows: list[dict[str, Any]] = []
        self.reasons: Counter[str] = Counter()
        self.serious: set[str] = set()

    def native_transaction(
        self, signature: str | None, slot: int | None, state: dict[str, Any]
    ) -> None:
        if signature is None or signature in self.transactions:
            return
        self.transactions.add(signature)
        scope_native_mutations(
            state["current_log_messages"], self.trusted, signature=signature, slot=slot
        )

    def native_event(self, event: Any, slot: int | None, state: dict[str, Any]) -> None:
        if isinstance(event, PumpCreate):
            self.launches.add(event.mint)
            self.launch_modes[event.mint] = event.is_mayhem_mode
            if event.is_mayhem_mode:
                self.reasons["OUT_OF_SCOPE_MAYHEM_LAUNCH"] += 1
            elif event.quote_mint in {NATIVE_SOL_MINT, WRAPPED_SOL_MINT}:
                self.markets[event.mint] = {"market": event.bonding_curve}
            else:
                self.reasons["UNSUPPORTED_QUOTE_LAUNCH"] += 1
            return
        if isinstance(event, (PumpMigration, PumpComplete)):
            self.migrated.add(event.mint)
            return
        if not isinstance(event, PumpTrade):
            return  # No Mayhem mechanics or PumpSwap research.
        if event.is_mayhem_mode is not False:
            self.reasons[
                "OUT_OF_SCOPE_MAYHEM" if event.is_mayhem_mode else "TOKEN_MODE_UNKNOWN"
            ] += 1
            return
        if event.mint in self.migrated:
            self.reasons["MIGRATED_MARKET"] += 1
            return
        if event.quote_mint not in {NATIVE_SOL_MINT, WRAPPED_SOL_MINT}:
            self.reasons["UNSUPPORTED_QUOTE"] += 1
            return
        signature, _, ordinal = state["current_event_id"].rpartition(":")
        trades = [
            e
            for _, e in extract_anchor_events(state["current_log_messages"])
            if isinstance(e, PumpTrade)
        ]
        multi = len(trades) > 1
        market = curve_address(event.mint)
        arguments = dict(
            market=market,
            slot=slot,
            signature=signature,
            ordinal=int(ordinal),
            multi_event_unknown=multi,
        )
        trusted = self.trusted.observe(event, **arguments)
        arithmetic = self.arithmetic.observe(event, **arguments)
        reason = research_rejection(trusted.evidence())
        self.reasons[reason or "RESEARCH_SCOPE_READY"] += 1
        self.activity[event.mint] += 1
        if reason is None and self.activity[event.mint] >= 2:
            self.serious.add(event.mint)
        self.rows.append(
            {
                "raw_event": asdict(event),
                "multi_event": multi,
                "trusted": trusted.model_dump(mode="json"),
                "arithmetic": arithmetic.model_dump(mode="json"),
            }
        )

    async def capture(self) -> dict[str, Any]:
        started = monotonic()
        task = asyncio.create_task(self.native_stream())
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=self.seconds)
        except TimeoutError:
            task.cancel()
        finally:
            await asyncio.gather(task, return_exceptions=True)
            for rpc in self.rpcs:
                await rpc.close()
        standard = sum(mode is False for mode in self.launch_modes.values())
        survivors = len(self.markets)
        result = {
            "captured_at": utc().isoformat(),
            "elapsed_seconds": monotonic() - started,
            "scope": "STANDARD_PUMP_FUN_ONLY",
            "runner": "BLOCKED",
            "launches_observed": len(self.launches),
            "standard_launches": standard,
            "standard_quote_survivors": survivors,
            "standard_launch_percent": 100 * standard / len(self.launches)
            if self.launches
            else None,
            "scope_survivor_percent": 100 * survivors / len(self.launches)
            if self.launches
            else None,
            "serious_eligible_candidates": len(self.serious),
            "entry_ready": 0,
            "rpc_reads": self.budget.used,
            "config_reads": 0,
            "identity_reads": 0,
            "execution_refreshes": 0,
            "excluded_deep_reads": 0,
            "rpc_per_serious_eligible_candidate": 0 if self.serious else None,
            "cost_limit": "PASSIVE_ONLY; canonical/state-sequence prerequisite not met",
            "trusted_counts": dict(Counter(r["trusted"]["continuity_status"] for r in self.rows)),
            "arithmetic_counts": dict(
                Counter(r["arithmetic"]["continuity_status"] for r in self.rows)
            ),
            "rejections": dict(self.reasons),
            "streams": self.streams,
            "observations": self.rows,
            "synchronized_pairs": 0,
            "bands": {"NORMAL": None, "ELEVATED": None, "SEVERE": None},
        }
        (ROOT / "analysis/standard_pumpfun_capture.json").write_text(
            json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8"
        )
        return {
            key: value for key, value in result.items() if key not in {"observations", "streams"}
        }


async def main() -> None:
    print(json.dumps(await StandardUniverseCollector(Settings()).capture(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
