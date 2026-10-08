# Transparent scoring

Status: Phase 4 implemented  
Boundary: research scores and decisions only; no execution

Every decision stores six components separately: momentum, wallet, risk, social,
lifecycle, and market. It also stores the configured weight, normalized weight,
contribution, availability, reason, and input evidence for each component. A
single opaque `score = 83` is never the only retained result.

The initial hypothesis weights are:

| Component | Weight |
| --- | ---: |
| Momentum | 25% |
| Wallet | 25% |
| Risk quality | 20% |
| Social | 15% |
| Lifecycle | 10% |
| Market validation | 5% |

Phase 8 calculates wallet alpha as a separate, auditable research result with
sample-size confidence. It deliberately remains `unknown` inside strategy
scoring until Phase 9 connects independent wallet consensus to decisions.
Social trading weight is disabled by default and excluded from the
enabled-weight denominator. Available components are renormalized, and the
decision records the resulting component-completeness percentage. Strategy
minimum-completeness gates prevent a small surviving component from silently
standing in for the whole model.

Momentum uses only the configured decision-time rolling window. Its bounded
subsignals include flow imbalance, raw-price change, volume acceleration,
transaction-rate acceleration, unique-buyer acceleration, and buy-pressure
acceleration. Raw acceleration is normalized relative to contemporaneous
velocity; no future price or outcome enters the calculation.

Risk quality is `100 - Phase 3 risk_score` only when `allowed=true`. Unknown or
rejected risk cannot contribute a synthetic score. Market validation and regime
are likewise explicit components.

These formulas and weights are initial research hypotheses, not claims of edge.
Phase 7 outcomes are required before optimizing them.
