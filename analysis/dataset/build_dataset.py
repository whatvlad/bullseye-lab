"""Build a research dataset from recorded Pump trades (read-only DB access).

One sample = one token at one moment (at a trade, >= 15 s after the previous sample of that
token, within the token's first 30 min as seen by us). Features use only trades up to that
moment; the label is the replayed net return of buying then (0.8 s latency, 2.25%/side) under
the current exit rules, with 15 min of future. Samples need [t-300 s, t+900 s] fully online.
"""
import asyncio
import csv
import json
import sys
from bisect import bisect_left, bisect_right
from datetime import UTC, datetime

from sqlalchemy import text

from memebot.core.config import Settings
from memebot.storage.database.engine import create_database_engine
from sim import simulate

SINCE = datetime(2026, 10, 2, tzinfo=UTC)
LAMPORTS = 1e9
GRAD_SOL = 85.0  # real SOL at graduation (approx.)
online = json.load(open("data/online.json"))
ONLINE = {m for m, _ in online["minutes"]}
CREATED = online["created"]


NO = 10**9
EXITS = {  # alternative exit styles (net %, same costs/latency); max 15 min of future
    "tp20_sl10": dict(tp=20, tp_frac=1.0, sl=10, act=NO, stag_s=NO, max_hold=900),
    "tp30_sl15": dict(tp=30, tp_frac=1.0, sl=15, act=NO, stag_s=NO, max_hold=900),
    "tp50_sl20": dict(tp=50, tp_frac=1.0, sl=20, act=NO, stag_s=NO, max_hold=900),
    "tp100_sl30": dict(tp=100, tp_frac=1.0, sl=30, act=NO, stag_s=NO, max_hold=900),
    "hold60": dict(tp=NO, sl=99, act=NO, stag_s=NO, max_hold=60, runner_hold=60),
    "hold180": dict(tp=NO, sl=99, act=NO, stag_s=NO, max_hold=180, runner_hold=180),
    "hold600": dict(tp=NO, sl=99, act=NO, stag_s=NO, max_hold=600, runner_hold=600),
    "trail10w8_sl15": dict(tp=NO, sl=15, act=10, wmin=8, wmax=8, stag_s=NO, max_hold=900),
    "trail20w15_sl15": dict(tp=NO, sl=15, act=20, wmin=15, wmax=15, stag_s=NO, max_hold=900),
    "half30_trail_sl15": dict(tp=30, tp_frac=0.5, sl=15, act=30, wmin=15, wmax=25, stag_s=NO, max_hold=900, runner_hold=900),
    "tp30_sl15_hold120": dict(tp=30, tp_frac=1.0, sl=15, act=NO, stag_s=NO, max_hold=120, runner_hold=120),
    # current rules, only the stop changed (stop is on net P&L incl. ~4.5% round-trip costs)
    "cur_sl6": dict(sl=6, max_hold=900, runner_hold=900),
    "cur_sl8": dict(sl=8, max_hold=900, runner_hold=900),
    "cur_sl10": dict(sl=10, max_hold=900, runner_hold=900),
    "cur_sl12": dict(sl=12, max_hold=900, runner_hold=900),
    "cur_sl15": dict(sl=15, max_hold=900, runner_hold=900),
    "cur_sl20": dict(sl=20, max_hold=900, runner_hold=900),
}


def covered(t0, before=300, after=900):
    start, end = int((t0 - before) // 60 * 60), int((t0 + after) // 60 * 60)
    return all(m in ONLINE for m in range(start, end + 60, 60))


def window(trades, times, t0, sec):
    lo = bisect_left(times, t0 - sec)
    hi = bisect_right(times, t0)
    return trades[lo:hi]


def feats(w, sec):
    n = len(w)
    buys = [x for x in w if x[2] == "buy"]
    sells = n - len(buys)
    bv = sum(x[3] for x in buys) / LAMPORTS
    sv = sum(x[3] for x in w if x[2] == "sell") / LAMPORTS
    by_wallet = {}
    for x in buys:
        by_wallet[x[4]] = by_wallet.get(x[4], 0) + x[3]
    top = max(by_wallet.values()) / LAMPORTS / bv if bv > 0 else None
    pc = (w[-1][1] / w[0][1] - 1) * 100 if n >= 2 and w[0][1] > 0 else None
    return {
        f"n{sec}": n, f"buys{sec}": len(buys), f"sells{sec}": sells,
        f"ubuy{sec}": len(by_wallet), f"bvol{sec}": round(bv, 4), f"svol{sec}": round(sv, 4),
        f"flow{sec}": round((bv - sv) / (bv + sv), 4) if bv + sv > 0 else None,
        f"top{sec}": round(top, 4) if top is not None else None,
        f"pc{sec}": round(pc, 3) if pc is not None else None,
    }


def samples_for(token_id, trades):
    times = [x[0] for x in trades]
    first = times[0]
    created = CREATED.get(token_id, first)
    out, last = [], -1e9
    for i, tr in enumerate(trades):
        t0 = tr[0]
        if t0 - first > 1800 or t0 - last < 15:
            continue
        if not covered(t0):
            continue
        last = t0
        row = {"token": token_id, "t": round(t0, 3), "age": round(t0 - created, 1),
               "seen_for": round(t0 - first, 1),
               "progress": round(tr[5] / LAMPORTS / GRAD_SOL * 100, 2) if tr[5] is not None else None,
               "trades_so_far": i + 1}
        for sec in (10, 60, 300):
            row.update(feats(window(trades, times, t0, sec), sec))
        pts = [[x[0] - t0, x[1], x[2], x[3], None, x[4]] for x in trades[i + 1:] if x[0] - t0 <= 900]
        res = simulate({"pts": pts}, max_hold=900, runner_hold=900) if pts else None
        row["ret"] = round(res["ret"], 3) if res else -100.0  # no later trade at all: dead
        row["exit"] = res["reason"] if res else "no_trades"
        for name, kw in EXITS.items():
            alt = simulate({"pts": pts}, **kw) if pts else None
            row["ret_" + name] = round(alt["ret"], 3) if alt else None
        future = [p[1] for p in pts]
        row["max_up"] = round((max(future) / tr[1] - 1) * 100, 2) if future else 0.0
        out.append(row)
    return out


async def main(out_path):
    engine = create_database_engine(Settings(pumpportal_api_key=None).database_url)
    total = 0
    with open(out_path, "w", newline="", encoding="utf-8") as handle:
        writer = None
        async with engine.connect() as conn:
            result = await conn.stream(text(
                "select token_id::text, extract(epoch from source_event_at), price_raw, side, "
                "quote_amount_raw, wallet, real_quote_reserves from token_trades "
                "where source_event_at >= :s order by token_id, source_event_at"), {"s": SINCE})
            current, trades = None, []
            async for tok, t, price, side, quote, wallet, rq in result:
                if tok != current:
                    if trades:
                        rows = samples_for(current, trades)
                        if rows:
                            if writer is None:
                                writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
                                writer.writeheader()
                            writer.writerows(rows)
                            total += len(rows)
                    current, trades = tok, []
                trades.append((float(t), float(price), side, int(quote), wallet, rq))
            if trades:
                rows = samples_for(current, trades)
                if rows and writer is not None:
                    writer.writerows(rows)
                    total += len(rows)
    await engine.dispose()
    print("samples", total)


if __name__ == "__main__" or True:
    asyncio.run(main(sys.argv[3] if len(sys.argv) > 3 else sys.argv[1]))
