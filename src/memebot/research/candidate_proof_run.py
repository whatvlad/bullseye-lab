"""Bounded standard candidate proof capture; no database or order execution."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from memebot.core.config import Settings
from memebot.events.models import TokenTrade, TradeSide
from memebot.intelligence.features.engine import RollingFeatureEngine
from memebot.models.market import MarketLifecycle
from memebot.models.risk import RiskResult
from memebot.paper.candidate_proof import (
    Candidate,
    CandidateProofService,
    Proof,
    TrustDimension,
    proof_cost_summary,
)
from memebot.providers.solana.canonical import FEE_PROGRAM, curve_address
from memebot.providers.solana.pump_idl import (
    PUMP_PROGRAM_ID,
    PumpComplete,
    PumpCreate,
    PumpMigration,
    PumpTrade,
)
from memebot.research.market_calibration import CalibrationRpc, RequestBudget, utc
from memebot.research.standard_universe import StandardUniverseCollector
from memebot.strategies.presets import initial_strategy_presets
from memebot.strategies.regimes import classify_regime
from memebot.strategies.scoring import TransparentScoreEngine

ROOT = Path(__file__).resolve().parents[3]


class CandidateRpc(CalibrationRpc):
    METHODS = CalibrationRpc.METHODS | {"getSignaturesForAddress", "getTransaction"}


class PassiveCandidateProof(StandardUniverseCollector):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings, seconds=120)
        self.rpc = CandidateRpc(str(settings.solana_rpc_http_url), RequestBudget(96))
        self.service = CandidateProofService(self.rpc)
        self.features = RollingFeatureEngine((10, 30, 60))
        self.configuration = next(c for c in initial_strategy_presets() if c.key == "aggressive")
        self.created: dict[str, datetime] = {}
        self.proofs: list[Proof] = []
        self.attempted: set[str] = set()
        self.candidate_queue: asyncio.Queue[Candidate] = asyncio.Queue(maxsize=8)
        self.skips: dict[str, int] = {}
        self.output_stem = "candidate"
        self.candidate_cap = 8

    def native_transaction(
        self, signature: str | None, slot: int | None, state: dict[str, Any]
    ) -> None:
        if signature in self.transactions:
            return
        prior = self.trusted.invalidations[-1] if self.trusted.invalidations else None
        super().native_transaction(signature, slot, state)
        new_records = []
        for record in reversed(self.trusted.invalidations):
            if record is prior:
                break
            new_records.append(record)
        for record in reversed(new_records):
            if record.signature != signature or not record.dimensions:
                continue
            if record.program not in {PUMP_PROGRAM_ID, FEE_PROGRAM}:
                continue
            unknown = record.reason in {
                "UNKNOWN_NATIVE_INSTRUCTION",
                "DECODER_FAILURE",
                "TRUNCATED_LOG",
            }
            dimensions = (
                frozenset(TrustDimension)
                if unknown
                else frozenset(
                    {TrustDimension.CONFIG, TrustDimension.FEE_ROUTE}
                    if "config" in record.dimensions
                    else {TrustDimension.RESERVE_STATE, TrustDimension.CONTINUITY}
                )
            )
            source = record.model_dump(mode="json")
            if record.scope.value in {"GLOBAL", "VENUE"}:
                self.service.invalidate(record.reason, dimensions=dimensions, source=source)
            else:
                for mint in set(self.service.lineage) | set(self.attempted):
                    if curve_address(mint) in record.affected_markets:
                        self.service.invalidate(
                            record.reason, mint, dimensions=dimensions, source=source
                        )

    def native_event(self, event: Any, slot: int | None, state: dict[str, Any]) -> None:
        before = len(self.rows)
        super().native_event(event, slot, state)
        if isinstance(event, (PumpMigration, PumpComplete)):
            self.service.invalidate(
                "MIGRATION_OR_COMPLETION",
                event.mint,
                dimensions=frozenset({TrustDimension.LIFECYCLE}),
                incompatible=True,
                source={"slot": slot, "event": type(event).__name__},
            )
        if isinstance(event, PumpCreate) and event.is_mayhem_mode is False:
            self.created[event.mint] = datetime.fromtimestamp(event.timestamp, UTC)
        if not isinstance(event, PumpTrade) or len(self.rows) == before:
            return
        if event.token_amount <= 0 or event.quote_amount <= 0:
            self.skips["unpriceable_native_event"] = (
                self.skips.get("unpriceable_native_event", 0) + 1
            )
            return
        row = self.rows[-1]
        if row["multi_event"] or event.mint in self.migrated:
            return
        normalized = self.arithmetic.states[row["arithmetic"]["market"]]
        signature, _, ordinal = state["current_event_id"].rpartition(":")
        trade = TokenTrade(
            provider="passive_candidate_proof",
            source_event_at=datetime.fromtimestamp(event.timestamp, UTC),
            provider_received_at=utc(),
            source_slot=slot,
            event_id=uuid5(NAMESPACE_URL, signature + ":" + ordinal),
            mint=event.mint,
            signature=signature,
            side=TradeSide.BUY if event.is_buy else TradeSide.SELL,
            token_amount=Decimal(event.token_amount),
            quote_amount=Decimal(event.quote_amount),
            quote_asset=event.quote_mint,
            wallet=event.user,
            market=normalized.market,
            normalized_state=normalized,
        )
        self.features.ingest_trade(trade)
        feature = self.features.current_snapshot(trade)
        if feature is None or normalized.continuity_status != "EXACT" or slot is None:
            return
        created = self.created.get(event.mint)
        if created is None:
            return  # No paid lookup to invent token age.
        age = max(0, int((trade.source_event_at - created).total_seconds()))
        configuration = self.configuration
        # Reuse the existing score and all market-quality constraints unchanged.
        feature = feature.model_copy(update={"lifecycle": MarketLifecycle.BONDING_CURVE})
        scorer = TransparentScoreEngine()
        regime = classify_regime(
            feature.lifecycle,
            token_age_seconds=age,
            momentum_score=scorer.momentum_score(feature, configuration.scoring_window_seconds),
        )
        score = scorer.score(feature, RiskResult(allowed=None), configuration, regime=regime)
        metric = next(
            m for m in feature.windows if m.window_seconds == configuration.scoring_window_seconds
        )
        reasons = []
        if regime not in configuration.allowed_regimes:
            reasons.append("regime")
        if age < configuration.minimum_token_age_seconds:
            reasons.append("age")
        if metric.trade_count < configuration.minimum_trades_in_window:
            reasons.append("trade_count")
        if metric.unique_buyers < configuration.minimum_unique_buyers_in_window:
            reasons.append("unique_buyers")
        if metric.observation_span_seconds < configuration.minimum_observation_seconds:
            reasons.append("span")
        if (
            metric.flow_imbalance is None
            or metric.flow_imbalance < configuration.minimum_flow_imbalance
        ):
            reasons.append("flow")
        if (
            metric.buyer_wallet_attribution_percent
            < configuration.minimum_buyer_attribution_percent
        ):
            reasons.append("attribution")
        if (
            metric.largest_buyer_volume_share is None
            or metric.largest_buyer_volume_share > configuration.maximum_largest_buyer_share
        ):
            reasons.append("concentration")
        if score.final_score is None or score.final_score < configuration.score_threshold:
            reasons.append("score")
        if (
            score.component_completeness_percent
            < configuration.minimum_component_completeness_percent
        ):
            reasons.append("completeness")
        if (
            configuration.maximum_price_change_percent is not None
            and abs(metric.price_change_percent or Decimal(0))
            > configuration.maximum_price_change_percent
        ):
            reasons.append("price_change")
        if configuration.require_sell_absorption and (
            metric.sell_count == 0 or (metric.price_change_percent or 0) < 0
        ):
            reasons.append("sell_absorption")
        for reason in reasons:
            self.skips[reason] = self.skips.get(reason, 0) + 1
        if reasons or event.mint in self.attempted or len(self.attempted) >= self.candidate_cap:
            return
        candidate = Candidate(
            event.mint,
            event,
            signature,
            slot,
            utc(),
            "EXACT",
            True,
            25_000_000,
            max(1, event.token_amount // 10),
            quality_evidence={
                "strategy_version_id": str(configuration.version_id),
                "score": str(score.final_score),
                "risk_not_assumed_approved": True,
                "metric": metric.model_dump(mode="json"),
                "token_age_seconds": age,
            },
            native_event_received_at=trade.provider_received_at,
            event_ordinal=int(ordinal),
        )
        try:
            self.candidate_queue.put_nowait(candidate)
            self.attempted.add(event.mint)
        except asyncio.QueueFull:
            self.skips["proof_queue_full"] = self.skips.get("proof_queue_full", 0) + 1

    async def native_stream(self) -> None:
        try:
            await super().native_stream()
        finally:
            self.service.invalidate(
                "NATIVE_STREAM_ENDED", dimensions=frozenset({TrustDimension.STREAM_COVERAGE})
            )

    async def proof_worker(self) -> None:
        while True:
            candidate = await self.candidate_queue.get()
            try:
                proof = await self.service.prove(candidate)
                self.proofs.append(proof)
                if proof.status == "PASS":
                    try:
                        proof.evidence["passive_refresh"] = await self.service.execution_refresh(
                            proof, decision_at=utc()
                        )
                    except Exception as error:
                        proof.evidence["passive_refresh_failure"] = str(error)
                print(
                    json.dumps(
                        {
                            "candidate": candidate.mint,
                            "status": proof.status,
                            "reason": proof.reason,
                            "costs": proof.costs,
                        }
                    ),
                    flush=True,
                )
            finally:
                self.candidate_queue.task_done()

    async def run_proofs(self) -> None:
        worker = asyncio.create_task(self.proof_worker())
        try:
            # Use capture but preserve prior standard capture: this subclass has
            # its own report and must not overwrite the previous experiment.
            task = asyncio.create_task(self.native_stream())
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=self.seconds)
            except TimeoutError:
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await asyncio.wait_for(self.candidate_queue.join(), timeout=30)
        finally:
            worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)
            await self.rpc.close()
            for rpc in self.rpcs:
                await rpc.close()
        out = ROOT / "analysis"
        payload = {
            "scope": "STANDARD_PUMP_FUN_ONLY",
            "runner": "BLOCKED",
            "duration_cap_seconds": self.seconds,
            "native_message_cap": self.native_message_cap,
            "candidate_cap": self.candidate_cap,
            "total_rpc_cap": self.rpc.budget.limit,
            "launches": len(self.launches),
            "standard_launches": sum(v is False for v in self.launch_modes.values()),
            "quality_rejections": self.skips,
            "stream": self.streams,
            "candidate_proofs": [p.report() for p in self.proofs],
            "proof_invalidations": self.service.invalidations,
            "native_invalidations": [i.model_dump(mode="json") for i in self.trusted.invalidations],
            "provider_calls": self.rpc.calls,
            "orders": 0,
            "database_mutations": 0,
            "historical_divergence_cases": "analysis/standard_pumpfun_validation.json",
            "observational_counts": {
                key: sum(r["arithmetic"]["continuity_status"] == key for r in self.rows)
                for key in ("FIRST_OBSERVATION", "EXACT", "DIVERGED", "UNKNOWN")
            },
        }
        (out / f"{self.output_stem}_execution_proofs.json").write_text(
            json.dumps(payload, indent=2, default=str) + "\n"
        )
        costs = proof_cost_summary(self.proofs)
        costs["total_http_requests"] = self.rpc.budget.used
        costs["per_candidate"] = [
            {
                "mint": p.candidate.mint,
                "status": p.status,
                "costs": p.costs,
                "latency_ms": p.proof_latency_ms,
            }
            for p in self.proofs
        ]
        (out / f"{self.output_stem}_proof_cost.json").write_text(
            json.dumps(costs, indent=2, default=str) + "\n"
        )
        print(
            json.dumps(
                {
                    key: costs[key]
                    for key in ("attempts", "statuses", "rpc_requests", "proof_latency_ms")
                },
                indent=2,
            )
        )


async def main() -> None:
    await PassiveCandidateProof(Settings()).run_proofs()


if __name__ == "__main__":
    asyncio.run(main())
