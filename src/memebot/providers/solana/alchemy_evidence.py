"""Filtered executed Geyser transport. Provider connectivity is not window proof."""

from __future__ import annotations

import asyncio
import base64
import struct
from collections import Counter
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from typing import Any

from memebot.providers.solana.encoding import encode_base58
from memebot.providers.solana.evidence_stream import (
    AccountEvidence,
    TransactionEvidence,
    normalize_transaction,
)
from memebot.providers.solana.pump_idl import PUMP_PROGRAM_ID
from memebot.providers.solana.stream_budget import RollingStreamBudget


def verified_v1_config(tx: Any) -> dict[str, int]:
    """Reconstitute SIMD-0385 signed bytes; never relabel V1 as V0."""
    from solders.pubkey import Pubkey
    from solders.signature import Signature

    message = tx.message
    header = message.header
    keys = message.account_keys
    instructions = message.instructions
    if (
        not message.versioned
        or message.address_table_lookups
        or not 1 <= header.num_required_signatures == len(tx.signatures) <= 12
        or not 1 <= len(keys) <= 64
        or len(instructions) > 64
        or len(message.recent_blockhash) != 32
        or any(len(k) != 32 for k in keys)
        or len(set(keys)) != len(keys)
        or header.num_readonly_signed_accounts >= header.num_required_signatures
        or header.num_required_signatures + header.num_readonly_unsigned_accounts > len(keys)
    ):
        raise ValueError("malformed_v1_message")
    mask, values = 0, b""
    config = {}
    for name, bits, fmt in (
        ("priority_fee", 3, "<Q"),
        ("compute_unit_limit", 4, "<I"),
        ("loaded_accounts_data_size_limit", 8, "<I"),
        ("heap_size", 16, "<I"),
    ):
        if message.config.HasField(name):
            value = int(getattr(message.config, name))
            config[name] = value
            mask |= bits
            values += struct.pack(fmt, value)
    payload = bytes(
        [
            129,
            header.num_required_signatures,
            header.num_readonly_signed_accounts,
            header.num_readonly_unsigned_accounts,
        ]
    )
    payload += struct.pack("<I", mask) + message.recent_blockhash
    payload += bytes([len(instructions), len(keys)]) + b"".join(keys) + values
    for item in instructions:
        if (
            item.program_id_index >= len(keys)
            or any(i >= len(keys) for i in item.accounts)
            or len(item.accounts) > 255
            or len(item.data) > 65535
        ):
            raise ValueError("malformed_v1_instruction")
        payload += struct.pack("<BBH", item.program_id_index, len(item.accounts), len(item.data))
    payload += b"".join(i.accounts + i.data for i in instructions)
    if len(payload) + 64 * len(tx.signatures) > 4096:
        raise ValueError("malformed_v1_size")
    if not all(
        Signature.from_bytes(signature).verify(Pubkey.from_bytes(keys[index]), payload)
        for index, signature in enumerate(tx.signatures)
    ):
        raise ValueError("invalid_v1_signature")
    return config


def rpc_packet(update: Any) -> dict[str, Any]:
    """Lossless execution fields in the existing RPC proof engine's shape."""
    info = update.transaction.transaction
    tx, meta = info.transaction, info.meta
    if not info.HasField("transaction") or not info.HasField("meta"):
        raise ValueError("missing_executed_transaction_or_meta")
    config = verified_v1_config(tx) if tx.message.HasField("config") else None

    def instruction(item: Any) -> dict[str, Any]:
        value = {
            "programIdIndex": item.program_id_index,
            "accounts": list(item.accounts),
            "data": encode_base58(item.data),
        }
        if "stack_height" in item.DESCRIPTOR.fields_by_name and item.HasField("stack_height"):
            value["stackHeight"] = item.stack_height
        return value

    def balances(items: Any) -> list[dict[str, Any]]:
        return [
            {
                "accountIndex": item.account_index,
                "mint": item.mint,
                "owner": item.owner,
                "programId": item.program_id,
                "uiTokenAmount": {
                    "amount": item.ui_token_amount.amount,
                    "decimals": item.ui_token_amount.decimals,
                    "uiAmount": item.ui_token_amount.ui_amount,
                    "uiAmountString": item.ui_token_amount.ui_amount_string,
                },
            }
            for item in items
        ]

    message = tx.message
    return {
        "slot": update.transaction.slot,
        "version": 1 if config is not None else (0 if message.versioned else "legacy"),
        "transaction": {
            "signatures": [encode_base58(s) for s in tx.signatures],
            "message": {
                "transactionConfig": config,
                "header": {
                    "numRequiredSignatures": message.header.num_required_signatures,
                    "numReadonlySignedAccounts": message.header.num_readonly_signed_accounts,
                    "numReadonlyUnsignedAccounts": message.header.num_readonly_unsigned_accounts,
                },
                "accountKeys": [encode_base58(k) for k in message.account_keys],
                "recentBlockhash": encode_base58(message.recent_blockhash),
                "instructions": [instruction(i) for i in message.instructions],
                "addressTableLookups": [
                    {
                        "accountKey": encode_base58(i.account_key),
                        "writableIndexes": list(i.writable_indexes),
                        "readonlyIndexes": list(i.readonly_indexes),
                    }
                    for i in message.address_table_lookups
                ],
            },
        },
        "meta": {
            "err": {"raw": base64.b64encode(meta.err.err).decode()}
            if meta.HasField("err")
            else None,
            "fee": meta.fee,
            "preBalances": list(meta.pre_balances),
            "postBalances": list(meta.post_balances),
            "innerInstructions": None
            if meta.inner_instructions_none
            else [
                {"index": i.index, "instructions": [instruction(j) for j in i.instructions]}
                for i in meta.inner_instructions
            ],
            "logMessages": None if meta.log_messages_none else list(meta.log_messages),
            "preTokenBalances": balances(meta.pre_token_balances),
            "postTokenBalances": balances(meta.post_token_balances),
            "loadedAddresses": {
                "writable": [encode_base58(k) for k in meta.loaded_writable_addresses],
                "readonly": [encode_base58(k) for k in meta.loaded_readonly_addresses],
            },
        },
    }


class FullStreamBudgetExceeded(ValueError):
    """The explicit paid streaming allowance has been consumed."""


class AlchemyTransactionEvidenceStream:
    def __init__(
        self,
        token: str,
        *,
        max_bytes: int = 32_000_000,
        on_packet: Callable[[dict[str, Any]], None] | None = None,
        on_control: Callable[[dict[str, Any]], None] | None = None,
        budget: RollingStreamBudget | None = None,
    ) -> None:
        self._token = token
        self.max_bytes = max_bytes
        self.budget = budget
        self.on_packet = on_packet
        self.on_control = on_control
        self.updates: asyncio.Queue[tuple[Any, int]] = asyncio.Queue(maxsize=16)
        self.metrics: Counter[str] = Counter()
        self.accounts: tuple[str, ...] = ()
        self.revision = 0
        self.acknowledged_revision = 0
        self.first_slot: int | None = None
        self.last_slot: int | None = None
        self.connected = False
        self.failure: dict[str, str] | None = None
        self.filter_history: list[dict[str, Any]] = []

    def update_filter(
        self, accounts: tuple[str, ...], config_accounts: tuple[str, ...] = ()
    ) -> None:
        from memebot.providers.solana._yellowstone_generated import geyser_pb2 as proto

        if PUMP_PROGRAM_ID in accounts or len(accounts) > 128:
            raise ValueError("explicit_narrow_market_filter_required")
        if accounts == self.accounts:
            return
        self.accounts = accounts
        self.revision += 1
        request = proto.SubscribeRequest(commitment=proto.CONFIRMED)
        # Empty tx map disables transactions; never send an empty global filter.
        if accounts:
            request.transactions[f"watch_{self.revision}"].CopyFrom(
                proto.SubscribeRequestFilterTransactions(
                    vote=False,
                    failed=False,
                    account_include=accounts,
                    account_required=[PUMP_PROGRAM_ID],
                )
            )
            request.accounts["watched"].account.extend(sorted(set(accounts + config_accounts)))
        request.slots["slots"].filter_by_commitment = True
        self.updates.put_nowait((request, self.revision))
        self.filter_history.append(
            {
                "revision": self.revision,
                "accounts": list(accounts),
                "at": datetime.now(UTC).isoformat(),
            }
        )

    async def transactions(self) -> AsyncIterator[TransactionEvidence | AccountEvidence]:
        import grpc

        from memebot.providers.solana._yellowstone_generated import geyser_pb2 as proto

        async with grpc.aio.secure_channel(
            "solana-mainnet.streaming.alchemy.com:443",
            grpc.ssl_channel_credentials(),
            options=(("grpc.max_receive_message_length", 2_000_000),),
        ) as channel:
            reply = await channel.unary_unary(
                "/geyser.Geyser/Ping",
                request_serializer=proto.PingRequest.SerializeToString,
                response_deserializer=proto.PongResponse.FromString,
            )(proto.PingRequest(count=1), metadata=(("x-token", self._token),), timeout=8)
            if reply.count != 1:
                raise ValueError("ping_mismatch")
            self.metrics["ping_success"] += 1

            async def requests() -> AsyncIterator[Any]:
                initial = proto.SubscribeRequest(commitment=proto.CONFIRMED)
                initial.slots["slots"].filter_by_commitment = True
                yield initial
                yield proto.SubscribeRequest(ping=proto.SubscribeRequestPing(id=0))
                while True:
                    try:
                        request, revision = await asyncio.wait_for(self.updates.get(), 10)
                        yield request
                        yield proto.SubscribeRequest(ping=proto.SubscribeRequestPing(id=revision))
                    except TimeoutError:
                        yield proto.SubscribeRequest(
                            ping=proto.SubscribeRequestPing(id=self.revision)
                        )

            call = channel.stream_stream(
                "/geyser.Geyser/Subscribe",
                request_serializer=proto.SubscribeRequest.SerializeToString,
                response_deserializer=proto.SubscribeUpdate.FromString,
            )(requests(), metadata=(("x-token", self._token),))
            self.connected = True
            self.metrics["connections"] += 1
            try:
                iterator = call.__aiter__()
                while True:
                    if self.budget is not None and not self.budget.can_receive():
                        raise FullStreamBudgetExceeded("rolling_stream_data_cap")
                    try:
                        update = await anext(iterator)
                    except StopAsyncIteration:
                        break
                    kind = update.WhichOneof("update_oneof")
                    if self.budget is not None:
                        self.budget.charge(update.ByteSize())
                    self.metrics[f"{kind}_bytes"] += update.ByteSize()
                    self.metrics[f"{kind}_messages"] += 1
                    if (
                        self.budget is None
                        and sum(v for k, v in self.metrics.items() if k.endswith("_bytes"))
                        > self.max_bytes
                    ):
                        self.metrics["buffer_overflow"] += 1
                        raise FullStreamBudgetExceeded("full_stream_data_cap")
                    if kind == "pong":
                        self.acknowledged_revision = max(self.acknowledged_revision, update.pong.id)
                        self.metrics["subscription_pongs"] += 1
                        if self.on_control:
                            self.on_control(
                                {
                                    "kind": "ack",
                                    "revision": update.pong.id,
                                    "at": datetime.now(UTC).isoformat(),
                                }
                            )
                    elif kind == "slot":
                        slot = update.slot.slot
                        self.first_slot = slot if self.first_slot is None else self.first_slot
                        self.last_slot = max(slot, self.last_slot or slot)
                        self.metrics["slot_updates"] += 1
                        if self.on_control:
                            self.on_control(
                                {"kind": "slot", "slot": slot, "at": datetime.now(UTC).isoformat()}
                            )
                    elif kind == "transaction":
                        self.metrics["full_packets"] += 1
                        received = datetime.now(UTC)
                        info = update.transaction.transaction
                        # Preserve the complete provider packet even if the
                        # current execution decoder rejects its message format.
                        if self.on_packet:
                            self.on_packet(
                                {
                                    "record_kind": "provider_protobuf",
                                    "signature": encode_base58(info.signature),
                                    "slot": update.transaction.slot,
                                    "transaction_index": info.index,
                                    "received_timestamp": received.isoformat(),
                                    "raw_protobuf_base64": base64.b64encode(
                                        update.SerializeToString()
                                    ).decode(),
                                }
                            )
                        try:
                            packet = rpc_packet(update)
                            info = update.transaction.transaction
                            signature = encode_base58(info.signature)
                            if self.on_packet:
                                self.on_packet(
                                    {
                                        "record_kind": "normalized_rpc",
                                        "signature": signature,
                                        "slot": update.transaction.slot,
                                        "transaction_index": info.index,
                                        "received_timestamp": received.isoformat(),
                                        "provider_created_at": update.created_at.ToJsonString(),
                                        "packet": packet,
                                    }
                                )
                            evidence = normalize_transaction(
                                packet,
                                slot=update.transaction.slot,
                                signature=signature,
                                index=info.index,
                                source="alchemy_yellowstone",
                                commitment="confirmed",
                                received_at=received,
                            )
                        except (ValueError, KeyError, TypeError) as error:
                            self.metrics["malformed_packets"] += 1
                            # Only fixed decoder labels, never arbitrary external
                            # exception messages or credential-bearing URLs.
                            label = (
                                str(error)
                                if str(error)
                                in {
                                    "unsupported_v1_message",
                                    "missing_executed_transaction_or_meta",
                                    "malformed_v1_message",
                                    "malformed_v1_instruction",
                                    "malformed_v1_size",
                                    "invalid_v1_signature",
                                }
                                else type(error).__name__
                            )
                            self.metrics[f"decoder_rejection_{label}"] += 1
                            continue
                        if evidence is not None:
                            self.metrics["usable_packets"] += 1
                            yield evidence
                        else:
                            self.metrics["scope_or_completeness_rejected"] += 1
                    elif kind == "account":
                        item = update.account.account
                        yield AccountEvidence(
                            encode_base58(item.pubkey),
                            update.account.slot,
                            {
                                "owner": encode_base58(item.owner),
                                "lamports": item.lamports,
                                "executable": item.executable,
                                "rentEpoch": item.rent_epoch,
                                "data": [base64.b64encode(item.data).decode(), "base64"],
                            },
                            datetime.now(UTC),
                            "alchemy_yellowstone",
                            "confirmed",
                            encode_base58(item.txn_signature)
                            if item.HasField("txn_signature")
                            else None,
                            item.write_version,
                        )
            except grpc.aio.AioRpcError as error:
                self.failure = {
                    "status": error.code().name,
                    "details": error.details().replace(self._token, "[REDACTED]"),
                }
                raise ValueError("stream_provider_error") from None
            finally:
                call.cancel()
                self.connected = False
                self.metrics["disconnects"] += 1

    def report(self) -> dict[str, Any]:
        return {
            "metrics": dict(self.metrics),
            "first_observed_slot": self.first_slot,
            "last_observed_slot": self.last_slot,
            "filter_history": self.filter_history,
            "acknowledged_revision": self.acknowledged_revision,
            "failure": self.failure,
            "reconnects": 0,
            "replay_backfill": 0,
            "complete_for_window": False,
            "acknowledgment": "request-stream pong; no per-market closed-window certificate",
        }
