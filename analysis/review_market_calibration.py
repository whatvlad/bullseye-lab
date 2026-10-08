"""Offline review of the bounded capture; optional four official documentation GETs."""
import argparse
import asyncio
import csv
import hashlib
import json
from collections import Counter
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import httpx

from memebot.models.market import LaunchVenue, MarketLifecycle
from memebot.paper.models import ExecutionMarketSnapshot
from memebot.providers.solana.pump_idl import IDL_COMMIT
from memebot.research.market_calibration import (
    distribution, grouped_distributions, local_quotes, percent,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis"


def write(name, payload):
    (OUT / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


async def official_idls():
    report = {"documentation_requests": [], "venues": {}}
    async with httpx.AsyncClient(timeout=15) as client:
        for venue, file, types in (
            ("pump_fun", "pump.json", ("BondingCurve", "CreateEvent", "TradeEvent", "Global", "FeeConfig")),
            ("pump_swap", "pump_amm.json", ("Pool", "CreatePoolEvent", "BuyEvent", "SellEvent", "GlobalConfig", "FeeConfig")),
        ):
            docs = {}
            for ref in (IDL_COMMIT, "main"):
                url = f"https://raw.githubusercontent.com/pump-fun/pump-public-docs/{ref}/idl/{file}"
                row = {"method": "GET", "url": url}
                report["documentation_requests"].append(row)
                try:
                    response = await client.get(url)
                    row["status"] = response.status_code
                    response.raise_for_status()
                    doc = response.json()
                    row["sha256"] = hashlib.sha256(response.content).hexdigest()
                    docs[ref] = {t["name"]: t["type"].get("fields", [])
                                 for t in doc["types"] if t["name"] in types}
                except (httpx.HTTPError, ValueError):
                    row["error"] = "DOCUMENT_UNAVAILABLE"
            result = {}
            for name in types:
                pinned = docs.get(IDL_COMMIT, {}).get(name)
                current = docs.get("main", {}).get(name)
                # Compare layout, not comments/docs.
                shape = lambda fields: [(f.get("name"), f.get("type")) for f in fields or []]
                old, new = shape(pinned), shape(current)
                result[name] = {"pinned_fields": old, "current_fields": new,
                                "same_layout": old == new and bool(old),
                                "pinned_prefix_preserved": new[:len(old)] == old and bool(old)}
            report["venues"][venue] = result
    write("fee_idl_validation.json", report)


def review():
    capture = json.loads((OUT / "market_data_samples.json").read_text())
    raw = OUT / "market_data_raw.json"
    if not raw.exists():
        raw.write_text(json.dumps(capture, indent=2) + "\n", encoding="utf-8")
    costs = json.loads((OUT / "provider_costs.json").read_text())
    samples = capture["samples"]
    for sample in samples:
        if sample["venue"] == "pump_swap":
            sample["pool_age_seconds_at_observation"] = sample.get("pool_age_seconds_at_observation", sample["token_age_seconds"])
            sample["token_age_seconds"] = None
            sample["token_age_bucket"] = "UNKNOWN"
            sample["token_age_quality"] = "POOL_CREATION_IS_NOT_TOKEN_CREATION"
        # Repair collector-only label inherited by refresh_with_diagnostics.
        # Reserves, timestamps and slots remain the captured historical instant.
        market = ExecutionMarketSnapshot(
            mint=sample["mint"], market=sample["market"], venue=LaunchVenue(sample["venue"]),
            lifecycle=MarketLifecycle.BONDING_CURVE if sample["venue"] == "pump_fun"
            else MarketLifecycle.POST_GRADUATION,
            observed_at=datetime.fromisoformat(sample["rpc_receipt_timestamp"]),
            source_slot=sample["rpc_response_slot"],
            observed_price_raw=Decimal(sample["rpc_marginal_mark"]),
            quote_asset=sample["quotes"][0]["buy"].get("quote_asset", "So11111111111111111111111111111111111111112"),
            **sample["rpc_reserves"],
        )
        market = replace(market, price_source="rpc_primary_reserves", source_timestamp=None,
                         received_timestamp=market.observed_at,
                         feed_timestamp=datetime.fromisoformat(sample["stream_receipt_timestamp"]),
                         feed_reference_price=Decimal(sample["stream_marginal_mark"]),
                         decision_price=Decimal(sample["stream_marginal_mark"]),
                         data_quality="rpc_slot_known_source_time_unknown", rpc_state="healthy")
        sample["quotes"] = local_quotes(market)
        sample["local_quote_state"] = "RPC_CAPTURED_RESERVES"
        sample["raw_price_unit"] = "quote_lamports_per_raw_token_unit"
        # A second purely local scenario shows execution spread at stream state.
        stream_market = replace(
            market, observed_at=market.feed_timestamp,
            received_timestamp=market.feed_timestamp, price_source=sample["provider"],
            source_slot=sample["stream_source_slot"],
            observed_price_raw=Decimal(sample["stream_marginal_mark"]),
            real_token_reserves_raw=sample["stream_real_token_reserves"],
            real_quote_reserves_raw=sample["stream_real_quote_reserves"],
            virtual_token_reserves_raw=sample["stream_virtual_token_reserves"]
                if sample["venue"] == "pump_fun" else None,
            virtual_quote_reserves_raw=sample["stream_virtual_quote_reserves"]
                if sample["venue"] == "pump_fun" else (
                    sample["stream_virtual_quote_reserves"] - sample["stream_real_quote_reserves"]),
        )
        sample["stream_state_quotes"] = local_quotes(stream_market)
        for q in sample["quotes"]:
            for side in ("buy", "sell"):
                price = q[side].get("executable_quote")
                q[f"stream_price_to_local_{side}_quote_percent"] = (
                    percent(Decimal(price), market.feed_reference_price) if price else None)
    capture["postprocessing"] = {
        "raw_capture_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
        "method": "Pure local quote replay at captured RPC reserves; corrected inherited provenance label; no new price observations",
        "review_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    write("market_data_samples.json", capture)
    dist = grouped_distributions(samples)
    for name, selected in (
        ("same_slot", [s for s in samples if s["slot_delta"] == 0]),
        ("same_slot_coherent", [s for s in samples if s["slot_delta"] == 0 and s["rpc_component_slots_coherent"]]),
        ("later_rpc_slot", [s for s in samples if (s["slot_delta"] or 0) > 0]),
    ):
        dist[name] = distribution([abs(s["stream_rpc_price_disagreement_percent"]) for s in selected])
    dist["receipt_delta_ms"] = distribution([s["receipt_time_delta_ms"] for s in samples])
    dist["slot_delta"] = distribution([s["slot_delta"] for s in samples if s["slot_delta"] is not None])
    dist["distinct_tokens_by_venue"] = {
        venue: len({s["mint"] for s in samples if s["venue"] == venue})
        for venue in ("pump_fun", "pump_swap")}
    write("disagreement_distribution.json", dist)
    # CSV has one quote-size row per pair; sample_id keeps pair N explicit.
    rows = []
    for i, s in enumerate(samples):
        for q in s["quotes"]:
            row = {"sample_id": i, **{k: v for k, v in s.items() if k != "quotes"}, **q}
            rows.append({k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in row.items()})
    if rows:
        with (OUT / "market_data_samples.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(dict.fromkeys(
                k for row in rows for k in row)))
            writer.writeheader()
            writer.writerows(rows)
    fee_path = OUT / "fee_idl_validation.json"
    if fee_path.exists():
        idls = json.loads(fee_path.read_text())
        costs["documentation_http_requests"] = idls["documentation_requests"]
        costs["documentation_http_request_count"] = len(idls["documentation_requests"])
    calls = [c for e in costs["rpc_endpoints"].values() for c in e["calls"]]
    costs["rpc_requests_by_method"] = dict(Counter(c["method"] for c in calls))
    if "observed_launch_mints" not in costs["funnel"]:
        costs["funnel"]["mixed_market_survivors_per_observed_launch_percent"] = 100 * costs["funnel"]["cheap_filter_survivors"] / costs["funnel"]["launches_observed"]
        costs["funnel"]["conversion_percent"]["launch_to_filter"] = None
        costs["funnel"]["launch_conversion_limitation"] = "Original pilot did not retain mint-set intersection; survivors mix new tokens and newly observed pools"
    pair_requests = sum(c["method"] != "getSlot" for c in calls) - 1  # one global config read
    costs["pairing_requests"] = pair_requests
    costs["pairing_requests_per_pair"] = pair_requests / len(samples) if samples else None
    costs["pairing_requests_per_deep_candidate"] = pair_requests / costs["funnel"]["deeply_inspected_candidates"] if costs["funnel"]["deeply_inspected_candidates"] else None
    costs["requests_per_candidate_including_probes"] = len(calls) / costs["funnel"]["cheap_filter_survivors"] if costs["funnel"]["cheap_filter_survivors"] else None
    costs["estimated_cost_per_1000_candidates"] = {
        "currency_cost": None, "nominal_rpc_requests_pump_fun": 1000,
        "nominal_rpc_requests_pump_swap_uncached": 2000, "pairs_per_candidate": 1}
    costs["estimated_cost_per_100_serious_candidates"] = {
        "currency_cost": None, "nominal_rpc_requests_pump_fun": 1000,
        "nominal_rpc_requests_pump_swap_uncached": 2000, "pairs_per_candidate": 10}
    costs["projection_scenarios"] = {
        "status": "REQUEST_COUNTS_ONLY_NOT_CURRENCY_OR_MEASURED_MONTHLY_FORECAST",
        "1000_selected_candidates_one_pair_each": {"pump_fun": 1000, "pump_swap_uncached_pool": 2000},
        "100_serious_candidates_ten_pairs_each": {"pump_fun": 1000, "pump_swap_uncached_pool": 2000},
        "monthly_formula_inputs_missing": ["representative launches/month", "filter conversion", "venue mix", "method CU billing", "provider plan"],
    }
    # Near-concurrent probes measure relative slots, not an independently known tip.
    endpoint_values = list(costs["rpc_endpoints"].values())
    costs["rpc_endpoint_comparisons"] = []
    if len(endpoint_values) == 2:
        probes = [[c for c in e["calls"] if c["method"] == "getSlot" and "slot" in c]
                  for e in endpoint_values]
        for a, b in zip(*probes):
            costs["rpc_endpoint_comparisons"].append({
                "primary_slot": a["slot"], "exit_slot": b["slot"],
                "primary_minus_exit_slot": a["slot"] - b["slot"],
                "receipt_delta_ms": abs((datetime.fromisoformat(a["received_at"]) - datetime.fromisoformat(b["received_at"])).total_seconds() * 1000)})
    write("provider_costs.json", costs)
    gate = json.loads((OUT / "calibration_gate.json").read_text())
    consistent = all(
        abs(Decimal(q[side]["actual_fill_price_raw"]) * Decimal(q[side]["token_amount_raw"])
        / Decimal(10**9) - Decimal(q[side]["gross_portfolio_amount"])) < Decimal("0.000000001")
        for s in samples for q in s["quotes"] for side in ("buy", "sell") if "rejection" not in q[side])
    gate["checks"]["prospective_distributions"] = len(samples) > 1
    gate["checks"]["execution_quotes_consistent"] = bool(samples) and consistent
    gate["coverage_sufficient"] = False
    gate["blockers"] = [k for k, v in gate["checks"].items() if not v] + [
        "180 snapshots / 8 tokens below 1000 / 100 targets; young active cohorts only",
        "No metered PumpPortal trade validation; discovery only",
        "Same-slot RPC reads are not transaction-specific synchronized state",
        "Dynamic fee config, canonical pool identity, mint supply and routing costs unverified",
        "CU billing and representative monthly volume unavailable; stopped at 200-request cap",
    ]
    gate["regression_validation"] = {"status": "PENDING"}
    write("calibration_gate.json", gate)
    documents(capture, costs, dist, gate)


def documents(capture, costs, dist, gate):
    run = costs["run"]
    f = costs["funnel"]
    stats = dist["overall_stream_rpc"]
    venue_rows = "\n".join(
        f"| {v} | {dist['distinct_tokens_by_venue'][v]} | " + " | ".join(
            str(round(x, 4)) if isinstance(x, float) else str(x)
            for x in dist["groups"].get(f"venue={v}", {}).get("stream_rpc_price_disagreement_percent", distribution([])).values()) + " |"
        for v in ("pump_fun", "pump_swap"))
    docs = {
        "MARKET_DATA_CALIBRATION.md": f"""# Market data calibration — BLOCKED

Passive pilot {run['started_at']} to {run['ended_at']} ({run['elapsed_seconds']:.3f}s).
Stopped at its hard 200-RPC-request cap before the 180s wall-clock cap. No orders, worker,
experiment activation or database writes. Strategy settings and live mode unchanged.
{f['paired_snapshots']} actual prospective pairs, {len({s['mint'] for s in capture['samples']})} tokens;
720 quote-size rows, not 720 independent pairs. Targets: 1000 pairs / 100 tokens.

| Venue | Tokens | N pairs | Median % | p75 % | p90 % | p95 % | p99 % | Max % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{venue_rows}

All-pair absolute disagreement: median {stats['median']:.4f}%, p95 {stats['p95']:.4f}%,
p99 {stats['p99']:.4f}%, max {stats['max']:.4f}%. These are pilot observations, not NORMAL bands.
Same-slot comparisons: `{json.dumps(dist['same_slot'])}`. Even same-slot comparisons
can represent different transactions, event pre/post state or end-of-slot account state.
No historical Cappuccinu ticks or fixture data were included.

The independent collector imports no trading engine, order publisher or database.
It subscribes to confirmed native logs for both programs and free PumpPortal creations/migrations.
Unknown markets cause no RPC reads. SOL markets created during the run enter a local filter
after two positive-amount trades. Queued observations older than two receipt seconds are rejected
as pairing failures; this is a research synchronization filter, not a strategy threshold.
Mayhem and non-SOL markets are excluded. Fee fidelity for cashback/rewards is not established.
Pump.fun ages are below 60s; PumpSwap token age is UNKNOWN. Pool creation age is recorded
separately and cannot substitute for token creation age. Original capture lacks the mint-set
intersection needed to prove an exact launch-only conversion. The collector now retains those
sets for future captures and caps each market at ten attempts with a one-second pairing interval.
Selection is biased toward young, active tokens; repeated snapshots of eight tokens are correlated.
Native activity received {costs['streams']['native_logs']['events']} tracked-market trades;
the collector received many more logs for unknown markets without querying their accounts.

Quote sizes .01/.025/.05/.1 SOL are research notionals only. Buy uses gross SOL budget;
sell uses token quantity of equal marginal SOL notional, not round-trip buy inventory.
Venue fees are modeled, service/network costs excluded and labeled. Slippage is UNKNOWN;
zero bps is a calculation scenario. Gross executable sell price is separated from net fee-adjusted
proceeds. All quotes remain ESTIMATED. JSON preserves integer reserves and complete local quote
evidence; CSV stores four rows per pair with explicit sample_id. The original capture is retained
in market_data_raw.json. Offline quote replay corrected inherited RPC provenance labels without
changing captured reserves, slots or times. The original collector hash stays in run metadata.

Distributions contain N/median/p75/p90/p95/p99/max separately for venue, quote size,
liquidity, age, adjacent-tick volatility and observed activity. Liquidity buckets use effective
quote reserves including virtual liquidity, not withdrawable depth. Unobserved buckets provide
no support. No NORMAL/ELEVATED/SEVERE values can be frozen from this sample.

Source policy: discovery can use free PumpPortal plus native creations; momentum needs native
trade events with gap/slot checks, with PumpPortal trade use still unvalidated. Entry and exit
execution require current owner/mint-validated reserves and quantity-specific executable quotes.
Exit recovery uses the existing independent RPC path. Unrealized PnL uses net executable full-size
sell proceeds less remaining basis. Marginal trades and reserve marks are references, not fills.

Both streams and both RPCs worked during this short pilot. That does not establish reliability
under outages. Large disagreement, missing venue/cohort coverage, fee fidelity and unpriced CU
usage keep the experiment BLOCKED. The experiment start gate now requires calibration PASSED
in addition to the earlier price prerequisite gate; this run cannot activate it.

Reproduce with `python -m memebot.research.market_calibration --seconds 180 --max-rpc-requests 200`.
Running again replaces primary outputs; archive them first. No extra provider spending is needed
to inspect the existing evidence. Before a larger capture, set a reviewed provider CU budget and
improve fair sampling so a handful of active tokens cannot consume the whole budget.
""",
        "RPC_VALIDATION.md": f"""# RPC validation — short pilot only

Confirmed slot probes ran four times on each configured HTTP endpoint. All were successful.
{json.dumps({k: {x: v[x] for x in ('requests', 'slot_sequence', 'duplicate_slots', 'regressions', 'latency_distribution_ms')} for k, v in costs['rpc_endpoints'].items()}, indent=2)}

Near-concurrent primary-minus-exit slots: {[c['primary_minus_exit_slot'] for c in costs['rpc_endpoint_comparisons']]}.
Receipt deltas are retained in provider_costs.json; this is relative endpoint comparison,
not lag against an independently proven chain tip. A fast HTTP response does not prove freshness.
Two paired reads were rejected as rpc_slot_regressed relative to their stream slot, despite
monotonically progressing getSlot probes. No HTTP 429, timeout or transport error occurred.
PumpSwap pool and vault reads can span distinct context slots and are explicitly flagged;
they must not be silently treated as an atomic snapshot. No transaction-specific historical
state query was made. The public endpoint was used only for four independent slot probes.
Its reserve/quote accuracy and long-term exit capacity are not established by this run.
RPC timing is SLOT_ONLY; block time/source wall-clock time and absolute price age remain unknown.
Endpoint identities contain hostname and digest, never credential-bearing URL paths.
""",
        "STREAM_VALIDATION.md": f"""# Stream validation — purpose-specific

Native logs: {costs['streams']['native_logs']['messages']} messages, two subscription acknowledgments,
{costs['streams']['native_logs']['events']} tracked-market trade observations, no reconnects or
reported connection/subscription errors. No tracked trade had a missing slot or lower slot than
the prior maximum. Duplicate signatures/events are counted and ignored. Most messages concern
unknown markets and trigger no RPC lookup. Event-rate/gap statistics describe tracked trades,
not the provider's entire trade universe. Zero reported reconnects is not an outage recovery test.

PumpPortal: {costs['streams']['pumpportal']['messages']} messages, two acknowledgments,
{costs['streams']['pumpportal']['events']} creation observations, all source times estimated and
all slots missing. Free discovery worked during this pilot. Trades were deliberately not
subscribed, so momentum/execution suitability remains UNVALIDATED, not proven unsuitable.
Discovery events never substitute for momentum ticks or executable state.

Native decoded event timestamps are chain-origin program fields but were not verified against
blockTime: classification SLOT_ONLY. RPC is SLOT_ONLY. PumpPortal is RECEIPT_ESTIMATE.
No samples claim VERIFIED_CHAIN_TIME. Receipt time is UTC wall clock; monotonic time measures
local durations only. Neither establishes transaction simultaneity. Gaps between market events
are not proof of stream failure or an unchanged price. Last-event silence is reported even if
the stream sends no further events. Track per-mint cadence and provider traffic separately
in a broader follow-up; this pilot cannot infer venue-wide missing trades.

Native tracked-trade receipt gaps (ms): {json.dumps(costs['streams']['native_logs']['receipt_gap_distribution_ms'])}.
PumpPortal creation gaps (ms): {json.dumps(costs['streams']['pumpportal']['receipt_gap_distribution_ms'])}.
There were 36 locally stale queue observations rejected, demonstrating why unlimited repeated
pairing on a handful of hot tokens is an inefficient collection policy.

PumpPortal explicitly prices token/account trade subscriptions while new-token/migration
subscriptions are free: [official fees](https://pumpportal.fun/fees/). No metered trade subscriptions
or wallet funding were performed. Receiving discovery does not validate paid-trade coverage.
""",
        "FEE_VALIDATION.md": f"""# Fee validation — ESTIMATED

Local Pump.fun uses 125 bps, with buy fee components 95 protocol + 30 creator bps.
Local canonical SOL PumpSwap uses market-cap tiers 125 down to 30 bps and a fixed 1B-token
supply assumption. The [current official fee page](https://pump.fun/docs/fees) supports the
published bonding-curve total and canonical tier schedule, but differentiates noncanonical
pools (30 bps), creator behavior and other modes. This is documentation agreement, not
per-market on-chain proof.

One chain read of PumpSwap GlobalConfig at slot {costs['fee_configuration'].get('slot')},
owner validated, captured fallback LP/protocol/creator bps:
{costs['fee_configuration'].get('lp_fee_bps')}/{costs['fee_configuration'].get('protocol_fee_bps')}/{costs['fee_configuration'].get('creator_fee_bps')}.
These are fallback fields, not evidence that the sampled canonical markets charge their sum.
Raw account bytes and SHA256 are retained in provider_costs.json.

The [official fee-program logic](https://github.com/pump-fun/pump-public-docs/blob/main/docs/FEE_PROGRAM_README.md)
requires FeeConfig when available, actual mint supply, market-cap tier selection and canonical
pool-authority verification. These were not obtained for every sampled market. Current/pinned
official IDL layout comparison is retained in fee_idl_validation.json with hashes. Added reward,
buyback or configurable creator fields require explicit support before exact-fidelity claims.
Pool/event prefix compatibility does not prove complete fee handling.

Creator existence, cashback/rewards, custom configurations and total protocol/creator/LP costs
are not automatically interchangeable. Pump graduation is an additional documented 0.015 SOL
operation, not a recurring fee for every research quote. Network signature/priority fees,
account creation/rent and transfer-fee extensions are route-dependent and unverified here.
No transaction was submitted or simulated against the chain. Local reserve quotes therefore
remain ESTIMATED and cannot support an exact or safely bounded fee gate.

PumpPortal [official fees](https://pumpportal.fun/fees/) currently separate Local transaction
service fee 50 bps from Lightning 100 bps, before slippage and excluding network/venue fees.
Research quotes use neither service and explicitly exclude those charges. Production routing
must match its actual fee model. Zero slippage in this calibration is a scenario, not a forecast.
""",
        "API_COST_CALIBRATION.md": f"""# API cost calibration — request cost measured; billing unresolved

Hard cap: 200 actual RPC requests, then stop. Method counts: {costs['rpc_requests_by_method']}.
Primary 196 / public exit 4. Native WSS: one connection, two subscription requests;
PumpPortal WSS: one connection, two FREE subscription requests. No metered trade events.
Four separately recorded official GitHub documentation GETs are outside trading-provider CU
billing. Browser documentation research is outside the calibration process.

Funnel: {f['launches_observed']} distinct creations observed, {f['pool_creations_observed']} pool
creations, {f['cheap_filter_survivors']} local activity survivors, {f['paired_calibration_candidates']}
paired tokens, {f['deeply_inspected_candidates']} deeply inspected tokens, {f['paired_snapshots']}
pairs. Creations are deduplicated across streams. Pool creations are recorded separately;
not all pool creations are new tokens. Original capture did not retain the exact mint-set
intersection for a launch-only conversion: this rate is UNKNOWN. Mixed market survivors per
observed launch is 36.36%, which is not a launch-only conversion.
Filter-to-pair {f['conversion_percent']['filter_to_pair']:.2f}%. These tiny-window conversions
are biased estimates and cannot be used as representative monthly throughput.

Observed requests: {costs['requests_per_launch_including_probes']:.3f}/launch including shared
health/config probes; {costs['requests_per_candidate_including_probes']:.3f}/candidate including
probes; {costs['pairing_requests_per_deep_candidate']:.3f} pairing reads/deep candidate;
{costs['pairing_requests_per_pair']:.3f} pairing reads/pair including unsuccessful attempts.
CU/credit/currency charges are UNKNOWN, not zero: RPC responses provide no billing counters,
and native WSS notification CU accounting was not supplied. No billing-plan query or new API
purchase was made. PumpPortal discovery/migration stream charge is zero under its
[published schedule](https://pumpportal.fun/fees/); RPC/WSS plan costs remain unresolved.

Analytic request-only scenarios, NOT dollar forecasts: 1000 selected candidates with one pair
each require about 1000 Pump.fun reads or 2000 uncached PumpSwap reads, plus failures/probes.
100 serious candidates with ten pairs each have the same nominal request totals. Cached pool
metadata can remove repeated PumpSwap pool reads, leaving one vault batch per pair; invalidate
on migration/config change. Add any independent reference subset explicitly to the budget.
Monthly currency cost cannot be estimated honestly from 41s without launch-volume, conversion,
sampling policy, venue mix and method/CU billing inputs. Machine projections are null, with
request-count scenarios and formula retained.

Calls avoided: account reads for every new/unknown token; RPC transaction lookup per trade;
separate buy/sell quote-provider calls; FX calls for SOL-unit research; repeated supply/fee
config fetching; optional price APIs; all order-building/submission calls. Event decoding,
trade amounts, reserve marks, token age and local activity/volatility can be calculated locally.
Cache immutable market identities and versioned config; fresh reserves and exit recovery still
need timely observations. The first pilot over-sampled eight hot tokens; fair per-market
quotas/throttling should improve coverage before authorizing a larger metered capture.
""",
    }
    for filename, text in docs.items():
        (ROOT / "docs" / filename).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch-official-idls", action="store_true")
    args = parser.parse_args()
    if args.fetch_official_idls:
        asyncio.run(official_idls())
    review()
