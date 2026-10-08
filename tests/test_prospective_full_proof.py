"""Audit instrumentation retains attempted proof responses without altering verdicts."""

from datetime import UTC, datetime

import pytest

from memebot.providers.solana.evidence_stream import EvidenceBuffer
from memebot.research.prospective_full_proof import AuditedStreamProof
from test_candidate_proof import Rpc
from test_stream_evidence import packet


@pytest.mark.asyncio
async def test_audit_retains_local_anchor_four_fences_bank_and_refresh():
    candidate, accounts, tx, evidence = packet()
    buffer = EvidenceBuffer()
    buffer.add(evidence)
    service = AuditedStreamProof(Rpc(accounts, tx), buffer=buffer)
    proof = await service.prove(candidate)
    assert proof.status == "PASS", proof.reason
    records = proof.evidence["stage_responses"]
    assert len(records) == 6
    assert records[0]["method"] == "getTransaction"
    assert records[0]["proof_rpc_count_before"] == records[0]["proof_rpc_count_after"] == 0
    assert records[0]["response"] == tx
    assert sum(r["method"] == "getSignaturesForAddress" for r in records) == 4
    assert all(r["status"] == "RECEIVED" and r["response"] is not None for r in records)
    refreshed = await service.execution_refresh(proof, decision_at=datetime.now(UTC))
    assert refreshed["execution_approved"]
    assert records[-1]["duty"] == "reserve_refresh_reads"
    assert records[-1]["response"]["context"]["slot"] == 101


@pytest.mark.asyncio
async def test_audit_keeps_error_context_and_does_not_fetch_after_failure():
    candidate, accounts, tx, evidence = packet()
    buffer = EvidenceBuffer()
    buffer.add(evidence)
    rpc = Rpc(accounts, tx)

    async def failing(method, params):
        raise RuntimeError("synthetic provider failure")

    rpc._call = failing
    proof = await AuditedStreamProof(rpc, buffer=buffer).prove(candidate)
    assert proof.status != "PASS"
    records = proof.evidence["stage_responses"]
    assert len(records) == 2
    assert records[-1]["status"] == "ERROR"
    assert records[-1]["error_type"] == "RuntimeError"
    assert "received_at" in records[-1]
    assert "response" not in records[-1]
