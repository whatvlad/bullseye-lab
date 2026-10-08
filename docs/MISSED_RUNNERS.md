# Never-bought observed runners

Research date: 1 October 2026 (Europe/Dublin). Historical timestamps below are UTC. Production configuration, thresholds and trading state were not changed.

All 171,676 discoveries were counted. Only 8,245 tokens have market-trade histories; 8,039 were never bought in any recorded portfolio. Unobserved launches cannot be labelled. 153 never-bought tokens meet at least one research-only strong-peak label.

Anchor: first recorded strategy decision, or first recorded trade when no decision exists. Labels: peak ≥25% within 10/30/60/120 seconds; ≥50% within 300 seconds. Require a baseline/end tick within two seconds, no observed intertrade gap >2s and the same market/quote. These round research cutoffs separate visibly large moves from modest marks; they are not optimized, production rules or guaranteed exits. Sparse positive peaks are retained as gappy observations but do not count as complete labels.

| Horizon | N all-token bounded labels | Never-bought labelled runners | N HIGH |
|---|---|---|---|
| 10 | 336 | 144 | 0 |
| 30 | 51 | 39 | 0 |
| 60 | 14 | 9 | 0 |
| 120 | 6 | 5 | 0 |
| 300 | 3 | 2 | 0 |

At five minutes only three all-token anchors have bounded follow-up. This cannot rank five-minute runner detection. Peak-return labels use hindsight for classification only; entry features remain causal.

| First Aggressive decision reason | Runner tokens with reason |
|---|---|
| risk_gate_not_approved | 98 |
| insufficient_observation_span | 72 |
| risk_score_unknown | 69 |
| score_component_completeness_below_minimum | 66 |
| insufficient_trades_in_scoring_window | 56 |
| buyer_flow_concentrated | 32 |
| insufficient_sustained_buy_flow | 28 |
| insufficient_unique_buyers_in_scoring_window | 28 |
| risk:top1_holder_above_limit | 26 |
| token_younger_than_strategy_minimum | 14 |

Reasons overlap. Historical strategies had different versions/thresholds; each token's JSON/CSV records first decisions for all profiles, scores, timestamps, execution status and rejection reason. The stored 29 strategy versions remain in the raw export. A token can pass the strategy and still remain unbought through execution/control vetoes; do not call all never-bought tokens strategy rejections. Missing risk, holder concentration, young age and insufficient observations are common blockers. They may have prevented rugs elsewhere. Lowering them based only on winners would select on the outcome.

Data proves some large observed moves were not traded. It does not prove they could have been bought and sold net-profitably. Full ideal-entry timing, WATCHING delay attribution and missed executable profit are **INSUFFICIENT EVIDENCE**.

Reproduction: see [DATA_QUALITY.md](DATA_QUALITY.md). Machine-readable JSON and CSV are in `analysis/`.