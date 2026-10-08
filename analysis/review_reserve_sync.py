"""Offline evidence review and request-count scenarios; no provider or trading writes."""
import json
import math
from decimal import Decimal
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from memebot.research.market_calibration import distribution

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis"


def load(name):
    return json.loads((OUT / name).read_text())


def write(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2) + "\n")


def main():
    anomalies = load("reserve_anomalies.json")
    live = load("reserve_live_pilot.json")
    original = load("market_data_samples.json")
    original_costs = load("provider_costs.json")
    extra = load("live_transition_forensics.json")
    local_rpc = []
    for r in live["reconciliations"]:
        event = r["latest_local_event_at_rpc_receipt"]
        snapshot = r["rpc_snapshot"]
        if not event or r["rpc_status"] != "refreshed":
            continue
        state = event["reported_reserves"] if r["venue"] == "pump_fun" else event["expected_reserves_after"]
        if state:
            q = state["virtual_quote"] if r["venue"] == "pump_fun" else state["real_quote"] + state["virtual_offset"]
            t = state["virtual_token"] if r["venue"] == "pump_fun" else state["real_token"]
            delta = float((Decimal(snapshot["observed_price_raw"]) / (Decimal(q) / Decimal(t)) - 1) * 100)
            local_rpc.append({"mint": r["mint"], "market": r["market"], "venue": r["venue"],
                "local_event_id": event["event_id"], "local_slot": event["slot"],
                "rpc_context_slot": snapshot["source_slot"],
                "latest_local_post_vs_rpc_percent": delta,
                "synchronization": "SLOT_ONLY", "eligible_for_threshold": False})
    # Preserve distinct event vs RPC contexts. Native transaction metadata is
    # independent evidence of event semantics, not simultaneous original RPC state.
    cases = anomalies["results"]
    for case in cases:
        native = case["rpc_state_matching_native_trade"]
        if native and case["sample"]["stream_rpc_price_disagreement_percent"] == 0:
            case["cause"] = "SAME_REPORTED_STATE"
        case["original_comparison_synchronization"] = "SLOT_ONLY"
        case["original_comparison_eligible_for_threshold"] = False
        case["transaction_correlated_semantic_evidence"] = bool(
            case["target_trade"] and case["target_trade"]["semantic"] in {"PRE_TRADE", "POST_TRADE"})
        # A matching endpoint is evidence of a later valid state, but incomplete
        # intermediate mutation coverage is not a complete state sequence proof.
        case["state_sequence_reconciled_complete"] = False
    write("reserve_anomalies.json", anomalies)
    transitions = Counter()
    previous = {}
    breaks = []
    for event in live["events"]:
        key = event["market_key"]
        prior = previous.get(key)
        if event["venue"] == "pump_swap" and prior and prior["expected_reserves_after"]:
            delta = {k: event["reported_reserves"][k] - prior["expected_reserves_after"][k]
                     for k in event["reported_reserves"]}
            if any(delta.values()):
                breaks.append({"venue": "pump_swap", "event_id": event["event_id"],
                               "previous_event_id": prior["event_id"], "delta": delta,
                               "cause": "UNKNOWN_VIRTUAL_OFFSET_MUTATION" if delta["real_token"] == delta["real_quote"] == 0 else "UNKNOWN_MISSING_OR_OTHER_MUTATION"})
            transitions["swap_physical_exact" if delta["real_token"] == delta["real_quote"] == 0 else "swap_physical_break"] += 1
        previous[key] = event
    tx = {"status": "PARTIAL_METHOD_VALIDATED_RUNNER_BLOCKED", "historical_selected": len(cases),
          "anomaly_cases": anomalies["selected_anomalies"], "random_controls": 3,
          "matched_signatures": sum(bool(c["target_trade"]) for c in cases),
          "semantic_counts": dict(Counter(c["target_trade"]["semantic"] for c in cases if c["target_trade"])),
          "causes": dict(Counter(c["cause"] for c in cases)),
          "live_local_transitions": dict(transitions), "continuity_breaks": breaks,
          "latest_local_post_vs_rpc_comparisons": local_rpc,
          "stream_rpc_threshold_eligible_comparisons": 0,
          "original_pilot_all_comparisons": [{"sample_id": i, "venue": s["venue"],
              "synchronization": "SLOT_ONLY", "eligible_for_threshold": False}
              for i, s in enumerate(original["samples"])],
          "coverage": {"all_market_changing_instructions_captured": False,
                       "canonical_pool_selection_independently_verified": False},
          "live_pilot": {"new_rpc_requests": len(live["current_run_provider_requests"]),
                         "candidate_tokens": len(live["serious_candidates"]),
                         "tracked_market_keys": len({e["market_key"] for e in live["events"]}),
                         "trade_events": len(live["events"])},
          "phase_rpc_requests": len(anomalies["provider_requests"]) + len(live["provider_requests"]) + len(extra["provider_requests"]),
          "continuity_break_native_investigation": extra["results"]}
    assert tx["phase_rpc_requests"] <= 300
    write("transaction_reconciliation.json", tx)
    dist = {"classifications": ["TRANSACTION_CORRELATED", "STATE_SEQUENCE_RECONCILED", "SLOT_ONLY", "RECEIPT_ONLY", "UNSYNCHRONIZED"],
            "threshold_eligible_original_pairs": 0, "bands": None, "venues": {}}
    for venue in ("pump_fun", "pump_swap"):
        selected = [c for c in cases if c["sample"]["venue"] == venue]
        events = [e for e in live["events"] if e["venue"] == venue]
        dist["venues"][venue] = {
            "original_slot_only_disagreement_percent": distribution([abs(s["stream_rpc_price_disagreement_percent"]) for s in original["samples"] if s["venue"] == venue]),
            "transaction_correlated_event_semantics": dict(Counter(c["target_trade"]["semantic"] for c in selected if c["target_trade"])),
            "validated_same_state_stream_rpc_percent": distribution([]),
            "local_events": len(events), "distinct_market_keys": len({e["market_key"] for e in events}),
            "local_supported_transitions": dict(Counter(e.get("post_trade_transition_matches") if venue == "pump_fun" else e.get("sequence_matches_previous_post") for e in events)),
            "selection_limitations": "Anomaly-first, three random controls; do not interpret matched-endpoint zero residual as a population distribution"}
    write("reconciliation_distribution.json", dist)
    markets = defaultdict(list)
    for sample in original["samples"]:
        markets[(sample["venue"], sample["market"])].append(sample)
    scenarios = {str(i): {"pump_fun": 0, "pump_swap": 0} for i in (5, 10, 30)}
    event_scenarios = {str(i): {"pump_fun": 0, "pump_swap": 0} for i in (10, 25)}
    for (venue, _), samples in markets.items():
        times = sorted(datetime.fromisoformat(s["stream_receipt_timestamp"]) for s in samples)
        duration = (times[-1] - times[0]).total_seconds()
        bootstrap = 2 if venue == "pump_swap" else 1
        for interval in (5, 10, 30):
            scenarios[str(interval)][venue] += bootstrap + math.floor(duration / interval)
        for interval in (10, 25):
            event_scenarios[str(interval)][venue] += bootstrap + math.floor((len(samples) - 1) / interval)
    baseline = {"pump_fun": 173, "pump_swap": 18}
    for policies in (scenarios, event_scenarios):
        for policy in policies.values():
            policy["reduction_percent"] = {v: 100 * (1 - policy[v] / baseline[v]) for v in baseline}
    elapsed = (datetime.fromisoformat(live["ended_at"]) - datetime.fromisoformat(live["started_at"])).total_seconds()
    current_calls = live["current_run_provider_requests"]
    data_reads = sum(c["method"] != "getSlot" for c in current_calls) - 1
    efficiency = {"current_calibration_pairing_reads": baseline, "shared_original_probes": 9,
                  "original_observed_trade_event_rate": original_costs["streams"]["native_logs"]["event_rate_per_second"],
                  "periodic_interval_seconds": scenarios, "every_n_recorded_events": event_scenarios,
                  "divergence_only": {"pump_fun": "7 bootstrap reads + anomaly/recovery reads (unknown count)",
                                      "pump_swap": "2 bootstrap reads + anomaly/recovery reads (unknown count)"},
                  "new_passive_pilot": {"duration_seconds": elapsed, "requests": len(current_calls),
                      "reads_per_launch": len(current_calls) / len(live["launches"]) if live["launches"] else None,
                      "reads_per_cheap_survivor": len(current_calls) / len(live["cheap_survivors"]) if live["cheap_survivors"] else None,
                      "reads_per_serious_candidate": len(current_calls) / len(live["serious_candidates"]) if live["serious_candidates"] else None,
                      "market_reads_per_serious_candidate": data_reads / len(live["serious_candidates"]) if live["serious_candidates"] else None,
                      "reads_per_minute": 60 * len(current_calls) / elapsed,
                      "request_methods": dict(Counter(c["method"] for c in current_calls))},
                  "all_phase_rpc_requests": tx["phase_rpc_requests"], "hard_cap": 300,
                  "provider_requests": anomalies["provider_requests"] + live["provider_requests"] + extra["provider_requests"],
                  "cu_and_currency_cost": None, "production_policy_selected": False,
                  "limitations": ["Event-count scenarios use 180 retained paired observations, not all 251 tracked pilot trades", "Intervals use per-market observed lifetimes; not a monthly forecast", "Cached immutable pool identity is assumed in periodic scenarios", "RPC needed additionally for disconnects, missed mutations, execution and exits", "Reconciliation frequency not validated for production"]}
    write("rpc_efficiency_v2.json", efficiency)
    documents(anomalies, tx, dist, efficiency, live)


def documents(a, tx, dist, eff, live):
    largest = max(a["results"], key=lambda c: abs(c["sample"]["stream_rpc_price_disagreement_percent"]))
    fun = max([c for c in a["results"] if c["sample"]["venue"] == "pump_fun"], key=lambda c: abs(c["sample"]["stream_rpc_price_disagreement_percent"]))
    target = largest["target_trade"]
    table = "\n".join(f"| {c['sample']['venue']} | {c['sample']['stream_rpc_price_disagreement_percent']:.4f}% | {c['sample']['stream_source_slot']}→{c['sample']['rpc_response_slot']} | {c['target_trade']['signature'] if c['target_trade'] else 'UNKNOWN'} | {c['target_trade']['semantic'] if c['target_trade'] else 'UNKNOWN'} | {c['cause']} |" for c in a["results"])
    texts = {
        "RESERVE_ANOMALY_FORENSICS.md": f"""# Reserve anomaly forensics — runner remains BLOCKED

Recovered all 21 selected trades: 18 distinct anomaly cases (top ten Pump.fun, every PumpSwap
>25%, top ten same-slot, deduplicated) plus three seeded random controls. Sixteen cached full
native blocks were read; three initial version-limited getBlock requests failed with -32015,
then a JSON version ceiling permitted the reads. All 19 requests are retained. No historic
signature was fabricated: slot+market+exact reserves identify a unique decoded native event.
Blocks, loaded addresses, signatures, event ordinal, transaction index, top/inner instructions
and transaction pre/post balances are preserved. Instruction index remains UNKNOWN where
event-to-instruction alignment is not independently unambiguous.

Pump.fun maximum {fun['sample']['stream_rpc_price_disagreement_percent']:.6f}%: native target
state Q={fun['sample']['stream_virtual_quote_reserves']:,} / T={fun['sample']['stream_virtual_token_reserves']:,} was followed by native trades reaching exactly
the RPC state Q=49,687,654,320 / T=647,847,044,526,129. The RPC state matches transaction
{fun['rpc_state_matching_native_trade']['signature']} at slot 452373114, index 708, although its
RPC observation context was 452373115. This is an intervening-state comparison, not proof of
simultaneous provider disagreement. SOL/token-vault deltas corroborate POST_TRADE event timing.

PumpSwap maximum 570.587037%: target signature {target['signature']}, slot 452373176,
transaction index 251, instruction 5. This transaction contains TWO buys. Instruction 2
moves base vault 206,900,000,000,000→204,523,279,829,579 and quote vault
67,405,853,768→68,393,705,619. Instruction 5 then buys 125,329,811,620,853 raw tokens
with a 137.7 SOL gross quote budget, reaching 79,193,468,208,726 tokens /
204,733,033,682 quote lamports. The event fields are PRE_TRADE for each instruction;
transaction-wide pre/post balances bracket both events, not each one independently.
Following native trades reach exactly the RPC state at slot 452373180, transaction index 827:
79,028,192,105,472 tokens / 205,198,909,168 quote lamports.
The same virtual quote offset 17,584,505,288 is present on both sides.

Identity evidence: AMM program pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA;
pool {largest['sample']['market']}; base mint {largest['sample']['mint']}; quote WSOL.
Base vault C7ES3jDWm7YrUy2nWPm6h8VpQEf9QHq9afLGemCC6g9r;
quote vault 97ToUd6M2FijFpyde5KpKiLmpvFnMbiA4MZcg2JM1obw. Both vault owners and
instruction mint/orientation references agree with that pool. No evidence of a wrong pool,
vault, token orientation or decoded virtual offset explains this maximum. Canonical authority
and migration identity continuity are not independently bootstrapped, so those remain UNKNOWN.
The isolated defect is treating AMM pre-trade fields as a contemporaneous post-state price.
This pass corrects the research model; production provider normalization remains a follow-up.

Intermediate slots 177–179 were not fetched. The endpoint match and instruction transition
explain the large movement, but do not prove a complete mutation history across those slots.
{tx['causes']} across selected cases. One random control has no exact later-state match and
remains UNKNOWN; two Pump.fun multi-event transactions retain UNKNOWN event semantics.
No unexplained case is promoted into a simultaneous-state provider error.

| Venue | Original signed difference | Stream→RPC slot | Recovered signature | Semantics | Evidence conclusion |
|---|---:|---|---|---|---|
{table}

Full preceding/target/following timelines are in analysis/reserve_anomalies.json. Cached raw
blocks and SHA256 manifest are retained under research_sessions/reserve-sync-20261001.
""",
        "TRANSACTION_RECONCILIATION.md": f"""# Transaction reconciliation — partial methodology validation

Matched {tx['matched_signatures']} original stream snapshots to native signatures by exact
market/reserve fields, retaining transaction slot, block transaction index, event ordinal and
instruction index where proven. The historical native metadata supports {tx['semantic_counts']}.
Pump.fun quote and token account deltas corroborate post-trade observations; inferred rent and
reserved-inventory offsets are disclosed and not independently bootstrapped. Multi-event
transactions require instruction-level reconstruction; whole-transaction balances alone do
not identify intermediate states. PumpSwap's two-buy maximum provides that reconstruction:
first event pre→second event pre→final native vault balances, with exact actual quote transfers.

Use the raw event's quote_amount_in_with_lp_fee (buy) or quote_amount_out_without_lp_fee (sell)
for vault movement. Gross quote_amount may differ substantially from that transfer; gross
budget plus an assumed LP fee is not equivalent. Existing pinned event decoding discards
those fields; the research decoder now captures them from the verified prefix without
changing production event classes or strategy settings.

The five synchronization classes are TRANSACTION_CORRELATED, STATE_SEQUENCE_RECONCILED,
SLOT_ONLY, RECEIPT_ONLY, UNSYNCHRONIZED. Only the first two are potentially eligible to
calibrate thresholds, and they still require verified identity, matching state boundary and
complete relevant mutations. Correlating the stream event to its transaction does NOT promote
the original later RPC comparison. All 180 original pairs remain SLOT_ONLY and ineligible.
There are zero validated simultaneous stream/RPC calibration residuals in this phase.
Finding a native event that exactly matches a later RPC state supports state evolution;
post-selecting such matches cannot produce a representative zero-disagreement distribution.

The fresh passive pilot captures signatures and log order, but confirmed-stream receipt order
does not prove block transaction order for every event. Its periodic RPC checks remain
SLOT_ONLY. Native snapshots also have virtual liquidity and token inventory distinct from
withdrawable vault balances. Pump.fun and PumpSwap statistics remain separate in
reconciliation_distribution.json. No disagreement bands or entry safety limit were set.
""",
        "LOCAL_STATE_TRACKER.md": f"""# Passive local reserve tracker

Implemented in src/memebot/research/reserve_sync.py, with no trading database or order publisher.
For Pump.fun, previous observed post-state plus signed quote/token changes predicts the next
post-state. A mismatch flags missing/other mutation evidence; it never silently declares a
stable price. For PumpSwap, use reported PRE state plus actual instruction quote-vault transfer
and signed base quantity to infer POST. Compare prior inferred post to next reported pre.
Duplicate signature/event pairs do not update state. Regressing slots do not overwrite latest
state. Unknown raw quote transfer yields UNKNOWN reconstructed post, rather than a guessed fee.

Final fresh pilot: {len(live['events'])} trade events across
{len({e['market_key'] for e in live['events']})} market keys, but only
{len(live['serious_candidates'])} new-token candidates required account reads. Candidate RPC:
bootstrap then at most once every ten receipt seconds, at most three checks/market and thirty
tokens; fair per-market quotas. The native notification cap of 25,000 stopped the pilot after
{eff['new_passive_pilot']['duration_seconds']:.3f}s; no automatic reconnect/retry spending.

{tx['live_local_transitions']} for physical AMM reserve continuity. Three full-state continuity
breaks are retained with exact deltas in transaction_reconciliation.json. Five additional native
block reads investigated these gaps: two have intervening native trades absent from the retained
stream capture; one remains UNKNOWN after examining adjacent blocks. This does not locate the
loss at the provider rather than buffering, decoding or collection cutoff. Virtual offsets can
change independently of ordinary trades; unexplained changes stay UNKNOWN. Fee, LP, boost,
deposit/withdraw, migration, direct vault transfers, burn/supply changes and missed messages
can invalidate a trade-only model. coverage_complete stays false. Tracker state is never
declared authoritative or used to open/close a position in this pass.

Future RPC duties: initial identity/reserve bootstrap, periodic reconciliation, anomaly repair,
execution-time refresh and exit recovery. Discovery/event ticks should update local evidence
without an account read each time. No production reconciliation interval is selected.
""",
        "RPC_EFFICIENCY_V2.md": f"""# RPC efficiency V2 — scenarios, no production policy

Entire phase: {eff['all_phase_rpc_requests']} RPC requests, below 300. Native transaction
evidence uses 16 cached block reads plus three failed version-limited attempts. Both passive
pilots, five local-gap block reads and shared getSlot/global-config probes are included. No transaction lookup for every
trade, no new provider, no trading writes, no orders. Currency/CU costs remain UNKNOWN;
getBlock and notification costs cannot be inferred from request count alone.

Final pilot measured {eff['new_passive_pilot']}. Shared health/config probes are separated
from market reads. Two sampled candidates in a short notification-limited window cannot
establish a universal requests-per-candidate requirement. The previous pilot had nine new
candidate tokens and 21 requests; its evidence is preserved separately. Candidate lifetimes,
venue mix, anomaly frequency, execution and exit duties determine real costs.

Original calibration pairing baseline: Pump.fun 173 reads (171 successes + two backward-slot
rejections), PumpSwap 18 (nine two-read snapshots), plus nine shared probes. Per-market
interval scenarios using recorded observation lifetimes and cached pool identity:
{json.dumps(eff['periodic_interval_seconds'], indent=2)}

Every 10 / 25 retained market-event scenarios:
{json.dumps(eff['every_n_recorded_events'], indent=2)}

Event-count scenarios use 180 retained observations, not all 251 original tracked events:
their exact venue allocation is unavailable. These are request-count projections, not validated
freshness policies. Divergence-only lower bound: seven curve bootstraps plus one pool bootstrap
and vault batch (two reads); anomaly repair adds unknown reads. It cannot replace periodic,
execution-time or exit RPC without demonstrated complete mutation capture.
Local trade decoding and actual quote-transfer arithmetic replace repeated observation reads;
cache pool identity and vault addresses, invalidate on migration/config change. No permanent
safety values, monthly cost forecast or production interval has been invented.
"""}
    for name, text in texts.items():
        (ROOT / "docs" / name).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
