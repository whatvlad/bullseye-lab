"""Stored divergences stay forensic facts; prospective eligibility rejects them."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from memebot.paper.candidate_proof import CandidateProofService
from test_candidate_proof import Rpc, fixture

REPORT = json.loads(
    (Path(__file__).parents[1] / "analysis/standard_pumpfun_validation.json").read_text()
)


@pytest.mark.parametrize(
    "case", REPORT["standard_divergences"], ids=lambda case: case["signature"][:8]
)
@pytest.mark.asyncio
async def test_retained_divergence_cannot_earn_proof_reads(case):
    assert not case["causality_proven"]
    assert set(case["delta"]) == {"quote", "token", "virtual_quote", "virtual_token"}
    candidate, accounts, tx, _, _ = fixture()
    rpc = Rpc(accounts, tx)
    proof = await CandidateProofService(rpc).prove(
        replace(
            candidate,
            arithmetic_status="EXACT",
            known_divergence=True,
            quality_evidence={"retained_forensic_case": case},
        )
    )
    assert proof.status != "PASS" and proof.reason == "CONTINUITY_DIVERGED"
    assert not rpc.calls


@pytest.mark.asyncio
async def test_unexplained_physical_reserve_mutation_fails_proof():
    candidate, accounts, tx, _, _ = fixture()
    # Native price arithmetic still matches; physical vault has an unexplained
    # mutation, like the missed-capture/transfer class the old cases could reflect.
    tx["meta"]["postTokenBalances"][0]["uiTokenAmount"]["amount"] = str(
        int(tx["meta"]["postTokenBalances"][0]["uiTokenAmount"]["amount"]) + 1
    )
    proof = await CandidateProofService(Rpc(accounts, tx)).prove(candidate)
    assert proof.status == "FAIL_CONTINUITY"
