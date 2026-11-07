"""Replay exit rules on recorded post-decision trade paths (research only)."""
import json
import statistics as st
import sys

SIDE_COST = 0.0225  # ~1.75% fees (median measured) + 0.5% slippage, per side
LATENCY = 0.8       # s, median measured entry latency


def fill_after(pts, i, t0):
    """Price of the first trade at or after t0 (index >= i); None if path ends."""
    for j in range(i, len(pts)):
        if pts[j][0] >= t0:
            return j, pts[j][1]
    return None, None


def simulate(path, *, sl=15.0, tp=100.0, tp_frac=0.5, act=50.0, wmin=18.0, wmax=30.0,
             stag_s=120, stag_mfe=5.0, max_hold=1800, runner_hold=7200, be_after=None,
             be_level=0.0, entry_delay=0.0, confirm=None):
    pts = [p for p in path["pts"] if p[0] >= 0]
    if not pts:
        return None
    j, entry = fill_after(pts, 0, LATENCY + entry_delay)
    if j is None:
        return None
    if confirm is not None:
        # Only enter if price after the delay is >= decision price * (1+confirm%).
        if entry < pts[0][1] * (1 + confirm / 100):
            return {"skipped": True}
    t_entry = pts[j][0]
    cost_basis = entry * (1 + SIDE_COST)
    remaining, realized, peak, partial = 1.0, 0.0, entry, False
    last_t = t_entry
    for k in range(j + 1, len(pts)):
        t, p = pts[k][0], pts[k][1]
        last_t = t
        age = t - t_entry
        peak = max(peak, p)
        change = (p / entry - 1) * 100
        net = (p * (1 - SIDE_COST) / cost_basis - 1) * 100
        peak_ret = (peak / entry - 1) * 100
        reason = None
        frac = remaining
        if net <= -sl:
            reason = "stop_loss"
        elif be_after is not None and peak_ret >= be_after and net <= be_level:
            reason = "break_even"
        elif not partial and change >= tp:
            reason, frac = "partial", remaining * tp_frac
        else:
            width = min(wmax, max(wmin, peak_ret / 4))
            hold = runner_hold if peak_ret >= act else max_hold
            if peak_ret >= act and p <= peak * (1 - width / 100):
                reason = "trailing"
            elif age >= stag_s and peak_ret < stag_mfe and change <= 0:
                reason = "stagnation"
            elif age >= hold:
                reason = "max_hold"
        if reason:
            m, px = fill_after(pts, k, t + LATENCY)
            px = px if px is not None else pts[-1][1]
            realized += frac * (px * (1 - SIDE_COST) / cost_basis - 1)
            remaining -= frac
            if reason == "partial":
                partial = True
                continue
            return {"ret": realized * 100, "reason": reason, "hold": t - t_entry, "peak": peak_ret}
    # Path ended (data stops): mark remainder at last price.
    realized += remaining * (pts[-1][1] * (1 - SIDE_COST) / cost_basis - 1)
    return {"ret": realized * 100, "reason": "end_of_data", "hold": last_t - t_entry, "peak": (peak / entry - 1) * 100}


def report(label, results):
    rs = [r for r in results if r and not r.get("skipped")]
    if not rs:
        print(label, "no trades")
        return
    rets = [r["ret"] for r in rs]
    wins = [x for x in rets if x > 0]
    print(f"{label:38} n={len(rs):4} win={len(wins)/len(rs):5.0%} mean={st.mean(rets):7.2f}% "
          f"median={st.median(rets):6.1f}% sum={sum(rets):8.0f}  p10={sorted(rets)[len(rets)//10]:6.1f}%")


if __name__ == "__main__":
    paths = json.load(open(sys.argv[1]))
    report("baseline", [simulate(p) for p in paths.values()])
