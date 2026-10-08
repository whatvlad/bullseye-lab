from dataclasses import replace

from memebot.providers.solana.pump_idl import PumpSwapTrade, PumpTrade
from memebot.research.reserve_sync import (
    ForensicRpc,
    LocalReserveTracker,
    select_anomalies,
    verify_semantics,
)


def fun(q=100, t=1000, amount=10, buy=True):
    return PumpTrade("mint", amount, 50, buy, "user", 1, t, q, t - 100, q - 30, "SOL")


def test_post_state_transition_and_missing_mutation_are_distinguished():
    tracker = LocalReserveTracker()
    tracker.update(fun(), event_id="sig1:0", slot=1, received_at="now")
    matched = tracker.update(fun(q=110, t=950), event_id="sig2:0", slot=1, received_at="now")
    assert matched["post_trade_transition_matches"] is True
    assert matched["coverage_complete"] is False
    gap = tracker.update(fun(q=140, t=800), event_id="sig3:0", slot=2, received_at="now")
    assert gap["post_trade_transition_matches"] is False
    assert gap["synchronization"] == "SLOT_ONLY"


def test_duplicates_and_regressions_do_not_overwrite_latest_state():
    tracker = LocalReserveTracker()
    first = tracker.update(fun(), event_id="sig:0", slot=2, received_at="now")
    duplicate = tracker.update(fun(q=999), event_id="sig:0", slot=2, received_at="now")
    assert duplicate["status"] == "DUPLICATE"
    tracker.update(fun(q=999), event_id="older:0", slot=1, received_at="now")
    assert tracker.latest["mint"] == first


def test_amm_requires_actual_quote_transfer_not_gross_quote_budget():
    event = PumpSwapTrade(1, "pool", "user", True, 50, 100, 1000, 2000, 300)
    tracker = LocalReserveTracker()
    unknown = tracker.update(event, event_id="sig:0", slot=1, received_at="now")
    assert unknown["expected_reserves_after"] is None
    inferred = tracker.update(
        replace(event, pool_base_token_reserves=950),
        event_id="sig:1",
        slot=1,
        received_at="now",
        mutation={"real_token": 900, "real_quote": 2099, "virtual_offset": 300},
    )
    assert inferred["expected_reserves_after"]["real_quote"] == 2099
    assert inferred["coverage_complete"] is False


def test_anomaly_selection_is_separate_by_venue_and_preserves_same_slot():
    samples = [
        {
            "mint": str(i),
            "stream_monotonic_timestamp": i,
            "venue": "pump_fun",
            "slot_delta": 1,
            "stream_rpc_price_disagreement_percent": i,
        }
        for i in range(15)
    ]
    swap = {
        "mint": "swap",
        "stream_monotonic_timestamp": 16,
        "venue": "pump_swap",
        "slot_delta": 0,
        "stream_rpc_price_disagreement_percent": 570,
    }
    selected = select_anomalies([*samples, swap])
    assert len([s for s in selected if s["venue"] == "pump_fun"]) == 10
    assert swap in selected
    assert "sendTransaction" not in ForensicRpc.METHODS


def test_two_trades_in_one_transaction_need_instruction_state_not_whole_tx_pre():
    from copy import deepcopy

    from memebot.providers.solana.pump_idl import PUMP_AMM_PROGRAM_ID

    def balance(idx, amount, mint):
        return {
            "accountIndex": idx,
            "owner": "pool",
            "mint": mint,
            "uiTokenAmount": {"amount": str(amount)},
        }

    common = {
        "venue": "pump_swap",
        "signature": "sig",
        "event": {"pool": "pool"},
        "semantic": "UNKNOWN",
        "account_keys": ["pool", "base_vault", "quote_vault", PUMP_AMM_PROGRAM_ID],
        "pre_token_balances": [balance(1, 1000, "base"), balance(2, 2000, "quote")],
        "post_token_balances": [balance(1, 900, "base"), balance(2, 2197, "quote")],
        "instructions": [{"programIdIndex": 3, "accounts": [0, 1, 2]}] * 2,
    }
    rows = [
        {
            **deepcopy(common),
            "event_ordinal": 0,
            "reported_reserves": {"real_token": 1000, "real_quote": 2000, "virtual_offset": 300},
            "expected_post_from_event_fields": {
                "real_token": 950,
                "real_quote": 2099,
                "virtual_offset": 300,
            },
        },
        {
            **deepcopy(common),
            "event_ordinal": 1,
            "reported_reserves": {"real_token": 950, "real_quote": 2099, "virtual_offset": 300},
            "expected_post_from_event_fields": {
                "real_token": 900,
                "real_quote": 2197,
                "virtual_offset": 300,
            },
        },
    ]
    verify_semantics(rows, {})
    assert [r["semantic"] for r in rows] == ["PRE_TRADE", "PRE_TRADE"]
    assert [r["instruction_index"] for r in rows] == [0, 1]
    broken = deepcopy(rows)
    for r in broken:
        r["semantic"] = "UNKNOWN"
        r["post_token_balances"][1]["uiTokenAmount"]["amount"] = "2198"
    verify_semantics(broken, {})
    assert all(r["semantic"] == "UNKNOWN" for r in broken)
