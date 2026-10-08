"""Provider-neutral prospective evidence. Connectivity is not coverage proof."""

from __future__ import annotations

import base64
import json
from collections import Counter, OrderedDict
from collections.abc import AsyncIterator
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

from solders.transaction import VersionedTransaction

from memebot.providers.solana.canonical import curve_address
from memebot.providers.solana.pump import extract_anchor_events
from memebot.providers.solana.pump_idl import NATIVE_SOL_MINT, WRAPPED_SOL_MINT, PumpTrade


class CoverageState(StrEnum):
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    GAP_DETECTED = "GAP_DETECTED"
    RECONNECTING = "RECONNECTING"
    RESUMED_WITH_GAP = "RESUMED_WITH_GAP"
    COMPLETE_FOR_WINDOW = "COMPLETE_FOR_WINDOW"


@dataclass(frozen=True)
class TransactionEvidence:
    signature: str
    slot: int
    index: int | None
    transaction: dict[str, Any]
    received_at: datetime
    source: str
    commitment: str
    mint: str
    curve: str

    @property
    def account_keys(self) -> list[str]:
        meta = self.transaction["meta"]
        loaded = meta.get("loadedAddresses", {})
        return (
            list(self.transaction["transaction"]["message"]["accountKeys"])
            + list(loaded.get("writable", []))
            + list(loaded.get("readonly", []))
        )


@dataclass(frozen=True)
class AccountEvidence:
    address: str
    slot: int
    account: dict[str, Any]
    received_at: datetime
    source: str
    commitment: str
    signature: str | None = None
    write_version: int | None = None


class TransactionEvidenceStream(Protocol):
    def transactions(self) -> AsyncIterator[TransactionEvidence | AccountEvidence]: ...


def normalize_transaction(
    transaction: dict[str, Any],
    *,
    slot: int,
    signature: str,
    index: int | None,
    source: str,
    commitment: str,
    received_at: datetime,
) -> TransactionEvidence | None:
    """Require raw instructions and full execution metadata, never parsed summaries."""
    tx = deepcopy(transaction)
    if isinstance(tx.get("transaction"), list):
        encoded, encoding = tx["transaction"]
        if encoding != "base64":
            return None
        raw = VersionedTransaction.from_bytes(base64.b64decode(encoded, validate=True))
        raw.verify_and_hash_message()
        # solders uses snake_case internally; construct the canonical RPC shape.
        message = raw.message
        tx["transaction"] = {
            "signatures": [str(s) for s in raw.signatures],
            "message": {
                "accountKeys": [str(k) for k in message.account_keys],
                "instructions": [
                    {
                        "programIdIndex": i.program_id_index,
                        "accounts": list(i.accounts),
                        "data": _base58(bytes(i.data)),
                    }
                    for i in message.instructions
                ],
            },
        }
    meta = tx.get("meta")
    if not isinstance(meta, dict) or "err" not in meta or meta.get("err") is not None:
        return None
    required = (
        "innerInstructions",
        "preBalances",
        "postBalances",
        "preTokenBalances",
        "postTokenBalances",
        "logMessages",
        "fee",
    )
    if any(meta.get(key) is None for key in required):
        return None
    native = tx.get("transaction", {})
    if not isinstance(native, dict) or signature not in native.get("signatures", []):
        return None
    message = native.get("message", {})
    keys = message.get("accountKeys")
    if not isinstance(keys, list) or not all(isinstance(k, str) for k in keys):
        return None
    if not isinstance(message.get("instructions"), list):
        return None
    full_keys = (
        keys
        + meta.get("loadedAddresses", {}).get("writable", [])
        + meta.get("loadedAddresses", {}).get("readonly", [])
    )
    if len(meta["preBalances"]) != len(full_keys) or len(meta["postBalances"]) != len(full_keys):
        return None
    trades = [e for _, e in extract_anchor_events(meta["logMessages"]) if isinstance(e, PumpTrade)]
    if len(trades) != 1:
        return None
    event = trades[0]
    if event.is_mayhem_mode is not False or event.quote_mint not in {
        NATIVE_SOL_MINT,
        WRAPPED_SOL_MINT,
    }:
        return None
    tx["slot"] = slot
    return TransactionEvidence(
        signature,
        slot,
        index,
        tx,
        received_at,
        source,
        commitment,
        event.mint,
        curve_address(event.mint),
    )


def _base58(value: bytes) -> str:
    from memebot.providers.solana.encoding import encode_base58

    return encode_base58(value)


class EvidenceBuffer:
    """TTL/count/byte bounded storage; account cache never substitutes an atomic bank.

    No production adapter currently certifies closed windows. Future adapters must
    reconcile delivered transaction/account sets against provider end-of-slot
    barriers before passing a window certificate. A slot heartbeat cannot do this.
    """

    def __init__(
        self,
        *,
        seconds: float = 120,
        max_events: int = 2048,
        per_market: int = 64,
        max_bytes: int = 32_000_000,
    ) -> None:
        if min(seconds, max_events, per_market, max_bytes) <= 0:
            raise ValueError("invalid evidence retention")
        self.seconds, self.max_events = seconds, max_events
        self.per_market, self.max_bytes = per_market, max_bytes
        self.items: OrderedDict[str, TransactionEvidence] = OrderedDict()
        self.accounts: OrderedDict[str, AccountEvidence] = OrderedDict()
        self.account_sizes: dict[str, int] = {}
        self.account_bytes = 0
        self.sizes: dict[str, int] = {}
        self.total_bytes = 0
        self.state = CoverageState.DEGRADED
        self.epoch = 0
        self.gaps: list[dict[str, Any]] = []
        self.metrics: Counter[str] = Counter()
        self.max_order: tuple[int, int] | None = None
        self.last_heartbeat_slot: int | None = None
        self.gap_serial = 0
        self.last_gap_at: datetime | None = None
        self.excluded: set[str] = set()
        self.evictions: list[dict[str, Any]] = []

    def gap(self, reason: str) -> None:
        self.gap_serial += 1
        self.last_gap_at = datetime.now(UTC)
        self.state = CoverageState.GAP_DETECTED
        self.gaps.append(
            {
                "at": self.last_gap_at.isoformat(),
                "reason": reason,
                "epoch": self.epoch,
                "slot": self.last_heartbeat_slot,
            }
        )
        self.gaps = self.gaps[-64:]
        self.metrics[reason] += 1

    def connect(self) -> None:
        self.epoch += 1
        self.state = CoverageState.CONNECTED if self.epoch == 1 else CoverageState.RESUMED_WITH_GAP
        if self.epoch > 1:
            self.gap("SUBSCRIPTION_RESTART")
            self.state = CoverageState.RESUMED_WITH_GAP

    def disconnect(self) -> None:
        self.gap("DISCONNECT")
        self.state = CoverageState.RECONNECTING

    def heartbeat(self, slot: int) -> None:
        # Only an unfiltered slot sequence can reveal slot delivery gaps. Pump
        # filtered transaction slots may legitimately skip many slots.
        previous = self.last_heartbeat_slot
        if previous is not None and slot > previous + 1:
            self.gap("SLOT_GAP_UNPROVEN")
        if previous is not None and slot < previous:
            self.gap("OUT_OF_ORDER_SLOT")
        self.last_heartbeat_slot = max(slot, previous or slot)

    def exclude(self, mint: str) -> None:
        self.excluded.add(mint)
        # Bound exclusion tombstones as well; no full-chain market archive.
        if len(self.excluded) > self.max_events:
            self.excluded.pop()
        for sig in [s for s, e in self.items.items() if e.mint == mint]:
            self._remove(sig)

    def _remove(
        self, signature: str, reason: str = "REMOVED", *, at: datetime | None = None
    ) -> None:
        removed = self.items.pop(signature)
        self.evictions.append(
            {
                "mint": removed.mint,
                "signature": signature,
                "received_at": removed.received_at.isoformat(),
                "evicted_at": (at or datetime.now(UTC)).isoformat(),
                "slot": removed.slot,
                "bytes": self.sizes[signature],
                "reason": reason,
            }
        )
        self.evictions = self.evictions[-8192:]
        self.total_bytes -= self.sizes.pop(signature)

    def expire(self, now: datetime) -> None:
        for sig, evidence in list(self.items.items()):
            if (now - evidence.received_at).total_seconds() > self.seconds:
                self._remove(sig, "EXPIRED", at=now)
                self.metrics["EXPIRED"] += 1
        for address, account in list(self.accounts.items()):
            if (now - account.received_at).total_seconds() > self.seconds:
                self.accounts.pop(address)
                self.account_bytes -= self.account_sizes.pop(address)
                self.metrics["ACCOUNT_EXPIRED"] += 1

    def add(self, evidence: TransactionEvidence) -> None:
        self.expire(evidence.received_at)
        if evidence.mint in self.excluded or evidence.commitment not in {"confirmed", "finalized"}:
            self.metrics["EXCLUDED"] += 1
            return
        previous = self.items.get(evidence.signature)
        if previous:
            self.metrics["DUPLICATE"] += 1
            if previous.transaction != evidence.transaction or previous.slot != evidence.slot:
                self.gap("CONFLICTING_DUPLICATE")
            return
        if evidence.index is not None:
            order = (evidence.slot, evidence.index)
            if self.max_order is not None and order < self.max_order:
                self.gap("OUT_OF_ORDER_TRANSACTION")
            self.max_order = max(order, self.max_order or order)
        size = len(json.dumps(evidence.transaction).encode())
        if size > self.max_bytes:
            self.gap("BUFFER_OVERFLOW")
            return
        self.items[evidence.signature] = deepcopy(evidence)
        self.sizes[evidence.signature] = size
        self.total_bytes += size
        owned = [sig for sig, e in self.items.items() if e.mint == evidence.mint]
        while len(owned) > self.per_market:
            self._remove(owned.pop(0), "MARKET_BUFFER_OVERFLOW", at=evidence.received_at)
            self.gap("MARKET_BUFFER_OVERFLOW")
        while len(self.items) > self.max_events or self.total_bytes > self.max_bytes:
            self._remove(next(iter(self.items)), "BUFFER_OVERFLOW", at=evidence.received_at)
            self.gap("BUFFER_OVERFLOW")
        self.metrics["TRANSACTIONS_STORED"] += 1

    def add_account(self, evidence: AccountEvidence) -> None:
        self.expire(evidence.received_at)
        if evidence.commitment not in {"confirmed", "finalized"}:
            return
        # Only accounts referenced by retained standard transactions, no broad
        # token-owner subscription or unrelated account archive.
        if not any(evidence.address in e.account_keys for e in self.items.values()):
            self.metrics["ACCOUNT_OUT_OF_SCOPE"] += 1
            return
        size = len(json.dumps(evidence.account).encode())
        if size > min(64_000, self.max_bytes):
            self.gap("ACCOUNT_OVERSIZE")
            return
        previous = self.accounts.get(evidence.address)
        if previous is not None:
            if evidence.slot < previous.slot or (
                evidence.slot == previous.slot
                and evidence.write_version is not None
                and previous.write_version is not None
                and evidence.write_version < previous.write_version
            ):
                self.gap("OUT_OF_ORDER_ACCOUNT")
                return
            self.account_bytes -= self.account_sizes.pop(evidence.address)
        self.accounts[evidence.address] = deepcopy(evidence)
        self.account_sizes[evidence.address] = size
        self.account_bytes += size
        self.accounts.move_to_end(evidence.address)
        while len(self.accounts) > self.max_events or self.account_bytes > self.max_bytes:
            address, _ = self.accounts.popitem(last=False)
            self.account_bytes -= self.account_sizes.pop(address)
            self.gap("ACCOUNT_BUFFER_OVERFLOW")
        self.metrics["ACCOUNTS_STORED"] += 1

    def get(self, signature: str, now: datetime) -> TransactionEvidence | None:
        self.expire(now)
        return deepcopy(self.items.get(signature))

    def crosses_gap(self, since: datetime) -> bool:
        return self.last_gap_at is not None and self.last_gap_at >= since

    def report(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "epoch": self.epoch,
            "gaps": self.gaps,
            "gap_serial": self.gap_serial,
            "metrics": dict(self.metrics),
            "retained_transactions": len(self.items),
            "retained_accounts": len(self.accounts),
            "retained_transaction_bytes": self.total_bytes,
            "retained_account_bytes": self.account_bytes,
            "complete_for_window": False,
            "history_fences_removable": False,
            "evictions": self.evictions,
        }
