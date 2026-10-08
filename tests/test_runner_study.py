import hashlib
import json
from pathlib import Path

import pytest

from memebot.research.runner_study import (
    asof,
    failure_signals,
    peak_label,
    perf,
    spearman,
    verify_capture,
)


def tick(t: float, price: float, market: str = "a") -> dict:
    return {"t": t, "price": price, "market_address": market, "quote_asset": "SOL"}


def test_asof_never_selects_a_future_or_expired_tick() -> None:
    ticks = [tick(1, 10), tick(5, 100)]
    assert asof(ticks, 3)["price"] == 10
    assert asof(ticks, 4) is None
    assert asof(ticks, 0.5) is None


def test_peak_label_excludes_future_and_other_market_prices() -> None:
    ticks = [tick(0, 100), tick(1, 110), tick(2, 500, "b"), tick(3, 120), tick(4, 1000)]
    result = peak_label(ticks, 0, 3)
    assert round(result["peak_return_percent"], 6) == 20
    assert result["coverage"] == "bounded_observation"


def test_a_sparse_peak_is_not_complete_forward_coverage() -> None:
    result = peak_label([tick(0, 100), tick(1, 200)], 0, 30)
    assert result["peak_return_percent"] == 100
    assert result["coverage"] == "gappy"
    assert result["endpoint_return_percent"] is None


def test_spearman_handles_tied_ranks_and_constant_variables() -> None:
    assert spearman([(1, 4), (1, 4), (2, 8), (3, 12)]) == 1
    assert spearman([(1, 4), (1, 8), (1, 12)]) is None


def test_missing_outcomes_are_excluded_not_zero_losses() -> None:
    result = perf(
        [
            {"net_return_percent": 10, "mint": "a"},
            {"net_return_percent": -20, "mint": "b"},
            {"net_return_percent": None, "mint": "c"},
        ]
    )
    assert result["N_total"] == 3
    assert result["N_usable"] == 2
    assert result["net_expectancy_percent"] == -5
    assert result["profit_factor"] == 0.5


def test_unknown_failure_evidence_cannot_trigger_a_signal() -> None:
    assert failure_signals({"metrics": {}}) == []
    assert (
        failure_signals(
            {
                "metrics": {
                    "latest_price_return_percent": -10,
                    "latest_sell_liquidity_fraction": None,
                }
            }
        )
        == []
    )
    assert failure_signals(
        {"metrics": {"latest_price_return_percent": -10, "latest_sell_liquidity_fraction": 0.1}}
    ) == ["large_sell_with_price_shock"]


def test_changed_evidence_capture_is_rejected(tmp_path: Path) -> None:
    evidence = b'{"record":1}\n'
    (tmp_path / "tokens.jsonl").write_bytes(evidence)
    (tmp_path / "manifest.json").write_text(
        json.dumps({"tokens": {"rows": 1, "sha256": hashlib.sha256(evidence).hexdigest()}})
    )
    verify_capture(tmp_path)
    (tmp_path / "tokens.jsonl").write_bytes(b'{"record":2}\n')
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_capture(tmp_path)
