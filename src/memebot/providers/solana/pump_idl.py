from __future__ import annotations

from dataclasses import dataclass

from memebot.providers.solana.encoding import BorshDecodeError, BorshReader, encode_base58

PUMP_PROGRAM_ID = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
PUMP_AMM_PROGRAM_ID = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
NATIVE_SOL_MINT = "11111111111111111111111111111111"
WRAPPED_SOL_MINT = "So11111111111111111111111111111111111111112"
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM_ID = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"

# Runtime schemas are pinned to this immutable revision of pump-public-docs.
IDL_REPOSITORY = "https://github.com/pump-fun/pump-public-docs"
IDL_COMMIT = "9c82f61cb711b044a17f770ab8ce9f9bdf78f333"
PUMP_IDL_SHA256 = "b90bc471327f671449271d5d1d42354d1fae6f5a06502f5834459a3108138e49"
PUMP_AMM_IDL_SHA256 = "6b5c7ec4e5ef9742fa99dc57b0d75b1031b379bba02a7e1b3c5a4cad68d77e56"

CREATE_EVENT_DISCRIMINATOR = bytes([27, 114, 169, 77, 222, 235, 99, 118])
TRADE_EVENT_DISCRIMINATOR = bytes([189, 219, 127, 211, 78, 230, 97, 238])
COMPLETE_EVENT_DISCRIMINATOR = bytes([95, 114, 97, 156, 212, 46, 152, 8])
MIGRATION_EVENT_DISCRIMINATOR = bytes([189, 233, 93, 185, 92, 148, 234, 148])
CREATE_POOL_EVENT_DISCRIMINATOR = bytes([177, 49, 12, 210, 160, 118, 167, 116])
BUY_EVENT_DISCRIMINATOR = bytes([103, 244, 82, 31, 44, 245, 119, 119])
SELL_EVENT_DISCRIMINATOR = bytes([62, 47, 55, 10, 165, 3, 220, 42])
BONDING_CURVE_ACCOUNT_DISCRIMINATOR = bytes([23, 183, 248, 55, 96, 216, 172, 96])
POOL_ACCOUNT_DISCRIMINATOR = bytes([241, 154, 109, 4, 17, 177, 109, 188])


@dataclass(frozen=True, slots=True)
class PumpCreate:
    name: str
    symbol: str
    uri: str
    mint: str
    bonding_curve: str
    user: str
    creator: str
    timestamp: int
    virtual_token_reserves: int
    virtual_quote_reserves: int
    real_token_reserves: int
    token_total_supply: int
    token_program: str
    is_mayhem_mode: bool
    is_cashback_enabled: bool
    quote_mint: str


@dataclass(frozen=True, slots=True)
class PumpTrade:
    mint: str
    quote_amount: int
    token_amount: int
    is_buy: bool
    user: str
    timestamp: int
    virtual_token_reserves: int
    virtual_quote_reserves: int
    real_token_reserves: int
    real_quote_reserves: int
    quote_mint: str
    is_mayhem_mode: bool | None = None
    instruction_name: str | None = None


@dataclass(frozen=True, slots=True)
class PumpComplete:
    user: str
    mint: str
    bonding_curve: str
    timestamp: int
    quote_mint: str


@dataclass(frozen=True, slots=True)
class PumpMayhemUpdate:
    timestamp: int
    mint: str
    virtual_token_reserves: int
    virtual_quote_reserves: int
    new_virtual_token_reserves: int
    new_virtual_quote_reserves: int
    real_token_reserves: int
    real_quote_reserves: int


@dataclass(frozen=True, slots=True)
class PumpMigration:
    user: str
    mint: str
    mint_amount: int
    quote_amount: int
    pool_migration_fee: int
    bonding_curve: str
    timestamp: int
    pool: str
    quote_mint: str


@dataclass(frozen=True, slots=True)
class PumpSwapPoolCreated:
    timestamp: int
    index: int
    creator: str
    base_mint: str
    quote_mint: str
    pool: str
    coin_creator: str
    is_mayhem_mode: bool


@dataclass(frozen=True, slots=True)
class PumpSwapTrade:
    timestamp: int
    pool: str
    user: str
    is_buy: bool
    base_amount: int
    quote_amount: int
    pool_base_token_reserves: int
    pool_quote_token_reserves: int
    virtual_quote_reserves: int
    quote_vault_transfer: int | None = None


@dataclass(frozen=True, slots=True)
class BondingCurveAccount:
    virtual_token_reserves: int
    virtual_quote_reserves: int
    real_token_reserves: int
    real_quote_reserves: int
    token_total_supply: int
    complete: bool
    creator: str
    is_mayhem_mode: bool
    is_cashback_coin: bool
    quote_mint: str


@dataclass(frozen=True, slots=True)
class PoolAccount:
    pool_bump: int
    index: int
    creator: str
    base_mint: str
    quote_mint: str
    lp_mint: str
    pool_base_token_account: str
    pool_quote_token_account: str
    lp_supply: int
    coin_creator: str
    is_mayhem_mode: bool
    is_cashback_coin: bool
    virtual_quote_reserves: int


@dataclass(frozen=True, slots=True)
class TokenAccountBalance:
    mint: str
    owner: str
    amount: int


@dataclass(frozen=True, slots=True)
class MintAccountState:
    mint_authority: str | None
    supply: int
    decimals: int
    initialized: bool
    freeze_authority: str | None


PumpAnchorEvent = (
    PumpCreate
    | PumpTrade
    | PumpComplete
    | PumpMigration
    | PumpSwapPoolCreated
    | PumpSwapTrade
    | PumpMayhemUpdate
)


def _require_discriminator(data: bytes, expected: bytes) -> BorshReader:
    if not data.startswith(expected):
        raise BorshDecodeError("unexpected Anchor discriminator")
    return BorshReader(data[8:])


def _decode_create(data: bytes) -> PumpCreate:
    reader = _require_discriminator(data, CREATE_EVENT_DISCRIMINATOR)
    return PumpCreate(
        name=reader.string(maximum_bytes=128),
        symbol=reader.string(maximum_bytes=32),
        uri=reader.string(maximum_bytes=1024),
        mint=reader.pubkey(),
        bonding_curve=reader.pubkey(),
        user=reader.pubkey(),
        creator=reader.pubkey(),
        timestamp=reader.i64(),
        virtual_token_reserves=reader.u64(),
        virtual_quote_reserves=reader.u64(),
        real_token_reserves=reader.u64(),
        token_total_supply=reader.u64(),
        token_program=reader.pubkey(),
        is_mayhem_mode=reader.boolean(),
        is_cashback_enabled=reader.boolean(),
        quote_mint=reader.pubkey(),
    )


def _decode_trade(data: bytes) -> PumpTrade:
    reader = _require_discriminator(data, TRADE_EVENT_DISCRIMINATOR)
    mint = reader.pubkey()
    _legacy_sol_amount = reader.u64()
    token_amount = reader.u64()
    is_buy = reader.boolean()
    user = reader.pubkey()
    timestamp = reader.i64()
    _virtual_sol_reserves = reader.u64()
    virtual_token_reserves = reader.u64()
    _real_sol_reserves = reader.u64()
    real_token_reserves = reader.u64()
    _fee_recipient = reader.pubkey()
    _fee_basis_points = reader.u64()
    _fee = reader.u64()
    _creator = reader.pubkey()
    _creator_fee_basis_points = reader.u64()
    _creator_fee = reader.u64()
    _track_volume = reader.boolean()
    _total_unclaimed_tokens = reader.u64()
    _total_claimed_tokens = reader.u64()
    _current_sol_volume = reader.u64()
    _last_update_timestamp = reader.i64()
    ix_name = reader.string(maximum_bytes=64)
    mayhem_mode = reader.boolean()
    _cashback_fee_basis_points = reader.u64()
    _cashback = reader.u64()
    _buyback_fee_basis_points = reader.u64()
    _buyback_fee = reader.u64()
    shareholder_count = reader.u32()
    if shareholder_count > 1024:
        raise BorshDecodeError("shareholder vector exceeds safety limit")
    # Shareholder is {address: pubkey, share_bps: u16} in the pinned IDL.
    for _ in range(shareholder_count):
        reader.pubkey()
        reader.u16()
    quote_mint = reader.pubkey()
    quote_amount = reader.u64()
    virtual_quote_reserves = reader.u64()
    real_quote_reserves = reader.u64()
    return PumpTrade(
        mint=mint,
        quote_amount=quote_amount,
        token_amount=token_amount,
        is_buy=is_buy,
        user=user,
        timestamp=timestamp,
        virtual_token_reserves=virtual_token_reserves,
        virtual_quote_reserves=virtual_quote_reserves,
        real_token_reserves=real_token_reserves,
        real_quote_reserves=real_quote_reserves,
        quote_mint=quote_mint,
        is_mayhem_mode=mayhem_mode,
        instruction_name=ix_name,
    )


def _decode_complete(data: bytes) -> PumpComplete:
    reader = _require_discriminator(data, COMPLETE_EVENT_DISCRIMINATOR)
    return PumpComplete(
        user=reader.pubkey(),
        mint=reader.pubkey(),
        bonding_curve=reader.pubkey(),
        timestamp=reader.i64(),
        quote_mint=reader.pubkey(),
    )


def _decode_migration(data: bytes) -> PumpMigration:
    reader = _require_discriminator(data, MIGRATION_EVENT_DISCRIMINATOR)
    return PumpMigration(
        user=reader.pubkey(),
        mint=reader.pubkey(),
        mint_amount=reader.u64(),
        quote_amount=reader.u64(),
        pool_migration_fee=reader.u64(),
        bonding_curve=reader.pubkey(),
        timestamp=reader.i64(),
        pool=reader.pubkey(),
        quote_mint=reader.pubkey(),
    )


def _decode_pool_created(data: bytes) -> PumpSwapPoolCreated:
    reader = _require_discriminator(data, CREATE_POOL_EVENT_DISCRIMINATOR)
    timestamp = reader.i64()
    index = reader.u16()
    creator = reader.pubkey()
    base_mint = reader.pubkey()
    quote_mint = reader.pubkey()
    reader.u8()  # base mint decimals
    reader.u8()  # quote mint decimals
    reader.u64()  # base amount in
    reader.u64()  # quote amount in
    reader.u64()  # pool base amount
    reader.u64()  # pool quote amount
    reader.u64()  # minimum liquidity
    reader.u64()  # initial liquidity
    reader.u64()  # LP token amount out
    reader.u8()  # pool bump
    pool = reader.pubkey()
    reader.pubkey()  # LP mint
    reader.pubkey()  # user base token account
    reader.pubkey()  # user quote token account
    coin_creator = reader.pubkey()
    is_mayhem_mode = reader.boolean()
    return PumpSwapPoolCreated(
        timestamp=timestamp,
        index=index,
        creator=creator,
        base_mint=base_mint,
        quote_mint=quote_mint,
        pool=pool,
        coin_creator=coin_creator,
        is_mayhem_mode=is_mayhem_mode,
    )


def _decode_buy(data: bytes) -> PumpSwapTrade:
    reader = _require_discriminator(data, BUY_EVENT_DISCRIMINATOR)
    timestamp = reader.i64()
    base_amount = reader.u64()
    reader.u64()  # maximum quote amount in
    reader.u64()  # user base reserves
    reader.u64()  # user quote reserves
    pool_base_reserves = reader.u64()
    pool_quote_reserves = reader.u64()
    quote_amount = reader.u64()
    reader.u64()  # LP fee basis points
    reader.u64()  # LP fee
    reader.u64()  # protocol fee basis points
    reader.u64()  # protocol fee
    quote_vault_transfer = reader.u64()  # actual quote amount in with LP fee
    reader.u64()  # user quote amount in
    pool = reader.pubkey()
    user = reader.pubkey()
    reader.pubkey()  # user base token account
    reader.pubkey()  # user quote token account
    reader.pubkey()  # protocol fee recipient
    reader.pubkey()  # protocol fee recipient token account
    reader.pubkey()  # coin creator
    reader.u64()  # coin creator fee basis points
    reader.u64()  # coin creator fee
    reader.boolean()  # track volume
    reader.u64()  # total unclaimed tokens
    reader.u64()  # total claimed tokens
    reader.u64()  # current SOL volume
    reader.i64()  # last update timestamp
    reader.u64()  # minimum base amount out
    reader.string(maximum_bytes=64)  # instruction name
    reader.u64()  # cashback fee basis points
    reader.u64()  # cashback
    reader.u64()  # buyback fee basis points
    reader.u64()  # buyback fee
    virtual_quote_reserves = reader.i128()
    reader.boolean()  # can boost
    reader.u64()  # base supply
    return PumpSwapTrade(
        timestamp=timestamp,
        pool=pool,
        user=user,
        is_buy=True,
        base_amount=base_amount,
        quote_amount=quote_amount,
        pool_base_token_reserves=pool_base_reserves,
        pool_quote_token_reserves=pool_quote_reserves,
        virtual_quote_reserves=virtual_quote_reserves,
        quote_vault_transfer=quote_vault_transfer,
    )


def _decode_sell(data: bytes) -> PumpSwapTrade:
    reader = _require_discriminator(data, SELL_EVENT_DISCRIMINATOR)
    timestamp = reader.i64()
    base_amount = reader.u64()
    reader.u64()  # minimum quote amount out
    reader.u64()  # user base reserves
    reader.u64()  # user quote reserves
    pool_base_reserves = reader.u64()
    pool_quote_reserves = reader.u64()
    quote_amount = reader.u64()
    reader.u64()  # LP fee basis points
    reader.u64()  # LP fee
    reader.u64()  # protocol fee basis points
    reader.u64()  # protocol fee
    quote_vault_transfer = reader.u64()  # actual quote amount out without LP fee
    reader.u64()  # user quote amount out
    pool = reader.pubkey()
    user = reader.pubkey()
    reader.pubkey()  # user base token account
    reader.pubkey()  # user quote token account
    reader.pubkey()  # protocol fee recipient
    reader.pubkey()  # protocol fee recipient token account
    reader.pubkey()  # coin creator
    reader.u64()  # coin creator fee basis points
    reader.u64()  # coin creator fee
    reader.u64()  # cashback fee basis points
    reader.u64()  # cashback
    reader.u64()  # buyback fee basis points
    reader.u64()  # buyback fee
    virtual_quote_reserves = reader.i128()
    reader.boolean()  # can boost
    reader.u64()  # base supply
    return PumpSwapTrade(
        timestamp=timestamp,
        pool=pool,
        user=user,
        is_buy=False,
        base_amount=base_amount,
        quote_amount=quote_amount,
        pool_base_token_reserves=pool_base_reserves,
        pool_quote_token_reserves=pool_quote_reserves,
        virtual_quote_reserves=virtual_quote_reserves,
        quote_vault_transfer=quote_vault_transfer,
    )


def decode_anchor_event(program_id: str, data: bytes) -> PumpAnchorEvent | None:
    """Decode only the Phase 1 event subset from the pinned official IDLs."""
    discriminator = data[:8]
    if program_id == PUMP_PROGRAM_ID:
        if discriminator == bytes([117, 123, 228, 182, 161, 168, 220, 214]):
            reader = BorshReader(data[8:])
            return PumpMayhemUpdate(
                reader.i64(),
                reader.pubkey(),
                reader.u64(),
                reader.u64(),
                reader.u64(),
                reader.u64(),
                reader.u64(),
                reader.u64(),
            )
        if discriminator == CREATE_EVENT_DISCRIMINATOR:
            return _decode_create(data)
        if discriminator == TRADE_EVENT_DISCRIMINATOR:
            return _decode_trade(data)
        if discriminator == COMPLETE_EVENT_DISCRIMINATOR:
            return _decode_complete(data)
        if discriminator == MIGRATION_EVENT_DISCRIMINATOR:
            return _decode_migration(data)
    if program_id == PUMP_AMM_PROGRAM_ID:
        if discriminator == CREATE_POOL_EVENT_DISCRIMINATOR:
            return _decode_pool_created(data)
        if discriminator == BUY_EVENT_DISCRIMINATOR:
            return _decode_buy(data)
        if discriminator == SELL_EVENT_DISCRIMINATOR:
            return _decode_sell(data)
    return None


def decode_bonding_curve_account(data: bytes) -> BondingCurveAccount:
    reader = _require_discriminator(data, BONDING_CURVE_ACCOUNT_DISCRIMINATOR)
    return BondingCurveAccount(
        virtual_token_reserves=reader.u64(),
        virtual_quote_reserves=reader.u64(),
        real_token_reserves=reader.u64(),
        real_quote_reserves=reader.u64(),
        token_total_supply=reader.u64(),
        complete=reader.boolean(),
        creator=reader.pubkey(),
        is_mayhem_mode=reader.boolean(),
        is_cashback_coin=reader.boolean(),
        quote_mint=reader.pubkey(),
    )


def decode_pool_account(data: bytes) -> PoolAccount:
    reader = _require_discriminator(data, POOL_ACCOUNT_DISCRIMINATOR)
    return PoolAccount(
        pool_bump=reader.u8(),
        index=reader.u16(),
        creator=reader.pubkey(),
        base_mint=reader.pubkey(),
        quote_mint=reader.pubkey(),
        lp_mint=reader.pubkey(),
        pool_base_token_account=reader.pubkey(),
        pool_quote_token_account=reader.pubkey(),
        lp_supply=reader.u64(),
        coin_creator=reader.pubkey(),
        is_mayhem_mode=reader.boolean(),
        is_cashback_coin=reader.boolean(),
        virtual_quote_reserves=reader.i128(),
    )


def decode_token_account(data: bytes) -> TokenAccountBalance:
    """Decode the common 72-byte prefix of SPL Token and Token-2022 accounts."""
    if len(data) < 72:
        raise BorshDecodeError("truncated SPL token account")
    return TokenAccountBalance(
        mint=encode_base58(data[0:32]),
        owner=encode_base58(data[32:64]),
        amount=int.from_bytes(data[64:72], "little"),
    )


def decode_mint_account(data: bytes) -> MintAccountState:
    """Decode the common SPL Token and Token-2022 mint prefix."""
    if len(data) < 82:
        raise BorshDecodeError("truncated SPL mint account")
    mint_authority_option = int.from_bytes(data[0:4], "little")
    freeze_authority_option = int.from_bytes(data[46:50], "little")
    if mint_authority_option not in {0, 1} or freeze_authority_option not in {0, 1}:
        raise BorshDecodeError("invalid SPL mint authority option")
    initialized = data[45]
    if initialized not in {0, 1}:
        raise BorshDecodeError("invalid SPL mint initialization flag")
    return MintAccountState(
        mint_authority=(encode_base58(data[4:36]) if mint_authority_option else None),
        supply=int.from_bytes(data[36:44], "little"),
        decimals=data[44],
        initialized=bool(initialized),
        freeze_authority=(encode_base58(data[50:82]) if freeze_authority_option else None),
    )
