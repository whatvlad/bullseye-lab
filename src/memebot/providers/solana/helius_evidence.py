"""Helius JSON/base64 adapter; provider envelope stays outside proof logic."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import websockets

from memebot.providers.solana.evidence_stream import (
    AccountEvidence,
    TransactionEvidence,
    normalize_transaction,
)
from memebot.providers.solana.pump_idl import PUMP_PROGRAM_ID


class HeliusTransactionEvidenceStream:
    def __init__(
        self, endpoint: str, *, max_bytes: int = 32_000_000, watched_accounts: tuple[str, ...] = ()
    ) -> None:
        self.endpoint = endpoint
        self.watched_accounts = watched_accounts
        self.max_bytes = max_bytes
        self.bytes_received = 0
        self.messages = 0
        self.subscription_error_code: int | None = None

    @staticmethod
    def normalize(result: dict[str, Any]) -> TransactionEvidence | None:
        return normalize_transaction(
            result["transaction"],
            slot=result["slot"],
            signature=result["signature"],
            index=result.get("transactionIndex"),
            source="helius_transactionSubscribe",
            commitment="confirmed",
            received_at=datetime.now(UTC),
        )

    async def transactions(self) -> AsyncIterator[TransactionEvidence | AccountEvidence]:
        if not self.watched_accounts or PUMP_PROGRAM_ID in self.watched_accounts:
            raise ValueError("explicit_narrow_market_filter_required")
        async with websockets.connect(
            self.endpoint, open_timeout=8, max_queue=64, max_size=2_000_000
        ) as ws:
            await ws.send(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "transactionSubscribe",
                        "params": [
                            {
                                "accountInclude": list(self.watched_accounts),
                                "accountRequired": [PUMP_PROGRAM_ID],
                                "vote": False,
                                "failed": False,
                            },
                            {
                                "commitment": "confirmed",
                                "encoding": "base64",
                                "transactionDetails": "full",
                                "maxSupportedTransactionVersion": 0,
                            },
                        ],
                    }
                )
            )
            async for raw in ws:
                self.bytes_received += len(raw.encode() if isinstance(raw, str) else raw)
                self.messages += 1
                if self.bytes_received > self.max_bytes:
                    raise ValueError("full_transaction_data_cap")
                message = json.loads(raw)
                if "error" in message:
                    self.subscription_error_code = message["error"].get("code")
                    raise ValueError("full_transaction_subscription_rejected")
                if message.get("method") != "transactionNotification":
                    continue
                evidence = self.normalize(message["params"]["result"])
                if evidence is not None:
                    yield evidence
