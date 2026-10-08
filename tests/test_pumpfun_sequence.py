from dataclasses import replace

import pytest

from memebot.providers.solana.canonical import associated_address, curve_address
from memebot.providers.solana.encoding import encode_base58
from memebot.providers.solana.idl_schema import schema
from memebot.providers.solana.pump_idl import (
    NATIVE_SOL_MINT,
    PUMP_PROGRAM_ID,
    TOKEN_PROGRAM_ID,
    PumpTrade,
)
from memebot.research.pumpfun_sequence import EVENT_CPI_TAG, reconstruct_transaction

MINT = encode_base58(bytes([4]) * 32)
CURVE = curve_address(MINT)
VAULT = associated_address(CURVE, MINT, TOKEN_PROGRAM_ID)


def fixture(monkeypatch):
    events = [
        PumpTrade(
            MINT,
            10,
            20,
            True,
            MINT,
            1,
            980 - 20 * i,
            110 + 10 * i,
            780 - 20 * i,
            10 + 10 * i,
            NATIVE_SOL_MINT,
            False,
            "buy",
        )
        for i in range(3)
    ]
    monkeypatch.setattr(
        "memebot.research.pumpfun_sequence.extract_anchor_events",
        lambda logs: [(PUMP_PROGRAM_ID, e) for e in events],
    )
    monkeypatch.setattr(
        "memebot.research.pumpfun_sequence.decode_anchor_event",
        lambda program, data: events[data[0]],
    )
    buy = next(row for row in schema(PUMP_PROGRAM_ID)["instructions"] if row["name"] == "buy")

    def balance(amount):
        return {
            "accountIndex": 2,
            "mint": MINT,
            "owner": CURVE,
            "uiTokenAmount": {"amount": str(amount)},
        }

    transaction = {
        "transaction": {
            "message": {
                "accountKeys": [PUMP_PROGRAM_ID, CURVE, VAULT, MINT],
                "instructions": [
                    {
                        "programIdIndex": 0,
                        "accounts": [1, 2, 3],
                        "data": encode_base58(bytes(buy["discriminator"])),
                    }
                    for _ in events
                ],
            }
        },
        "meta": {
            "err": None,
            "logMessages": [],
            "preBalances": [0, 1000, 0, 0],
            "postBalances": [0, 1030, 0, 0],
            "preTokenBalances": [balance(1000)],
            "postTokenBalances": [balance(940)],
            "innerInstructions": [
                {
                    "index": i,
                    "instructions": [
                        {
                            "programIdIndex": 0,
                            "accounts": [1],
                            "data": encode_base58(EVENT_CPI_TAG + bytes([i])),
                        }
                    ],
                }
                for i in range(3)
            ],
        },
    }
    return transaction, events


def test_generic_three_event_sequence_proves_physical_inventory(monkeypatch):
    tx, _ = fixture(monkeypatch)
    proof = reconstruct_transaction(tx)[0]
    assert proof["status"] == "TRANSACTION_SEQUENCE_VERIFIED"
    assert proof["reserved_inventory"] == 200
    assert proof["residuals"] == {"physical_token": 0, "curve_lamports": 0}
    assert not proof["production_promotion"]


@pytest.mark.parametrize(
    "mutation", ["truncated", "native_inner", "direct_vault", "ordering", "mayhem", "balance"]
)
def test_ambiguity_never_promotes_intermediate_state(monkeypatch, mutation):
    tx, events = fixture(monkeypatch)
    if mutation == "truncated":
        tx["meta"]["logMessages"] = ["Log truncated"]
    elif mutation == "native_inner":
        tx["meta"]["innerInstructions"][0]["instructions"][0]["data"] = encode_base58(b"unknown")
    elif mutation == "direct_vault":
        tx["transaction"]["message"]["accountKeys"].append(TOKEN_PROGRAM_ID)
        tx["transaction"]["message"]["instructions"].append(
            {"programIdIndex": 4, "accounts": [2], "data": "1"}
        )
    elif mutation == "ordering":
        tx["meta"]["innerInstructions"].reverse()
    elif mutation == "mayhem":
        events[0] = replace(events[0], is_mayhem_mode=True)
    elif mutation == "balance":
        tx["meta"]["postBalances"][1] += 1
    assert reconstruct_transaction(tx)[0]["status"] == "UNKNOWN"
