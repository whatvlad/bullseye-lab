"""Render offline strategy reports from measured study outputs."""
# ruff: noqa: E501
# Long lines are embedded Markdown/SVG report prose, not application logic.

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from memebot.core.config import Settings
from memebot.research.runner_study import iso, quantiles, rows, stamp, write_csv, write_json
from memebot.strategies.presets import initial_strategy_presets


def fmt(value: Any, digits: int = 2) -> str:
    return "UNKNOWN" if value is None else f"{value:.{digits}f}"


def table(headers: list[str], data: list[list[Any]]) -> str:
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "|" + "---|" * len(headers),
            *["| " + " | ".join(str(v) for v in row) + " |" for row in data],
        ]
    )


def render(source: Path, analysis: Path, docs: Path) -> None:
    def load(name: str) -> Any:
        return json.loads((analysis / f"{name}.json").read_text(encoding="utf-8"))

    s, trades, timeline = load("summary"), load("trade_excursions"), load("worst_trade_timeline")
    missed, labels, cohorts = (
        load("missed_runners"),
        load("candidate_labels"),
        load("age_matched_features"),
    )
    exits, concentration = load("exit_signals"), load("loss_concentration")
    worst = s["worst_positions"]
    raw_outcomes = {r["position_id"]: r for r in rows(source / "trade_outcomes.jsonl")}
    prefix = "Research date: 1 October 2026 (Europe/Dublin). Historical timestamps below are UTC. "
    prefix += "Production configuration, thresholds and trading state were not changed.\n\n"
    suffix = "\n\nReproduction: see [DATA_QUALITY.md](DATA_QUALITY.md). Machine-readable JSON and CSV are in `analysis/`."

    # Explicit analytic cost reference, not synthetic historical observations.
    floors = []
    for size in (0.01, 0.025, 0.05, 0.1, 0.25, 0.5):
        friction_factor = 0.995 * 0.995 * 0.9825 / 1.0125
        for tip in (0, 0.0001):
            network = 0.00011 + tip
            breakeven = ((size * 1.005 + 2 * network) / (size * friction_factor) - 1) * 100
            floors.append(
                {
                    "size_sol": size,
                    "tip_sol_each_side": tip,
                    "linear_no_impact_break_even_percent": breakeven,
                    "scope": "analytic friction floor; no historical trade or executable quote",
                }
            )
    write_json(analysis / "analytic_cost_floors.json", floors)
    write_csv(analysis / "analytic_cost_floors.csv", floors)
    quality = [
        {
            "entity": "position",
            "id": r["position_id"],
            "mint": r["mint"],
            "quality": r["quality"],
            "source_timestamp_quality": r["source_timestamp_quality"],
            "max_gap_seconds": r["max_intertrade_gap_seconds"],
            "ticks": r["N_observed_ticks"],
            "holder_coverage": r["holder_coverage"],
            "wallet_coverage": r["wallet_coverage"],
            "rpc_fill_vs_feed_difference_percent": r["recorded_exit_mark_difference_percent"],
        }
        for r in trades
    ]
    quality += [
        {
            "entity": "token",
            "id": r["mint"],
            "mint": r["mint"],
            "quality": r["quality"],
            "source_timestamp_quality": r["source_timestamp_quality"],
            "forward_coverage": {h: v["coverage"] for h, v in r["forward_peak_labels"].items()},
            "holder_coverage": "snapshot only if assessed; dynamic count unknown",
            "wallet_coverage": "observed addresses, no verified profitable wallet label",
        }
        for r in labels
    ]
    health = list(rows(source / "health.jsonl"))
    by_position = {r["position_id"]: r for r in trades}
    for row in quality:
        if row["entity"] == "position":
            p = by_position[row["id"]]
            row["overlapping_provider_error_records"] = sum(
                bool(h["error_code"])
                and stamp(p["entry_at"]) <= stamp(h["ingested_at"]) <= stamp(p["exit_at"])
                for h in health
            )
            row["interruption_attribution"] = (
                "global health overlap, not proof of a lost token event"
            )
    write_json(analysis / "data_quality.json", quality)
    write_csv(analysis / "data_quality.csv", quality)
    token_flags = Counter(r["quality"] for r in labels)
    eligible_losers = [
        r for r in trades if r["net_pnl"] < 0 and r["observed_mfe_percent"] is not None
    ]
    eligible_winners = [
        r for r in trades if r["net_pnl"] > 0 and r["observed_mae_percent"] is not None
    ]
    excursion_groups = {
        name: {
            field: quantiles([r[field] for r in group if r.get(field) is not None])
            for field in (
                "observed_mfe_percent",
                "observed_mae_percent",
                "time_to_observed_mfe_seconds",
                "time_to_recorded_mae_seconds",
                "holding_seconds",
                "net_return_percent",
            )
        }
        for name, group in (("losers", eligible_losers), ("winners", eligible_winners))
    }
    write_json(analysis / "excursion_groups.json", excursion_groups)
    docs.mkdir(parents=True, exist_ok=True)
    sections = []
    for w in worst:
        mint = w["mint"]
        o = raw_outcomes[w["position_id"]]
        steps = [
            r
            for r in timeline
            if r["mint"] == mint
            and r["kind"]
            in (
                "discovery",
                "buy:signal_at",
                "buy:decision_at",
                "buy:submitted_at",
                "buy:filled_at",
                "observed_MFE",
                "observed_MAE",
                "sell:signal_at",
                "sell:decision_at",
                "sell:filled_at",
            )
            and (r.get("status") in (None, "filled"))
        ]
        window = next(x for x in o["feature_snapshot_json"]["windows"] if x["window_seconds"] == 10)
        evidence = {
            r["code"]: r.get("value")
            for r in o["risk_snapshot_json"]["evidence"]
            if r.get("availability") == "available"
        }
        entry_table = table(
            ["10-second entry-window metric", "Recorded value"],
            [
                [key, window.get(key, "UNKNOWN")]
                for key in (
                    "buy_count",
                    "sell_count",
                    "unique_buyers",
                    "buy_volume_quote_raw",
                    "sell_volume_quote_raw",
                    "buy_sell_volume_ratio",
                    "price_velocity_percent_per_second",
                    "price_acceleration_percent_per_second2",
                    "volume_velocity_quote_raw_per_second",
                    "volume_acceleration_quote_raw_per_second2",
                    "unique_buyer_rate_acceleration_per_second2",
                    "largest_buy_quote_raw",
                    "largest_sell_quote_raw",
                    "latest_price_return_percent",
                    "latest_sell_liquidity_fraction",
                )
            ],
        )
        steps_table = table(
            ["T+seconds", "UTC timestamp", "Stage", "Price raw if retained"],
            [
                [
                    fmt(r["T_plus_seconds"], 3),
                    iso(r["t"]),
                    r["kind"],
                    (
                        (r.get("fill") or {}).get("actual_fill_price_raw")
                        if r["kind"].endswith("filled_at")
                        else r.get("price_raw", "—")
                    ),
                ]
                for r in steps
            ],
        )
        components = ", ".join(
            f"{c['name']}={c.get('score')} (weight {c['configured_weight']})"
            for c in o["score_snapshot_json"]["components"]
        )
        sections.append(
            f"## {w['symbol']} — {mint}\n\nPosition `{w['position_id']}`. "
            f"Net {w['net_pnl']:.8f} USDT / {w['net_return_percent']:.2f}%. "
            f"Quality {w['quality']}; {w['N_observed_ticks']} in-position trade ticks.\n\n"
            f"{steps_table}\n\nEntered because Aggressive emitted `early_demand` and score "
            f"{o['score_snapshot_json']['final_score']} exceeded 55. Risk allowed=true, "
            f"score={o['risk_snapshot_json']['risk_score']}, completeness="
            f"{o['risk_snapshot_json']['data_completeness_percent']}%, no hard rejects. "
            f"Components: {components}.\n\n{entry_table}\n\n"
            f"Top-1 / top-10 holders: {evidence.get('top1_holder_percent')}% / "
            f"{evidence.get('top10_holder_percent')}%; creator holding snapshot "
            f"{evidence.get('creator_holding_percent')}%. This is not evidence that creator "
            f"never sold. Funding/insider graph, organic score, smart-wallet participation "
            f"and time-series holder growth are UNKNOWN.\n\n"
            f"First trade was {w['baseline_gap_from_discovery_seconds']:.3f}s after discovery. "
            f"Return from that first recorded price to entry mark: "
            f"{w['return_first_observed_price_to_entry_mark_percent']:.2f}%; "
            f"from the observed pre-entry low: {w['return_observed_low_to_entry_mark_percent']:.2f}%; "
            f"from first structural momentum signal: "
            f"{fmt(w['return_first_momentum_to_entry_mark_percent'])}%. Exact "
            f"discovery-price return is UNKNOWN. Actual fill versus first recorded price: "
            f"{w['actual_fill_vs_first_observed_price_percent']:.2f}%. "
            f"Signal→decision {w['signal_to_decision_seconds']:.3f}s; decision→fill "
            f"{w['decision_to_fill_seconds']:.3f}s.\n\n"
            f"Recorded MFE / MAE {w['recorded_mfe_percent']:.2f}% / {w['recorded_mae_percent']:.2f}%. "
            f"Time to observed MFE {fmt(w['time_to_observed_mfe_seconds'])}s; "
            f"time to recorded MAE {fmt(w['time_to_recorded_mae_seconds'])}s. "
            f"RPC exit mark differs from the last available feed tick by "
            f"{fmt(w['recorded_exit_mark_difference_percent'])}%. The complete timeline "
            f"retains this discrepancy; it is not interpolated away."
        )
    text_worst = "# Two worst trades — causal forensics\n\n" + prefix + "\n\n".join(sections)
    entry_evidence = {w["mint"]: raw_outcomes[w["position_id"]] for w in worst}
    write_json(analysis / "worst_entry_evidence.json", entry_evidence)
    text_worst += "\n\n## Broader-window evidence available at entry\n\n"
    for w in worst:
        original = raw_outcomes[w["position_id"]]
        broad: dict[str, Any] = next(
            (r for r in original["feature_snapshot_json"]["windows"] if r["window_seconds"] == 60),
            {},
        )
        text_worst += (
            f"{w['symbol']}: saved 60s-window buy/sell volume ratio "
            f"{broad.get('buy_sell_volume_ratio', 'UNKNOWN')}; buyer acceleration "
            f"{broad.get('unique_buyer_rate_acceleration_per_second2', 'UNKNOWN')}; "
            f"volume acceleration {broad.get('volume_acceleration_quote_raw_per_second2', 'UNKNOWN')}. "
            f"Observed creator-address sells during the position: "
            f"{w.get('observed_creator_sell_count_in_position', 'UNKNOWN')}. "
            "Zero observed creator sells cannot rule out linked-wallet dumping.\n\n"
        )
    text_worst += (
        "All recorded entry windows, risk evidence and score components are retained in "
        "`analysis/worst_entry_evidence.json`. Broader-window disagreement motivates an ablation; "
        "it does not establish a reject rule.\n\n"
    )
    text_worst += """

## Failure classification and rejection feasibility

FLETCH: **observed overextension, sell shock, rapid reversal and tail loss**. Its linked entry feature already showed -9.61% on the latest trade, a 2.48 SOL sell, 13.89% of reported real quote liquidity and a 13.64 MAD sell-size score. The snapshot preceded decision/fill. Rejection on a sell-shock hypothesis was mechanically possible without future information. This flag appears in only one losing entry and no winning entries among 215 available entry snapshots: insufficient to estimate its true benefit. Creator dump, insider dump and rug attribution are **INSUFFICIENT EVIDENCE**. A stop signal existed; calling this NO_EXIT_SIGNAL would be wrong. A 3.29-second crash also limits how much an exit can avoid.

Cappuccinu: **profit giveback, feed/RPC disagreement, coverage gaps and tail loss**. It entered -21.07% below its first observed price, not after the same kind of initial chase. Its entry's last 10 seconds had five trades/three buyers and strong buy-volume imbalance; short-window evidence looked favorable despite weak broader flow. A negative earlier episode is not proof of failure at this entry. Observed MFE took 1,782s after entry. The final feed gap reached 268.81s, and the RPC exit mark was 73.33% below the latest feed tick. Recorded MAE cannot be timestamped from these ticks. Holding/exit quality deserves investigation, but a reliably executable earlier exit price or a pre-entry rejection rule is **INSUFFICIENT EVIDENCE**.

The two losses total 35.99317504 USDT: 81.19% of net experiment loss, but 75.64% of **gross losing-position amounts**. Denominators are different. Both exits were stop_loss. Do not infer a new TP/SL optimum from two trades.

The complete CSV/JSON timeline includes every retained 10-second feature snapshot, profile decision, signal, submission, fill, RPC reserve time and SOL/USD reference time. T+1/T+2 fields remain unknown where no event exists. `risk_snapshot_causal_at_this_time=false` means a linked risk assessment arrived later; it was not known at that observation. Market cap assumes 1B six-decimal Pump tokens; liquidity is real SOL quote reserves, not a liquidity valuation. Research phases are annotations, not historical production states.
"""
    (docs / "WORST_TRADES_FORENSICS.md").write_text(text_worst + suffix, encoding="utf-8")

    mfe_table = table(
        ["Statistic", "Observed MFE %", "Observed MAE %"],
        [
            [q, fmt(s["mfe"].get(q)), fmt(s["mae"].get(q))]
            for q in ("median", "p25", "p75", "p90", "p95")
        ],
    )
    (docs / "MFE_MAE_ANALYSIS.md").write_text(
        "# Excursions, profit retention and loss concentration\n\n"
        + prefix
        + f"225 closed positions; 215 retained trade outcomes; 198 positions permit an observed tick excursion. "
        f"65 have bounded local gaps (MEDIUM), 160 LOW, zero verified HIGH histories. "
        f"The 215 stored net-return outcomes span 200 tokens: mean -3.99%, win rate 32.56%, "
        f"equal-return profit factor 0.724. This mixes versions/sizes/periods and is not portfolio return.\n\n"
        f"{mfe_table}\n\n48 of {len(eligible_losers)} losing positions with usable tick histories "
        f"rose above actual entry fill price; 43 have positive stored MFE. These are mark gains, "
        f"not proof of net executable profit. 18 of {len(eligible_winners)} winning positions with "
        f"tick histories dipped more than 10% below entry. Tightening stops based on losers alone "
        f"would ignore these winners.\n\n"
        + table(
            ["Group", "N excursion rows", "Median time to observed MFE, s", "Median holding, s"],
            [
                [
                    name,
                    excursion_groups[name]["observed_mfe_percent"]["n"],
                    fmt(excursion_groups[name]["time_to_observed_mfe_seconds"]["median"]),
                    fmt(excursion_groups[name]["holding_seconds"]["median"]),
                ]
                for name in excursion_groups
            ],
        )
        + "\n\nMFE/MAE start at zero at the fill. Recorded extrema can include RPC marks absent from trade "
        "history; times are only supplied when corresponding data exists. Gaps make extrema lower-bound "
        "observations and chronological dip-before-MFE ordering uncertain. Losing mark excursions do "
        "not establish that an exit was available. Optimal stop width, early profit taking and the typical "
        "time a true runner reveals failure are **INSUFFICIENT EVIDENCE**.\n\n"
        + table(
            [
                "Experiment",
                "N losses",
                "Largest/gross losses",
                "Top 3/gross losses",
                "Top 5/gross losses",
            ],
            [
                [
                    r["name"],
                    r["N_losses"],
                    fmt(100 * r["top_1_fraction_of_gross_losses"]),
                    fmt(100 * r["top_3_fraction_of_gross_losses"]),
                    fmt(100 * r["top_5_fraction_of_gross_losses"]),
                ]
                for r in concentration
                if r["N_losses"] and r["name"].startswith("Experiment:")
            ],
        )
        + "\n\nTail concentration is unusually high in the latest run, but baseline-v2's largest loss "
        "is only 6.26% of gross losses. Tail control alone does not solve all historical selection "
        "problems. Removing the worst trade is a hindsight upper bound, not a tradable circuit breaker. "
        "Keep portfolios separate; USD/USDT capital, sizing and periods differ." + suffix,
        encoding="utf-8",
    )

    reason_counts = Counter(
        reason
        for r in missed
        for d in r["first_decisions_by_strategy"]
        if d["strategy"] == "aggressive"
        for reason in d["reasons"]
    )
    (docs / "MISSED_RUNNERS.md").write_text(
        "# Never-bought observed runners\n\n"
        + prefix
        + "All 171,676 discoveries were counted. Only 8,245 tokens have market-trade histories; "
        "8,039 were never bought in any recorded portfolio. Unobserved launches cannot be labelled. "
        "153 never-bought tokens meet at least one research-only strong-peak label.\n\n"
        "Anchor: first recorded strategy decision, or first recorded trade when no decision exists. "
        "Labels: peak ≥25% within 10/30/60/120 seconds; ≥50% within 300 seconds. "
        "Require a baseline/end tick within two seconds, no observed intertrade gap >2s and the same "
        "market/quote. These round research cutoffs separate visibly large moves from modest marks; "
        "they are not optimized, production rules or guaranteed exits. Sparse positive peaks are "
        "retained as gappy observations but do not count as complete labels.\n\n"
        + table(
            ["Horizon", "N all-token bounded labels", "Never-bought labelled runners", "N HIGH"],
            [
                [
                    h,
                    sum(
                        r["forward_peak_labels"][str(h)]["coverage"] == "bounded_observation"
                        for r in labels
                    ),
                    sum(
                        r["forward_peak_labels"][str(h)]["coverage"] == "bounded_observation"
                        and r["forward_peak_labels"][str(h)]["peak_return_percent"]
                        >= (50 if h == 300 else 25)
                        for r in missed
                    ),
                    0,
                ]
                for h in (10, 30, 60, 120, 300)
            ],
        )
        + "\n\nAt five minutes only three all-token anchors have bounded follow-up. This cannot rank "
        "five-minute runner detection. Peak-return labels use hindsight for classification only; "
        "entry features remain causal.\n\n"
        + table(
            ["First Aggressive decision reason", "Runner tokens with reason"],
            [[reason, count] for reason, count in reason_counts.most_common(10)],
        )
        + "\n\nReasons overlap. Historical strategies had different versions/thresholds; each token's "
        "JSON/CSV records first decisions for all profiles, scores, timestamps, execution status and "
        "rejection reason. The stored 29 strategy versions remain in the raw export. "
        "A token can pass the strategy and still remain unbought through execution/control vetoes; "
        "do not call all never-bought tokens strategy rejections. Missing risk, holder concentration, "
        "young age and insufficient observations are common blockers. They may have prevented rugs "
        "elsewhere. Lowering them based only on winners would select on the outcome.\n\n"
        "Data proves some large observed moves were not traded. It does not prove they could have "
        "been bought and sold net-profitably. Full ideal-entry timing, WATCHING delay attribution and "
        "missed executable profit are **INSUFFICIENT EVIDENCE**." + suffix,
        encoding="utf-8",
    )

    timing_table = table(
        ["Entry offset, s", "N total", "N usable", "N HIGH", "Conditional mean net %", "PF"],
        [
            [
                offset,
                v["N_total"],
                v["N_usable"],
                v["N_high_quality"],
                fmt(v["net_expectancy_percent"]),
                fmt(v["profit_factor"]),
            ]
            for offset, v in s["entry_offsets"].items()
        ],
    )
    obs_table = table(
        ["Observation age, s", "N tokens", "N conditional simulations", "N HIGH"],
        [
            [age, v["N_total"], v["N_usable"], v["N_high_quality"]]
            for age, v in s["observation_windows"].items()
        ],
    )
    cost_table = table(
        ["Size SOL", "N usable positions", "Conditional mean net %", "No-impact break-even %"],
        [
            [
                size,
                v["N_usable"],
                fmt(v["net_expectancy_percent"]),
                fmt(
                    next(
                        r["linear_no_impact_break_even_percent"]
                        for r in floors
                        if r["size_sol"] == float(size) and r["tip_sol_each_side"] == 0
                    )
                ),
            ]
            for size, v in s["cost_sizes"].items()
        ],
    )
    (docs / "ENTRY_TIMING_ANALYSIS.md").write_text(
        "# Entry timing, observation and size sensitivity\n\n"
        + prefix
        + timing_table
        + "\n\nNo position is usable at **all eight offsets**; the common panel is zero. "
        "Usable cells contain only 0-2 positions and different survivors. There is no basis to choose "
        "an offset. The broader claim 'the bot generally enters too late' is **INSUFFICIENT EVIDENCE**. "
        "FLETCH was late relative to its first observed expansion; Cappuccinu was not the same chase.\n\n"
        "Conditional simulations hold exit decision fixed and do not reconstruct dynamic exits/partials. "
        "They use the same PaperFillSimulator, .05 SOL standard stake, 800ms delay, 50bps adverse "
        "latency adjustment per side, modeled venue/service/network/priority fees. Require recorded "
        "real reserves, fresh causal ticks, same market, Pump.fun/WSOL and ≤300bps modeled impact. "
        "A historical RPC exit-mark mismatch above 5% invalidates net timing/avoided-loss claims; "
        "the mathematical two-state result stays in a separately named column. This is a research "
        "reconciliation tolerance, not a trading threshold.\n\n"
        + obs_table
        + "\n\nEach age uses only a feature received by that time, no older than two seconds, "
        "then a fixed 60-second conditional holding period. These are not existing-strategy decisions "
        "or an optimized observation window. Small surviving panels and candidate-only reserve "
        "coverage produce large apparent gains in some cells; those are selection-biased and "
        "do not demonstrate an early-runner edge. A useful observation duration is **INSUFFICIENT EVIDENCE**.\n\n"
        + cost_table
        + "\n\nAnalytic friction floors are not empirical expectancy and exclude impact, rent "
        "and token extensions. Jito baseline is zero because no Jito path exists; an additional "
        "0.0001 SOL tip each side is a separate labelled stress scenario, not an observed Jito fee. "
        "Minimum economically sensible and maximum profitable size are **INSUFFICIENT EVIDENCE**. "
        "Larger size reduces fixed-cost proportion but increases impact.\n\n"
        + table(
            ["Entry expansion from first observed trade", "N net outcomes", "Mean net %"],
            [
                [bucket, v["N_usable"], fmt(v["net_expectancy_percent"])]
                for bucket, v in s["extension_buckets"].items()
            ],
        )
        + "\n\nThe ≥60% groups look worse descriptively; the 20-40% group is positive. "
        "This is neither monotonic nor age/version matched, includes repeated tokens, and has "
        "unknown discovery prices. No chasing cutoff was fitted. Last-5s/10s return and 10s observed "
        "VWAP distance are recorded for future testing, not introduced into production." + suffix,
        encoding="utf-8",
    )

    signals = (
        "large_sell_with_price_shock",
        "buyer_deceleration_and_net_selling",
        "reserves_and_price_falling",
    )
    (docs / "EXIT_TIMING_ANALYSIS.md").write_text(
        "# Failure-signal and exit timing study\n\n"
        + prefix
        + "Research signals use the saved 10-second rolling window: (1) latest-trade return ≤-5% "
        "with latest sell ≥5% of real quote liquidity; (2) negative buyer acceleration together "
        "with negative flow imbalance; (3) negative reserve velocity together with negative price "
        "velocity. The numeric shock cutoffs are research definitions; none were enabled. "
        "Absent reserve/wallet values do not satisfy a signal.\n\n"
        + table(
            [
                "Signal",
                "Positions with post-entry flag",
                "Usable avoided-return comparisons",
                "N HIGH",
            ],
            [
                [
                    signal,
                    sum(r["first_observed_at"] is not None for r in exits if r["signal"] == signal),
                    sum(
                        r.get("conditional_avoided_return_points") is not None
                        for r in exits
                        if r["signal"] == signal
                    ),
                    0,
                ]
                for signal in signals
            ],
        )
        + "\n\nFor FLETCH all three first post-entry flags appeared about 1.38s before exit. "
        "That leaves little execution headroom; its pre-entry shock is the more relevant hypothesis. "
        "For Cappuccinu the first buyer/flow warning appeared 2,071.57s before exit, reserve/price "
        "warning 2,149.36s before, and large-sell shock 643.47s before. These can precede substantial "
        "recovery: treating the earliest flag as certain failure is unjustified. Its unreconciled "
        "exit mark prevents a credible USDT avoided-loss calculation.\n\n"
        + table(
            ["Pre-entry flag", "Losers flagged", "Winners flagged", "N snapshots available"],
            [
                [signal, v["losers"], v["winners"], v["N_feature_available"]]
                for signal, v in s["preentry_signal_counts"].items()
            ],
        )
        + "\n\nPre-entry sell shock flags one loser and zero winners; buyer/flow flags four losers "
        "and one winner. These sparse counts are hypotheses, not estimates of stable sensitivity "
        "or profit improvement. The latest catastrophic exits had stop signals; 'no stop' is not "
        "the observed failure. General exit lateness, optimal TP/SL, and avoided loss are "
        "**INSUFFICIENT EVIDENCE**. Counterfactual return deltas are conditional equal-size two-state "
        "comparisons, not dollar savings or full execution replay." + suffix,
        encoding="utf-8",
    )

    group_counts = Counter((r["token_age_seconds"], r["group"]) for r in cohorts)
    (docs / "RUNNER_FEATURE_STUDY.md").write_text(
        "# Age-matched runner feature and phase research\n\n"
        + prefix
        + table(
            ["Age, s", "Bought losers", "Never-bought observed runners", "Other", "N HIGH"],
            [
                [
                    age,
                    group_counts[(age, "bought_loser")],
                    group_counts[(age, "missed_runner")],
                    group_counts[(age, "other")],
                    0,
                ]
                for age in (10, 20, 30, 60)
            ],
        )
        + "\n\nEach token contributes once per age; windows are fixed at ten seconds. A feature must "
        "have arrived by the age checkpoint and be fresh. Risk is unavailable before its assessment "
        "time. Outcomes use the following 60s, not the features' future history. Only 1-2 bought "
        "losers survive per age. Median/quantile comparisons, Spearman ranks and seeded 500-replicate "
        "token bootstrap results are exported; bootstrap intervals are suppressed for groups under "
        "five. **No feature is established as separating bought losers from missed runners.**\n\n"
        "Buyer/volume/price acceleration, flow ratio, reserve growth, unique buyers, trade frequency, "
        "concentration/HHI, liquidity, market cap, risk and runner score are covered where recorded. "
        "Last-5s/10s returns and observed VWAP distance are exported. Holder growth, verified "
        "profitable-wallet participation, linked-wallet/bundled supply and continuous creator activity "
        "lack usable histories. Unknown values stay null. Market cap uses the stated Pump supply "
        "assumption; native quote normalization and market changes limit comparability.\n\n"
        "Useful hypotheses: pre-entry sell shock/large liquidity-relative sell, adverse velocity, "
        "return from first observation and divergence across 10s/60s windows. FLETCH supports asking "
        "these questions, not a production cutoff. The previous weak five-minute linear relationships "
        "do not prove acceleration features useless. **INSUFFICIENT EVIDENCE** to declare any "
        "existing feature generally useless. Zero-weight wallet/social components could not "
        "explain these entry score decisions, which used momentum and graduation velocity.\n\n"
        "Research phases in the worst-trade timeline: EARLY_EXPANSION if price velocity, buyer and "
        "volume acceleration are positive; OVEREXTENDED if price rises without positive buyer "
        "acceleration; DISTRIBUTION/FAILED if the research failure signals appear; IGNITION/WATCHING "
        "otherwise. UNKNOWN when inputs are missing. These annotations can switch rapidly. "
        "CONFIRMED_RUNNER and DEAD require persistence/coverage that these histories do not prove. "
        "The phase model is not calibrated or enabled, and no tree model was fitted to a "
        "1-2-loser comparison panel. Multiple testing, regimes, strategy versions and selected "
        "follow-up prevent causal conclusions." + suffix,
        encoding="utf-8",
    )

    (docs / "DATA_QUALITY.md").write_text(
        "# Research data quality and reproducibility\n\n"
        + prefix
        + f"Export: repeatable-read, READ ONLY PostgreSQL; {s['manifest']['database_time_utc']}. "
        "No current market APIs or trading process was used. Per-file counts and SHA256 are "
        "in `analysis/source_manifest.json`; source data stays under ignored `research_sessions/`.\n\n"
        + table(
            ["Universe", "N total", "N usable for indicated purpose", "N HIGH"],
            [
                ["Discoveries", 171676, 8245, 0],
                ["Closed positions", 225, 215, 0],
                ["Tick excursions", 225, 198, 0],
                ["All-offset entry comparisons", 225, 0, 0],
                ["Tokens at first anchor, 300s bounded label", 8245, 3, 0],
            ],
        )
        + f"\n\nPosition quality: {s['quality_counts']}. Token anchor quality: {dict(token_flags)}. "
        "Every position and trade-covered token has a row in `data_quality.json/csv`. "
        "Feature/decision-only and launch-only tokens lack price follow-up; their unusable count "
        "is shown rather than silently labelled zero.\n\n"
        "MEDIUM: two-sided observed timestamps and gaps ≤2s in the evaluated interval. "
        "LOW: missing baseline/end/extrema, larger gaps, unknown reserves or conflicting evidence. "
        "HIGH would require independently validated source timestamps and complete stream coverage; "
        "none meet that standard. PumpPortal's historical source stamps were receipt times even "
        "when an older schema said estimated=false. Native events may have slots but receipt of "
        "all events is not established. Gap thresholds score observed coverage only; quiet trading "
        "and dropped events cannot be distinguished.\n\n"
        "Holder coverage is a risk snapshot, not holder growth. Wallet coverage is observed "
        "addresses, not independently verified smart-wallet PnL. Funding graphs/insider attribution "
        "are unknown. Provider health transitions were exported; a provider error overlapping a "
        "position does not prove its price history is corrupt or causally explain a loss. "
        "No assumed zero is substituted for absent evidence.\n\n"
        "Cappuccinu's RPC exit mark was 73.33% below its nearby feed tick; FLETCH's was 21.77% "
        "below. Recorded RPC extrema do not have a complete matching tick chronology. Those "
        "positions are excluded from net timing/avoided-loss reconstruction. Stored market "
        "marks and integer execution formulas alone cannot certify executable profit.\n\n"
        "Reproduce into a NEW raw directory, then derive outputs:\n\n```powershell\n"
        ".venv\\Scripts\\python.exe -m memebot.research.strategy_capture --output research_sessions/strategy-new\n"
        ".venv\\Scripts\\python.exe -m memebot.research.runner_study --source research_sessions/strategy-new --output analysis\n"
        ".venv\\Scripts\\python.exe -m memebot.research.runner_reports --source research_sessions/strategy-new --analysis analysis --docs docs\n"
        "```\n\nThe exporter refuses an existing destination. Reports are descriptive mixed-history "
        "statistics, not holdout evaluation. Common timing panels, rejected simulation reasons, "
        "unknown MAE times and conditional-only results are explicit. A new dataset will require "
        "reviewing narrative case conclusions rather than automatically trusting old statements.",
        encoding="utf-8",
    )

    frozen = {
        "experiment_id": "runner-edge-prospective-v1",
        "status": "PROPOSED_NOT_STARTED",
        "start_time_utc": None,
        "minimum_days": 14,
        "minimum_candidates": 1000,
        "minimum_completed_baseline_trades": 100,
        "minimum_independent_trade_tokens": 100,
        "strategies": [json.loads(c.model_dump_json()) for c in initial_strategy_presets()],
        "arms": {
            "A": "unchanged frozen Aggressive decisions and exits; standardized research stake",
            "B": "same as A; record a research veto if latest return<=-5% and sell/real liquidity>=5%",
        },
        "stake_sol": "0.05",
        "cost_model": {
            "venue_fee_bps": 125,
            "service_fee_bps_each_side": 50,
            "latency_slippage_bps_each_side": 50,
            "latency_ms": 800,
            "network_sol_each_side": "0.00001",
            "priority_sol_each_side": "0.0001",
            "jito_sol_each_side": "0",
            "impact_cap_bps": 300,
        },
        "scope": "paper/shadow research only; B is a preregistered hypothesis, no live thresholds changed",
        "primary_metric": "paired after-cost net PnL per baseline opportunity including vetoed no-trades=0",
        "secondary_metrics": [
            "token-cluster bootstrap net EV",
            "profit factor",
            "max drawdown",
            "worst 5% loss",
            "missed executable runners",
            "false veto of winners",
            "entry/exit latency",
            "cost/impact",
            "coverage and unknowns",
        ],
        "stop_conditions": [
            "critical data outage or ambiguous reserve/feed disagreement: pause research entries",
            "paper drawdown >=10% in either separately funded arm: stop and diagnose",
            "any accounting inconsistency or accidental live configuration: stop",
            "30 days without required counts: report underpowered, do not tune",
        ],
        "recording": "all decision-time features/risk, raw source/receive/ingestion stamps, reserve snapshots "
        "at signal/quote/delayed buy/sell, SOL/USD, all failed attempts, venue/pool, model outputs",
        "control_sampling": "deterministic hash(mint) sampling fixed before outcomes; persist inclusion probability",
        "evaluation": "do not alter parameters mid-run; assess paired outcomes on same feed and timestamps; "
        "if positive, require a second independent unseen frozen run before claiming edge",
    }
    raw_settings = Settings().model_dump(mode="json")
    frozen["decision_execution_settings"] = {
        key: value
        for key, value in raw_settings.items()
        if key.startswith(("paper_", "pulse_", "alpha_filter_", "ollama_", "risk_"))
        and not any(part in key for part in ("key", "url", "secret", "auth_token"))
    }
    experiment_records = list(rows(source / "experiments.jsonl"))
    incident_record = next(
        (r for r in experiment_records if r["name"] == "sniper-v9-forward-2026-09-13"), None
    )
    captured_control = (
        incident_record["configuration_snapshot_json"].get("trading_control", {})
        if incident_record
        else {}
    )
    frozen["historical_control_reference"] = {
        key: value
        for key, value in captured_control.items()
        if key
        in {
            "active_strategy_key",
            "base_position_percent",
            "max_position_percent",
            "max_open_positions",
            "stop_loss_percent",
            "entries_paused",
        }
    }
    frozen["runtime_code_sha256"] = {
        str(p).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [
            Path("src/memebot/paper/engine.py"),
            Path("src/memebot/paper/execution.py"),
            Path("src/memebot/strategies/presets.py"),
            Path("src/memebot/apps/worker.py"),
        ]
    }
    serial = json.dumps(frozen, sort_keys=True, separators=(",", ":"))
    frozen["configuration_sha256"] = hashlib.sha256(serial.encode()).hexdigest()
    frozen["hash_scope"] = "canonical JSON before configuration_sha256 and hash_scope fields"
    write_json(analysis / "next_experiment.json", frozen)
    (docs / "NEXT_EXPERIMENT.md").write_text(
        "# Next frozen prospective paper experiment\n\n"
        + prefix
        + f"**PROPOSED, NOT STARTED.** Experiment `runner-edge-prospective-v1`; canonical configuration "
        f"SHA256 `{frozen['configuration_sha256']}` in `analysis/next_experiment.json`. "
        "Start time remains null until activation; no active experiment or entry controls were changed.\n\n"
        "Question: does vetoing a fresh large-sell/price-shock entry improve after-cost paired "
        "expectancy without rejecting too many future winners? This is the highest-priority "
        "strategy hypothesis because it was visible before FLETCH's catastrophic fill. Its "
        "expected value is not established from one flagged loser.\n\n"
        "Arm A: current frozen Aggressive presets and existing exits. Arm B: identical feed, "
        "stake and decisions, with a research-only latest-trade ≤-5% plus sell/real-liquidity ≥5% "
        "veto. Log the flag in shadow first. These cutoffs are a preregistered hypothesis, not an "
        "endorsed production change. Unknown inputs cannot become a veto/approval. Retain the "
        "other two profiles as observation-only comparisons.\n\n"
        "Use independent paper ledgers, .05 SOL standard stakes, the exact saved execution "
        "assumptions and a 300bps research impact cap. Standardizing a stake controls the "
        "comparison; it is not an optimized size. Existing 30-40% portfolio exposure is unsuitable "
        "for isolating signal quality. No signer or LIVE mode.\n\n"
        "Before activation: verify funded trade access or validated native feed, resolve stream/RPC "
        "price consistency, preserve complete causal quote/reserve/FX evidence, and provide separate "
        "arm accounting. The current research code does not run these two portfolios or claim "
        "execution parity. Implement only this bounded experiment support when launching it.\n\n"
        "Minimum 14 days, 1,000 candidates, 100 completed baseline trades and 100 independent "
        "trade tokens; continue until all are met, with a 30-day underpowered-review boundary. "
        "These are minimum operational targets, not proof of statistical power against rare "
        "catastrophes. No parameter changes mid-run. Any change starts a new experiment/hash.\n\n"
        "Primary: paired net PnL per baseline opportunity, with arm-B vetoes counted as zero "
        "trades and every eligible baseline token retained. Cluster uncertainty by token/session. "
        "Also report EV, PF, drawdown, tail loss, false vetoes, missed executable runners, latency, "
        "slippage/fees/impact and quality. Fixed hash-sampled rejected controls must be selected "
        "before returns are known; save sampling probabilities. No cherry-picked runner cohort.\n\n"
        "Pause on critical missing/stale data or reserve/stream disagreement; stop on accounting "
        "inconsistency, accidental live configuration, or 10% arm paper drawdown. Diagnose without "
        "retuning. Positive paired results still require another unseen frozen run and complete "
        "cost reconciliation. Otherwise state **INSUFFICIENT EVIDENCE**." + suffix,
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--docs", type=Path, required=True)
    args = parser.parse_args()
    render(args.source, args.analysis, args.docs)


if __name__ == "__main__":
    main()
