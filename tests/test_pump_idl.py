import base64

from memebot.providers.solana.encoding import encode_base58
from memebot.providers.solana.pump import extract_anchor_events
from memebot.providers.solana.pump_idl import (
    BONDING_CURVE_ACCOUNT_DISCRIMINATOR,
    BUY_EVENT_DISCRIMINATOR,
    CREATE_EVENT_DISCRIMINATOR,
    PUMP_AMM_PROGRAM_ID,
    PUMP_PROGRAM_ID,
    TRADE_EVENT_DISCRIMINATOR,
    PumpCreate,
    PumpSwapTrade,
    PumpTrade,
    decode_anchor_event,
    decode_bonding_curve_account,
    decode_mint_account,
)


def _number(value: int, size: int, *, signed: bool = False) -> bytes:
    return value.to_bytes(size, "little", signed=signed)


def _string(value: str) -> bytes:
    encoded = value.encode()
    return _number(len(encoded), 4) + encoded


def _pubkey(seed: int) -> tuple[bytes, str]:
    raw = bytes([seed]) * 32
    return raw, encode_base58(raw)


def _create_payload() -> tuple[bytes, dict[str, str]]:
    mint, mint_text = _pubkey(1)
    curve, curve_text = _pubkey(2)
    user, _ = _pubkey(3)
    creator, creator_text = _pubkey(4)
    token_program, _ = _pubkey(5)
    quote_mint, quote_text = _pubkey(6)
    payload = b"".join(
        [
            CREATE_EVENT_DISCRIMINATOR,
            _string("Research Coin"),
            _string("RCH"),
            _string("https://example.invalid/metadata.json"),
            mint,
            curve,
            user,
            creator,
            _number(1_777_000_000, 8, signed=True),
            _number(1_073_000_000, 8),
            _number(30_000_000_000, 8),
            _number(793_100_000, 8),
            _number(1_000_000_000, 8),
            token_program,
            b"\x00",
            b"\x01",
            quote_mint,
            _number(30_000_000_000, 8),
        ]
    )
    return payload, {
        "mint": mint_text,
        "curve": curve_text,
        "creator": creator_text,
        "quote": quote_text,
    }


def test_decodes_pinned_create_event_and_log_context() -> None:
    payload, expected = _create_payload()
    event = decode_anchor_event(PUMP_PROGRAM_ID, payload)

    assert isinstance(event, PumpCreate)
    assert event.mint == expected["mint"]
    assert event.bonding_curve == expected["curve"]
    assert event.creator == expected["creator"]
    assert event.quote_mint == expected["quote"]
    assert event.name == "Research Coin"

    logs = [
        f"Program {PUMP_PROGRAM_ID} invoke [1]",
        f"Program data: {base64.b64encode(payload).decode()}",
        f"Program {PUMP_PROGRAM_ID} success",
    ]
    extracted = extract_anchor_events(logs)
    assert len(extracted) == 1
    assert isinstance(extracted[0][1], PumpCreate)


def test_decodes_current_trade_tail_after_shareholders() -> None:
    mint, mint_text = _pubkey(7)
    user, _ = _pubkey(8)
    fee_recipient, _ = _pubkey(9)
    creator, _ = _pubkey(10)
    shareholder, _ = _pubkey(11)
    quote_mint, quote_text = _pubkey(12)
    payload = b"".join(
        [
            TRADE_EVENT_DISCRIMINATOR,
            mint,
            _number(100, 8),
            _number(200, 8),
            b"\x01",
            user,
            _number(1_777_000_001, 8, signed=True),
            _number(300, 8),
            _number(400, 8),
            _number(500, 8),
            _number(600, 8),
            fee_recipient,
            _number(100, 8),
            _number(3, 8),
            creator,
            _number(50, 8),
            _number(2, 8),
            b"\x01",
            _number(0, 8),
            _number(0, 8),
            _number(100, 8),
            _number(1_777_000_001, 8, signed=True),
            _string("buy"),
            b"\x00",
            _number(0, 8),
            _number(0, 8),
            _number(0, 8),
            _number(0, 8),
            _number(1, 4),
            shareholder,
            _number(2500, 2),
            quote_mint,
            _number(101, 8),
            _number(700, 8),
            _number(800, 8),
        ]
    )

    event = decode_anchor_event(PUMP_PROGRAM_ID, payload)

    assert isinstance(event, PumpTrade)
    assert event.mint == mint_text
    assert event.quote_mint == quote_text
    assert event.quote_amount == 101
    assert event.real_quote_reserves == 800


def test_decodes_and_validates_bonding_curve_account_layout() -> None:
    creator, creator_text = _pubkey(13)
    quote, quote_text = _pubkey(14)
    payload = b"".join(
        [
            BONDING_CURVE_ACCOUNT_DISCRIMINATOR,
            _number(10, 8),
            _number(20, 8),
            _number(30, 8),
            _number(40, 8),
            _number(50, 8),
            b"\x00",
            creator,
            b"\x01",
            b"\x00",
            quote,
        ]
    )

    account = decode_bonding_curve_account(payload)

    assert account.creator == creator_text
    assert account.quote_mint == quote_text
    assert account.real_token_reserves == 30


def test_decodes_pinned_pump_swap_buy_event() -> None:
    pool, pool_text = _pubkey(20)
    user, user_text = _pubkey(21)
    remaining_keys = [_pubkey(seed)[0] for seed in range(22, 27)]
    payload = b"".join(
        [
            BUY_EVENT_DISCRIMINATOR,
            _number(1_777_000_100, 8, signed=True),
            _number(100, 8),
            _number(200, 8),
            _number(10, 8),
            _number(20, 8),
            _number(1000, 8),
            _number(2000, 8),
            _number(150, 8),
            *[_number(0, 8) for _ in range(6)],
            pool,
            user,
            *remaining_keys,
            _number(0, 8),
            _number(0, 8),
            b"\x01",
            _number(0, 8),
            _number(0, 8),
            _number(0, 8),
            _number(1_777_000_100, 8, signed=True),
            _number(90, 8),
            _string("buy"),
            *[_number(0, 8) for _ in range(4)],
            _number(25, 16, signed=True),
            b"\x01",
            _number(1_000_000, 8),
        ]
    )

    event = decode_anchor_event(PUMP_AMM_PROGRAM_ID, payload)

    assert isinstance(event, PumpSwapTrade)
    assert event.is_buy is True
    assert event.pool == pool_text
    assert event.user == user_text
    assert event.base_amount == 100
    assert event.quote_amount == 150
    assert event.pool_base_token_reserves == 1000
    assert event.pool_quote_token_reserves == 2000
    assert event.virtual_quote_reserves == 25


def test_decodes_spl_mint_security_prefix() -> None:
    authority, authority_text = _pubkey(31)
    freeze, freeze_text = _pubkey(32)
    payload = b"".join(
        [
            _number(1, 4),
            authority,
            _number(1_000_000, 8),
            b"\x06",
            b"\x01",
            _number(1, 4),
            freeze,
        ]
    )

    mint = decode_mint_account(payload)

    assert mint.mint_authority == authority_text
    assert mint.freeze_authority == freeze_text
    assert mint.supply == 1_000_000
    assert mint.decimals == 6
    assert mint.initialized is True
