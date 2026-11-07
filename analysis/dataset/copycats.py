"""Copycat test: when the N-th coin with the same ticker/name/tweet appears, buy the original.

Read-only. Uses tokens (all seen coins), fetched tweet links, and recorded trades. A trigger
fires at the creation time of the N-th coin in a group whose first coin is <= 24 h older.
At the trigger we replay a buy of (a) the original and (b) the new copy, 0.8 s latency,
2.25%/side, with 15 min of future; the trigger must fall in fully recorded (online) minutes.
"""
import asyncio
import json
import re
import statistics as st
import sys
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import text

from memebot.core.config import Settings
from memebot.storage.database.engine import create_database_engine
from sim import simulate

online = json.load(open("data/online.json"))
ONLINE = {m for m, _ in online["minutes"]}
LINKS = json.load(open("data/socials_links.json"))
NO = 10**9
ALIVE = len(sys.argv) > 1 and sys.argv[1] == "alive"
EXITS = {
    "current": dict(max_hold=900, runner_hold=900),
    "tp30_sl15": dict(tp=30, tp_frac=1.0, sl=15, act=NO, stag_s=NO, max_hold=900),
}


def covered(t0, after=900):
    return all(m in ONLINE for m in range(int(t0 // 60 * 60), int((t0 + after) // 60 * 60) + 60, 60))


def norm_symbol(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def norm_name(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def tweet_id(url):
    m = re.search(r"/status/(\d+)", url or "")
    return m.group(1) if m else None


async def main():
    engine = create_database_engine(Settings(pumpportal_api_key=None).database_url)
    async with engine.connect() as conn:
        tokens = (await conn.execute(text(
            "select id::text, mint, name, symbol, "
            "extract(epoch from coalesce(source_created_at, first_seen_at)) from tokens"))).all()
        print("tokens", len(tokens), flush=True)
        groups = defaultdict(list)
        for tid, mint, name, symbol, created in tokens:
            created = float(created)
            if sym := norm_symbol(symbol):
                groups[("symbol", sym)].append((created, tid))
            if (nm := norm_name(name)) and len(nm) >= 3:
                groups[("name", nm)].append((created, tid))
            if tw := tweet_id((LINKS.get(tid) or {}).get("twitter")):
                groups[("tweet", tw)].append((created, tid))
        triggers = []  # (kind, N, trigger_time, original_tid, copy_tid)
        for (kind, _), items in groups.items():
            items.sort()
            for n in (3, 5, 10):
                if len(items) >= n:
                    origin_t, origin = items[0]
                    t_n, copy = items[n - 1]
                    if t_n - origin_t <= 86400 and covered(t_n):
                        triggers.append((kind, n, t_n, origin, copy, t_n - origin_t))
        print("triggers", len(triggers), flush=True)
        need = defaultdict(list)
        for i, tr in enumerate(triggers):
            need[tr[3]].append(i)
            need[tr[4]].append(i)
        paths = {}
        ids = list(need)
        for start in range(0, len(ids), 500):
            batch = ids[start:start + 500]
            rows = (await conn.execute(text(
                "select token_id::text, extract(epoch from source_event_at), price_raw, side, "
                "quote_amount_raw from token_trades where token_id = any(cast(:ids as uuid[])) "
                "order by token_id, source_event_at"), {"ids": batch})).all()
            for tid, t, price, side, quote in rows:
                paths.setdefault(tid, []).append((float(t), float(price), side, int(quote)))
    await engine.dispose()

    results = defaultdict(list)
    for kind, n, t0, origin, copy, gap in triggers:
        for who, tid in (("original", origin), ("copy", copy)):
            trades = paths.get(tid) or []
            last_before = [x for x in trades if x[0] <= t0]
            future = [[x[0] - t0, x[1], x[2], x[3], None, None] for x in trades if t0 < x[0] <= t0 + 900]
            if who == "original" and not last_before and not future:
                continue  # we never saw the original trade
            recent = sum(1 for x in last_before if x[0] >= t0 - 60)
            if ALIVE and recent < 5:
                continue  # only buy a coin that is still actively trading
            for ex, kw in EXITS.items():
                res = simulate({"pts": future}, **kw) if future else None
                ret = res["ret"] if res else -4.5  # no trades after: dead, sell back ~ -costs
                results[(kind, n, who, ex)].append(ret)
                results[("any", n, who, ex)].append(ret)
    print(f"\n{'group':8} {'N':>3} {'buy':9} {'exit':10} {'n':>5} {'win':>5} {'mean':>8}")
    for key in sorted(results):
        v = results[key]
        if len(v) >= 10:
            print(f"{key[0]:8} {key[1]:>3} {key[2]:9} {key[3]:10} {len(v):5} "
                  f"{sum(x > 0 for x in v) / len(v):5.0%} {st.mean(v):7.2f}%")


asyncio.run(main())
