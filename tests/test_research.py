from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from memebot.core.metrics import EventMetrics, distribution
from memebot.events.models import (
    MarketFeatureSnapshotCreated,
    TokenDiscovered,
    TokenRiskAssessed,
)
from memebot.models.risk import RiskResult
from memebot.research.features import analyze_rows
from memebot.research.forensics import performance, summarize_snapshot
from memebot.research.replay import replay_decisions
from memebot.strategies.presets import initial_strategy_presets
from memebot.strategies.runner import MultiStrategyRunner

NOW = datetime(2026, 9, 30, tzinfo=UTC)
MINT = "So11111111111111111111111111111111111111112"


def evidence():
    discovery = TokenDiscovered(
        event_id=UUID(int=1),
        provider="test",
        mint=MINT,
        source_event_at=NOW - timedelta(seconds=30),
        ingested_at=NOW,
    )
    feature = MarketFeatureSnapshotCreated(
        event_id=UUID(int=2),
        provider="test",
        mint=MINT,
        trigger_event_id=UUID(int=1),
        source_event_at=NOW,
        ingested_at=NOW + timedelta(seconds=1),
        windows=(),
    )
    risk = TokenRiskAssessed(
        event_id=UUID(int=3),
        provider="test",
        mint=MINT,
        trigger_event_id=UUID(int=2),
        source_event_at=NOW,
        ingested_at=NOW + timedelta(seconds=2),
        result=RiskResult(
            allowed=False,
            risk_score=Decimal(100),
            data_completeness_percent=Decimal(100),
            hard_reject_reasons=("freeze_authority_enabled",),
        ),
    )
    return discovery, feature, risk


def test_replay_matches_live_strategy_and_is_deterministic():
    discovery, feature, risk = evidence()
    configurations = initial_strategy_presets()
    stream = [discovery, feature, risk, risk]
    replayed = list(replay_decisions(stream, configurations))
    expected = [
        decision.model_dump(mode="json")
        for decision in MultiStrategyRunner(configurations).evaluate(
            risk, feature, token_created_at=discovery.source_event_at
        )
    ]
    assert replayed == expected
    assert list(replay_decisions(stream, configurations)) == replayed
    assert len(replayed) == 3


def test_replay_never_uses_future_or_not_yet_received_feature():
    discovery, feature, risk = evidence()
    future = feature.model_copy(update={"source_event_at": NOW + timedelta(seconds=10)})
    decisions = list(replay_decisions([discovery, future, risk], initial_strategy_presets()))
    assert all(row["feature_event_id"] is None for row in decisions)
    delayed = feature.model_copy(update={"ingested_at": NOW + timedelta(seconds=3)})
    decisions = list(replay_decisions([discovery, risk, delayed], initial_strategy_presets()))
    assert all(row["feature_event_id"] is None for row in decisions)


def test_replay_rejects_source_sorted_arrival_history():
    discovery, feature, risk = evidence()
    with pytest.raises(ValueError, match="ingestion order"):
        list(replay_decisions([risk, discovery, feature], initial_strategy_presets()))


def test_metrics_do_not_claim_estimated_launch_latency():
    discovery, _, _ = evidence()
    metrics = EventMetrics(sample_capacity=2)
    metrics.observe(discovery.model_copy(update={"source_timestamp_estimated": True}), NOW)
    assert metrics.snapshot()["latency"] == {}
    metrics.observe(discovery, NOW)
    assert metrics.snapshot()["latency"]["discovery_latency_ms"]["p50"] == 30000
    assert distribution([])["p99"] is None


def test_expectancy_counts_breakevens_and_uses_net_costs_once():
    stats = performance([Decimal(3), Decimal(-5), Decimal(0)], initial_cash=Decimal(100))
    assert stats["net_pnl"] == -2
    assert stats["net_expectancy"] == Decimal(-2) / 3
    assert stats["profit_factor"] == Decimal("0.6")
    assert stats["realized_max_drawdown_amount"] == 5
    assert performance([])["win_rate"] is None


def test_portfolios_with_duplicate_names_are_not_lost():
    report = summarize_snapshot(
        {
            "portfolios": [
                {
                    "id": "a",
                    "name": "Default",
                    "initial_cash": "100",
                    "cash_balance": "100",
                    "realized_pnl": "0",
                },
                {
                    "id": "b",
                    "name": "Default",
                    "initial_cash": "100",
                    "cash_balance": "100",
                    "realized_pnl": "0",
                },
            ]
        }
    )
    assert set(report["portfolios"]) == {"a", "b"}


def test_feature_research_excludes_unknown_labels_and_purges_split_boundaries():
    row = {
        "mint": MINT,
        "decision_event_id": "a",
        "decided_at": NOW,
        "feature_snapshot_json": {
            "event_id": "feature",
            "observed_at": NOW.isoformat(),
            "windows": [{"window_seconds": 30, "buy_sell_volume_ratio": "2"}],
        },
        "horizon_returns_json": {
            "10": {"return_percent": "50", "coverage": "observed"},
            "30": {"return_percent": "100"},
            "300": {"return_percent": "200", "coverage": "observed"},
        },
    }
    report = analyze_rows([row, row], NOW + timedelta(seconds=120), NOW + timedelta(days=1))
    assert report["coverage"]["train:10s:observed"] == 1
    assert report["coverage"]["train:30s:unknown_quality"] == 1
    assert report["coverage"]["train:300s:purged_boundary"] == 1
