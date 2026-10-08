"""Stable mint-level control sampling, independent of strategy score."""

from hashlib import sha256


def sampled_mint(mint: str, percent: int) -> bool:
    return int.from_bytes(sha256(mint.encode()).digest()[:8], "big") % 100 < percent
