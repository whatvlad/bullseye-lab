"""60-second probe: how heavy is a PumpSwap logsSubscribe, and do logs carry buy/sell events?

Read-only; prints counts only (never the RPC URL).
"""
import asyncio
import base64
import json
import sys
import time

import websockets

from memebot.core.config import Settings
from memebot.providers.solana.pump_idl import PUMP_AMM_PROGRAM_ID, PumpSwapTrade, decode_anchor_event

SECONDS = float(sys.argv[1]) if len(sys.argv) > 1 else 60


async def main():
    url = str(Settings(pumpportal_api_key=None).solana_rpc_ws_url)
    messages = nbytes = txs = failed = events = buys = sells = 0
    pools = set()
    async with websockets.connect(url, max_size=2**24) as ws:
        await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
                                  "params": [{"mentions": [PUMP_AMM_PROGRAM_ID]},
                                             {"commitment": "confirmed"}]}))
        await ws.recv()
        end = time.monotonic() + SECONDS
        while time.monotonic() < end:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=end - time.monotonic())
            except TimeoutError:
                break
            messages += 1
            nbytes += len(raw)
            value = json.loads(raw).get("params", {}).get("result", {}).get("value", {})
            txs += 1
            if value.get("err"):
                failed += 1
                continue
            for line in value.get("logs") or []:
                if not line.startswith("Program data: "):
                    continue
                try:
                    event = decode_anchor_event(PUMP_AMM_PROGRAM_ID,
                                                base64.b64decode(line[14:], validate=True))
                except Exception:  # noqa: BLE001 - other programs' events
                    continue
                if isinstance(event, PumpSwapTrade):
                    events += 1
                    buys += event.is_buy
                    sells += not event.is_buy
                    pools.add(event.pool)
    mb_hour = nbytes / SECONDS * 3600 / 1e6
    print(json.dumps({"seconds": SECONDS, "tx_notifications": txs, "failed_tx": failed,
                      "bytes": nbytes, "mb_per_hour": round(mb_hour, 1),
                      "trade_events_in_logs": events, "buys": buys, "sells": sells,
                      "pools": len(pools)}, indent=1))


asyncio.run(main())
