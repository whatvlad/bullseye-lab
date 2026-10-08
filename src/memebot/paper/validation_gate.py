"""A research run needs recorded validation of the actual code and safety configuration."""

import hashlib
import json
from pathlib import Path
from typing import Any

RUNNER_EXPERIMENT = "runner-edge-prospective-v1"
ROOT = Path(__file__).resolve().parents[3]
REQUIRED_CHECKS = (
    "price_provenance_explicit",
    "execution_evidence_consistent",
    "stale_entries_blocked",
    "exit_recovery_tested",
    "source_disagreement_configured",
    "regression_tests_passed",
    "operational_feed_and_rpc_verified",
)
SAFETY_KEYS = (
    "paper_entry_max_feed_age_seconds",
    "paper_entry_require_rpc",
    "paper_entry_allow_estimated_feed_time",
    "paper_entry_max_source_disagreement_percent",
    "paper_max_market_staleness_seconds",
    "paper_exit_recovery_attempt_timeout_seconds",
)
CRITICAL_FILES = (
    "src/memebot/providers/solana/trade_alignment.py",
    "src/memebot/providers/solana/execution_accounting.py",
    "src/memebot/research/early_watch.py",
    "src/memebot/research/early_watch_run.py",
    "src/memebot/research/packet_forensics.py",
    "src/memebot/providers/solana/alchemy_evidence.py",
    "src/memebot/providers/solana/watch_cohort.py",
    "src/memebot/research/filtered_stream_run.py",
    "src/memebot/providers/solana/_yellowstone_generated/SOURCE.json",
    "src/memebot/providers/solana/_yellowstone_generated/geyser.proto",
    "src/memebot/providers/solana/_yellowstone_generated/solana-storage.proto",
    "src/memebot/providers/solana/_yellowstone_generated/geyser_pb2.py",
    "src/memebot/providers/solana/_yellowstone_generated/solana_storage_pb2.py",
    "src/memebot/paper/stream_proof.py",
    "src/memebot/providers/solana/evidence_stream.py",
    "src/memebot/providers/solana/helius_evidence.py",
    "src/memebot/research/stream_proof_run.py",
    "src/memebot/paper/candidate_proof.py",
    "src/memebot/paper/standard_math.py",
    "src/memebot/research/candidate_proof_run.py",
    "src/memebot/eligibility.py",
    "src/memebot/research/standard_universe.py",
    "src/memebot/intelligence/alpha_filter.py",
    "src/memebot/intelligence/risk/coordinator.py",
    "src/memebot/market_state.py",
    "src/memebot/providers/solana/bootstrap.py",
    "src/memebot/providers/solana/canonical.py",
    "src/memebot/providers/solana/idl_schema.py",
    "src/memebot/providers/solana/invalidation.py",
    "src/memebot/providers/solana/idl/pump.json",
    "src/memebot/providers/solana/idl/pump_amm.json",
    "src/memebot/providers/solana/idl/pump_fees.json",
    "src/memebot/research/state_trust_validation.py",
    "src/memebot/research/pumpfun_sequence.py",
    "src/memebot/providers/solana/encoding.py",
    "pyproject.toml",
    "src/memebot/paper/models.py",
    "src/memebot/market_price.py",
    "src/memebot/providers/solana/pump.py",
    "src/memebot/research/production_state_validation.py",
    "src/memebot/paper/engine.py",
    "src/memebot/paper/execution.py",
    "src/memebot/paper/price_safety.py",
    "src/memebot/paper/market_refresh.py",
    "src/memebot/paper/manual.py",
    "src/memebot/paper/validation_gate.py",
    "src/memebot/research/market_calibration.py",
    "src/memebot/research/reserve_sync.py",
    "src/memebot/paper/fees.py",
    "src/memebot/providers/solana/pump_idl.py",
    "src/memebot/core/config.py",
    "src/memebot/storage/database/registry.py",
    "src/memebot/storage/database/models.py",
    "src/memebot/storage/database/experiments.py",
    "src/memebot/apps/worker.py",
    "src/memebot/apps/telegram.py",
    "src/memebot/intelligence/features/engine.py",
    "src/memebot/strategies/runner.py",
    "src/memebot/models/paper.py",
    "src/memebot/events/models.py",
    "migrations/versions/20261001_0016_execution_marks.py",
)


def require_price_validation(
    name: str, settings_snapshot: dict[str, Any], *, root: Path = ROOT
) -> None:
    if name != RUNNER_EXPERIMENT:
        return
    try:
        calibration = json.loads(
            (root / "analysis/calibration_gate.json").read_text(encoding="utf-8")
        )
        calibration_checks = (
            "prospective_distributions",
            "timing_understood",
            "rpc_freshness_acceptable",
            "stream_reliability_acceptable",
            "execution_quotes_consistent",
            "fees_bounded",
            "cost_understood",
            "safety_bands_supported",
        )
        if (
            calibration.get("status") != "PASSED"
            or calibration.get("coverage_sufficient") is not True
            or not all(
                calibration.get("checks", {}).get(check) is True for check in calibration_checks
            )
        ):
            raise ValueError("market-data calibration has not passed")
        report = json.loads((root / "analysis/price_validation.json").read_text(encoding="utf-8"))
        if report["status"] != "passed" or not all(
            report["checks"].get(check) is True for check in REQUIRED_CHECKS
        ):
            raise ValueError("prerequisite checks have not all passed")
        fingerprints = report["code_sha256"]
        if not set(CRITICAL_FILES).issubset(fingerprints):
            raise ValueError("validation has no code fingerprints")
        for relative, expected in fingerprints.items():
            path = (root / relative).resolve()
            if not path.is_relative_to(root.resolve()):
                raise ValueError("invalid validation path")
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError("code changed since prerequisite validation")
        if settings_snapshot.get("paper_entry_max_source_disagreement_percent") is None:
            raise ValueError("source disagreement entry limit is unconfigured")
        for key in SAFETY_KEYS:
            expected = report["safety_configuration"][key]
            if settings_snapshot.get(key) != expected:
                raise ValueError("safety configuration changed since validation")
    except (OSError, KeyError, TypeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(
            f"runner price validation blocked: {exc}; see docs/PRICE_VALIDATION.md"
        ) from exc
