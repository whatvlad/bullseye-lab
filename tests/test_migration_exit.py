import base64
import json
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from memebot.models.market import LaunchVenue, MarketLifecycle
from memebot.models.paper import PositionEffect
from memebot.paper.market_refresh import (
    CurrentPaperMarketRefresher,
    FallbackMarketSnapshotRefresher,
)
from memebot.paper.migration_exit import decode_migration_exit, migration_sell_quote
from memebot.paper.models import ExecutionMarketSnapshot
from memebot.providers.solana.bootstrap import decode_config
from memebot.providers.solana.canonical import curve_address
from memebot.providers.solana.pump_idl import PUMP_AMM_PROGRAM_ID, PUMP_PROGRAM_ID, WRAPPED_SOL_MINT
from test_candidate_proof import record
from test_current_paper_execution import quote, simulator


def fixture():
    retained = json.loads(
        (Path(__file__).parent / "fixtures/aww_migration_atomic.json").read_text()
    )
    market = ExecutionMarketSnapshot(
        retained["mint"],
        curve_address(retained["mint"]),
        LaunchVenue.PUMP_FUN,
        MarketLifecycle.BONDING_CURVE,
        datetime.now(UTC) - timedelta(minutes=30),
        None,
        Decimal(1),
        WRAPPED_SOL_MINT,
        None,
        None,
        None,
        None,
    )
    return market, deepcopy(retained["raw"])


def mutate_record(raw, row_index, program, name, **changes):
    fields, _ = decode_config(program, base64.b64decode(raw["value"][row_index]["data"][0]), name)
    raw["value"][row_index]["data"][0] = base64.b64encode(
        record(program, name, {**fields, **changes})
    ).decode()


def test_migrated_burned_supply_sell_is_fresh_but_new_buy_is_out_of_scope():
    market, raw = fixture()
    at = datetime.now(UTC)
    fresh = decode_migration_exit(market, raw, at.isoformat())
    sell = simulator().simulate_sell(
        fresh,
        quote(at),
        token_amount_raw=Decimal(3214072554134),
        position_effect=PositionEffect.CLOSE,
        exit_reason="stop_loss",
        signal_at=at,
        decision_at=at,
    )
    assert sell.fill is not None
    assert sell.fill.price_source == "atomic_migration_exit"
    assert sell.fill.venue_fee_quote_raw > 0
    assert sell.fill.execution_state["sell_only"] is True
    buy = simulator().simulate_buy(
        fresh, quote(at), requested_portfolio_amount=Decimal(10), signal_at=at, decision_at=at
    )
    assert buy.fill is None and buy.rejection_reason == "OUT_OF_SCOPE_PUMPSWAP"
    stale = simulator().simulate_sell(
        replace(fresh, observed_at=at - timedelta(seconds=10)),
        quote(at),
        token_amount_raw=Decimal(3214072554134),
        position_effect=PositionEffect.CLOSE,
        exit_reason="manual_paper_force_sell",
        signal_at=at,
        decision_at=at,
        allow_stale_market=True,
    )
    assert stale.fill is None and stale.rejection_reason == "market_snapshot_stale"


@pytest.mark.parametrize(
    "index,program,name,changes",
    [
        (1, PUMP_PROGRAM_ID, "BondingCurve", {"complete": False}),
        (1, PUMP_PROGRAM_ID, "BondingCurve", {"is_mayhem_mode": True}),
        (2, PUMP_AMM_PROGRAM_ID, "Pool", {"is_mayhem_mode": True}),
        (2, PUMP_AMM_PROGRAM_ID, "Pool", {"is_holder_reward": True}),
        (2, PUMP_AMM_PROGRAM_ID, "Pool", {"index": 1}),
        (2, PUMP_AMM_PROGRAM_ID, "Pool", {"virtual_quote_reserves": -1}),
        (2, PUMP_AMM_PROGRAM_ID, "Pool", {"pool_base_token_account": WRAPPED_SOL_MINT}),
        (7, PUMP_AMM_PROGRAM_ID, "GlobalConfig", {"disable_flags": 1}),
    ],
)
def test_invalid_or_ineligible_migration_never_authorizes_fill(index, program, name, changes):
    market, raw = fixture()
    mutate_record(raw, index, program, name, **changes)
    with pytest.raises(ValueError):
        decode_migration_exit(market, raw, datetime.now(UTC).isoformat())


@pytest.mark.parametrize(
    "index,mutation", [(2, "owner"), (6, "missing"), (5, "frozen"), (8, "truncated")]
)
def test_atomic_account_failure_is_rejected(index, mutation):
    market, raw = fixture()
    if mutation == "owner":
        raw["value"][index]["owner"] = PUMP_PROGRAM_ID
    elif mutation == "missing":
        raw["value"][index] = None
    else:
        data = bytearray(base64.b64decode(raw["value"][index]["data"][0]))
        if mutation == "frozen":
            data[108] = 2
        else:
            data = data[:10]
        raw["value"][index]["data"][0] = base64.b64encode(data).decode()
    with pytest.raises(ValueError):
        decode_migration_exit(market, raw, datetime.now(UTC).isoformat())


def test_sdk_sell_effective_reserves_and_real_liquidity_cap():
    state = dict(
        reserves=dict(base=1000, quote=1000, offset=200),
        rates=dict(lp_bps=20, protocol_bps=5, creator_bps=30),
    )
    # 1200 * 100 / 1100 = 109; each separate fee is rounded up.
    assert migration_sell_quote(state, 100) == dict(
        token_input=100, gross_output=109, lp_fee=1, protocol_fee=1, creator_fee=1, net_output=106
    )
    state["reserves"]["offset"] = 100000
    with pytest.raises(ValueError):
        migration_sell_quote(state, 100)


@pytest.mark.asyncio
async def test_exit_refresh_uses_fallback_when_primary_is_down():
    market, raw = fixture()
    market = replace(market, curve_complete=True)

    class Down:
        async def _call(self, *args):
            raise TimeoutError()

    class Working:
        async def _call(self, *args):
            return raw

    fresh = await FallbackMarketSnapshotRefresher(
        CurrentPaperMarketRefresher(Down(), for_exit=True),
        CurrentPaperMarketRefresher(Working(), for_exit=True),
    ).refresh(market)
    assert fresh.rpc_state == "healthy" and fresh.venue == LaunchVenue.PUMP_SWAP
    blocked = await CurrentPaperMarketRefresher(Working()).refresh(market)
    assert blocked.execution_state is None


@pytest.mark.asyncio
async def test_both_unavailable_retain_specific_reason_without_old_execution_state():
    market, _ = fixture()
    market = replace(market, curve_complete=True, execution_state={"old": "state"})

    class Down:
        async def _call(self, *args):
            raise TimeoutError()

    result = await FallbackMarketSnapshotRefresher(
        CurrentPaperMarketRefresher(Down(), for_exit=True)
    ).refresh(market)
    assert result.execution_state is None and result.rpc_state == "degraded"
    assert "migration_exit_unavailable:TimeoutError" in result.data_quality
