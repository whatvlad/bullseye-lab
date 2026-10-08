from __future__ import annotations

from datetime import UTC, datetime
from time import monotonic_ns
from typing import Protocol


def utc_now() -> datetime:
    """Return an aware UTC wall-clock timestamp."""
    return datetime.now(UTC)


class Clock(Protocol):
    """Injectable wall and monotonic clocks for deterministic research code."""

    def now(self) -> datetime: ...

    def monotonic_ns(self) -> int: ...


class SystemClock:
    def now(self) -> datetime:
        return utc_now()

    def monotonic_ns(self) -> int:
        return monotonic_ns()
