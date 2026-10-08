import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from memebot.paper.candidate_proof import CandidateProofService, TrustDimension
from test_candidate_proof import Rpc, fixture


@pytest.mark.parametrize(
    "dimension",
    [
        TrustDimension.RESERVE_STATE,
        TrustDimension.IDENTITY,
        TrustDimension.CONFIG,
        TrustDimension.FEE_ROUTE,
    ],
)
@pytest.mark.asyncio
async def test_independent_current_dimensions_recover(dimension):
    candidate, accounts, tx, _, _ = fixture()
    service = CandidateProofService(Rpc(accounts, tx))
    proof = await service.prove(candidate)
    service.invalidate("SPECIFIC", candidate.mint, dimensions=frozenset({dimension}))
    assert not proof.trust[dimension] and proof.trust[TrustDimension.CONTINUITY]
    fresh = await service.execution_refresh(proof, decision_at=datetime.now(UTC))
    assert (
        fresh["execution_approved"] and fresh["revalidation_outcome"] == "FRESH_STATE_REVALIDATED"
    )


@pytest.mark.parametrize("dimension", [TrustDimension.CONTINUITY, TrustDimension.STREAM_COVERAGE])
@pytest.mark.asyncio
async def test_current_batch_never_recovers_history(dimension):
    candidate, accounts, tx, _, _ = fixture()
    service = CandidateProofService(Rpc(accounts, tx))
    proof = await service.prove(candidate)
    service.invalidate("HISTORY_LOST", candidate.mint, dimensions=frozenset({dimension}))
    fresh = await service.execution_refresh(proof, decision_at=datetime.now(UTC))
    assert not fresh["execution_approved"] and not proof.trust[dimension]
    assert fresh["revalidation_outcome"] == "STILL_BLOCKED_BY_UNPROVEN_CONTINUITY"
    assert proof.trust[TrustDimension.RESERVE_STATE]


@pytest.mark.asyncio
async def test_incompatible_lifecycle_never_restores_eligibility():
    candidate, accounts, tx, _, _ = fixture()
    service = CandidateProofService(Rpc(accounts, tx))
    proof = await service.prove(candidate)
    service.invalidate(
        "MIGRATION",
        candidate.mint,
        dimensions=frozenset({TrustDimension.LIFECYCLE}),
        incompatible=True,
    )
    fresh = await service.execution_refresh(proof, decision_at=datetime.now(UTC))
    assert not fresh["execution_approved"]
    assert fresh["revalidation_outcome"] == "INCOMPATIBLE_MUTATION_BLOCKED"
    repeated = await service.prove(candidate)
    assert repeated.reason == "KNOWN_INCOMPATIBLE_LIFECYCLE_OR_MODE"
    assert repeated.costs["total_rpc_requests"] == 0


@pytest.mark.asyncio
async def test_old_proof_fresh_state_has_separate_outcome():
    candidate, accounts, tx, _, _ = fixture()
    service = CandidateProofService(Rpc(accounts, tx))
    proof = await service.prove(candidate)
    proof.proof_completed_at = datetime.now(UTC) - timedelta(seconds=3)
    fresh = await service.execution_refresh(proof, decision_at=datetime.now(UTC))
    assert not fresh["execution_approved"]
    assert fresh["revalidation_outcome"] == "PROOF_STALE_BUT_CURRENT_STATE_VALID"


def test_provider_indexing_and_evidence_failure_classes_are_separate():
    from memebot.paper.candidate_proof import Proof, proof_failure_category

    candidate, _, _, _, _ = fixture()
    assert (
        proof_failure_category(Proof(candidate, status="FAIL_RPC", reason="rpc_-32015"))
        == "PROVIDER_RPC_RESPONSE_ERROR"
    )
    assert (
        proof_failure_category(Proof(candidate, status="FAIL_RPC", reason="http_429"))
        == "PROVIDER_TRANSPORT_OR_CAPACITY"
    )
    assert (
        proof_failure_category(
            Proof(
                candidate, status="FAIL_CONTINUITY", reason="direct anchor transaction unavailable"
            )
        )
        == "PROVIDER_TRANSACTION_AVAILABILITY"
    )
    assert (
        proof_failure_category(
            Proof(candidate, status="FAIL_CONTINUITY", reason="direct anchor event mismatch")
        )
        == "PROOF_EVIDENCE"
    )


@pytest.mark.asyncio
async def test_history_read_minimization_does_not_remove_fences():
    candidate, accounts, tx, _, _ = fixture()
    rpc = Rpc(accounts, tx)
    proof = await CandidateProofService(rpc).prove(candidate)
    assert proof.status == "PASS"
    assert [m for m, _ in rpc.calls].count("getTransaction") == 1
    assert [m for m, _ in rpc.calls].count("getSignaturesForAddress") == 4


@pytest.mark.asyncio
async def test_original_live_packet_config_only_and_unknown_recovery():
    # Replay historical bytes; synthetic receipt timing is explicitly test-only.
    packet = json.loads(
        (Path(__file__).parents[1] / "analysis/live_execution_proofs_run3.json").read_text()
    )
    row = next(p for p in packet["candidate_proofs"] if p["status"] == "PASS")
    from memebot.paper.candidate_proof import Candidate, Proof
    from memebot.providers.solana.pump import extract_anchor_events

    event = extract_anchor_events(
        row["evidence"]["direct_anchor_transaction"]["meta"]["logMessages"]
    )[0][1]
    candidate = Candidate(
        row["candidate"]["mint"],
        event,
        row["candidate"]["anchor_signature"],
        row["candidate"]["anchor_slot"],
        datetime.now(UTC),
        "EXACT",
        True,
        row["candidate"]["buy_budget_raw"],
        row["candidate"]["sell_quantity_raw"],
    )
    batch = row["evidence"]["execution_refresh_account_batch"]

    class PacketRpc:
        async def _call(self, method, params):
            assert method == "getMultipleAccounts"
            return batch["response"]

    for dimensions, approved in ((frozenset({TrustDimension.CONFIG}), True), (None, False)):
        service = CandidateProofService(PacketRpc())
        proof = Proof(
            candidate,
            status="PASS",
            proof_completed_at=datetime.now(UTC),
            reserve_slot=row["reserve_slot"],
            evidence=dict(row["evidence"]),
            trust=dict.fromkeys(TrustDimension, True),
        )
        service.lineage[candidate.mint] = proof
        service.receipts[candidate.mint] = proof
        service.invalidate("REPLAY", dimensions=dimensions)
        fresh = await service.execution_refresh(proof, decision_at=datetime.now(UTC))
        assert fresh["execution_approved"] == approved
        assert fresh["buy"] == row["evidence"]["buy"]


@pytest.mark.asyncio
async def test_complete_live_style_buy_pass_and_refresh_from_real_bytes():
    # Complete offline replay of a naturally serious v2 BUY; not a new live sample.
    from memebot.paper.candidate_proof import Candidate
    from memebot.providers.solana.pump import extract_anchor_events

    packet = json.loads(
        (Path(__file__).parents[1] / "analysis/live_execution_proofs_run1.json").read_text()
    )
    row = next(p for p in packet["candidate_proofs"] if p["evidence"].get("parity"))
    evidence = row["evidence"]
    tx = evidence["native_transactions"][0]
    event = extract_anchor_events(tx["meta"]["logMessages"])[0][1]
    raw_candidate = row["candidate"]
    candidate = Candidate(
        raw_candidate["mint"],
        event,
        raw_candidate["anchor_signature"],
        raw_candidate["anchor_slot"],
        datetime.now(UTC),
        "EXACT",
        True,
        raw_candidate["buy_budget_raw"],
        raw_candidate["sell_quantity_raw"],
    )
    batch = evidence["candidate_account_batch"]["response"]
    history = evidence["history_reads"]

    class PacketRpc:
        def __init__(self):
            self.history_index = 0

        async def _call(self, method, params):
            if method == "getTransaction":
                return tx
            if method == "getMultipleAccounts":
                return batch
            assert method == "getSignaturesForAddress"
            rows = history[self.history_index]["rows"]
            self.history_index += 1
            return rows

    service = CandidateProofService(PacketRpc())
    proof = await service.prove(candidate)
    assert proof.status == "PASS", proof.reason
    assert proof.evidence["parity"][0]["side"] == "buy"
    assert proof.evidence["parity"][0]["fee_destination_deltas"]["protocol_buyback"] == 532210
    fresh = await service.execution_refresh(proof, decision_at=datetime.now(UTC))
    assert fresh["execution_approved"]


def test_zero_quote_native_dust_is_observed_without_crashing_or_candidate():
    from memebot.core.config import Settings
    from memebot.research.candidate_proof_run import PassiveCandidateProof

    collector = PassiveCandidateProof(Settings())
    packet = json.loads(
        (Path(__file__).parents[1] / "analysis/cohort_execution_proofs.json").read_text()
    )
    from memebot.providers.solana.pump import extract_anchor_events

    logs = packet["stream"]["native_logs"]["current_log_messages"]
    event = extract_anchor_events(logs)[0][1]
    assert event.quote_amount == 0 and event.token_amount == 1
    collector.native_event(
        event, 452447000, {"current_event_id": "dust:0", "current_log_messages": logs}
    )
    assert collector.skips["unpriceable_native_event"] == 1
    assert not collector.attempted
