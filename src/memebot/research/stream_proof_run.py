"""Bounded passive paired pilot on configured endpoints, never orders/calibration."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from time import monotonic
from typing import Any

import websockets

from memebot.core.config import Settings
from memebot.paper.candidate_proof import TrustDimension
from memebot.paper.stream_proof import StreamFirstProofService
from memebot.providers.solana.canonical import FEE_PROGRAM, config_addresses
from memebot.providers.solana.evidence_stream import EvidenceBuffer
from memebot.providers.solana.helius_evidence import HeliusTransactionEvidenceStream
from memebot.providers.solana.pump import extract_anchor_events
from memebot.providers.solana.pump_idl import PUMP_PROGRAM_ID, PumpComplete, PumpMigration
from memebot.research.candidate_proof_run import ROOT, PassiveCandidateProof


class StreamProofPilot(PassiveCandidateProof):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.seconds = 300
        self.candidate_cap = 4  # Eight total paired proof attempts, unchanged 96-read capture cap.
        self.output_stem = "stream_pilot"
        self.buffer = EvidenceBuffer()
        self.local_service = StreamFirstProofService(self.rpc, buffer=self.buffer)
        self.pairs: list[dict[str, Any]] = []
        self.meter: dict[str, Any] = {
            "decoded_application_bytes": 0,
            "compressed_bytes": None,
            "logs": 0,
            "account_updates": 0,
            "slot_updates": 0,
            "full_transactions": 0,
            "errors": [],
        }
        self.started_monotonic = monotonic()
        self.full_adapter = HeliusTransactionEvidenceStream(str(settings.solana_rpc_ws_url))

    def native_transaction(
        self, signature: str | None, slot: int | None, state: dict[str, Any]
    ) -> None:
        prior = len(self.service.invalidations)
        super().native_transaction(signature, slot, state)
        for item in self.service.invalidations[prior:]:
            self.local_service.invalidate(
                item["reason"],
                None if item["mint"] == "ALL" else item["mint"],
                dimensions=frozenset(TrustDimension(d) for d in item["dimensions"]),
                incompatible=item["incompatible"],
                source=item["source"],
            )

    def native_event(self, event: Any, slot: int | None, state: dict[str, Any]) -> None:
        super().native_event(event, slot, state)
        if isinstance(event, (PumpMigration, PumpComplete)):
            self.buffer.exclude(event.mint)
            self.local_service.invalidate(
                "MIGRATION_OR_COMPLETION",
                event.mint,
                dimensions=frozenset({TrustDimension.LIFECYCLE}),
                incompatible=True,
            )

    async def full_stream(self) -> None:
        adapter = self.full_adapter
        try:
            async for evidence in adapter.transactions():
                from memebot.providers.solana.evidence_stream import TransactionEvidence

                if isinstance(evidence, TransactionEvidence):
                    self.buffer.add(evidence)
                    self.meter["full_transactions"] += 1
        except Exception as error:
            self.meter["full_stream_error"] = {
                "type": type(error).__name__,
                "code": adapter.subscription_error_code,
            }
        finally:
            self.meter["full_stream_bytes"] = adapter.bytes_received

    async def native_stream(self) -> None:
        state = self.stream_state("metered_native_logs")
        self.buffer.connect()
        full = asyncio.create_task(self.full_stream())
        try:
            async with websockets.connect(
                str(self.settings.solana_rpc_ws_url),
                open_timeout=8,
                max_queue=64,
                max_size=2_000_000,
            ) as ws:
                requests = (
                    [
                        ("logsSubscribe", [{"mentions": [p]}, {"commitment": "confirmed"}])
                        for p in (PUMP_PROGRAM_ID, FEE_PROGRAM)
                    ]
                    + [("slotSubscribe", [])]
                    + [
                        ("accountSubscribe", [a, {"commitment": "confirmed", "encoding": "base64"}])
                        for a in [config_addresses()[k][0] for k in ("pump_global", "pump_fee")]
                    ]
                )
                for idx, (method, params) in enumerate(requests, 1):
                    await ws.send(
                        json.dumps(
                            {"jsonrpc": "2.0", "id": idx, "method": method, "params": params}
                        )
                    )
                async for raw in ws:
                    self.meter["decoded_application_bytes"] += len(
                        raw.encode() if isinstance(raw, str) else raw
                    )
                    state["messages"] += 1
                    if state["messages"] > self.native_message_cap or (
                        self.meter["decoded_application_bytes"] + self.full_adapter.bytes_received
                        > 32_000_000
                    ):
                        self.meter["errors"].append("CAPTURE_LIMIT")
                        self.buffer.gap("CAPTURE_LIMIT")
                        break
                    message = json.loads(raw)
                    if "error" in message:
                        self.meter["errors"].append({"code": message["error"].get("code")})
                        self.buffer.gap("SUBSCRIPTION_REJECTED")
                        continue
                    method = message.get("method")
                    result = message.get("params", {}).get("result", {})
                    if method == "slotNotification":
                        self.meter["slot_updates"] += 1
                        self.buffer.heartbeat(result["slot"])
                    elif method == "accountNotification":
                        self.meter["account_updates"] += 1
                        # These config-only notifications are observational. They
                        # are not an atomic bank or a proof of every market write.
                    elif method == "logsNotification":
                        self.meter["logs"] += 1
                        value = result.get("value", {})
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
        finally:
            full.cancel()
            await asyncio.gather(full, return_exceptions=True)
            self.buffer.disconnect()
            for service in (self.service, self.local_service):
                service.invalidate(
                    "PILOT_STREAM_ENDED", dimensions=frozenset({TrustDimension.STREAM_COVERAGE})
                )

    async def proof_worker(self) -> None:
        while True:
            candidate = await self.candidate_queue.get()
            try:
                pair: dict[str, Any] = {
                    "signature": candidate.anchor_signature,
                    "mint": candidate.mint,
                    "comparison": "sequential independent bank reads; not atomic A/B",
                }
                for name, service in (("OLD", self.service), ("NEW", self.local_service)):
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
                print(
                    json.dumps(
                        {
                            "paired": len(self.pairs),
                            "OLD": pair["OLD"]["status"],
                            "NEW": pair["NEW"]["status"],
                        }
                    ),
                    flush=True,
                )
            finally:
                self.candidate_queue.task_done()

    async def run_proofs(self) -> None:
        await super().run_proofs()
        self.meter["duration_seconds"] = monotonic() - self.started_monotonic
        report = {
            "runner": "BLOCKED",
            "calibration_started": False,
            "orders": 0,
            "pairs": self.pairs,
            "coverage": self.buffer.report(),
            "meter": self.meter,
            "rpc_reads": self.rpc.budget.used,
            "launches": len(self.launches),
            "standard_launches": sum(v is False for v in self.launch_modes.values()),
        }
        (ROOT / "analysis/stream_pilot.json").write_text(
            json.dumps(report, indent=2, default=str) + "\n"
        )


if __name__ == "__main__":
    asyncio.run(StreamProofPilot(Settings()).run_proofs())
