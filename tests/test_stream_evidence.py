from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from memebot.paper.candidate_proof import TrustDimension
from memebot.paper.stream_proof import StreamFirstProofService
from memebot.providers.solana.evidence_stream import (
    AccountEvidence,
    CoverageState,
    EvidenceBuffer,
    normalize_transaction,
)
from test_candidate_proof import Rpc, fixture


@pytest.mark.asyncio
async def test_gap_arriving_during_atomic_refresh_cannot_be_overwritten():
    candidate, accounts, tx, evidence = packet()
    buffer = EvidenceBuffer()
    buffer.add(evidence)
    rpc = Rpc(accounts, tx)
    service = StreamFirstProofService(rpc, buffer=buffer)
    proof = await service.prove(candidate)
    original = rpc._call

    async def interrupted(method, params):
        if method == "getMultipleAccounts":
            buffer.disconnect()
        return await original(method, params)

    rpc._call = interrupted
    fresh = await service.execution_refresh(proof, decision_at=datetime.now(UTC))
    assert not fresh["execution_approved"]
    assert not proof.trust[TrustDimension.STREAM_COVERAGE]


def test_out_of_order_account_update_and_retention_are_explicit():
    _, accounts, _, evidence = packet()
    buffer = EvidenceBuffer(seconds=1)
    buffer.add(evidence)
    address = evidence.curve
    update = AccountEvidence(
        address,
        100,
        accounts[address],
        evidence.received_at,
        "fixture",
        "confirmed",
        write_version=2,
    )
    buffer.add_account(update)
    buffer.add_account(replace(update, write_version=1))
    assert buffer.metrics["OUT_OF_ORDER_ACCOUNT"] == 1
    assert buffer.accounts[address].write_version == 2
    buffer.expire(evidence.received_at + timedelta(seconds=2))
    assert not buffer.accounts and buffer.account_bytes == 0


@pytest.mark.parametrize(
    "file,side",
    [("live_execution_proofs_run1.json", "buy"), ("live_execution_proofs_run3.json", "sell")],
)
@pytest.mark.asyncio
async def test_complete_historical_packet_replay_uses_local_metadata(file, side):
    """Real bytes, synthetic current receipt time: never counted as a live PASS."""
    import json
    from pathlib import Path

    from memebot.paper.candidate_proof import Candidate
    from memebot.providers.solana.pump import extract_anchor_events

    packet = json.loads((Path(__file__).parents[1] / "analysis" / file).read_text())
    row = next(p for p in packet["candidate_proofs"] if p["evidence"].get("parity"))
    retained = row["evidence"]
    tx = retained.get("direct_anchor_transaction") or retained["native_transactions"][0]
    raw = row["candidate"]
    event = next(
        e for _, e in extract_anchor_events(tx["meta"]["logMessages"]) if hasattr(e, "is_buy")
    )
    candidate = Candidate(
        raw["mint"],
        event,
        raw["anchor_signature"],
        raw["anchor_slot"],
        datetime.now(UTC),
        "EXACT",
        True,
        raw["buy_budget_raw"],
        raw["sell_quantity_raw"],
    )
    evidence = normalize_transaction(
        tx,
        slot=raw["anchor_slot"],
        signature=raw["anchor_signature"],
        index=None,
        source="historical_replay_not_live",
        commitment="confirmed",
        received_at=datetime.now(UTC),
    )
    assert evidence is not None
    buffer = EvidenceBuffer()
    buffer.add(evidence)
    batch = retained["candidate_account_batch"]["response"]

    class ReplayRpc:
        def __init__(self):
            self.calls = []
            self.index = 0

        async def _call(self, method, params):
            self.calls.append(method)
            assert method != "getTransaction"
            if method == "getMultipleAccounts":
                return batch
            rows = retained["history_reads"][self.index]["rows"]
            self.index += 1
            return rows

    rpc = ReplayRpc()
    service = StreamFirstProofService(rpc, buffer=buffer)
    proof = await service.prove(candidate)
    assert proof.status == "PASS", proof.reason
    assert proof.evidence["parity"][0]["side"] == side
    assert len(rpc.calls) == 5
    fresh = await service.execution_refresh(proof, decision_at=datetime.now(UTC))
    assert fresh["execution_approved"] and len(rpc.calls) == 6


def packet():
    candidate, accounts, tx, _, _ = fixture()
    tx["meta"]["fee"] = 0  # Fixture's existing parity assumes zero network fee.
    evidence = normalize_transaction(
        tx,
        slot=100,
        signature="anchor",
        index=1,
        source="test_complete_packet",
        commitment="confirmed",
        received_at=datetime.now(UTC),
    )
    assert evidence is not None
    return candidate, accounts, tx, evidence


@pytest.mark.asyncio
async def test_local_complete_transaction_sequence_reuses_native_packet_and_requires_refresh():
    candidate, accounts, _, evidence = packet()
    buffer = EvidenceBuffer()
    buffer.connect()
    buffer.add(evidence)
    rpc = Rpc(accounts, None)  # RPC cannot supply this already captured transaction.
    service = StreamFirstProofService(rpc, buffer=buffer)
    proof = await service.prove(candidate)
    assert proof.status == "PASS", proof.reason
    assert proof.costs["local_transaction_hits"] == 1
    assert not any(m == "getTransaction" for m, _ in rpc.calls)
    assert sum(m == "getSignaturesForAddress" for m, _ in rpc.calls) == 4
    assert proof.evidence["execution_refresh_required"] and proof.execution_refresh_at is None
    fresh = await service.execution_refresh(proof, decision_at=datetime.now(UTC))
    assert fresh["execution_approved"]
    assert sum(m == "getMultipleAccounts" for m, _ in rpc.calls) == 2


@pytest.mark.asyncio
async def test_missing_local_evidence_only_falls_back_to_existing_rpc_policy():
    candidate, accounts, tx, _ = packet()
    rpc = Rpc(accounts, tx)
    proof = await StreamFirstProofService(rpc, buffer=EvidenceBuffer()).prove(candidate)
    assert proof.status == "PASS", proof.reason
    assert sum(m == "getTransaction" for m, _ in rpc.calls) == 1
    assert proof.costs["total_rpc_requests"] == 6


@pytest.mark.parametrize("cause", ["disconnect", "slot", "restart", "out_of_order", "overflow"])
@pytest.mark.asyncio
async def test_candidate_crossing_gap_rejects_without_rpc(cause):
    candidate, accounts, tx, evidence = packet()
    buffer = EvidenceBuffer(max_events=1)
    buffer.connect()
    buffer.add(evidence)
    if cause == "disconnect":
        buffer.disconnect()
    elif cause == "slot":
        buffer.heartbeat(100)
        buffer.heartbeat(102)
    elif cause == "restart":
        buffer.connect()
        assert buffer.state == CoverageState.RESUMED_WITH_GAP
    elif cause == "out_of_order":
        buffer.add(replace(evidence, signature="earlier", index=0))
    else:
        buffer.add(replace(evidence, signature="next", slot=101))
    rpc = Rpc(accounts, tx)
    proof = await StreamFirstProofService(rpc, buffer=buffer).prove(candidate)
    assert proof.status == "FAIL_CONTINUITY" and not rpc.calls


def test_duplicate_is_idempotent_conflicting_duplicate_exposes_gap():
    _, _, _, evidence = packet()
    buffer = EvidenceBuffer()
    buffer.add(evidence)
    buffer.add(evidence)
    assert len(buffer.items) == 1 and buffer.metrics["DUPLICATE"] == 1
    buffer.add(replace(evidence, slot=101))
    assert buffer.state == CoverageState.GAP_DETECTED


def test_buffer_expiration_and_filtered_slot_jump_never_claim_coverage():
    _, _, _, evidence = packet()
    buffer = EvidenceBuffer(seconds=1)
    buffer.connect()
    buffer.add(evidence)
    buffer.add(replace(evidence, signature="later", slot=105))
    assert buffer.gap_serial == 0  # A filtered stream can legitimately skip slots.
    assert not buffer.report()["complete_for_window"]
    assert buffer.get("anchor", evidence.received_at + timedelta(seconds=2)) is None


@pytest.mark.parametrize("kind", ["stream_gap", "invalidation"])
@pytest.mark.asyncio
async def test_stream_evidence_cannot_authorize_execution_after_invalidation(kind):
    candidate, accounts, tx, evidence = packet()
    buffer = EvidenceBuffer()
    buffer.add(evidence)
    rpc = Rpc(accounts, tx)
    service = StreamFirstProofService(rpc, buffer=buffer)
    proof = await service.prove(candidate)
    assert proof.status == "PASS"
    if kind == "stream_gap":
        buffer.disconnect()
    else:
        service.invalidate(
            "UNKNOWN_MUTATION", candidate.mint, dimensions=frozenset({TrustDimension.CONTINUITY})
        )
    fresh = await service.execution_refresh(proof, decision_at=datetime.now(UTC))
    assert not fresh["execution_approved"]
    assert fresh["revalidation_outcome"] == "STILL_BLOCKED_BY_UNPROVEN_CONTINUITY"


@pytest.mark.parametrize("missing", ["innerInstructions", "preBalances", "postTokenBalances"])
def test_incomplete_packet_never_silently_becomes_execution_evidence(missing):
    _, _, tx, _ = packet()
    tx["meta"].pop(missing)
    assert (
        normalize_transaction(
            tx,
            slot=100,
            signature="anchor",
            index=None,
            source="fixture",
            commitment="confirmed",
            received_at=datetime.now(UTC),
        )
        is None
    )
