"""10-second probe: read PumpSwap fee basis points (LP / protocol / creator) from live buy events.

Read-only; prints a fee summary only. Uses the bot's pinned PumpSwap event layout.
"""
import asyncio
import base64
import collections
import json
import sys
import time

import websockets

from memebot.core.config import Settings
from memebot.providers.solana.pump_idl import (
    BUY_EVENT_DISCRIMINATOR,
    PUMP_AMM_PROGRAM_ID,
    SELL_EVENT_DISCRIMINATOR,
)
from memebot.providers.solana.encoding import BorshReader

SECONDS = float(sys.argv[1]) if len(sys.argv) > 1 else 10


def fees(data: bytes):
    side = "buy" if data[:8] == BUY_EVENT_DISCRIMINATOR else "sell" if data[:8] == SELL_EVENT_DISCRIMINATOR else None
    if side is None:
        return None
    r = BorshReader(data[8:])
    r.i64()
    base = r.u64()
    r.u64(); r.u64(); r.u64()  # max/min, user base, user quote
    pool_base, pool_quote = r.u64(), r.u64()
    quote = r.u64()
    lp_bps = r.u64(); r.u64()
    proto_bps = r.u64(); r.u64()
    r.u64(); r.u64()
    for _ in range(7):
        r.pubkey()
    creator_bps = r.u64()
    return side, lp_bps, proto_bps, creator_bps, pool_quote


async def main():
    url = str(Settings(pumpportal_api_key=None).solana_rpc_ws_url)
    counts = collections.Counter()
    async with websockets.connect(url, max_size=2**24) as ws:
        await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
                                  "params": [{"mentions": [PUMP_AMM_PROGRAM_ID]}, {"commitment": "confirmed"}]}))
        await ws.recv()
        end = time.monotonic() + SECONDS
        while time.monotonic() < end:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=end - time.monotonic())
            except TimeoutError:
                break
            value = json.loads(raw).get("params", {}).get("result", {}).get("value", {})
            if value.get("err"):
                continue
            for line in value.get("logs") or []:
                if line.startswith("Program data: "):
                    try:
                        f = fees(base64.b64decode(line[14:], validate=True))
                    except Exception:  # noqa: BLE001
                        continue
                    if f:
                        side, lp, proto, creator, pool_quote = f
                        bucket = "pool<120 SOL" if pool_quote < 120e9 else ("pool<300 SOL" if pool_quote < 300e9 else "pool>=300 SOL")
                        counts[(side, lp, proto, creator, bucket)] += 1
    for key, n in counts.most_common(15):
        side, lp, proto, creator, bucket = key
        print(f"{side:4} lp={lp} protocol={proto} creator={creator} total={lp + proto + creator} bps  {bucket:14} n={n}")


asyncio.run(main())
