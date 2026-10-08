"""Candidate-only RPC calibration; never assume virtual reserves are real liquidity."""

from __future__ import annotations

import base64
from dataclasses import dataclass

from memebot.providers.solana.base import SolanaRpcProvider
from memebot.providers.solana.pump import extract_anchor_events
from memebot.providers.solana.pump_idl import (
    PUMP_PROGRAM_ID,
    PumpCreate,
    decode_bonding_curve_account,
)


@dataclass(frozen=True)
class CurveCalibration:
    initial_real_tokens: int | None
    token_offset: int
    quote_offset: int


async def calibrate_curve(
    rpc: SolanaRpcProvider, mint: str, curve: str, signature: str | None
) -> CurveCalibration | None:
    account = await rpc.get_account(curve, "confirmed")
    if account is None or account.owner != PUMP_PROGRAM_ID:
        return None
    state = decode_bonding_curve_account(base64.b64decode(account.data_base64, validate=True))
    if state.is_mayhem_mode or state.complete:
        return None
    initial = None
    if signature:
        transaction = await rpc.get_transaction(signature, "confirmed")
        meta = transaction.get("meta") if transaction else None
        logs = meta.get("logMessages") if isinstance(meta, dict) else None
        if isinstance(logs, list) and all(isinstance(line, str) for line in logs):
            for _, event in extract_anchor_events(logs):
                if (
                    isinstance(event, PumpCreate)
                    and event.mint == mint
                    and event.bonding_curve == curve
                ):
                    initial = event.real_token_reserves
    return CurveCalibration(
        initial,
        state.virtual_token_reserves - state.real_token_reserves,
        state.virtual_quote_reserves - state.real_quote_reserves,
    )
