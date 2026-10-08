import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from memebot.providers.pool_lookup import DexScreenerPoolLookup
from memebot.providers.solana.pump_idl import WRAPPED_SOL_MINT
from memebot.pulse.filters import decode_export, evaluate, load_presets
from memebot.pulse.service import market_row
from memebot.storage.database.models import TokenRecord, TokenTradeRecord


@pytest.mark.parametrize("cap,matched", [(5000, True), (4999, True), (None, True)])
def test_user_export_boundary_and_unknown(cap, matched):
    preset = load_presets(Path("config/pulse.json"))["newPairs"]
    exported = json.dumps(preset).replace(" ", "&#x20;")
    preset = decode_export(exported)
    row = dict(tab="newPairs", protocol="pump", quote="sol", marketCap=cap, stale=False)
    assert evaluate(preset, row).matched is matched
    assert not evaluate(preset, {**row, "protocol": "pumpAmm"}).matched
    assert not evaluate(preset, {**row, "stale": True}).matched
    preset["filters"]["snipers"]["max"] = 20
    assert "unknown:snipers" in evaluate(preset, row).reasons


def test_market_cap_uses_raw_supply_and_never_stale_trade():
    now = datetime.now(UTC)
    token = TokenRecord(
        mint="mint",
        current_market="pool",
        current_lifecycle="bonding_curve",
        first_seen_at=now,
        metadata_json={"token_total_supply": 10**15},
    )
    trade = TokenTradeRecord(
        market_address="pool",
        quote_mint=WRAPPED_SOL_MINT,
        source_event_at=now,
        virtual_token_reserves=10**15,
        virtual_quote_reserves=80_000_000_000,
    )
    args = dict(now=now, sol_usd=Decimal(100), max_age=60, market_venue="pump_fun")
    row = market_row(token, None, trade, None, **args)
    assert row["marketCap"] == Decimal(8000)
    assert row["liquidity"] is None
    trade.source_event_at = now - timedelta(seconds=61)
    assert market_row(token, None, trade, None, **args)["marketCap"] is None
    trade.source_event_at = now + timedelta(seconds=1)
    assert market_row(token, None, trade, None, **args)["stale"]


@pytest.mark.asyncio
async def test_pool_lookup_filters_foreign_and_malformed_pools():
    mint = "8p7uhDVpe5Pw4fg2tfHXskHmCicfr7gTrnbRtzAopump"
    address = "EkgDHmHiYUk6iaP53E3TPMJgjMb8QNAhdsWcLxjsPCHJ"
    valid = dict(
        chainId="solana",
        dexId="pumpswap",
        pairAddress=address,
        baseToken={"address": mint},
        quoteToken={"address": WRAPPED_SOL_MINT},
    )

    def respond(request):
        return httpx.Response(
            200, json=[{**valid, "baseToken": "bad"}, {**valid, "dexId": "other"}, valid, valid]
        )

    lookup = DexScreenerPoolLookup(transport=httpx.MockTransport(respond))
    assert await lookup.pools(mint) == (address,)
