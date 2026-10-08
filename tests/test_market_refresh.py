import base64
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from memebot.models.market import LaunchVenue, MarketLifecycle
from memebot.paper.market_refresh import SolanaRpcMarketSnapshotRefresher
from memebot.paper.models import ExecutionMarketSnapshot
from memebot.providers.solana.base import RpcAccount
from memebot.providers.solana.encoding import BASE58_ALPHABET, encode_base58
from memebot.providers.solana.pump_idl import (
    BONDING_CURVE_ACCOUNT_DISCRIMINATOR,
    NATIVE_SOL_MINT,
    POOL_ACCOUNT_DISCRIMINATOR,
    PUMP_AMM_PROGRAM_ID,
    PUMP_PROGRAM_ID,
    TOKEN_PROGRAM_ID,
    WRAPPED_SOL_MINT,
)


class FakeRpc:
    def __init__(self, accounts: dict[str, RpcAccount]) -> None:
        self.accounts = accounts

    async def get_account(self, address: str, _commitment: str) -> RpcAccount | None:
        return self.accounts.get(address)

    async def get_multiple_accounts(
        self, addresses: list[str], _commitment: str
    ) -> tuple[RpcAccount | None, ...]:
        return tuple(self.accounts.get(address) for address in addresses)


def _u(value: int, size: int, *, signed: bool = False) -> bytes:
    return value.to_bytes(size, "little", signed=signed)


def _decode_base58(value: str) -> bytes:
    number = 0
    for character in value:
        number = number * 58 + BASE58_ALPHABET.index(character)
    decoded = number.to_bytes((number.bit_length() + 7) // 8, "big") if number else b""
    return b"\0" * (len(value) - len(value.lstrip("1"))) + decoded


def _account(address: str, owner: str, slot: int, data: bytes) -> RpcAccount:
    return RpcAccount(
        address=address,
        slot=slot,
        owner=owner,
        lamports=1,
        executable=False,
        data_base64=base64.b64encode(data).decode(),
    )


def _market(*, mint: str, address: str) -> ExecutionMarketSnapshot:
    return ExecutionMarketSnapshot(
        mint=mint,
        market=address,
        venue=LaunchVenue.PUMP_FUN,
        lifecycle=MarketLifecycle.BONDING_CURVE,
        observed_at=datetime(2026, 8, 22, tzinfo=UTC),
        source_slot=1,
        observed_price_raw=Decimal("1"),
        quote_asset=WRAPPED_SOL_MINT,
        real_token_reserves_raw=1,
        real_quote_reserves_raw=1,
        virtual_token_reserves_raw=1,
        virtual_quote_reserves_raw=1,
    )


@pytest.mark.asyncio
async def test_refreshes_pump_bonding_curve_without_waiting_for_trade() -> None:
    market_address = encode_base58(bytes([2]) * 32)
    creator = bytes([3]) * 32
    # Pump bonding curves encode native SOL while normalized trade snapshots use WSOL.
    quote = _decode_base58(NATIVE_SOL_MINT)
    data = b"".join(
        [
            BONDING_CURVE_ACCOUNT_DISCRIMINATOR,
            _u(1_000, 8),
            _u(2_500, 8),
            _u(800, 8),
            _u(2_000, 8),
            _u(10_000, 8),
            b"\0",
            creator,
            b"\0\0",
            quote,
        ]
    )
    rpc = FakeRpc({market_address: _account(market_address, PUMP_PROGRAM_ID, 42, data)})

    original = replace(
        _market(mint=encode_base58(bytes([1]) * 32), address=market_address),
        feed_timestamp=datetime(2026, 8, 22, tzinfo=UTC),
        feed_reference_price=Decimal(1),
    )
    refreshed = await SolanaRpcMarketSnapshotRefresher(
        rpc, commitment="confirmed", source_name="rpc_exit_reserves", bootstrap_identity=False
    ).refresh(original)

    assert refreshed.source_slot == 42
    assert refreshed.virtual_token_reserves_raw == 1_000
    assert refreshed.virtual_quote_reserves_raw == 2_500
    assert refreshed.observed_price_raw == Decimal("2.5")
    assert refreshed.observed_at > datetime(2026, 8, 22, tzinfo=UTC)
    assert refreshed.feed_timestamp == original.feed_timestamp
    assert refreshed.source_timestamp is None
    assert refreshed.received_timestamp == refreshed.observed_at
    assert refreshed.price_source_disagreement_pct == Decimal(150)
    assert refreshed.price_source == "rpc_exit_reserves"


@pytest.mark.asyncio
@pytest.mark.parametrize("recover", [False, True])
async def test_refreshes_pump_swap_vault_reserves(recover: bool) -> None:
    raw_mint = bytes([4]) * 32
    mint = encode_base58(raw_mint)
    raw_quote = _decode_base58(WRAPPED_SOL_MINT)
    market_address = encode_base58(bytes([5]) * 32)
    base_vault = encode_base58(bytes([6]) * 32)
    quote_vault = encode_base58(bytes([7]) * 32)
    pool_data = b"".join(
        [
            POOL_ACCOUNT_DISCRIMINATOR,
            _u(1, 1),
            _u(0, 2),
            bytes([8]) * 32,
            raw_mint,
            raw_quote,
            bytes([9]) * 32,
            _decode_base58(base_vault),
            _decode_base58(quote_vault),
            _u(1_000, 8),
            bytes([10]) * 32,
            b"\0\0",
            _u(500, 16, signed=True),
        ]
    )
    base_data = raw_mint + _decode_base58(market_address) + _u(2_000, 8)
    quote_data = raw_quote + _decode_base58(market_address) + _u(3_500, 8)
    rpc = FakeRpc(
        {
            market_address: _account(market_address, PUMP_AMM_PROGRAM_ID, 50, pool_data),
            base_vault: _account(base_vault, TOKEN_PROGRAM_ID, 52, base_data),
            quote_vault: _account(quote_vault, TOKEN_PROGRAM_ID, 52, quote_data),
        }
    )

    curve_address = encode_base58(bytes([13]) * 32)
    completed_curve = (
        BONDING_CURVE_ACCOUNT_DISCRIMINATOR
        + _u(0, 8) * 4
        + _u(10_000, 8)
        + b"\1"
        + bytes([3]) * 32
        + b"\0\0"
        + _decode_base58(NATIVE_SOL_MINT)
    )
    rpc.accounts[curve_address] = _account(curve_address, PUMP_PROGRAM_ID, 42, completed_curve)

    class Lookup:
        async def pools(self, _mint: str) -> tuple[str, ...]:
            return (market_address,)

    recovered = []

    async def record(snapshot: ExecutionMarketSnapshot) -> None:
        from memebot.paper.recovery import recovery_event

        recovered.append(recovery_event(snapshot))

    refresher = SolanaRpcMarketSnapshotRefresher(
        rpc,
        commitment="confirmed",
        pool_lookup=Lookup(),
        on_recovered=record,
        bootstrap_identity=False,
    )
    initial = _market(mint=mint, address=curve_address if recover else market_address)
    refreshed = await refresher.refresh(initial)

    assert refreshed.source_slot == 52
    assert refreshed.real_token_reserves_raw == 2_000
    assert refreshed.real_quote_reserves_raw == 3_500
    assert refreshed.virtual_token_reserves_raw is None
    assert refreshed.virtual_quote_reserves_raw == 500
    assert refreshed.observed_price_raw == Decimal("2")
    assert refreshed.market == market_address
    assert refreshed.curve_complete is False
    assert len(recovered) == int(recover)
    if recover:
        # A lookup suggestion cannot substitute a pool for another token.
        invalid = _market(mint=encode_base58(bytes([20]) * 32), address=curve_address)
        rejected = await refresher.refresh_with_diagnostics(invalid)
        assert rejected.status == "not_refreshed"
        assert rejected.market.market == curve_address
        assert rejected.market.curve_complete is True
        assert rejected.market.observed_at == invalid.observed_at
        assert len(recovered) == 1
