"""Persistent conservative rolling limits for operational gRPC payload bytes.

The discovery instance lock owns this ledger. Credit is reserved durably in 64 KiB
chunks before use; unused credit is deliberately not refunded after a restart.
Minute buckets retain an extra boundary minute, so a clock boundary cannot double
the allowance. Provider wire framing/billing is separate from protobuf bytes.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from time import time


class RollingStreamBudget:
    def __init__(self, path: Path, hourly_bytes: int, *, clock: Callable[[], float] = time) -> None:
        if not 2_100_000 <= hourly_bytes <= 128_000_000:
            raise ValueError("invalid operational stream allowance")
        self.path = path
        self.hourly_bytes = hourly_bytes
        self.daily_bytes = hourly_bytes * 24
        self.clock = clock
        self.credit = 0
        self.credit_minute = -1
        self.buckets: dict[int, int] = {}
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            self.buckets = {int(k): int(v) for k, v in raw["minute_reservations"].items()}
            if any(k < 0 or v < 0 for k, v in self.buckets.items()):
                raise ValueError("invalid stream budget ledger")

    def usage(self) -> tuple[int, int]:
        minute = int(self.clock() // 60)
        self.buckets = {k: v for k, v in self.buckets.items() if k >= minute - 1440}
        if self.credit_minute != minute:
            self.credit = 0
            self.credit_minute = minute
        return sum(v for k, v in self.buckets.items() if k >= minute - 60), sum(
            self.buckets.values()
        )

    def can_receive(self) -> bool:
        hourly, daily = self.usage()
        # Reserve room for the adapter's maximum 2 MB protobuf frame plus
        # rounding before requesting another update; don't overshoot at the cap.
        return min(self.hourly_bytes - hourly, self.daily_bytes - daily) >= 2_065_536

    def charge(self, size: int) -> None:
        hourly, daily = self.usage()
        if size <= self.credit:
            self.credit -= size
            return
        reserve = ((size - self.credit + 65_535) // 65_536) * 65_536
        if reserve > min(self.hourly_bytes - hourly, self.daily_bytes - daily):
            raise ValueError("stream budget exhausted")
        minute = self.credit_minute
        self.buckets[minute] = self.buckets.get(minute, 0) + reserve
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump({"minute_reservations": self.buckets}, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.path)
        self.credit += reserve - size

    def retry_after_seconds(self) -> float:
        return max(1.0, 60 - self.clock() % 60)
