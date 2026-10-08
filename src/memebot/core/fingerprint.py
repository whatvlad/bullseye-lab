"""Version experiments by executable source, not by a mutable display version."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import Any

from memebot.storage.database.control import TradingControlSnapshot


def code_fingerprint() -> str:
    root = Path(__file__).resolve().parents[1]
    digest = sha256()
    for path in sorted(root.rglob("*.py")):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def experiment_matches(
    experiment: dict[str, Any] | None,
    summary: dict[str, object],
    control: TradingControlSnapshot | None,
) -> bool:
    if experiment is None or control is None:
        return False
    snapshot = experiment.get("configuration_snapshot", {})
    settings = snapshot.get("settings", {})
    if settings.get("code_fingerprint") != summary.get("code_fingerprint"):
        return False
    if settings.get("execution_parameters") != summary.get("execution_parameters"):
        return False
    actual = {key: str(value) for key, value in asdict(control).items() if key != "entries_paused"}
    expected = {key: str(value) for key, value in snapshot.get("trading_control", {}).items()}
    return actual == expected
