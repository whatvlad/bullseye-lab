"""Replay entry filters and exit rules on recorded trade prints (read-only research).

For each token's first `enter_candidate` decision (strategy `aggressive`) since --since, take
the recorded trades for 30 min, buy at the first trade >= latency after the decision, pay
--cost per side, run the paper exit rules on every later trade, and sell at the first trade
>= latency after an exit fires. Prints mean/median return per trade for the current rules
and for the shadow entry filters from docs/TRADE_REVIEW_20261009.md:

  confirm10  price 10 s after the signal is still >= the signal price (buy then)
  speed      net SOL added to the curve per trade in the 60 s before the signal (top third)
  holders5x3 5+ holders each >= 3% of supply (from `insider_facts` in analysis logs)

Usage:  .venv\\Scripts\\python.exe analysis\\replay_exits.py [--since 2026-10-08T17:51:00Z]
"""

from __future__ import annotations

import argparse
import asyncio
import glob
import json
import statistics as st
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text

from memebot.core.config import Settings
from memebot.storage.database.engine import create_database_engine

ROOT = Path(__file__).resolve().parents[1]
PATHS_SQL = """
with first_dec as (
  select distinct on (mint) mint, token_id, decided_at
  from decision_outcomes
  where decided_at >= :since and strategy_key = 'aggressive' and action = 'enter_candidate'
  order by mint, decided_at
)
select f.mint, extract(epoch from tt.source_event_at - f.decided_at) as t, tt.price_raw,
  tt.side, tt.quote_amount_raw
from first_dec f
join token_trades tt on tt.token_id = f.token_id
 and tt.source_event_at >= f.decided_at - interval '60 seconds'
 and tt.source_event_at <= f.decided_at + interval '1800 seconds'
order by f.mint, tt.source_event_at
"""


def fill_after(pts, start, t0):
    for j in range(start, len(pts)):
        if pts[j][0] >= t0:
            return j, pts[j][1]
    return None, None


def simulate(pts, *, cost, latency, sl=15.0, tp=100.0, tp_frac=0.5, act=50.0, wmin=18.0,
             wmax=30.0, stag_s=120, stag_mfe=5.0, max_hold=1800, runner_hold=7200,
             entry_delay=0.0, confirm=None):
    """Return net % for one position, None if no fill, 'skip' if the confirm filter says no."""
    pts = [p for p in pts if p[0] >= 0]
    if not pts:
        return None
    j, entry = fill_after(pts, 0, latency + entry_delay)
    if j is None:
        return None
    if confirm is not None and entry < pts[0][1] * (1 + confirm / 100):
        return "skip"
    t_entry, basis = pts[j][0], entry * (1 + cost)
    remaining, realized, peak, partial = 1.0, 0.0, entry, False
    for k in range(j + 1, len(pts)):
        t, p = pts[k][0], pts[k][1]
        peak = max(peak, p)
        change, peak_ret = (p / entry - 1) * 100, (peak / entry - 1) * 100
        net = (p * (1 - cost) / basis - 1) * 100
        reason, frac = None, remaining
        if net <= -sl:
            reason = "stop_loss"
        elif not partial and change >= tp:
            reason, frac = "partial", remaining * tp_frac
        else:
            width = min(wmax, max(wmin, peak_ret / 4))
            hold = runner_hold if peak_ret >= act else max_hold
            if peak_ret >= act and p <= peak * (1 - width / 100):
                reason = "trailing"
            elif t - t_entry >= stag_s and peak_ret < stag_mfe and change <= 0:
                reason = "stagnation"
            elif t - t_entry >= hold:
                reason = "max_hold"
        if reason:
            _, px = fill_after(pts, k, t + latency)
            px = px if px is not None else pts[-1][1]
            realized += frac * (px * (1 - cost) / basis - 1)
            remaining -= frac
            if reason == "partial":
                partial = True
                continue
            return realized * 100
    return (realized + remaining * (pts[-1][1] * (1 - cost) / basis - 1)) * 100


def sol_per_trade(pts):
    """Net SOL added per trade in the 60 s before the decision (trading-speed proxy)."""
    before = [p for p in pts if -60 <= p[0] <= 0]
    if len(before) < 3:
        return None
    net = sum(p[3] if p[2] == "buy" else -p[3] for p in before) / 1e9
    return net / len(before)


def insider_flags():
    """mint -> True if 5+ holders each hold >= 3% (latest insider_facts line per mint)."""
    flags = {}
    files = glob.glob(str(ROOT / "analysis" / "*.err.log")) + glob.glob(
        str(ROOT / "analysis" / "logs" / "*.log")
    )
    for name in files:
        with open(name, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if '"insider_facts"' not in line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                over3 = (row.get("holders_over") or {}).get("3")
                if row.get("mint") and over3:
                    flags[row["mint"]] = int(over3[0]) >= 5
    return flags


def line(label, values):
    rets = [v for v in values if isinstance(v, float)]
    if not rets:
        print(f"{label:46} no trades")
        return
    wins = sum(1 for r in rets if r > 0)
    print(f"{label:46} n={len(rets):4}  win={wins / len(rets):4.0%}  "
          f"mean={st.mean(rets):6.1f}%  median={st.median(rets):6.1f}%")


async def load(since):
    engine = create_database_engine(Settings(pumpportal_api_key=None).database_url)
    async with engine.connect() as conn:
        rows = (await conn.execute(text(PATHS_SQL), {"since": since})).all()
    await engine.dispose()
    paths: dict[str, list] = {}
    for mint, t, price, side, quote in rows:
        paths.setdefault(mint, []).append((float(t), float(price), side, int(quote)))
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--since", default="2026-10-08T17:51:00+00:00")
    parser.add_argument("--cost", type=float, default=0.0225, help="per side, fees+slippage")
    parser.add_argument("--latency", type=float, default=0.8, help="seconds to fill")
    args = parser.parse_args()
    since = datetime.fromisoformat(args.since.replace("Z", "+00:00")).astimezone(UTC)
    paths = asyncio.run(load(since))
    kw = {"cost": args.cost, "latency": args.latency}
    base = {m: simulate(p, **kw) for m, p in paths.items()}
    print(f"Candidates since {since:%Y-%m-%d %H:%M} UTC: {len(paths)} tokens; "
          f"cost {args.cost:.2%}/side, latency {args.latency}s\n")
    line("Current rules (all candidates)", base.values())

    confirm = [simulate(p, entry_delay=10, confirm=0, **kw) for p in paths.values()]
    line("confirm10: buy only if price after 10 s >= signal", confirm)

    speeds = {m: sol_per_trade(p) for m, p in paths.items()}
    known = sorted(v for v in speeds.values() if v is not None)
    if len(known) >= 9:
        cut = known[2 * len(known) // 3]
        line("speed: top third SOL/trade (current exits)",
             [base[m] for m, v in speeds.items() if v is not None and v >= cut])
        line("speed: lower two thirds", [base[m] for m, v in speeds.items() if v is not None and v < cut])

    flags = insider_flags()
    seen = [m for m in paths if m in flags]
    line("holders5x3: flagged (5+ holders >= 3%)", [base[m] for m in seen if flags[m]])
    line("holders5x3: not flagged", [base[m] for m in seen if not flags[m]])
    print(f"\n(insider_facts found for {len(seen)} of {len(paths)} candidates; "
          "older runs' logs were overwritten)")


if __name__ == "__main__":
    main()
