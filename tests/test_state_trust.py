import asyncio
import base64
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from solders.pubkey import Pubkey

from memebot.market_state import InvalidationScope, MarketStateTracker, StateStatus
from memebot.providers.solana.bootstrap import ReadOnlyConfigCache, bootstrap_curve, bootstrap_pool
from memebot.providers.solana.canonical import associated_address, config_addresses, curve_address
from memebot.providers.solana.invalidation import scope_native_mutations
from memebot.providers.solana.pump_idl import (
    NATIVE_SOL_MINT,
    PUMP_AMM_PROGRAM_ID,
    PUMP_PROGRAM_ID,
    TOKEN_PROGRAM_ID,
    BondingCurveAccount,
    PoolAccount,
    PumpTrade,
)
from test_market_refresh import FakeRpc, _account
from test_market_state import identity, swap

MINT = str(Pubkey.from_bytes(bytes([4]) * 32))
CURVE = curve_address(MINT)
NOW = datetime(2026, 10, 1, tzinfo=UTC)


def seed():
    tracker = MarketStateTracker()
    for market in ("pool-a", "pool-b"):
        tracker.observe(swap(), market=market, slot=1, signature=market, ordinal=0)
    event = PumpTrade(MINT, 50, 100, True, MINT, 1, 900, 650, 800, 550, NATIVE_SOL_MINT)
    tracker.observe(event, market=CURVE, slot=1, signature="fun", ordinal=0)
    return tracker


def test_single_market_unsupported_and_provenance_survives_following_tick():
    tracker = seed()
    # An unsupported native instruction still has an exactly decoded market event.
    from unittest.mock import patch

    from memebot.providers.solana.invalidation import NativeFrame

    frame = NativeFrame(PUMP_AMM_PROGRAM_ID, "Unrecognized", [{"name": "x", "pool": "pool-a"}])
    with patch("memebot.providers.solana.invalidation.native_frames", return_value=[frame]):
        scope_native_mutations([], tracker, signature="mutation", slot=2, transaction_index=7)
    record = tracker.invalidations[-1]
    assert record.scope == InvalidationScope.POOL
    assert record.affected_markets == ("pool-a",)
    assert record.signature == "mutation" and record.transaction_index == 7
    assert record.reconciliation_queued
    assert tracker.states["pool-b"].observational_price is not None
    result = tracker.observe(
        swap(pool_base_token_reserves=900, pool_quote_token_reserves=550),
        market="pool-a",
        slot=3,
        signature="next",
        ordinal=0,
    )
    assert result.continuity_status == "UNKNOWN"
    assert result.invalidation_scope == "POOL"
    assert result.invalidation_reason == "UNKNOWN_NATIVE_INSTRUCTION"
    assert len(tracker.reconciliation_requests) == 1


def test_unknown_instruction_without_market_is_venue_scoped():
    tracker = seed()
    scope_native_mutations(
        [
            f"Program {PUMP_AMM_PROGRAM_ID} invoke [1]",
            "Program log: Instruction: Unrecognized",
            f"Program {PUMP_AMM_PROGRAM_ID} success",
        ],
        tracker,
        signature="x",
        slot=2,
    )
    assert tracker.invalidations[-1].scope == InvalidationScope.VENUE
    assert tracker.states[CURVE].observational_price is not None
    assert tracker.states["pool-a"].observational_price is None


def test_unscopable_truncation_retains_global_invalidation():
    tracker = seed()
    scope_native_mutations(["Log truncated"], tracker, signature="x", slot=2)
    assert tracker.invalidations[-1].scope == InvalidationScope.GLOBAL
    assert all(s.observational_price is None for s in tracker.states.values())


def test_silent_self_cpi_uses_parent_market_but_is_not_ignored():
    from unittest.mock import patch

    from memebot.providers.solana.invalidation import NativeFrame

    tracker = seed()
    parent = NativeFrame(PUMP_AMM_PROGRAM_ID, "Buy", [{"name": "BuyEvent", "pool": "pool-a"}])
    child = NativeFrame(PUMP_AMM_PROGRAM_ID, parent=parent)
    with patch("memebot.providers.solana.invalidation.native_frames", return_value=[parent, child]):
        scope_native_mutations([], tracker, signature="x", slot=2)
    assert tracker.invalidations[-1].affected_markets == ("pool-a",)
    assert tracker.states["pool-a"].observational_price is None
    assert tracker.states["pool-b"].observational_price is not None


def test_reserve_repair_cannot_verify_missing_fees_or_execution_assumptions():
    tracker = seed()
    state = tracker.states["pool-a"]
    ident = replace(
        identity(),
        market="pool-a",
        config_verified=False,
        config_version=None,
        execution_assumptions_verified=False,
    )
    assert tracker.reconcile(ident, state, validated=True, now=NOW)
    repaired = tracker.states["pool-a"]
    assert repaired.observational_price is not None
    assert repaired.execution_identity_verified
    assert not repaired.execution_config_verified
    assert repaired.state_quality == StateStatus.INCOMPLETE
    tracker.invalidate("pool-a", "CONFIG_CHANGE", dimensions=("config",))
    assert tracker.states["pool-a"].observational_price is not None
    assert tracker.identities["pool-a"].config_version is None


def test_observationally_safe_state_still_refuses_incomplete_execution():
    from memebot.core.config import Settings
    from memebot.paper.price_safety import entry_data_block
    from test_price_safety import NOW as PRICE_NOW
    from test_price_safety import fresh_market

    tracker = seed()
    state = tracker.states["pool-a"]
    assert state.evidence()["observational_trust"] == "OBSERVATIONAL_HEALTHY"
    assert not state.evidence()["execution_config_verified"]
    market = replace(fresh_market(), normalized_state=state)
    assert entry_data_block(market, PRICE_NOW, Settings(_env_file=None)) == "OUT_OF_SCOPE_PUMPSWAP"


@pytest.mark.asyncio
async def test_curve_canonical_binding_and_wrong_address():
    curve = BondingCurveAccount(
        1000, 2000, 800, 100, 10000, False, MINT, False, False, NATIVE_SOL_MINT
    )
    vault = associated_address(CURVE, MINT, TOKEN_PROGRAM_ID)
    mint_bytes = b"\0" * 36 + (10000).to_bytes(8, "little") + b"\6\1" + b"\0" * 36
    vault_bytes = (
        bytes(Pubkey.from_string(MINT))
        + bytes(Pubkey.from_string(CURVE))
        + (1000).to_bytes(8, "little")
    )
    account = _account(CURVE, PUMP_PROGRAM_ID, 10, b"unused")
    rpc = FakeRpc(
        {
            MINT: _account(MINT, TOKEN_PROGRAM_ID, 11, mint_bytes),
            vault: _account(vault, TOKEN_PROGRAM_ID, 11, vault_bytes),
        }
    )
    proof = await bootstrap_curve(
        rpc, "confirmed", mint=MINT, account=account, curve=curve, config_version=None
    )
    assert proof.identity is not None and proof.identity.canonical_verified
    assert not proof.identity.config_verified and not proof.identity.complete
    assert proof.reserved_token_inventory == 200
    bad = await bootstrap_curve(
        rpc,
        "confirmed",
        mint=MINT,
        account=account.model_copy(update={"address": MINT}),
        curve=curve,
        config_version=None,
    )
    assert bad.identity is None and not bad.checks["curve_pda"]


@pytest.mark.asyncio
async def test_pool_internally_consistent_is_not_canonical():
    pool = PoolAccount(
        1, 0, MINT, MINT, NATIVE_SOL_MINT, MINT, MINT, MINT, 1, MINT, False, False, 0
    )
    account = _account(MINT, PUMP_AMM_PROGRAM_ID, 10, b"unused")
    vault = _account(MINT, TOKEN_PROGRAM_ID, 10, b"unused")
    proof = await bootstrap_pool(
        FakeRpc({}),
        "confirmed",
        account=account,
        pool=pool,
        base_vault=vault,
        quote_vault=vault,
        config_version=None,
    )
    assert proof.identity is None and not proof.checks["pool_pda"]


@pytest.mark.asyncio
async def test_config_cache_coalesces_and_invalidates_version(monkeypatch):
    accounts = {
        address: _account(address, owner, 10, b"version-one")
        for address, owner, _ in config_addresses().values()
    }

    class Rpc(FakeRpc):
        calls = 0

        async def get_multiple_accounts(self, addresses, commitment):
            self.calls += 1
            await asyncio.sleep(0)
            return await super().get_multiple_accounts(addresses, commitment)

    rpc = Rpc(accounts)
    monkeypatch.setattr(
        "memebot.providers.solana.bootstrap.decode_config", lambda *args: ({"fee": 5}, [])
    )
    cache = ReadOnlyConfigCache(rpc, "confirmed")
    await asyncio.gather(cache.ensure({}), cache.ensure({}))
    assert rpc.calls == 1
    old = cache.version("pump_fun")
    for address, value in accounts.items():
        accounts[address] = value.model_copy(
            update={"data_base64": base64.b64encode(b"version-two").decode()}
        )
    await cache.ensure({PUMP_PROGRAM_ID: 1})
    assert rpc.calls == 2 and old != cache.version("pump_fun")
    await cache.ensure({PUMP_PROGRAM_ID: 1})
    assert rpc.calls == 2
