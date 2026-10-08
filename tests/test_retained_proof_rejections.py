"""Public executed packets, exact arithmetic and adversarial accounting regressions."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from memebot.paper.candidate_proof import (
    CandidateProofService,
    ProofFailure,
    ProofPolicy,
    validate_transaction_parity,
)
from memebot.paper.standard_math import buy_exact_input
from memebot.providers.solana.execution_accounting import execution_accounting
from memebot.providers.solana.pump import extract_anchor_events
from memebot.providers.solana.pump_idl import PumpTrade
from memebot.providers.solana.trade_alignment import account_keys, trade_invocations
from memebot.research.pumpfun_sequence import reconstruct_transaction

CASES = json.loads((Path(__file__).parent / "fixtures/proof_rejections.json").read_text())


def parity(case, tx=None):
    tx = tx or case["tx"]
    event = next(
        e
        for _, e in extract_anchor_events(tx["meta"]["logMessages"])
        if isinstance(e, PumpTrade) and e.mint == case["mint"]
    )
    direction = 1 if event.is_buy else -1
    pre = {
        k: getattr(event, k)
        + (direction * event.token_amount if "token" in k else -direction * event.quote_amount)
        for k in (
            "virtual_token_reserves",
            "virtual_quote_reserves",
            "real_token_reserves",
            "real_quote_reserves",
        )
    }
    return validate_transaction_parity(
        tx, event, case["bank"], pre, tx["transaction"]["signatures"][0]
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: str(c["case"]))
def test_retained_single_event_alignment_and_exact_accounting(case):
    calls = trade_invocations(case["tx"], case["mint"])
    assert len(calls) == 1
    result = reconstruct_transaction(case["tx"])
    if case["case"] in (3, 5, 10, 12):
        assert result[0]["status"] != "TRANSACTION_SEQUENCE_VERIFIED"
        with pytest.raises(ValueError, match=r"MISSING_PACKET|PHYSICAL_BALANCE_MISMATCH"):
            execution_accounting(case["tx"], case["mint"])
    else:
        assert result[0]["status"] == "TRANSACTION_SEQUENCE_VERIFIED"
        accounting = execution_accounting(case["tx"], case["mint"])
        assert not accounting["lamport_residuals"] and not accounting["token_residuals"]
        assert accounting["canonical_ownership_bank_required"]


@pytest.mark.parametrize(
    "index,net,tokens",
    [
        (4, 197530863, 5808275502868),
        (14, 752378171, 9883194423530),
        (15, 29629629, 649050083068),
    ],
)
def test_retained_exact_input_rounding_is_exact(index, net, tokens):
    result = parity(CASES[index])
    assert result["quote"]["net_curve_input"] == net
    assert result["quote"]["token_output"] == tokens
    assert result["actual_quote_transfer"] == result["quote"]["gross_input"]
    assert result["instruction"] in {"buy_exact_sol_in", "buy_exact_quote_in_v2"}


@pytest.mark.parametrize("index", [1, 8, 11, 16])
def test_retained_sell_proceeds_and_actual_refunds(index):
    case = CASES[index]
    for tx in {
        t["transaction"]["signatures"][0]: t for t in [case["tx"], *case["successors"]]
    }.values():
        result = parity(case, tx)
        assert result["actual_quote_transfer"] == result["quote"]["net_output"]
        if index == 1 and result["quote"]["net_output"] == 7915645:
            # Retained Token-2022 account has an actual 1,513,840 close refund.
            # A hardcoded 2,039,280 rent refund would incorrectly reject it.
            assert result["sell_rent_refund"] == 1513840


@pytest.mark.parametrize("index", [7, 9, 13])
def test_cpi_stack_boundary_cannot_be_guessed(index):
    tx = deepcopy(CASES[index]["tx"])
    call = trade_invocations(tx, CASES[index]["mint"])[0]
    group = next(g for g in tx["meta"]["innerInstructions"] if g["index"] == call["top_index"])
    group["instructions"][call["inner_index"]].pop("stackHeight")
    with pytest.raises(ValueError, match="ACCOUNT_ORDERING_AMBIGUITY"):
        execution_accounting(tx, CASES[index]["mint"])


@pytest.mark.parametrize("index", [7, 9, 13, 8, 11, 16])
def test_one_unexplained_lamport_is_rejected(index):
    tx = deepcopy(CASES[index]["tx"])
    tx["meta"]["postBalances"][0] += 1
    with pytest.raises(ValueError, match="PHYSICAL_BALANCE_MISMATCH"):
        execution_accounting(tx, CASES[index]["mint"])


def test_missing_close_authority_is_rejected():
    tx = deepcopy(CASES[16]["tx"])
    accounting = execution_accounting(tx, CASES[16]["mint"])
    source = next(
        m["source"] for m in accounting["movements"] if m["kind"] == "TOKEN_ACCOUNT_CLOSE_REFUND"
    )
    index = account_keys(tx).index(source)
    for row in tx["meta"]["preTokenBalances"]:
        if row["accountIndex"] == index:
            row.pop("owner")
    with pytest.raises(ValueError, match="close provenance incomplete"):
        execution_accounting(tx, CASES[16]["mint"])


def test_unknown_inner_program_cannot_touch_protected_market():
    tx = deepcopy(CASES[7]["tx"])
    call = trade_invocations(tx, CASES[7]["mint"])[0]
    top = tx["transaction"]["message"]["instructions"][call["top_index"]]
    group = next(g for g in tx["meta"]["innerInstructions"] if g["index"] == call["top_index"])
    unknown = deepcopy(top)
    unknown["stackHeight"] = 2
    group["instructions"].append(unknown)
    with pytest.raises(ValueError, match="unknown program has protected accounts"):
        execution_accounting(tx, CASES[7]["mint"])


def test_unrelated_balanced_transfer_to_curve_is_rejected():
    tx = deepcopy(CASES[8]["tx"])
    keys = account_keys(tx)
    call = trade_invocations(tx, CASES[8]["mint"])[0]
    curve = call["mapping"]["bonding_curve"]
    movement = next(
        m
        for m in execution_accounting(tx, CASES[8]["mint"])["movements"]
        if m["kind"] == "UNRELATED_SYSTEM_TRANSFER"
    )
    top_index, inner_index = movement["coordinate"]
    assert inner_index is None
    tip = tx["transaction"]["message"]["instructions"][top_index]
    old = keys[tip["accounts"][1]]
    from memebot.providers.solana.encoding import decode_base58

    amount = int.from_bytes(decode_base58(tip["data"])[4:], "little")
    tip["accounts"][1] = keys.index(curve)
    tx["meta"]["postBalances"][keys.index(old)] -= amount
    tx["meta"]["postBalances"][keys.index(curve)] += amount
    with pytest.raises(ValueError, match="ancillary transfer touches protected account"):
        execution_accounting(tx, CASES[8]["mint"])


def test_exact_input_completion_branch_stays_unsupported():
    with pytest.raises(ValueError, match="reserve-cap branch"):
        buy_exact_input(
            {
                "virtual_token_reserves": 1000,
                "virtual_quote_reserves": 100,
                "real_token_reserves": 1,
            },
            100,
            {"protocol_bps": 0, "creator_bps": 0},
        )


@pytest.mark.asyncio
async def test_failed_signatures_do_not_consume_successful_state_budget():
    from test_candidate_proof import Rpc, fixture

    candidate, accounts, tx, _, _ = fixture()
    rpc = Rpc(accounts, tx)
    original = rpc._call

    async def rows(method, params):
        if method == "getSignaturesForAddress":
            return [
                {"signature": f"failed{i}", "slot": 100, "err": {"InstructionError": [0, 1]}}
                for i in range(4)
            ] + [{"signature": "anchor", "slot": 100, "err": None}]
        return await original(method, params)

    rpc._call = rows
    proof = await CandidateProofService(rpc).prove(candidate)
    assert proof.status == "PASS", proof.reason
    assert proof.evidence["signature_window"] == ["anchor"]
    assert len(proof.evidence["history_reads"]) == 4


@pytest.mark.asyncio
@pytest.mark.parametrize("history_slot", [100, 102])
async def test_failed_full_page_above_anchor_still_needs_boundary(history_slot):
    from test_candidate_proof import Rpc, fixture

    candidate, accounts, tx, _, _ = fixture()
    rpc = Rpc(accounts, tx)
    original = rpc._call

    async def rows(method, params):
        if method == "getSignaturesForAddress":
            return [
                {
                    "signature": f"failed{i}",
                    "slot": history_slot,
                    "err": {"InstructionError": [0, 1]},
                }
                for i in range(5)
            ]
        return await original(method, params)

    rpc._call = rows
    service = CandidateProofService(rpc)
    proof = await service.prove(candidate)
    assert proof.status == "FAIL_BUDGET" and proof.reason == "successor boundary not reached"
    assert service.policy == ProofPolicy()
    assert not service.receipts


def test_bad_native_fee_is_not_tolerated():
    tx = deepcopy(CASES[4]["tx"])
    recipient = CASES[4]["bank"]["global"]["fee_recipient"]
    keys = account_keys(tx)
    actual = next(
        m["destination"]
        for m in execution_accounting(tx, CASES[4]["mint"])["movements"]
        if m["kind"] == "TRADE_SYSTEM_TRANSFER"
        and m["destination"] != recipient
        and m["destination"] in CASES[4]["bank"]["global"]["buyback_fee_recipients"]
    )
    tx["meta"]["postBalances"][keys.index(actual)] += 1
    with pytest.raises(ProofFailure, match="fee destination balance delta mismatch"):
        parity(CASES[4], tx)


@pytest.mark.asyncio
async def test_offline_replay_never_synthesizes_a_bank_or_reuses_a_fence():
    import runpy

    module = runpy.run_path(str(Path(__file__).parents[1] / "analysis/replay_proof_rejections.py"))
    original = {
        "proof_started_at": "2026-10-02T13:00:00+00:00",
        "evidence": {
            "direct_anchor_transaction": CASES[7]["tx"],
            "history_reads": [
                {"address": "curve", "rows": [], "received_at": "2026-10-02T13:00:01+00:00"}
            ],
        },
    }
    rpc = module["RecordedRpc"](original, {})
    assert await rpc._call("getSignaturesForAddress", ["curve"]) == []
    with pytest.raises(ProofFailure, match="MISSING_REPLAY_HISTORY_FENCE"):
        await rpc._call("getSignaturesForAddress", ["curve"])
    with pytest.raises(ProofFailure, match="MISSING_REPLAY_ATOMIC_BANK"):
        await rpc._call("getMultipleAccounts", [["mint", "curve"]])


@pytest.mark.asyncio
async def test_late_stream_packet_cannot_retroactively_fill_replay_evidence():
    import runpy

    module = runpy.run_path(str(Path(__file__).parents[1] / "analysis/replay_proof_rejections.py"))
    original = {
        "proof_started_at": "2026-10-02T13:00:00+00:00",
        "evidence": {"direct_anchor_transaction": CASES[7]["tx"]},
    }
    rpc = module["RecordedRpc"](
        original,
        {
            "late": {
                "received_timestamp": "2026-10-02T13:00:00.001+00:00",
            }
        },
    )
    with pytest.raises(ProofFailure, match="MISSING_REPLAY_TRANSACTION:late"):
        await rpc._call("getTransaction", ["late"])
