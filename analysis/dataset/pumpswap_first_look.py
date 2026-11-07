"""First look at graduated coins: replay buying N seconds after migration (research only).

Data: analysis/pumpswap/*.jsonl (recorder). Price = pool_quote / pool_base from each trade
event. Only pools first seen <= 60 s after graduation. Fill = first trade >= latency after
the decision; costs per side from --cost (fresh PumpSwap pools charge ~1.25% in fees).
Data can stop early when the recorder's hourly cap paused it: those positions are marked at
the last recorded price ("end_of_data").
"""
import argparse
import collections
import glob
import json
import statistics as st

import sim
from memebot.paper.graduation import REAL_POOL_QUOTE_LAMPORTS, reserves_after

parser = argparse.ArgumentParser()
parser.add_argument("--cost", type=float, default=0.0185, help="per side: 1.25%% fees + slippage")
args = parser.parse_args()
sim.SIDE_COST = args.cost

pools = collections.defaultdict(list)
for name in glob.glob("../pumpswap/trades_*.jsonl"):
    for line in open(name, encoding="utf-8"):
        r = json.loads(line)
        pools[r["pool"]].append(r)

paths = {}
for pool, rows in pools.items():
    rows.sort(key=lambda r: (r["slot"] or 0, r["received_at"], r["log_index"]))
    grad = rows[0]["graduated_at"]
    if rows[0]["received_at"] - grad > 60:
        continue
    low, high = REAL_POOL_QUOTE_LAMPORTS  # real graduations only (dust/old pools excluded)
    if not low <= rows[0]["pool_quote"] <= high:
        continue
    pts = []
    for r in rows:  # event reserves are pre-trade: price after each trade
        base, quote = reserves_after(r["side"], r["base_amount"], r["quote_amount"],
                                     r["pool_base"], r["pool_quote"])
        if base > 0:
            pts.append((r["received_at"] - grad, quote / base, r["side"], r["quote_amount"]))
    paths[pool] = pts
print(f"real graduation pools caught <= 60 s after graduation: {len(paths)}; cost {args.cost:.2%}/side\n")

NO = 10**9
EXITS = {
    "current rules": dict(),
    "tp30 / sl15": dict(tp=30, tp_frac=1.0, sl=15, act=NO, stag_s=NO),
    "tp50 / sl20": dict(tp=50, tp_frac=1.0, sl=20, act=NO, stag_s=NO),
    "tp100 / sl30": dict(tp=100, tp_frac=1.0, sl=30, act=NO, stag_s=NO),
    "hold 5 min": dict(tp=NO, sl=99, act=NO, stag_s=NO, max_hold=300, runner_hold=300),
    "hold 30 min": dict(tp=NO, sl=99, act=NO, stag_s=NO, max_hold=1800, runner_hold=1800),
}


def at(pts, t0):
    """Path re-based so the decision is at time 0."""
    return {"pts": [[t - t0, p, s, q, None, None] for t, p, s, q in pts if t >= t0]}


def fmt(rets):
    if not rets:
        return "n=0"
    return (f"n={len(rets):3} win={sum(r > 0 for r in rets) / len(rets):4.0%} "
            f"mean={st.mean(rets):6.1f}% median={st.median(rets):6.1f}%")


for delay in (0, 30, 60, 120, 300, 600):
    print(f"Buy {delay:>3} s after graduation:")
    for name, kw in EXITS.items():
        rets, ends = [], 0
        for pts in paths.values():
            if not any(t >= delay for t, *_ in pts):
                continue
            res = sim.simulate(at(pts, delay), **kw)
            if res:
                rets.append(res["ret"])
                ends += res["reason"] == "end_of_data"
        print(f"   {name:14} {fmt(rets)}  (data ended early: {ends})")

# Simple entry filter at 120 s: price vs graduation and buy pressure in the first 2 minutes.
print("\nBuy at 120 s, current rules, split by what happened in the first 2 minutes:")
groups = collections.defaultdict(list)
for pts in paths.values():
    first = [x for x in pts if x[0] <= 120]
    if len(first) < 5 or not any(t >= 120 for t, *_ in pts):
        continue
    change = (first[-1][1] / first[0][1] - 1) * 100
    buys = sum(q for t, p, s, q in first if s == "buy")
    sells = sum(q for t, p, s, q in first if s == "sell")
    flow = (buys - sells) / (buys + sells) if buys + sells else 0
    res = sim.simulate(at(pts, 120))
    if not res:
        continue
    groups["price up since graduation" if change > 0 else "price down since graduation"].append(res["ret"])
    groups["net buying (flow > 0)" if flow > 0 else "net selling (flow <= 0)"].append(res["ret"])
for key, rets in groups.items():
    print(f"   {key:30} {fmt(rets)}")
