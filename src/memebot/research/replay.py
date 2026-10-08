from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from memebot.events.models import (
    DomainEvent,
    MarketFeatureSnapshotCreated,
    TokenDiscovered,
    TokenRiskAssessed,
    parse_core_event,
)
from memebot.models.strategy import StrategyConfiguration
from memebot.strategies.presets import initial_strategy_presets
from memebot.strategies.runner import MultiStrategyRunner


def read_events(path: Path) -> Iterator[DomainEvent]:
    with path.open(encoding="utf-8-sig") as stream:
        for number, line in enumerate(stream, 1):
            if line.strip():
                try:
                    yield parse_core_event(json.loads(line))
                except (ValueError, TypeError) as error:
                    raise ValueError(f"invalid event at line {number}") from error


def replay_decisions(
    events: Iterable[DomainEvent],
    configurations: tuple[StrategyConfiguration, ...],
) -> Iterator[dict[str, Any]]:
    """Live scoring/gates, recorded risk/features, strictly in arrival order.

    Decision replay, not fill replay. No retrospective risk API queries.
    Features arriving after a risk assessment cannot affect that assessment.
    """
    runner = MultiStrategyRunner(configurations)
    created: dict[str, datetime] = {}
    features: dict[str, list[MarketFeatureSnapshotCreated]] = defaultdict(list)
    seen: set[UUID] = set()
    last_ingested: datetime | None = None
    for event in events:
        if last_ingested is not None and event.ingested_at < last_ingested:
            raise ValueError("events must be in ingestion order; never sort by source time")
        last_ingested = event.ingested_at
        if event.event_id in seen:
            continue
        seen.add(event.event_id)
        if isinstance(event, TokenDiscovered):
            created.setdefault(event.mint, event.source_event_at)
        elif isinstance(event, MarketFeatureSnapshotCreated):
            features[event.mint].append(event)
        elif isinstance(event, TokenRiskAssessed):
            eligible = [
                item
                for item in features[event.mint]
                if item.source_event_at <= event.source_event_at
            ]
            feature = max(eligible, key=lambda item: item.source_event_at, default=None)
            birth = created.get(event.mint)
            if birth is not None and birth > event.source_event_at:
                birth = None
            for decision in runner.evaluate(event, feature, token_created_at=birth):
                yield decision.model_dump(mode="json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline deterministic decision replay")
    parser.add_argument(
        "--session", type=Path, required=True, help="JSONL file or exported session directory"
    )
    parser.add_argument(
        "--configurations",
        type=Path,
        help="immutable strategy configurations; defaults to session manifest",
    )
    parser.add_argument(
        "--current-presets",
        action="store_true",
        help="explicit counterfactual using current presets",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.session / "events.jsonl" if args.session.is_dir() else args.session
    config_path = args.configurations or source.parent / "strategies.json"
    if args.current_presets:
        configurations = initial_strategy_presets()
        config_source = "current_presets_counterfactual"
    else:
        if not config_path.exists():
            parser.error("strategy manifest missing; supply --configurations or --current-presets")
        configurations = tuple(
            StrategyConfiguration.model_validate(item)
            for item in json.loads(config_path.read_text(encoding="utf-8-sig"))
        )
        config_source = str(config_path)
    counts: Counter[str] = Counter()
    digest = hashlib.sha256()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as stream:
        for decision in replay_decisions(read_events(source), configurations):
            line = json.dumps(decision, sort_keys=True, separators=(",", ":")) + "\n"
            stream.write(line)
            digest.update(line.encode())
            counts[f"{decision['strategy_key']}:{decision['action']}"] += 1
    print(
        json.dumps(
            {
                "mode": "decision_replay",
                "input": str(source),
                "configurations": config_source,
                "decisions": dict(counts),
                "output_sha256": digest.hexdigest(),
                "execution_simulated": False,
                "pnl": None,
                "limitations": ["recorded risk only", "no Ollama replay", "no fill/latency replay"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
