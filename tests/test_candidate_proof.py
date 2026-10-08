import asyncio
import base64
import json
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from solders.pubkey import Pubkey

from memebot.paper.candidate_proof import (
    Candidate,
    CandidateProofService,
    ProofFailure,
    ProofPolicy,
    observational_stage,
)
from memebot.paper.standard_math import buy_exact_tokens, buy_quote, fee, select_fees, sell_quote
from memebot.providers.solana.canonical import (
    associated_address,
    config_addresses,
    curve_address,
    pda,
)
from memebot.providers.solana.encoding import encode_base58
from memebot.providers.solana.idl_schema import schema
from memebot.providers.solana.pump import extract_anchor_events
from memebot.providers.solana.pump_idl import NATIVE_SOL_MINT, PUMP_PROGRAM_ID, TOKEN_PROGRAM_ID
from memebot.research.pumpfun_sequence import EVENT_CPI_TAG

MINT = str(Pubkey.from_bytes(bytes([4]) * 32))
CREATOR = str(Pubkey.from_bytes(bytes([5]) * 32))
CURVE = curve_address(MINT)
VAULT = associated_address(CURVE, MINT, TOKEN_PROGRAM_ID)


def encode_type(program, kind, value=None):
    if isinstance(kind, str):
        if kind == "pubkey":
            return bytes(Pubkey.from_string(value or NATIVE_SOL_MINT))
        if kind == "bool":
            return bytes([bool(value)])
        if kind == "string":
            raw = (value or "").encode()
            return len(raw).to_bytes(4, "little") + raw
        return int(value or 0).to_bytes(int(kind[1:]) // 8, "little", signed=kind[0] == "i")
    if "defined" in kind:
        definition = next(
            row for row in schema(program)["types"] if row["name"] == kind["defined"]["name"]
        )
        return b"".join(
            encode_type(program, row["type"], (value or {}).get(row["name"]))
            for row in definition["type"]["fields"]
        )
    if "vec" in kind:
        return len(value or []).to_bytes(4, "little") + b"".join(
            encode_type(program, kind["vec"], v) for v in value or []
        )
    if "array" in kind:
        item, size = kind["array"]
        return b"".join(encode_type(program, item, v) for v in (value or [None] * size))
    if "option" in kind:
        return b"\0" if value is None else b"\1" + encode_type(program, kind["option"], value)
    raise AssertionError(kind)


def record(program, name, values, collection="accounts"):
    definition = next(row for row in schema(program)[collection] if row["name"] == name)
    return bytes(definition["discriminator"]) + encode_type(
        program, {"defined": {"name": name}}, values
    )


def fixture(*, is_buy=True):
    retained = json.loads(
        (Path(__file__).parents[1] / "analysis/fee_config_bootstrap.json").read_text()
    )["accounts"]
    global_state = retained["pump_global"]["fields"]
    global_state["buyback_basis_points"] = (
        0  # Synthetic legacy route; live split tested separately.
    )
    fee_config = retained["pump_fee"]["fields"]
    pre = dict(
        virtual_token_reserves=1_000_000_000_000,
        virtual_quote_reserves=10_000_000_000,
        real_token_reserves=800_000_000_000,
        real_quote_reserves=1_000_000_000,
        token_total_supply=1_000_000_000_000_000,
        complete=False,
        creator=CREATOR,
        is_mayhem_mode=False,
        is_cashback_coin=False,
        quote_mint=NATIVE_SOL_MINT,
        creator_fee_bps=0,
        can_edit_creator_fee=False,
        is_holder_reward=False,
    )
    rates = select_fees(global_state, fee_config, pre, pre["token_total_supply"])
    quote = (
        buy_exact_tokens(pre, 100_000_000, rates) if is_buy else sell_quote(pre, 100_000_000, rates)
    )
    net, tokens = (quote["net_curve_input"] if is_buy else quote["gross_output"]), 100_000_000
    direction = 1 if is_buy else -1
    post = {
        **pre,
        "virtual_quote_reserves": pre["virtual_quote_reserves"] + direction * net,
        "real_quote_reserves": pre["real_quote_reserves"] + direction * net,
        "virtual_token_reserves": pre["virtual_token_reserves"] - direction * tokens,
        "real_token_reserves": pre["real_token_reserves"] - direction * tokens,
    }
    event_fields = {
        "mint": MINT,
        "sol_amount": net,
        "quote_amount": net,
        "token_amount": tokens,
        "is_buy": is_buy,
        "user": CREATOR,
        "timestamp": 1,
        "virtual_sol_reserves": post["virtual_quote_reserves"],
        "real_sol_reserves": post["real_quote_reserves"],
        "virtual_quote_reserves": post["virtual_quote_reserves"],
        "real_quote_reserves": post["real_quote_reserves"],
        "virtual_token_reserves": post["virtual_token_reserves"],
        "real_token_reserves": post["real_token_reserves"],
        "fee_recipient": global_state["fee_recipient"],
        "fee_basis_points": rates["protocol_bps"],
        "fee": quote["protocol_fee"],
        "creator": CREATOR,
        "creator_fee_basis_points": rates["creator_bps"],
        "creator_fee": quote["creator_fee"],
        "ix_name": "buy" if is_buy else "sell",
        "mayhem_mode": False,
        "quote_mint": NATIVE_SOL_MINT,
    }
    payload = record(PUMP_PROGRAM_ID, "TradeEvent", event_fields, "events")
    ix = next(
        row
        for row in schema(PUMP_PROGRAM_ID)["instructions"]
        if row["name"] == ("buy" if is_buy else "sell")
    )
    configs = config_addresses()
    mapping = {
        "system_program": NATIVE_SOL_MINT,
        "token_program": TOKEN_PROGRAM_ID,
        "mint": MINT,
        "bonding_curve": CURVE,
        "associated_bonding_curve": VAULT,
        "associated_user": associated_address(CREATOR, MINT, TOKEN_PROGRAM_ID),
        "global": configs["pump_global"][0],
        "fee_config": configs["pump_fee"][0],
        "creator_vault": pda(
            PUMP_PROGRAM_ID, [b"creator-vault", bytes(Pubkey.from_string(CREATOR))]
        ),
        "fee_recipient": global_state["fee_recipient"],
    }
    account_names = [mapping.get(row["name"], CREATOR) for row in ix["accounts"]]
    keys = list(dict.fromkeys([PUMP_PROGRAM_ID, *account_names]))
    curve_index, vault_index = keys.index(CURVE), keys.index(VAULT)
    prebalances = [0] * len(keys)
    postbalances = [0] * len(keys)
    prebalances[curve_index] = pre["real_quote_reserves"] + 10000
    postbalances[curve_index] = post["real_quote_reserves"] + 10000
    postbalances[keys.index(mapping["fee_recipient"])] = quote["protocol_fee"]
    postbalances[keys.index(mapping["creator_vault"])] = quote["creator_fee"]
    prebalances[keys.index(CREATOR)] = 1_000_000_000_000
    postbalances[keys.index(CREATOR)] = prebalances[keys.index(CREATOR)] + (
        -quote["gross_input"] if is_buy else quote["net_output"]
    )
    logs = [
        f"Program {PUMP_PROGRAM_ID} invoke [1]",
        "Program log: Instruction: Buy" if is_buy else "Program log: Instruction: Sell",
        "Program data: " + base64.b64encode(payload).decode(),
        f"Program {PUMP_PROGRAM_ID} success",
    ]
    tx = {
        "slot": 100,
        "transaction": {
            "signatures": ["anchor"],
            "message": {
                "accountKeys": keys,
                "instructions": [
                    {
                        "programIdIndex": 0,
                        "accounts": [keys.index(key) for key in account_names],
                        "data": encode_base58(
                            bytes(ix["discriminator"])
                            + tokens.to_bytes(8, "little")
                            + (quote["gross_input"] if is_buy else quote["net_output"]).to_bytes(
                                8, "little"
                            )
                            + b"\0"
                        ),
                    }
                ],
            },
        },
        "meta": {
            "fee": 0,
            "err": None,
            "logMessages": logs,
            "preBalances": prebalances,
            "postBalances": postbalances,
            "preTokenBalances": [
                {
                    "mint": MINT,
                    "owner": CREATOR,
                    "programId": TOKEN_PROGRAM_ID,
                    "accountIndex": keys.index(mapping["associated_user"]),
                    "uiTokenAmount": {"amount": str(0 if is_buy else tokens)},
                },
                {
                    "mint": MINT,
                    "owner": CURVE,
                    "accountIndex": vault_index,
                    "uiTokenAmount": {"amount": str(pre["real_token_reserves"] + 1000)},
                },
            ],
            "postTokenBalances": [
                {
                    "mint": MINT,
                    "owner": CREATOR,
                    "programId": TOKEN_PROGRAM_ID,
                    "accountIndex": keys.index(mapping["associated_user"]),
                    "uiTokenAmount": {"amount": str(tokens if is_buy else 0)},
                },
                {
                    "mint": MINT,
                    "owner": CURVE,
                    "accountIndex": vault_index,
                    "uiTokenAmount": {"amount": str(post["real_token_reserves"] + 1000)},
                },
            ],
            "innerInstructions": [
                {
                    "index": 0,
                    "instructions": [
                        {
                            "programIdIndex": keys.index(TOKEN_PROGRAM_ID),
                            "accounts": [
                                keys.index(VAULT if is_buy else mapping["associated_user"]),
                                keys.index(MINT),
                                keys.index(mapping["associated_user"] if is_buy else VAULT),
                                keys.index(CURVE if is_buy else CREATOR),
                            ],
                            "data": encode_base58(b"\x0c" + tokens.to_bytes(8, "little") + b"\x06"),
                        },
                        *(
                            [
                                {
                                    "programIdIndex": keys.index(NATIVE_SOL_MINT),
                                    "accounts": [keys.index(CREATOR), keys.index(destination)],
                                    "data": encode_base58(
                                        b"\x02\0\0\0" + amount.to_bytes(8, "little")
                                    ),
                                }
                                for destination, amount in (
                                    (CURVE, quote["net_curve_input"]),
                                    (mapping["fee_recipient"], quote["protocol_fee"]),
                                    (mapping["creator_vault"], quote["creator_fee"]),
                                )
                            ]
                            if is_buy
                            else []
                        ),
                        {
                            "programIdIndex": 0,
                            "accounts": [],
                            "data": encode_base58(EVENT_CPI_TAG + payload),
                        },
                    ],
                }
            ],
        },
    }
    mint_bytes = b"\0" * 36 + pre["token_total_supply"].to_bytes(8, "little") + b"\6\1" + b"\0" * 36
    vault_bytes = bytearray(
        bytes(Pubkey.from_string(MINT))
        + bytes(Pubkey.from_string(CURVE))
        + (post["real_token_reserves"] + 1000).to_bytes(8, "little")
        + b"\0" * 93
    )
    vault_bytes[108] = 1

    def account(owner, data, lamports=0):
        return {
            "owner": owner,
            "data": [base64.b64encode(data).decode(), "base64"],
            "lamports": lamports,
            "executable": False,
        }

    accounts = {
        MINT: account(TOKEN_PROGRAM_ID, mint_bytes),
        CURVE: account(
            PUMP_PROGRAM_ID,
            record(PUMP_PROGRAM_ID, "BondingCurve", post),
            postbalances[curve_index],
        ),
        VAULT: account(TOKEN_PROGRAM_ID, vault_bytes),
    }
    for key in ("pump_global", "pump_fee"):
        address, owner, name = configs[key]
        accounts[address] = account(owner, record(owner, name, retained[key]["fields"]))
    event = extract_anchor_events(logs)[0][1]
    candidate = Candidate(
        MINT, event, "anchor", 100, datetime.now(UTC), "EXACT", True, 100_000_000, 1_000_000
    )
    return candidate, accounts, tx, pre, rates


class Rpc:
    def __init__(self, accounts, tx):
        self.accounts, self.tx = accounts, tx
        self.calls = []
        self.fence_changes = False

    async def _call(self, method, params):
        self.calls.append((method, params))
        if method == "getMultipleAccounts":
            return {"context": {"slot": 101}, "value": [self.accounts.get(a) for a in params[0]]}
        if method == "getTransaction":
            return deepcopy(self.tx)
        if method == "getSignaturesForAddress":
            row = {"signature": "anchor", "slot": 100, "err": None}
            if self.fence_changes and len(self.calls) > 4:
                row["signature"] = "unseen"
            return [row]
        raise AssertionError(method)


@pytest.mark.asyncio
async def test_candidate_success_and_required_cheap_execution_refresh():
    candidate, accounts, tx, _, _ = fixture()
    rpc = Rpc(accounts, tx)
    service = CandidateProofService(rpc)
    proof = await service.prove(candidate)
    assert proof.status == "PASS", proof.reason
    assert proof.slot_span == 0 and proof.evidence["native_sequence_anchored"]
    assert proof.execution_refresh_at is None
    fresh = await service.execution_refresh(proof, decision_at=datetime.now(UTC))
    assert fresh["buy"]["token_output"] > 0 and proof.costs["reserve_refresh_reads"] == 1
    assert len(service.config_cache) == 1
    assert sum(method == "getMultipleAccounts" for method, _ in rpc.calls) == 2


@pytest.mark.asyncio
async def test_candidate_native_sell_integer_parity_success():
    candidate, accounts, tx, _, _ = fixture(is_buy=False)
    proof = await CandidateProofService(Rpc(accounts, tx)).prove(candidate)
    assert proof.status == "PASS", proof.reason
    assert proof.evidence["parity"][0]["side"] == "sell"


@pytest.mark.asyncio
async def test_failed_execution_refresh_revokes_receipt():
    candidate, accounts, tx, _, _ = fixture()
    service = CandidateProofService(Rpc(accounts, tx))
    proof = await service.prove(candidate)
    accounts[CURVE]["owner"] = TOKEN_PROGRAM_ID
    with pytest.raises(ProofFailure):
        await service.execution_refresh(proof, decision_at=datetime.now(UTC))
    assert not service.receipts


@pytest.mark.asyncio
async def test_deadline_exhaustion_never_approves():
    candidate, accounts, tx, _, _ = fixture()
    rpc = Rpc(accounts, tx)
    original = rpc._call

    async def delayed(method, params):
        await asyncio.sleep(0.05)
        return await original(method, params)

    rpc._call = delayed
    proof = await CandidateProofService(rpc, ProofPolicy(timeout_seconds=0.01)).prove(candidate)
    assert proof.status == "FAIL_BUDGET" and proof.stage == "REJECTED"


@pytest.mark.asyncio
async def test_invalidation_during_reads_cannot_race_into_approval():
    candidate, accounts, tx, _, _ = fixture()
    rpc = Rpc(accounts, tx)
    service = CandidateProofService(rpc)
    original = rpc._call

    async def invalidate_during_read(method, params):
        result = await original(method, params)
        if method == "getTransaction":
            service.invalidate("CONFIG_UPDATE")
        return result

    rpc._call = invalidate_during_read
    proof = await service.prove(candidate)
    assert proof.status == "FAIL_CONFIG" and not service.receipts


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("identity", "FAIL_IDENTITY"),
        ("config", "FAIL_CONFIG"),
        ("continuity", "FAIL_CONTINUITY"),
        ("fence", "FAIL_STATE_SYNC"),
        ("fee", "FAIL_FEE"),
    ],
)
@pytest.mark.asyncio
async def test_candidate_rejects_incomplete_evidence(mutation, expected):
    candidate, accounts, tx, _, _ = fixture()
    rpc = Rpc(accounts, tx)
    if mutation == "identity":
        accounts[CURVE]["owner"] = TOKEN_PROGRAM_ID
    if mutation == "config":
        accounts[config_addresses()["pump_fee"][0]]["owner"] = PUMP_PROGRAM_ID
    if mutation == "continuity":
        tx["meta"]["innerInstructions"] = []
    if mutation == "fence":
        rpc.fence_changes = True
    if mutation == "fee":
        # Real native/event quantity doesn't agree with reserve-model integer quote.
        tx["transaction"]["message"]["instructions"][0]["data"] = encode_base58(
            bytes(
                next(
                    row for row in schema(PUMP_PROGRAM_ID)["instructions"] if row["name"] == "buy"
                )["discriminator"]
            )
            + (1).to_bytes(8, "little")
            + (1).to_bytes(8, "little")
            + b"\0"
        )
    proof = await CandidateProofService(rpc).prove(candidate)
    assert proof.status == expected, proof.reason


@pytest.mark.asyncio
async def test_budget_exhaustion_and_stale_proof_never_approve():
    candidate, accounts, tx, _, _ = fixture()
    rpc = Rpc(accounts, tx)
    proof = await CandidateProofService(rpc, ProofPolicy(max_requests=1)).prove(candidate)
    assert proof.status == "FAIL_BUDGET" and len(rpc.calls) == 1
    service = CandidateProofService(Rpc(accounts, tx))
    proof = await service.prove(candidate)
    with pytest.raises(ProofFailure, match="stale"):
        await service.execution_refresh(
            proof, decision_at=proof.proof_completed_at + timedelta(seconds=3)
        )


@pytest.mark.asyncio
async def test_config_cache_reuse_invalidation_and_changed_version():
    candidate, accounts, tx, _, _ = fixture()
    service = CandidateProofService(Rpc(accounts, tx))
    proof = await service.prove(candidate)
    assert proof.status == "PASS", proof.reason
    await service.execution_refresh(proof, decision_at=datetime.now(UTC))
    assert len(service.config_cache) == 1
    accounts[config_addresses()["pump_fee"][0]]["data"][0] = base64.b64encode(b"wrong").decode()
    with pytest.raises(ProofFailure):
        await service.execution_refresh(proof, decision_at=datetime.now(UTC))
    service.invalidate("CONFIG_UPDATE")
    assert not service.config_cache and not service.receipts and not service.stable


@pytest.mark.parametrize(
    "updates",
    [
        {"multi_event": True},
        {"venue": "pump_swap"},
        {"known_divergence": True},
        {"migrated": True},
        {"arithmetic_status": "DIVERGED"},
        {"quality_passed": False},
    ],
)
@pytest.mark.asyncio
async def test_excluded_and_unearned_candidates_do_not_invoke_rpc(updates):
    candidate, accounts, tx, _, _ = fixture()
    rpc = Rpc(accounts, tx)
    candidate = replace(candidate, **updates)
    assert observational_stage(candidate)[0] != "SERIOUS_CANDIDATE"
    proof = await CandidateProofService(rpc).prove(candidate)
    assert proof.status != "PASS" and not rpc.calls


def test_integer_buy_sell_rounding_tiers_creator_zero_and_override():
    _, _, _, curve, rates = fixture()
    assert fee(1, 95) == 1 and fee(10000, 95) == 95
    buy = buy_quote(curve, 100_000_000, rates)
    assert buy["token_output"] == ((100_000_000 - 1) * 10000 // 10125) * curve[
        "virtual_token_reserves"
    ] // (curve["virtual_quote_reserves"] + (100_000_000 - 1) * 10000 // 10125)
    sell = sell_quote(curve, 1_000_000, rates)
    assert sell["gross_output"] == 9999
    assert sell["net_output"] == 9999 - fee(9999, 95) - fee(9999, 30)
    config = {
        "fee_tiers": [
            {
                "market_cap_lamports_threshold": 0,
                "fees": {"protocol_fee_bps": 95, "creator_fee_bps": 30, "lp_fee_bps": 0},
            },
            {
                "market_cap_lamports_threshold": 10,
                "fees": {"protocol_fee_bps": 90, "creator_fee_bps": 20, "lp_fee_bps": 0},
            },
        ]
    }
    global_state = {"creator_fee_configurable": True, "max_configurable_creator_fee_bps": 300}
    assert (
        select_fees(
            global_state, config, {**curve, "creator_fee_bps": 77}, curve["token_total_supply"]
        )["creator_bps"]
        == 77
    )
    assert (
        select_fees(
            global_state, config, {**curve, "creator": NATIVE_SOL_MINT}, curve["token_total_supply"]
        )["creator_bps"]
        == 0
    )
    assert (
        select_fees(global_state, config, curve, curve["token_total_supply"])["protocol_bps"] == 90
    )
