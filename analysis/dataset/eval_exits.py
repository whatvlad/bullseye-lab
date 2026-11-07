"""For each exit style: bot-like rule and a logistic model (train < Oct 8, test after)."""
import csv
import math
import random
import statistics as st
import sys
from datetime import UTC, datetime

SPLIT = datetime(2026, 10, 8, tzinfo=UTC).timestamp()
DEAD = -4.5
R = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))
STYLES = ["ret"] + [k for k in R[0] if k.startswith("ret_")]
NUM = [k for k in R[0] if k not in ("token", "t", "exit", "max_up") and not k.startswith("ret")]


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def slog(v):
    return math.copysign(math.log1p(abs(v)), v)


def label(r, style):
    v = f(r[style])
    return DEAD if v is None or (style == "ret" and r["exit"] == "no_trades") else v


def botlike(r):
    try:
        return (f(r["n10"]) >= 5 and f(r["ubuy10"]) >= 3 and (f(r["flow10"]) or -1) >= 0.1
                and (f(r["top10"]) if r["top10"] else 1) <= 0.65 and r["pc10"]
                and 0 < f(r["pc10"]) <= 50 and f(r["age"]) >= 3)
    except TypeError:
        return False


R.sort(key=lambda r: float(r["t"]))
train = [r for r in R if float(r["t"]) < SPLIT]
test = [r for r in R if float(r["t"]) >= SPLIT]
med = [st.median([f(r[k]) for r in train if f(r[k]) is not None] or [0]) for k in NUM]


def vec(r):
    xs = [f(r[k]) for k in NUM]
    return [slog(x if x is not None else m) for x, m in zip(xs, med)] + [
        1.0 if x is None else 0.0 for x in xs
    ]


Xtr = [vec(r) for r in train]
mu = [st.mean(c) for c in zip(*Xtr)]
sd = [st.pstdev(c) or 1.0 for c in zip(*Xtr)]
Xtr = [[(a - m) / s for a, m, s in zip(v, mu, sd)] for v in Xtr]
Xte = [[(a - m) / s for a, m, s in zip(vec(r), mu, sd)] for r in test]


def logistic(X, y, epochs=6, lr=0.01, lam=1e-4):
    random.seed(7)
    w, b = [0.0] * len(X[0]), 0.0
    idx = list(range(len(X)))
    for _ in range(epochs):
        random.shuffle(idx)
        for i in idx:
            x = X[i]
            z = b + sum(a * c for a, c in zip(w, x))
            e = 1 / (1 + math.exp(-max(-30, min(30, z)))) - y[i]
            b -= lr * e
            w = [wi - lr * (e * a + lam * wi) for wi, a in zip(w, x)]
        lr *= 0.7
    return w, b


def one_per_token(rows, keep, style):
    seen, out = set(), []
    for r, k in zip(rows, keep):
        if k and r["token"] not in seen:
            seen.add(r["token"])
            out.append(label(r, style))
    return out


def fmt(rets):
    if not rets:
        return "n=0"
    return f"n={len(rets):5} win={sum(x > 0 for x in rets) / len(rets):4.0%} mean={st.mean(rets):6.2f}%"


print(f"train {len(train)} samples, test {len(test)} samples (one buy per token)\n")
for style in STYLES:
    name = "current rules" if style == "ret" else style[4:]
    bot = one_per_token(test, [botlike(r) for r in test], style)
    model = logistic(Xtr, [1.0 if label(r, style) > 0 else 0.0 for r in train])
    w, b = model
    s_tr = [b + sum(a * c for a, c in zip(w, x)) for x in Xtr]
    s_te = [b + sum(a * c for a, c in zip(w, x)) for x in Xte]
    parts = [f"{name:20} bot-rule {fmt(bot)}"]
    for q in (0.95, 0.99):
        thr = sorted(s_tr)[int(len(s_tr) * q)]
        parts.append(f"model top {1 - q:.0%} {fmt(one_per_token(test, [s >= thr for s in s_te], style))}")
    print("\n   ".join(parts), flush=True)
