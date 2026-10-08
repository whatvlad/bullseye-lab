from dataclasses import replace
from decimal import Decimal

import httpx
import pytest

from memebot.core.config import Settings
from memebot.paper.validation_gate import require_price_validation
from memebot.providers.solana.rpc import SolanaRpcError
from memebot.research.market_calibration import (
    CalibrationRpc,
    Collector,
    RequestBudget,
    distribution,
    grouped_distributions,
    identity,
    local_quotes,
    percent,
)
from test_paper_execution import _market


def test_empty_evidence_does_not_become_zero_disagreement_or_bands():
    result = grouped_distributions([])
    assert result["overall_stream_rpc"]["N"] == 0
    assert result["overall_stream_rpc"]["p99"] is None
    assert all(value is None for value in result["bands"].values())
    assert percent(3, 0) is None


def test_quantiles_include_tails_and_singleton_without_nan():
    assert distribution([1, 2, 3, 4])["median"] == 2.5
    assert distribution([float("nan"), 7])["p99"] == 7
    assert distribution([])["max"] is None


def test_disagreement_group_counts_pairs_once_in_each_cohort():
    base = {
        "venue": "pump_fun",
        "liquidity_bucket": "10to100SOL",
        "token_age_bucket": "lt60s",
        "volatility_bucket": "lt1pct",
        "market_activity_state": "active",
        "stream_rpc_price_disagreement_percent": 2,
        "quotes": [{"research_size_sol": str(size)} for size in range(4)],
    }
    result = grouped_distributions([base, {**base, "venue": "pump_swap"}])
    assert result["groups"]["venue=pump_fun"]["stream_rpc_price_disagreement_percent"]["N"] == 1
    assert result["groups"]["venue=pump_swap"]["stream_rpc_price_disagreement_percent"]["N"] == 1
    assert (
        result["groups"]["liquidity_bucket=10to100SOL"]["stream_rpc_price_disagreement_percent"][
            "N"
        ]
        == 2
    )


def test_endpoint_identity_cannot_expose_key_path_or_query():
    result = identity("https://example.com/v2/SECRET?api-key=ANOTHER")
    assert result.startswith("example.com#")
    assert "SECRET" not in result and "ANOTHER" not in result


@pytest.mark.asyncio
async def test_rpc_budget_whitelist_and_request_accounting():
    rpc = CalibrationRpc("https://example.com/secret", RequestBudget(1))
    await rpc._client.aclose()
    rpc._client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": 123})
        )
    )
    try:
        with pytest.raises(ValueError, match="forbidden"):
            await rpc._call("sendTransaction")
        assert rpc.budget.used == 0
        assert await rpc._call("getSlot") == 123
        with pytest.raises(SolanaRpcError, match="calibration_request_cap"):
            await rpc._call("getSlot")
        assert rpc.budget.used == 1
        assert len(rpc.calls) == 1
        assert rpc.calls[0]["slot"] == 123
        assert rpc.calls[0]["latency_ms"] >= 0
    finally:
        await rpc.close()


def test_quote_sizes_use_reserves_fees_and_do_not_guarantee_marginal_fill():
    rows = local_quotes(_market())
    assert [row["research_size_sol"] for row in rows] == ["0.01", "0.025", "0.05", "0.1"]
    for row in rows:
        assert row["quality"] == "ESTIMATED"
        assert row["estimated_slippage_bps"] is None
        assert row["rpc_mark_to_local_buy_quote_percent"] > 0
        assert row["rpc_mark_to_local_sell_quote_percent"] < 0
        assert Decimal(row["buy"]["venue_fee_quote_raw"]) > 0
        assert Decimal(row["sell_net_unit_price_raw"]) < Decimal(row["sell"]["executable_quote"])


def test_missing_real_reserves_are_rejected_by_calibration_model():
    market = replace(_market(), real_quote_reserves_raw=None)
    rows = local_quotes(market)
    assert all(row["buy"].get("rejection") for row in rows)
    assert all(row["sell"].get("rejection") for row in rows)


@pytest.mark.asyncio
async def test_output_gate_never_automatically_starts_an_experiment(tmp_path, monkeypatch):
    import json

    import memebot.research.market_calibration as module

    monkeypatch.setattr(module, "ROOT", tmp_path)
    collector = Collector(Settings(_env_file=None), seconds=1, max_requests=8)
    try:
        collector.write_outputs()
        gate = json.loads((tmp_path / "analysis/calibration_gate.json").read_text())
        assert gate["status"] == "BLOCKED"
        assert gate["runner-edge-prospective-v1"] == "BLOCKED"
        assert gate["automatically_activates_experiment"] is False
        assert gate["paired_snapshots"] == 0
        costs = json.loads((tmp_path / "analysis/provider_costs.json").read_text())
        assert costs["currency_cost"] is None
        assert costs["requests_per_paired_snapshot"] is None
    finally:
        for rpc in collector.rpcs:
            await rpc.close()


def test_experiment_gate_requires_calibration_and_representative_coverage(tmp_path):
    import json

    path = tmp_path / "analysis"
    path.mkdir()
    (path / "calibration_gate.json").write_text(
        json.dumps({"status": "PASSED", "coverage_sufficient": False, "checks": {}})
    )
    with pytest.raises(ValueError, match="market-data calibration has not passed"):
        require_price_validation("runner-edge-prospective-v1", {}, root=tmp_path)


@pytest.mark.asyncio
async def test_cheap_filter_and_pending_market_quota_make_no_provider_calls():
    from test_paper_execution import NOW

    collector = Collector(Settings(_env_file=None), seconds=1, max_requests=8)
    context = {
        "mint": _market().mint,
        "market": _market().market,
        "venue": _market().venue,
        "created": NOW.timestamp(),
        "quote": _market().quote_asset,
    }
    state = collector.stream_state("native_logs")
    try:
        collector.observe(
            context,
            1,
            int(NOW.timestamp()),
            NOW,
            state,
            30_000_000_000,
            1_000_000_000_000_000,
            1_000_000_000,
            700_000_000_000_000,
            1,
            1,
        )
        assert collector.queue.empty()  # launch/first trade never deeply queried
        for _ in range(3):
            collector.observe(
                context,
                1,
                int(NOW.timestamp()),
                NOW,
                state,
                30_000_000_000,
                1_000_000_000_000_000,
                1_000_000_000,
                700_000_000_000_000,
                1,
                1,
            )
        assert collector.queue.qsize() == 1
        assert collector.market_pair_attempts[context["market"]] == 1
        assert collector.budget.used == 0
        assert state["local_sampling_skips"] == 2
    finally:
        for rpc in collector.rpcs:
            await rpc.close()
