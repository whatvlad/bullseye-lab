import base64
import json
from dataclasses import replace
from pathlib import Path

import pytest

from memebot.paper.candidate_proof import CandidateProofService, validate_transaction_parity
from memebot.providers.solana.pump import extract_anchor_events
from memebot.providers.solana.pump_idl import PUMP_PROGRAM_ID, PumpTrade
from test_candidate_proof import CURVE, Rpc, fixture, record


@pytest.mark.asyncio
async def test_known_anchor_with_lagging_history_has_exact_bank_proof():
    candidate, accounts, tx, _, _ = fixture()
    rpc = Rpc(accounts, tx)
    original = rpc._call

    async def lagging(method, params):
        if method == "getSignaturesForAddress":
            rpc.calls.append((method, params))
            return [{"signature": "predecessor", "slot": 99, "err": None}]
        return await original(method, params)

    rpc._call = lagging
    proof = await CandidateProofService(rpc).prove(candidate)
    assert proof.status == "PASS", proof.reason
    assert rpc.calls[0][0] == "getTransaction"
    assert rpc.calls[0][1][0] == "anchor"
    assert not proof.evidence["history_anchor_visible"]
    assert sum(method == "getTransaction" for method, _ in rpc.calls) == 1


@pytest.mark.parametrize("mutation", ["unavailable", "slot", "signature", "payload"])
@pytest.mark.asyncio
async def test_bad_direct_anchor_never_passes(mutation):
    candidate, accounts, tx, _, _ = fixture()
    if mutation == "unavailable":
        tx = None
    elif mutation == "slot":
        tx["slot"] = 99
    elif mutation == "signature":
        tx["transaction"]["signatures"] = ["other"]
    else:
        candidate = replace(candidate, anchor=replace(candidate.anchor, token_amount=1))
    proof = await CandidateProofService(Rpc(accounts, tx)).prove(candidate)
    assert proof.status == "FAIL_CONTINUITY", proof.reason


@pytest.mark.parametrize("branch", ["is_cashback_coin", "is_holder_reward"])
@pytest.mark.asyncio
async def test_complex_route_is_explicitly_rejected(branch):
    candidate, accounts, tx, _, _ = fixture()
    from memebot.providers.solana.bootstrap import decode_config

    fields, _ = decode_config(
        PUMP_PROGRAM_ID, base64.b64decode(accounts[CURVE]["data"][0]), "BondingCurve"
    )
    fields[branch] = True
    accounts[CURVE]["data"][0] = base64.b64encode(
        record(PUMP_PROGRAM_ID, "BondingCurve", fields)
    ).decode()
    proof = await CandidateProofService(Rpc(accounts, tx)).prove(candidate)
    assert proof.status == "FAIL_FEE"
    assert proof.evidence["fee_route_class"] == "STANDARD_COMPLEX_FEE_ROUTE"


def test_retained_live_integer_buy_and_protocol_split_parity():
    packet = json.loads(
        (Path(__file__).parents[1] / "analysis/live_execution_proofs_run1.json").read_text()
    )
    proof = next(p for p in packet["candidate_proofs"] if p["evidence"].get("parity"))
    bundle = proof["evidence"]
    tx = bundle["native_transactions"][0]
    event = next(
        e for _, e in extract_anchor_events(tx["meta"]["logMessages"]) if isinstance(e, PumpTrade)
    )
    direction = 1 if event.is_buy else -1
    pre = {
        key: getattr(event, key)
        + (direction * event.token_amount if "token" in key else -direction * event.quote_amount)
        for key in (
            "virtual_token_reserves",
            "virtual_quote_reserves",
            "real_token_reserves",
            "real_quote_reserves",
        )
    }
    parity = validate_transaction_parity(
        tx, event, bundle, pre, proof["candidate"]["anchor_signature"]
    )
    assert parity["native_integer_parity"]
    assert parity["fee_destination_deltas"] == {
        "protocol_primary": 532210,
        "protocol_buyback": 532210,
        "creator_vault": 336133,
    }


def test_retained_live_integer_sell_and_actual_quote_transfer():
    packet = json.loads(
        (Path(__file__).parents[1] / "analysis/live_execution_proofs_run3.json").read_text()
    )
    proof = next(p for p in packet["candidate_proofs"] if p["status"] == "PASS")
    bundle = proof["evidence"]
    tx = bundle["native_transactions"][0]
    event = next(
        e for _, e in extract_anchor_events(tx["meta"]["logMessages"]) if isinstance(e, PumpTrade)
    )
    prior = bundle["parity"][0]
    parity = validate_transaction_parity(
        tx, event, bundle, prior["pre_reserves"], prior["signature"]
    )
    assert parity["actual_quote_transfer"] == 97530861
    assert parity["sell_rent_refund"] == 1513840
    assert parity["quote"]["gross_output"] == 98765430


@pytest.mark.asyncio
async def test_predecessor_does_not_bridge_missing_bank_state():
    candidate, accounts, tx, _, _ = fixture()
    from memebot.providers.solana.bootstrap import decode_config

    fields, _ = decode_config(
        PUMP_PROGRAM_ID, base64.b64decode(accounts[CURVE]["data"][0]), "BondingCurve"
    )
    fields["virtual_quote_reserves"] += 1
    accounts[CURVE]["data"][0] = base64.b64encode(
        record(PUMP_PROGRAM_ID, "BondingCurve", fields)
    ).decode()
    rpc = Rpc(accounts, tx)
    original = rpc._call

    async def lagging(method, params):
        if method == "getSignaturesForAddress":
            rpc.calls.append((method, params))
            return [{"signature": "predecessor", "slot": 99, "err": None}]
        return await original(method, params)

    rpc._call = lagging
    proof = await CandidateProofService(rpc).prove(candidate)
    assert proof.status == "FAIL_STATE_SYNC", proof.reason


@pytest.mark.asyncio
async def test_refresh_invalidation_race_rejects_even_identical_accounts():
    from datetime import UTC, datetime

    candidate, accounts, tx, _, _ = fixture()
    rpc = Rpc(accounts, tx)
    service = CandidateProofService(rpc)
    proof = await service.prove(candidate)
    assert proof.status == "PASS"
    original = rpc._call

    async def invalidating(method, params):
        result = await original(method, params)
        if method == "getMultipleAccounts":
            service.invalidate("UNRESOLVED_NATIVE_CONFIG")
        return result

    rpc._call = invalidating
    fresh = await service.execution_refresh(proof, decision_at=datetime.now(UTC))
    assert not fresh["execution_approved"]
    assert fresh["revalidation_outcome"] == "STILL_BLOCKED_BY_UNPROVEN_CONTINUITY"
    assert not service.receipts
