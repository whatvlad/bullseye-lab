"""Bounded coverage-before-proof research. CandidateProofService is unchanged."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from typing import Any

from memebot.core.config import Settings
from memebot.paper.candidate_proof import TrustDimension
from memebot.paper.stream_proof import StreamFirstProofService
from memebot.providers.solana._yellowstone_generated import geyser_pb2 as proto
from memebot.providers.solana.canonical import curve_address
from memebot.providers.solana.evidence_stream import (
    AccountEvidence,
    EvidenceBuffer,
    TransactionEvidence,
)
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
from memebot.research.candidate_proof_run import ROOT
from memebot.research.early_watch import EarlyWatch, ResearchStage
from memebot.research.filtered_stream_run import FilteredStreamPilot, simple_fee_event
from memebot.research.packet_forensics import inspect_packet
from memebot.research.stream_proof_run import StreamProofPilot


class EarlyWatchPilot(FilteredStreamPilot):
    def __init__(
        self,
        settings: Settings,
        *,
        capacity: int,
        seconds: int,
        paired: bool,
        both_discovery_programs: bool = False,
        per_market_event_cap: int = 512,
        output_stem: str | None = None,
    ) -> None:
        super().__init__(settings, output_stem=output_stem or f"early_watch_{capacity}")
        self.seconds = seconds
        self.paired = paired
        self.early = EarlyWatch(capacity)
        # TTL and byte budget unchanged. Count limits are bounded sizing tests.
        if per_market_event_cap not in {128, 256, 512}:
            raise ValueError("bounded research retention required")
        self.buffer = EvidenceBuffer(
            seconds=120, max_events=8192, per_market=per_market_event_cap, max_bytes=32_000_000
        )
        self.local_service = StreamFirstProofService(self.rpc, buffer=self.buffer)
        if not both_discovery_programs:
            self.discovery_programs = (PUMP_PROGRAM_ID,)
        self.executed_stream.on_control = self.control
        self.rejections: Counter[str] = Counter()
        self.representatives: dict[str, list[str]] = defaultdict(list)
        self.packet_inventory: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.relevant_failures: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.feed_inventory: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.global_faults: list[dict[str, Any]] = []
        self.received_raw = 0
        self.previous_slot: int | None = None
        self.ack_history: list[dict[str, Any]] = []
        self.discovery_metrics: Counter[str] = Counter()
        self.subscription_programs: dict[int, str] = {}
        self.discovery_seen: set[str] = set()
        self.serious_records: list[dict[str, Any]] = []
        self.excluded_from_research: dict[str, str] = {}
        self.source_hashes = {
            p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
            for p in (
                "src/memebot/research/early_watch_run.py",
                "src/memebot/research/early_watch.py",
                "src/memebot/providers/solana/alchemy_evidence.py",
                "src/memebot/providers/solana/evidence_stream.py",
            )
        }

    def control(self, event: dict[str, Any]) -> None:
        at = datetime.fromisoformat(event["at"])
        if event["kind"] == "ack":
            revision = event["revision"]
            record = next(
                (r for r in self.executed_stream.filter_history if r["revision"] == revision), None
            )
            if record:
                self.early.acknowledge(record["accounts"], at)
                self.ack_history.append({"revision": revision, "at": at.isoformat()})
        elif event["kind"] == "slot":
            slot = event["slot"]
            if self.previous_slot is not None and slot != self.previous_slot + 1:
                if slot != self.previous_slot:
                    self.global_faults.append({"at": at.isoformat(), "reason": "SLOT_ORDER_OR_GAP"})
            self.previous_slot = max(slot, self.previous_slot or slot)

    def sync_filter(self) -> None:
        self.early.expire(datetime.now(UTC))
        self.executed_stream.update_filter(tuple(self.early.accounts()), self.config_keys)

    def archive_packet(self, record: dict[str, Any]) -> None:
        super().archive_packet(record)
        if record.get("record_kind") != "provider_protobuf":
            return
        self.received_raw += 1
        raw = base64.b64decode(record["raw_protobuf_base64"], validate=True)
        digest = hashlib.sha256(raw).hexdigest()
        update = proto.SubscribeUpdate.FromString(raw)
        at = datetime.fromisoformat(record["received_timestamp"])
        inspection = inspect_packet(update, at)
        category = inspection["category"]
        self.rejections[category] += 1
        if len(self.representatives[category]) < 3:
            self.representatives[category].append(digest)
        for mint, market in self.early.markets.items():
            if set(market.accounts).intersection(inspection["accounts"]):
                entry = {
                    "signature": record["signature"],
                    "at": at.isoformat(),
                    "slot": record["slot"],
                    "index": record["transaction_index"],
                    "bytes": len(raw),
                    "hash": digest,
                    "category": category,
                }
                self.packet_inventory[mint].append(entry)
                if category not in {"USABLE", "NON_TRADE_EXECUTION"}:
                    self.relevant_failures[mint].append(entry)

    def native_event(self, event: Any, slot: int | None, state: dict[str, Any]) -> None:
        now = datetime.now(UTC)
        trades = [
            e
            for _, e in extract_anchor_events(state["current_log_messages"])
            if isinstance(e, PumpTrade)
        ]
        if isinstance(event, PumpTrade):
            if event.mint in self.excluded_from_research:
                return
            signature = state["current_event_id"].rpartition(":")[0]
            self.feed_inventory[event.mint].append(
                {"signature": signature, "at": now.isoformat(), "slot": slot}
            )
            if (
                len(trades) != 1
                or event.is_mayhem_mode is not False
                or not simple_fee_event(state["current_log_messages"], event.mint)
            ):
                self.early.remove(event.mint, "OUT_OF_SCOPE_OR_AMBIGUOUS", now)
                self.excluded_from_research[event.mint] = "OUT_OF_SCOPE_OR_AMBIGUOUS"
                self.sync_filter()
                return
        StreamProofPilot.native_event(self, event, slot, state)
        if isinstance(event, PumpCreate):
            eligible = (
                event.is_mayhem_mode is False
                and not event.is_cashback_enabled
                and event.quote_mint in {NATIVE_SOL_MINT, WRAPPED_SOL_MINT}
                and event.bonding_curve == curve_address(event.mint)
                and len(trades) <= 1
            )
            if eligible:
                self.early.admit(event.mint, now)
            else:
                self.early.remove(event.mint, "CHEAP_UNIVERSE_EXCLUSION", now)
                self.excluded_from_research[event.mint] = "CHEAP_UNIVERSE_EXCLUSION"
        elif isinstance(event, PumpTrade) and event.mint in self.created:
            if event.mint not in self.early.markets:
                self.early.admit(event.mint, now)
            self.early.touch(event.mint, now)
        elif isinstance(event, (PumpComplete, PumpMigration)):
            self.early.remove(event.mint, "MIGRATED_OR_COMPLETE", now)
            self.excluded_from_research[event.mint] = "MIGRATED_OR_COMPLETE"
        self.ever_watched.update(self.early.history)
        self.sync_filter()

    async def full_stream(self) -> None:
        try:
            async for evidence in self.executed_stream.transactions():
                if (
                    isinstance(evidence, TransactionEvidence)
                    and evidence.mint in self.early.markets
                ):
                    self.buffer.add(evidence)
                    self.packet_by_market[evidence.mint] += 1
                elif isinstance(evidence, AccountEvidence):
                    self.buffer.add_account(evidence)
                    if evidence.address in self.config_keys:
                        # Preserve configuration invalidation even without the
                        # duplicate global Fee-program log subscription.
                        for service in (self.service, self.local_service):
                            service.invalidate(
                                "WATCHED_CONFIG_UPDATE",
                                dimensions=frozenset(
                                    {TrustDimension.CONFIG, TrustDimension.FEE_ROUTE}
                                ),
                            )
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self.meter["full_stream_error"] = {
                "type": type(error).__name__,
                "provider": self.executed_stream.failure,
            }
            self.global_faults.append(
                {"at": datetime.now(UTC).isoformat(), "reason": "FULL_STREAM_FAILED"}
            )
            self.buffer.gap("FULL_STREAM_FAILED")

    def observe_discovery(self, raw: str | bytes, message: dict[str, Any]) -> None:
        size = len(raw.encode() if isinstance(raw, str) else raw)
        kind = message.get("method", "ack_or_error")
        self.discovery_metrics[f"{kind}_messages"] += 1
        self.discovery_metrics[f"{kind}_bytes"] += size
        if "id" in message and "result" in message:
            idx = message["id"] - 1
            if 0 <= idx < len(self.discovery_programs):
                self.subscription_programs[message["result"]] = self.discovery_programs[idx]
        if kind != "logsNotification":
            return
        params = message["params"]
        program = self.subscription_programs.get(params["subscription"], "UNKNOWN")
        value = params["result"]["value"]
        signature = value.get("signature", "")
        logs = value.get("logs", [])
        log_bytes = len(json.dumps(logs).encode())
        self.discovery_metrics[f"program_{program}_bytes"] += size
        self.discovery_metrics[f"program_{program}_messages"] += 1
        self.discovery_metrics["log_array_json_bytes"] += log_bytes
        self.discovery_metrics["json_envelope_bytes"] += size - log_bytes
        if signature in self.discovery_seen:
            self.discovery_metrics["duplicate_signature_messages"] += 1
            self.discovery_metrics["duplicate_signature_bytes"] += size
        self.discovery_seen.add(signature)
        events = extract_anchor_events(logs) if value.get("err") is None else []
        self.discovery_metrics["failed_transaction_messages"] += int(value.get("err") is not None)
        self.discovery_metrics["no_supported_event_messages"] += int(not events)
        self.discovery_metrics["create_events"] += sum(isinstance(e, PumpCreate) for _, e in events)
        self.discovery_metrics[f"program_{program}_create_events"] += sum(
            isinstance(e, PumpCreate) for _, e in events
        )

    def certificate(self, candidate: Any, at: datetime) -> dict[str, Any]:
        market = self.early.history.get(candidate.mint)
        metric = candidate.quality_evidence["metric"]
        span = max(float(metric["window_seconds"]), float(metric["observation_span_seconds"]))
        start = candidate.detected_at - timedelta(seconds=span)
        reasons = []
        if market is None or not market.acknowledged or market.acknowledged > start:
            reasons.append("ACK_AFTER_REQUIRED_START")
        if candidate.mint not in self.early.markets:
            reasons.append("FILTER_NOT_ACTIVE")
        if any(start <= datetime.fromisoformat(x["at"]) <= at for x in self.global_faults):
            reasons.append("SLOT_OR_CONNECTION_GAP")
        if any(
            start <= datetime.fromisoformat(x["at"]) <= at
            for x in self.relevant_failures[candidate.mint]
        ):
            reasons.append("RELEVANT_UNDECODABLE_PACKET")
        lost = [
            e
            for e in self.buffer.evictions
            if e["mint"] == candidate.mint
            and start <= datetime.fromisoformat(e["received_at"]) <= at
        ]
        if lost:
            reasons.append("REQUIRED_EVIDENCE_EVICTED")
        feed = {
            e["signature"]
            for e in self.feed_inventory[candidate.mint]
            if start <= datetime.fromisoformat(e["at"]) <= candidate.detected_at
        }
        retained = {e.signature for e in self.buffer.items.values() if e.mint == candidate.mint}
        if candidate.anchor_signature not in retained or not feed.issubset(retained):
            reasons.append("KNOWN_NATIVE_SIGNATURE_MISSING")
        order = [
            (e["slot"], e["index"])
            for e in self.packet_inventory[candidate.mint]
            if start <= datetime.fromisoformat(e["at"]) <= at
        ]
        if any(right < left for left, right in pairwise(order)):
            reasons.append("UNRESOLVED_OUT_OF_ORDER")
        if not self.executed_stream.connected or (self.previous_slot or 0) <= candidate.anchor_slot:
            reasons.append("WINDOW_NOT_CLOSED_BY_LATER_SLOT")
        return {
            "status": "COMPLETE_FOR_WINDOW" if not reasons else "INCOMPLETE",
            "scope": "observed Pump transaction window; not all-program account mutation proof",
            "required_start": start.isoformat(),
            "end": at.isoformat(),
            "reasons": reasons,
            "known_native_signatures": len(feed),
            "lost_events": lost,
        }

    async def proof_worker(self) -> None:
        while True:
            candidate = await self.candidate_queue.get()
            try:
                record = self.early.serious(candidate.mint, candidate.detected_at)
                market = self.early.history.get(candidate.mint)
                interval = [
                    e
                    for e in self.packet_inventory[candidate.mint]
                    if market
                    and market.started <= datetime.fromisoformat(e["at"]) <= candidate.detected_at
                ]
                record.update(
                    events_watch_to_serious=len(interval),
                    bytes_watch_to_serious=sum(e["bytes"] for e in interval),
                )
                self.serious_records.append(record)
                pair: dict[str, Any] = {
                    "mint": candidate.mint,
                    "signature": candidate.anchor_signature,
                    "early_watch": record,
                    "local_before_retrospective": self.buffer.get(
                        candidate.anchor_signature, datetime.now(UTC)
                    )
                    is not None,
                }
                if self.paired:
                    self.early.stages[candidate.mint] = ResearchStage.PROOF_PENDING
                    for name, service in (("OLD", self.service), ("NEW", self.local_service)):
                        if name == "NEW":
                            pair["local_before_stream_proof"] = (
                                self.buffer.get(candidate.anchor_signature, datetime.now(UTC))
                                is not None
                            )
                            pair["window_certificate"] = self.certificate(
                                candidate, datetime.now(UTC)
                            )
                            self.local_hits_before_proof += int(pair["local_before_stream_proof"])
                        proof = await service.prove(candidate)
                        self.proofs.append(proof)
                        if proof.status == "PASS":
                            try:
                                proof.evidence["passive_refresh"] = await service.execution_refresh(
                                    proof, decision_at=datetime.now(UTC)
                                )
                            except Exception as error:
                                proof.evidence["passive_refresh_failure"] = type(error).__name__
                        pair[name] = proof.report()
                    if pair["NEW"]["status"] != "PASS":
                        self.early.touch(candidate.mint, datetime.now(UTC), favorable=False)
                else:
                    pair["local_before_stream_proof"] = pair["local_before_retrospective"]
                    pair["window_certificate"] = self.certificate(candidate, datetime.now(UTC))
                self.pairs.append(pair)
                print(
                    json.dumps(
                        {
                            "capacity": self.early.capacity,
                            "serious": len(self.pairs),
                            "local": pair["local_before_stream_proof"],
                            "recall": record["early_watch_before_serious"],
                            "window": pair["window_certificate"]["status"],
                            "NEW": pair.get("NEW", {}).get("status"),
                        }
                    ),
                    flush=True,
                )
            finally:
                self.candidate_queue.task_done()

    async def run_proofs(self) -> None:
        await super().run_proofs()
        path = ROOT / f"analysis/{self.output_stem}.json"
        report = json.loads(path.read_text())
        serious_mints = {r["mint"] for r in self.serious_records}
        report.update(
            early_watch=self.early.report(),
            serious_records=self.serious_records,
            serious_early_watch_recall=sum(
                r["early_watch_before_serious"] for r in self.serious_records
            )
            / len(self.serious_records)
            if self.serious_records
            else None,
            false_watch_markets=len(set(self.early.history) - serious_mints),
            classifications=dict(self.rejections),
            rejection_hashes=dict(self.representatives),
            raw_packets_archived=self.received_raw,
            packet_inventory=dict(self.packet_inventory),
            relevant_failures=dict(self.relevant_failures),
            global_faults=self.global_faults,
            native_feed_inventory=dict(self.feed_inventory),
            cheap_research_exclusions=self.excluded_from_research,
            discovery_breakdown=dict(self.discovery_metrics),
            ack_history=self.ack_history,
            capture_code_sha256=self.source_hashes,
            paired=self.paired,
            retention={
                "seconds": self.buffer.seconds,
                "per_market_event_cap": self.buffer.per_market,
                "global_event_cap": self.buffer.max_events,
                "transaction_byte_cap": self.buffer.max_bytes,
            },
        )
        path.write_text(json.dumps(report, indent=2, default=str) + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--capacity", type=int, choices=(8, 16, 32), required=True)
    parser.add_argument("--seconds", type=int, default=90)
    parser.add_argument("--paired", action="store_true")
    parser.add_argument("--both-discovery-programs", action="store_true")
    parser.add_argument("--per-market-event-cap", type=int, choices=(128, 256, 512), default=512)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 300:
        raise ValueError("bounded capture required")
    asyncio.run(
        EarlyWatchPilot(
            Settings(),
            capacity=args.capacity,
            seconds=args.seconds,
            paired=args.paired,
            both_discovery_programs=args.both_discovery_programs,
            per_market_event_cap=args.per_market_event_cap,
        ).run_proofs()
    )
