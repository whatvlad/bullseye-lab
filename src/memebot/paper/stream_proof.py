"""Local transaction reuse with unchanged proof caps, checks and atomic refresh."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from memebot.paper.candidate_proof import CandidateProofService, Proof, ProofFailure, TrustDimension
from memebot.providers.solana.evidence_stream import EvidenceBuffer


class StreamFirstProofService(CandidateProofService):
    def __init__(self, *args: Any, buffer: EvidenceBuffer, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.buffer = buffer

    async def _read(self, proof: Proof, method: str, params: list[object], duty: str) -> Any:
        if method == "getTransaction" and isinstance(params[0], str):
            packet = self.buffer.get(params[0], datetime.now(UTC))
            if packet is not None and packet.mint == proof.candidate.mint:
                proof.costs["local_transaction_hits"] = (
                    proof.costs.get("local_transaction_hits", 0) + 1
                )
                proof.evidence.setdefault("stream_packets", []).append(
                    {
                        "signature": packet.signature,
                        "slot": packet.slot,
                        "index": packet.index,
                        "source": packet.source,
                        "received_at": packet.received_at.isoformat(),
                        "commitment": packet.commitment,
                    }
                )
                return deepcopy(packet.transaction)
        serial = self.buffer.gap_serial
        response = await super()._read(proof, method, params, duty)
        if duty == "reserve_refresh_reads" and serial != self.buffer.gap_serial:
            self.invalidate(
                "STREAM_GAP_DURING_REFRESH",
                proof.candidate.mint,
                dimensions=frozenset({TrustDimension.STREAM_COVERAGE}),
            )
        return response

    async def _prove(self, proof: Proof) -> None:
        anchor = self.buffer.get(proof.candidate.anchor_signature, datetime.now(UTC))
        since = (
            anchor.received_at
            if anchor
            else (proof.candidate.native_event_received_at or proof.candidate.detected_at)
        )
        if self.buffer.crosses_gap(since):
            raise ProofFailure("FAIL_CONTINUITY", "candidate crosses unproven stream gap")
        serial = self.buffer.gap_serial
        await super()._prove(proof)
        if serial != self.buffer.gap_serial:
            raise ProofFailure("FAIL_CONTINUITY", "stream gap during candidate proof")
        proof.evidence["stream_coverage"] = self.buffer.report()
        proof.evidence["history_fences_retained"] = True
        proof.evidence["execution_refresh_required"] = True

    async def execution_refresh(self, proof: Proof, *, decision_at: datetime) -> dict[str, Any]:
        serial = proof.evidence.get("stream_coverage", {}).get("gap_serial")
        if serial is not None and serial != self.buffer.gap_serial:
            self.invalidate(
                "STREAM_GAP_AFTER_PROOF",
                proof.candidate.mint,
                dimensions=frozenset({TrustDimension.STREAM_COVERAGE}),
            )
        return await super().execution_refresh(proof, decision_at=decision_at)
