from __future__ import annotations

import html
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import Any

TABS = ("newPairs", "finalStretch", "migrated")
SUPPORTED_PROTOCOLS = frozenset({"pump", "pumpAmm"})
RANGES = frozenset(
    {
        "age",
        "userCount",
        "axiomCommunityMembers",
        "imgReuseCount",
        "top10Holders",
        "devHolding",
        "snipers",
        "insiders",
        "bundle",
        "holders",
        "botUsers",
        "bondingCurve",
        "liquidity",
        "volume",
        "marketCap",
        "fees",
        "txns",
        "numBuys",
        "numSells",
        "numMigrations",
        "numDevPairs",
        "devMigrationsPercent",
        "tweetAgeMins",
        "twitter",
        "twitterFollowers",
        "twitterFollowing",
    }
)
FLAGS = frozenset(
    {"dexPaid", "twitterExists", "website", "telegram", "tiktok", "atLeastOneSocial", "isStreaming"}
)
DISPLAY_FLAGS = frozenset({"showPumpOffchain", "showHolderRewards", "showBoosted"})


def number(value: object) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except InvalidOperation:
        return None


def validate_preset(preset: dict[str, Any]) -> dict[str, Any]:
    if preset.get("tab") not in TABS or not isinstance(preset.get("filters"), dict):
        raise ValueError("Expected Axiom export with tab and filters")
    filters = preset["filters"]
    known = (
        RANGES
        | FLAGS
        | DISPLAY_FLAGS
        | {
            "protocols",
            "showQuoteTokens",
            "searchKeywords",
            "excludeKeywords",
            "twitterHandles",
            "devMigrationsMinLaunches",
        }
    )
    if set(filters) - known:
        raise ValueError(f"Unsupported filter keys: {sorted(set(filters) - known)}")
    for key in RANGES & filters.keys():
        bounds = filters[key]
        if not isinstance(bounds, dict) or set(bounds) - {"min", "max", "unit"}:
            raise ValueError(f"Invalid range: {key}")
        if "unit" in bounds and bounds["unit"] != "minutes":
            raise ValueError(f"Unsupported time unit: {key}")
        for bound in ("min", "max"):
            raw = bounds.get(bound)
            if raw is not None and (number(raw) is None or Decimal(str(raw)) < 0):
                raise ValueError(f"Invalid {key}.{bound}")
        low, high = number(bounds.get("min")), number(bounds.get("max"))
        if low is not None and high is not None and low > high:
            raise ValueError(f"Inverted range: {key}")
    for key in (FLAGS | DISPLAY_FLAGS) & filters.keys():
        if not isinstance(filters[key], bool):
            raise ValueError(f"Expected boolean: {key}")
    for key in ("protocols", "showQuoteTokens"):
        if key in filters and (
            not isinstance(filters[key], dict)
            or any(not isinstance(v, bool) for v in filters[key].values())
        ):
            raise ValueError(f"Expected boolean map: {key}")
    for key in ("searchKeywords", "excludeKeywords", "twitterHandles"):
        if key in filters and (
            not isinstance(filters[key], list) or any(not isinstance(v, str) for v in filters[key])
        ):
            raise ValueError(f"Expected string list: {key}")
    launches = filters.get("devMigrationsMinLaunches")
    if launches is not None and (number(launches) is None or Decimal(str(launches)) < 0):
        raise ValueError("Invalid devMigrationsMinLaunches")
    return preset


def decode_export(text: str) -> dict[str, Any]:
    value = json.loads(html.unescape(text))
    if not isinstance(value, dict):
        raise ValueError("Expected an object")
    return validate_preset(value)


def load_presets(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or set(data) != set(TABS):
        raise ValueError("Pulse configuration must contain all three tabs")
    for tab in TABS:
        validate_preset(data[tab])
        if data[tab]["tab"] != tab:
            raise ValueError("Pulse tab mismatch")
    return data


def presets_digest(path: Path) -> str:
    return sha256(json.dumps(load_presets(path), sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class FilterResult:
    matched: bool
    reasons: tuple[str, ...]


def evaluate(preset: dict[str, Any], row: dict[str, Any]) -> FilterResult:
    filters = preset["filters"]
    reasons = []
    if row.get("tab") != preset["tab"]:
        reasons.append("different_stage")
    protocols = filters.get("protocols")
    if protocols is not None and not protocols.get(row.get("protocol"), False):
        reasons.append("protocol_excluded")
    quotes = filters.get("showQuoteTokens")
    if quotes is not None and not quotes.get(row.get("quote"), False):
        reasons.append("quote_excluded")
    text = f"{row.get('symbol') or ''} {row.get('name') or ''}".casefold()
    search = filters.get("searchKeywords", [])
    if search and not any(word.casefold() in text for word in search):
        reasons.append("keyword_not_found")
    if any(word.casefold() in text for word in filters.get("excludeKeywords", [])):
        reasons.append("excluded_keyword")
    for key in RANGES:
        bounds = filters.get(key) or {}
        low, high = number(bounds.get("min")), number(bounds.get("max"))
        if low is None and high is None:
            continue
        value = number(row.get(key))
        if value is None:
            reasons.append(f"unknown:{key}")
        elif low is not None and value < low:
            reasons.append(f"below_min:{key}")
        elif high is not None and value > high:
            reasons.append(f"above_max:{key}")
    for key in FLAGS:
        if filters.get(key) and row.get(key) is not True:
            reasons.append(f"unknown_or_false:{key}")
    for key in DISPLAY_FLAGS:
        if filters.get(key) is False:
            if row.get(key) is None:
                reasons.append(f"unknown:{key}")
            elif row[key]:
                reasons.append(f"excluded:{key}")
    if filters.get("twitterHandles"):
        reasons.append("unsupported:twitterHandles")
    if filters.get("devMigrationsMinLaunches") is not None:
        count = number(row.get("numDevPairs"))
        if count is None or count < Decimal(str(filters["devMigrationsMinLaunches"])):
            reasons.append("developer_history_insufficient")
    if row.get("stale", True):
        reasons.append("stale_market_data")
    return FilterResult(not reasons, tuple(sorted(reasons)))
