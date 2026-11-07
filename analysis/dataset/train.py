"""Time-split models on samples.csv (pure Python SGD). Train < Oct 8 00:00 UTC, test after."""
import csv
import math
import random
import statistics as st
from datetime import UTC, datetime

SPLIT = datetime(2026, 10, 8, tzinfo=UTC).timestamp()
DEAD = -4.5  # no further trades: sell back into the curve at ~entry minus round-trip costs
import sys
R = list(csv.DictReader(open(sys.argv[1] if len(sys.argv) > 1 else "data/samples.csv", encoding="utf-8")))
NUM = [k for k in R[0] if k not in ("token", "t", "ret", "exit", "max_up")]


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def slog(v):
    return math.copysign(math.log1p(abs(v)), v)


rows = []
for r in R:
    x = [f(r[k]) for k in NUM]
    ret = DEAD if r["exit"] == "no_trades" else float(r["ret"])
    rows.append((float(r["t"]), r["token"], x, ret))
train = [r for r in rows if r[0] < SPLIT]
test = [r for r in rows if r[0] >= SPLIT]
print(f"train {len(train)} samples / {len({r[1] for r in train})} tokens; "
      f"test {len(test)} / {len({r[1] for r in test})} tokens")

med = [st.median([r[2][i] for r in train if r[2][i] is not None] or [0]) for i in range(len(NUM))]


def vec(x):
    v = [slog(x[i] if x[i] is not None else med[i]) for i in range(len(NUM))]
    return v + [1.0 if x[i] is None else 0.0 for i in range(len(NUM)) if "pc" in NUM[i] or "top" in NUM[i] or "flow" in NUM[i]]


Xtr = [vec(r[2]) for r in train]
mu = [st.mean(c) for c in zip(*Xtr)]
sd = [st.pstdev(c) or 1.0 for c in zip(*Xtr)]


def norm(v):
    return [(a - m) / s for a, m, s in zip(v, mu, sd)]


Xtr = [norm(v) for v in Xtr]
Xte = [norm(vec(r[2])) for r in test]


def sgd(X, y, logistic, epochs=8, lr=0.01, lam=1e-4):
    random.seed(7)
    w, b = [0.0] * len(X[0]), 0.0
    idx = list(range(len(X)))
    for ep in range(epochs):
        random.shuffle(idx)
        for i in idx:
            x = X[i]
            z = b + sum(a * c for a, c in zip(w, x))
            p = 1 / (1 + math.exp(-max(-30, min(30, z)))) if logistic else z
            e = p - y[i]
            if not logistic:
                e = max(-5.0, min(5.0, e))  # Huber-like: tame fat tails
            b -= lr * e
            w = [wi - lr * (e * a + lam * wi) for wi, a in zip(w, x)]
        lr *= 0.7
    return w, b


def predict(model, X):
    w, b = model
    return [b + sum(a * c for a, c in zip(w, x)) for x in X]


def policy(samples, scores, threshold):
    """First moment per token whose score clears the threshold: one trade per token."""
    taken, rets = set(), []
    for (t, tok, _, ret), s in sorted(zip(samples, scores), key=lambda z: z[0][0]):
        if s >= threshold and tok not in taken:
            taken.add(tok)
            rets.append(ret)
    return rets


def show(label, rets):
    if rets:
        print(f"  {label:44} trades={len(rets):5}  win={sum(r > 0 for r in rets) / len(rets):4.0%}  "
              f"mean={st.mean(rets):6.2f}%  median={st.median(rets):6.1f}%")


ytr_win = [1.0 if r[3] > 0 else 0.0 for r in train]
ytr_ret = [max(-50.0, min(200.0, r[3])) / 20 for r in train]
models = {
    "logistic (win yes/no)": sgd(Xtr, ytr_win, True),
    "linear (return)": sgd(Xtr, ytr_ret, False),
}
print("\nBaseline on TEST (one trade per token, first moment):")
show("buy every token at first sample", policy(test, [1] * len(test), 0))
for name, model in models.items():
    tr_scores = predict(model, Xtr)
    te_scores = predict(model, Xte)
    print(f"\n{name}")
    for q in (0.80, 0.95, 0.99):
        thr = sorted(tr_scores)[int(len(tr_scores) * q)]
        show(f"TRAIN top {1 - q:.0%} threshold", policy(train, tr_scores, thr))
        show(f"TEST  top {1 - q:.0%} threshold (unseen)", policy(test, te_scores, thr))
    w, _ = model
    names = NUM + [f"{k}_missing" for k in NUM if "pc" in k or "top" in k or "flow" in k]
    top = sorted(zip(names, w), key=lambda z: -abs(z[1]))[:8]
    print("  strongest inputs:", ", ".join(f"{n} {v:+.2f}" for n, v in top))
