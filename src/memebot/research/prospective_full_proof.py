"""One bounded passive capture, with stage audit; no proof/qualification changes."""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from memebot.core.config import Settings
from memebot.paper.candidate_proof import Proof
from memebot.paper.stream_proof import StreamFirstProofService
from memebot.paper.validation_gate import CRITICAL_FILES
from memebot.research.candidate_proof_run import ROOT
from memebot.research.early_watch_run import EarlyWatchPilot


class AuditedStreamProof(StreamFirstProofService):
    async def _read(self, proof: Proof, method: str, params: list[object], duty: str) -> Any:
        record: dict[str, Any] = {
            "method": method,
            "params": params,
            "duty": duty,
            "request_at": datetime.now(UTC).isoformat(),
            "proof_rpc_count_before": proof.costs.get("total_rpc_requests", 0),
        }
        proof.evidence.setdefault("stage_responses", []).append(record)
        try:
            response = await super()._read(proof, method, params, duty)
            record["response"] = response
            record["status"] = "RECEIVED"
            return response
        except Exception as error:
            record["status"] = "ERROR"
            record["error_type"] = type(error).__name__
            record["error_code"] = getattr(error, "code", None)
            raise
        finally:
            record["received_at"] = datetime.now(UTC).isoformat()
            record["proof_rpc_count_after"] = proof.costs.get("total_rpc_requests", 0)
            record["availability"] = "AVAILABLE_AT_PROOF_TIME"


class ProspectiveFullProofPilot(EarlyWatchPilot):
    def __init__(self, settings: Settings) -> None:
        super().__init__(
            settings,
            capacity=32,
            seconds=300,
            paired=False,
            per_market_event_cap=512,
            output_stem="prospective_capture",
        )
        self.local_service = AuditedStreamProof(self.rpc, buffer=self.buffer)
        self.audit: list[dict[str, Any]] = []
        self.code_hashes = {
            p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
            for p in (*CRITICAL_FILES, "src/memebot/research/prospective_full_proof.py")
        }

    async def proof_worker(self) -> None:
        while True:
            candidate = await self.candidate_queue.get()
            try:
                watch = self.early.serious(candidate.mint, candidate.detected_at)
                self.serious_records.append(watch)
                at = datetime.now(UTC)
                local = self.buffer.get(candidate.anchor_signature, at)
                certificate = self.certificate(candidate, at)
                proof = await self.local_service.prove(candidate)
                self.proofs.append(proof)
                before = proof.report()
                before = json.loads(json.dumps(before, default=str))
                refresh: dict[str, Any] = {"attempted": False}
                if proof.status == "PASS":
                    refresh = {
                        "attempted": True,
                        "request_at": datetime.now(UTC).isoformat(),
                        "rpc_count_before": self.rpc.budget.used,
                    }
                    try:
                        refresh["result"] = await self.local_service.execution_refresh(
                            proof, decision_at=datetime.now(UTC)
                        )
                    except Exception as error:
                        refresh["error_type"] = type(error).__name__
                        refresh["reason"] = str(error) if isinstance(error, ValueError) else None
                    finally:
                        refresh["received_at"] = datetime.now(UTC).isoformat()
                        refresh["rpc_count_after"] = self.rpc.budget.used
                record = {
                    "mint": candidate.mint,
                    "signature": candidate.anchor_signature,
                    "window_certificate": certificate,
                    "early_watch": watch,
                    "local_before_stream_proof": local is not None,
                    "local_anchor": (
                        {
                            "index": local.index,
                            "slot": local.slot,
                            "received_at": local.received_at.isoformat(),
                            "transaction": local.transaction,
                        }
                        if local
                        else None
                    ),
                    "proof_before_refresh": before,
                    "refresh": refresh,
                    "NEW": proof.report(),
                    "full_pass": proof.status == "PASS"
                    and refresh.get("result", {}).get("execution_approved") is True,
                }
                self.audit.append(record)
                self.pairs.append(record)
                self.local_hits_before_proof += int(local is not None)
                # Preserve unchanged watch lifetime; late packets remain in the raw archive.
                if proof.status != "PASS":
                    self.early.touch(candidate.mint, datetime.now(UTC), favorable=False)
                with (ROOT / "analysis/prospective_candidate_stages.jsonl").open("a") as file:
                    file.write(json.dumps(record, default=str) + "\n")
                print(
                    json.dumps(
                        {
                            "serious": len(self.audit),
                            "side": "BUY" if candidate.anchor.is_buy else "SELL",
                            "proof": proof.status,
                            "reason": proof.reason,
                            "full_pass": record["full_pass"],
                            "rpc_used": self.rpc.budget.used,
                        }
                    ),
                    flush=True,
                )
            finally:
                self.candidate_queue.task_done()

    async def run_proofs(self) -> None:
        if (ROOT / "analysis/prospective_candidate_stages.jsonl").exists():
            raise ValueError("prospective archive already exists; do not overwrite evidence")
        await super().run_proofs()
        payload = json.loads((ROOT / "analysis/prospective_capture.json").read_text())
        payload.update(
            candidate_stages=self.audit,
            proof_code_sha256=self.code_hashes,
            actual_policy=self.local_service.policy.__dict__,
            mode="PASSIVE_NO_ORDERS_NO_CALIBRATION",
            live_trading_enabled=False,
        )
        (ROOT / "analysis/prospective_full_proofs.json").write_text(
            json.dumps(payload, indent=2, default=str) + "\n"
        )


if __name__ == "__main__":
    asyncio.run(ProspectiveFullProofPilot(Settings()).run_proofs())
