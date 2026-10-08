"""Read-only standard/simple cohort pilot. Existing proof logic and RPC caps."""

from __future__ import annotations

import asyncio
import base64
import json
from collections import Counter
from datetime import UTC, datetime
from time import monotonic
from typing import Any
from urllib.parse import urlsplit

import websockets

from memebot.core.config import Settings
from memebot.providers.solana.alchemy_evidence import AlchemyTransactionEvidenceStream
from memebot.providers.solana.canonical import FEE_PROGRAM, config_addresses
from memebot.providers.solana.evidence_stream import AccountEvidence, TransactionEvidence
from memebot.providers.solana.idl_schema import decode_record
from memebot.providers.solana.pump import extract_anchor_events
from memebot.providers.solana.pump_idl import (
    PUMP_PROGRAM_ID,
    PumpComplete,
    PumpCreate,
    PumpMigration,
    PumpTrade,
)
from memebot.providers.solana.watch_cohort import WatchCohort
from memebot.research.candidate_proof_run import ROOT
from memebot.research.stream_proof_run import StreamProofPilot


def simple_fee_event(logs: list[str], mint: str) -> bool:
    records = []
    for line in logs:
        if not line.startswith("Program data: "):
            continue
        try:
            name, fields = decode_record(
                PUMP_PROGRAM_ID, base64.b64decode(line[14:], validate=True), collection="events"
            )
            if name == "TradeEvent" and fields["mint"] == mint:
                records.append(fields)
        except ValueError:
            continue
    return len(records) == 1 and not any(
        records[0].get(key, 0) for key in ("cashback", "holder_rewards", "shareholders")
    )


class FilteredStreamPilot(StreamProofPilot):
    def __init__(
        self,
        settings: Settings,
        *,
        total_rpc_cap: int = 96,
        output_stem: str = "filtered_stream_pilot",
    ) -> None:
        super().__init__(settings)
        self.seconds = 300
        self.candidate_cap = 20
        if not 0 < total_rpc_cap <= self.rpc.budget.limit:
            raise ValueError("filtered pilot cannot increase the existing RPC budget")
        self.rpc.budget.limit = total_rpc_cap
        self.output_stem = output_stem
        self.discovery_programs: tuple[str, ...] = (PUMP_PROGRAM_ID, FEE_PROGRAM)
        self.cohort = WatchCohort()
        self.cashback: set[str] = set()
        self.ever_watched: set[str] = set()
        self.dead_candidates: set[str] = set()
        self.config_keys = tuple(config_addresses()[k][0] for k in ("pump_global", "pump_fee"))
        self.raw_archive_bytes = 0
        packet_name = (
            "filtered_stream_packets"
            if output_stem == "filtered_stream_pilot"
            else f"{output_stem}_packets"
        )
        self.packet_file = (ROOT / f"analysis/{packet_name}.jsonl").open("w")
        self.executed_stream = AlchemyTransactionEvidenceStream(
            urlsplit(str(settings.solana_rpc_http_url)).path.rsplit("/", 1)[-1],
            on_packet=self.archive_packet,
        )
        self.local_hits_before_proof = 0
        self.packet_by_market: Counter[str] = Counter()
        self.started_at = datetime.now(UTC)

    def archive_packet(self, packet: dict[str, Any]) -> None:
        text = json.dumps(packet) + "\n"
        size = len(text.encode())
        if self.raw_archive_bytes + size > 128_000_000:
            raise ValueError("raw_packet_archive_cap")
        self.packet_file.write(text)
        self.raw_archive_bytes += size

    def sync_filter(self) -> None:
        self.cohort.expire(datetime.now(UTC))
        self.executed_stream.update_filter(tuple(self.cohort.accounts()), self.config_keys)

    def native_event(self, event: Any, slot: int | None, state: dict[str, Any]) -> None:
        if isinstance(event, PumpCreate) and event.is_cashback_enabled:
            self.cashback.add(event.mint)
        if isinstance(event, PumpTrade):
            simple = event.mint not in self.cashback and simple_fee_event(
                state["current_log_messages"], event.mint
            )
            if not simple:
                self.cohort.remove(event.mint, "UNSUPPORTED_FEE_ROUTE", datetime.now(UTC))
                self.skips["unsupported_simple_fee_route"] = (
                    self.skips.get("unsupported_simple_fee_route", 0) + 1
                )
                self.sync_filter()
                return  # Cheap exclusion, no proof, enrichment or RPC.
        before = len(self.rows)
        super().native_event(event, slot, state)
        if isinstance(event, (PumpMigration, PumpComplete)):
            self.cohort.remove(event.mint, "MIGRATED_OR_COMPLETE", datetime.now(UTC))
        elif isinstance(event, PumpTrade):
            row = self.rows[-1] if len(self.rows) > before else None
            if event.mint not in self.created or event.mint in self.dead_candidates:
                self.sync_filter()
                return  # Watch only observed launches that can qualify without paid age lookup.
            if self.cohort.observe(
                event.mint,
                now=datetime.now(UTC),
                standard=event.is_mayhem_mode is False,
                quote_mint=event.quote_mint,
                continuity=row["arithmetic"]["continuity_status"] if row else "UNKNOWN",
                multi_event=row["multi_event"] if row else True,
                migrated=event.mint in self.migrated,
                cashback=event.mint in self.cashback,
                supported_fee_route=True,
            ):
                self.ever_watched.add(event.mint)
        self.sync_filter()

    async def full_stream(self) -> None:
        try:
            async for evidence in self.executed_stream.transactions():
                if isinstance(evidence, TransactionEvidence):
                    if evidence.mint in self.cohort.markets:
                        self.buffer.add(evidence)
                        self.packet_by_market[evidence.mint] += 1
                elif isinstance(evidence, AccountEvidence):
                    self.buffer.add_account(evidence)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self.meter["full_stream_error"] = {
                "type": type(error).__name__,
                "provider": self.executed_stream.failure,
            }
            self.buffer.gap("FULL_STREAM_FAILED")

    async def expire_watches(self) -> None:
        while True:
            await asyncio.sleep(1)
            self.sync_filter()

    async def native_stream(self) -> None:
        state = self.stream_state("filtered_pilot_native_discovery")
        full = asyncio.create_task(self.full_stream())
        expiry = asyncio.create_task(self.expire_watches())
        # Demonstrate decoded Ping + Subscribe pong before broader discovery.
        for _ in range(80):
            if self.executed_stream.metrics["subscription_pongs"]:
                break
            if full.done():
                break
            await asyncio.sleep(0.1)
        if not self.executed_stream.metrics["subscription_pongs"]:
            full.cancel()
            expiry.cancel()
            await asyncio.gather(full, expiry, return_exceptions=True)
            self.meter["errors"].append("NO_SUBSCRIBE_PONG")
            return
        self.buffer.connect()
        try:
            async with websockets.connect(
                str(self.settings.solana_rpc_ws_url),
                open_timeout=8,
                max_queue=64,
                max_size=2_000_000,
            ) as ws:
                for idx, program in enumerate(self.discovery_programs, 1):
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
                async for raw in ws:
                    self.meter["decoded_application_bytes"] += len(
                        raw.encode() if isinstance(raw, str) else raw
                    )
                    state["messages"] += 1
                    if (
                        state["messages"] > self.native_message_cap
                        or self.meter["decoded_application_bytes"] > 384_000_000
                    ):
                        self.meter["errors"].append("DISCOVERY_CAPTURE_CAP")
                        self.buffer.gap("DISCOVERY_CAPTURE_CAP")
                        break
                    if full.done():
                        self.meter["errors"].append("FULL_STREAM_ENDED")
                        break
                    if (
                        len(self.pairs) >= self.candidate_cap
                        or self.rpc.budget.used >= self.rpc.budget.limit
                    ):
                        break
                    message = json.loads(raw)
                    self.observe_discovery(raw, message)
                    if "error" in message:
                        self.meter["errors"].append({"code": message["error"].get("code")})
                        self.buffer.gap("DISCOVERY_SUBSCRIPTION_REJECTED")
                        break
                    if message.get("method") != "logsNotification":
                        continue
                    self.meter["logs"] += 1
                    result = message["params"]["result"]
                    value = result["value"]
                    if value.get("err") is not None:
                        continue
                    slot = result.get("context", {}).get("slot")
                    state["current_log_messages"] = value.get("logs", [])
                    self.native_transaction(value.get("signature"), slot, state)
                    for ordinal, (_, event) in enumerate(
                        extract_anchor_events(state["current_log_messages"])
                    ):
                        key = f"{value.get('signature')}:{ordinal}"
                        if key in self.seen:
                            continue
                        self.seen.add(key)
                        state["current_event_id"] = key
                        self.native_event(event, slot, state)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self.meter["errors"].append({"type": type(error).__name__})
            self.buffer.gap("DISCOVERY_STREAM_FAILED")
        finally:
            # Finish queued proof comparisons while both evidence streams remain
            # live; forced teardown would invalidate an in-flight proof.
            try:
                await asyncio.wait_for(self.candidate_queue.join(), 15)
            except TimeoutError:
                self.buffer.gap("PROOF_DRAIN_TIMEOUT")
            full.cancel()
            expiry.cancel()
            await asyncio.gather(full, expiry, return_exceptions=True)
            self.buffer.disconnect()

    def observe_discovery(self, raw: str | bytes, message: dict[str, Any]) -> None:
        """Optional research metering hook; no execution or qualification changes."""

    async def proof_worker(self) -> None:
        while True:
            candidate = await self.candidate_queue.get()
            try:
                pair: dict[str, Any] = {
                    "mint": candidate.mint,
                    "signature": candidate.anchor_signature,
                    "comparison": "sequential independent bank reads, unchanged proof rules",
                    "local_before_retrospective": self.buffer.get(
                        candidate.anchor_signature, datetime.now(UTC)
                    )
                    is not None,
                }
                for name, service in (("OLD", self.service), ("NEW", self.local_service)):
                    if name == "NEW":
                        pair["local_before_stream_proof"] = (
                            self.buffer.get(candidate.anchor_signature, datetime.now(UTC))
                            is not None
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
                self.pairs.append(pair)
                if pair["NEW"]["status"] != "PASS":
                    self.dead_candidates.add(candidate.mint)
                    self.cohort.remove(candidate.mint, "CANDIDATE_PROOF_FAILED", datetime.now(UTC))
                    self.sync_filter()
                print(
                    json.dumps(
                        {
                            "paired": len(self.pairs),
                            "OLD": pair["OLD"]["status"],
                            "NEW": pair["NEW"]["status"],
                            "local": pair["local_before_stream_proof"],
                        }
                    ),
                    flush=True,
                )
            finally:
                self.candidate_queue.task_done()

    async def run_proofs(self) -> None:
        # Skip StreamProofPilot's historical report writer; preserve prior pilot.
        from memebot.research.candidate_proof_run import PassiveCandidateProof

        try:
            await PassiveCandidateProof.run_proofs(self)
        finally:
            self.packet_file.close()
        duration = monotonic() - self.started_monotonic
        report = {
            "started_at": self.started_at.isoformat(),
            "finished_at": datetime.now(UTC).isoformat(),
            "runner": "BLOCKED",
            "calibration_started": False,
            "orders": 0,
            "provider": "alchemy_yellowstone_PAYG",
            "pairs": self.pairs,
            "coverage": self.buffer.report(),
            "transport": self.executed_stream.report(),
            "meter": self.meter,
            "elapsed_seconds": duration,
            "launches": len(self.launches),
            "standard_launches": sum(v is False for v in self.launch_modes.values()),
            "watched_markets": len(self.ever_watched),
            "watch_removals": self.cohort.removals,
            "packets_by_market": dict(self.packet_by_market),
            "raw_archive_bytes": self.raw_archive_bytes,
            "local_evidence_before_proof": self.local_hits_before_proof,
            "rpc_reads": self.rpc.budget.used,
            "total_rpc_cap": self.rpc.budget.limit,
            "proof_rules": "unchanged; four history fences and final atomic refresh retained",
        }
        (ROOT / f"analysis/{self.output_stem}.json").write_text(
            json.dumps(report, indent=2, default=str) + "\n"
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--rpc-cap", type=int, default=96)
    args = parser.parse_args()
    asyncio.run(FilteredStreamPilot(Settings(), total_rpc_cap=args.rpc_cap).run_proofs())
