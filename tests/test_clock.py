from datetime import UTC

from memebot.core.clock import SystemClock, utc_now


def test_utc_now_is_aware_and_utc() -> None:
    timestamp = utc_now()

    assert timestamp.tzinfo is UTC
    assert timestamp.utcoffset() is not None


def test_system_clock_exposes_monotonic_measurement() -> None:
    clock = SystemClock()

    first = clock.monotonic_ns()
    second = clock.monotonic_ns()

    assert second >= first
