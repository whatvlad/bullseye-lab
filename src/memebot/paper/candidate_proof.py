"""Candidate-only read proofs. Never submits orders or promotes the global stream."""

from __future__ import annotations

import asyncio
import base64
import hashlib
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from time import monotonic
from typing import Any, Protocol

from memebot.paper.standard_math import (
    buy_exact_input,
    buy_exact_tokens,
    buy_quote,
    fee,
    select_fees,
    sell_quote,
)
from memebot.providers.solana.bootstrap import decode_config
from memebot.providers.solana.canonical import (
    associated_address,
    config_addresses,
    curve_address,
    pda,
)
from memebot.providers.solana.encoding import decode_base58
from memebot.providers.solana.execution_accounting import execution_accounting
from memebot.providers.solana.idl_schema import decode_record, schema
from memebot.providers.solana.pump import extract_anchor_events
from memebot.providers.solana.pump_idl import (
    NATIVE_SOL_MINT,
    PUMP_PROGRAM_ID,
    TOKEN_2022_PROGRAM_ID,
    TOKEN_PROGRAM_ID,
    WRAPPED_SOL_MINT,
    PumpTrade,
    decode_mint_account,
    decode_token_account,
)
from memebot.providers.solana.rpc import SolanaRpcError
from memebot.providers.solana.trade_alignment import trade_invocations
from memebot.research.pumpfun_sequence import reconstruct_transaction


class FunnelStage(StrEnum):
    STANDARD_DISCOVERED = "STANDARD_DISCOVERED"
    OBSERVATION_ELIGIBLE = "OBSERVATION_ELIGIBLE"
    ARITHMETIC_CONTINUITY_OK = "ARITHMETIC_CONTINUITY_OK"
    SERIOUS_CANDIDATE = "SERIOUS_CANDIDATE"
    CANDIDATE_PROOF_PENDING = "CANDIDATE_PROOF_PENDING"
    EXECUTION_READY = "EXECUTION_READY"
    REJECTED = "REJECTED"


class ReadRpc(Protocol):
    async def _call(self, method: str, params: list[object] | None = None) -> Any: ...


@dataclass(frozen=True)
class ProofPolicy:
    max_requests: int = 12
    max_signatures: int = 4
    timeout_seconds: float = 12
    max_proof_age_ms: int = 2000

    def __post_init__(self) -> None:
        if not (
            0 < self.max_requests <= 64
            and 0 < self.max_signatures <= 16
            and 0 < self.timeout_seconds <= 60
            and 0 < self.max_proof_age_ms <= 60000
        ):
            raise ValueError("invalid bounded proof policy")


@dataclass(frozen=True)
class Candidate:
    mint: str
    anchor: PumpTrade
    anchor_signature: str
    anchor_slot: int
    detected_at: datetime
    arithmetic_status: str
    quality_passed: bool
    buy_budget_raw: int
    sell_quantity_raw: int
    multi_event: bool = False
    complete: bool = False
    migrated: bool = False
    quality_evidence: dict[str, Any] = field(default_factory=dict)
    venue: str = "pump_fun"
    known_divergence: bool = False
    native_event_received_at: datetime | None = None
    event_ordinal: int | None = None


def observational_stage(candidate: Candidate) -> tuple[FunnelStage, str | None]:
    event = candidate.anchor
    if candidate.venue != "pump_fun" or not isinstance(event, PumpTrade):
        return FunnelStage.REJECTED, "OUT_OF_SCOPE_PUMPSWAP_OR_VENUE"
    if event.is_mayhem_mode is not False:
        return FunnelStage.REJECTED, "OUT_OF_SCOPE_MAYHEM_OR_MODE_UNKNOWN"
    if candidate.complete or candidate.migrated:
        return FunnelStage.REJECTED, "MIGRATED_MARKET"
    if candidate.multi_event:
        return FunnelStage.REJECTED, "MULTI_EVENT_AMBIGUOUS"
    if event.quote_mint not in {NATIVE_SOL_MINT, WRAPPED_SOL_MINT}:
        return FunnelStage.REJECTED, "UNSUPPORTED_QUOTE"
    if candidate.known_divergence or candidate.arithmetic_status == "DIVERGED":
        return FunnelStage.REJECTED, "CONTINUITY_DIVERGED"
    if candidate.arithmetic_status != "EXACT":
        return FunnelStage.OBSERVATION_ELIGIBLE, "ARITHMETIC_NOT_EXACT"
    if not candidate.quality_passed:
        return FunnelStage.ARITHMETIC_CONTINUITY_OK, "QUALITY_NOT_SERIOUS"
    return FunnelStage.SERIOUS_CANDIDATE, None


class ProofFailure(ValueError):
    def __init__(self, status: str, reason: str) -> None:
        super().__init__(reason)
        self.status = status


class TrustDimension(StrEnum):
    RESERVE_STATE = "RESERVE_STATE"
    IDENTITY = "IDENTITY"
    CONFIG = "CONFIG"
    CONTINUITY = "CONTINUITY"
    FEE_ROUTE = "FEE_ROUTE"
    LIFECYCLE = "LIFECYCLE"
    MODE = "MODE"
    STREAM_COVERAGE = "STREAM_COVERAGE"


_STANDARD_SUPPLY = 1_000_000_000_000_000
CURRENT_DIMENSIONS = frozenset(
    {
        TrustDimension.RESERVE_STATE,
        TrustDimension.IDENTITY,
        TrustDimension.CONFIG,
        TrustDimension.FEE_ROUTE,
        TrustDimension.LIFECYCLE,
        TrustDimension.MODE,
    }
)


@dataclass
class Proof:
    candidate: Candidate
    status: str = "FAIL_OTHER"
    stage: FunnelStage = FunnelStage.CANDIDATE_PROOF_PENDING
    reason: str | None = None
    candidate_detected_at: datetime | None = None
    proof_started_at: datetime | None = None
    identity_slot: int | None = None
    reserve_slot: int | None = None
    config_slot: int | None = None
    proof_completed_at: datetime | None = None
    decision_at: datetime | None = None
    execution_refresh_at: datetime | None = None
    proof_latency_ms: float | None = None
    decision_age_ms: float | None = None
    slot_span: int | None = None
    costs: dict[str, int] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    trust: dict[str, bool] = field(default_factory=dict)
    incompatible_mutation: bool = False

    def report(self) -> dict[str, Any]:
        return asdict(self)


class CandidateProofService:
    def __init__(self, rpc: ReadRpc, policy: ProofPolicy | None = None) -> None:
        self.rpc = rpc
        self.policy = policy or ProofPolicy()
        self.stable: dict[str, dict[str, Any]] = {}
        self.config_cache: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
        self.receipts: dict[str, Proof] = {}
        self.lineage: dict[str, Proof] = {}
        self.incompatible_markets: set[str] = set()
        self.invalidations: list[dict[str, Any]] = []
        self.lock = asyncio.Lock()
        self.generation = 0
        self.market_generations: Counter[str] = Counter()

    def invalidate(
        self,
        reason: str,
        mint: str | None = None,
        *,
        dimensions: frozenset[TrustDimension] | None = None,
        incompatible: bool = False,
        source: dict[str, Any] | None = None,
    ) -> None:
        lost = dimensions if dimensions is not None else frozenset(TrustDimension)
        record = {
            "reason": reason,
            "mint": mint or "ALL",
            "at": datetime.now(UTC).isoformat(),
            "dimensions": sorted(lost),
            "incompatible": incompatible,
            "source": source,
        }
        self.invalidations.append(record)
        if incompatible:
            self.incompatible_markets.update({mint} if mint else self.lineage)
        for key, receipt in self.lineage.items():
            if mint is None or mint == key:
                receipt.trust.update({d: False for d in lost})
                receipt.incompatible_mutation |= incompatible
                receipt.evidence.setdefault("trust_invalidations", []).append(record)
                receipt.evidence["trust_invalidations"] = receipt.evidence["trust_invalidations"][
                    -32:
                ]
        if mint:
            self.market_generations[mint] += 1
            self.stable.pop(mint, None)
            self.receipts.pop(mint, None)
        else:
            self.generation += 1
            self.stable.clear()
            self.receipts.clear()
            self.config_cache.clear()

    async def _read(self, proof: Proof, method: str, params: list[object], duty: str) -> Any:
        if not getattr(self.rpc, "available", True):
            raise ProofFailure("FAIL_RPC", "provider circuit open; no HTTP request sent")
        if proof.costs.get("total_rpc_requests", 0) >= self.policy.max_requests:
            raise ProofFailure("FAIL_BUDGET", "candidate request budget exhausted")
        proof.costs["total_rpc_requests"] = proof.costs.get("total_rpc_requests", 0) + 1
        proof.costs[duty] = proof.costs.get(duty, 0) + 1
        if duty == "identity_config_batch_reads":
            # Overlapping roles of one HTTP batch, not additive requests.
            proof.costs["identity_reads"] = proof.costs.get("identity_reads", 0) + 1
            proof.costs["config_reads"] = proof.costs.get("config_reads", 0) + 1
        try:
            return await self.rpc._call(method, params)
        except SolanaRpcError as error:
            proof.evidence.setdefault("rpc_failures", []).append(
                {"method": method, "code": error.code}
            )
            raise ProofFailure("FAIL_RPC", error.code) from None

    async def _history(self, proof: Proof, address: str) -> list[dict[str, Any]]:
        rows = await self._read(
            proof,
            "getSignaturesForAddress",
            [
                address,
                {
                    "commitment": "confirmed",
                    "limit": self.policy.max_signatures + 1,
                    "minContextSlot": proof.candidate.anchor_slot,
                },
            ],
            "transaction_block_reads",
        )
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ProofFailure("FAIL_CONTINUITY", "signature history unavailable")
        proof.evidence.setdefault("history_reads", []).append(
            {"address": address, "rows": rows, "received_at": datetime.now(UTC).isoformat()}
        )
        if any(row.get("signature") == proof.candidate.anchor_signature for row in rows):
            proof.evidence.setdefault(
                "address_signature_index_visible_at", datetime.now(UTC).isoformat()
            )
        return rows

    async def _bundle(
        self,
        proof: Proof | None,
        *,
        refresh: bool = False,
        mint: str | None = None,
        minimum_slot: int = 0,
    ) -> dict[str, Any]:
        # PAPER may reuse the canonical atomic decoder without creating a historical proof.
        if proof is not None:
            mint = proof.candidate.mint
            minimum_slot = proof.reserve_slot or proof.candidate.anchor_slot
        if mint is None:
            raise ValueError("mint required for current account read")
        curve = curve_address(mint)
        configs = config_addresses()
        addresses = [
            mint,
            curve,
            associated_address(curve, mint, TOKEN_PROGRAM_ID),
            associated_address(curve, mint, TOKEN_2022_PROGRAM_ID),
            configs["pump_global"][0],
            configs["pump_fee"][0],
            pda(configs["pump_fee"][1], [b"sharing-config", decode_base58(mint)]),
        ]
        params: list[object] = [
            addresses,
            {
                "commitment": "confirmed",
                "encoding": "base64",
                "minContextSlot": minimum_slot,
            },
        ]
        raw = (
            await self._read(
                proof,
                "getMultipleAccounts",
                params,
                "reserve_refresh_reads" if refresh else "identity_config_batch_reads",
            )
            if proof is not None
            else await self.rpc._call("getMultipleAccounts", params)
        )
        account_batch = {
            "addresses": addresses,
            "response": raw,
            "received_at": datetime.now(UTC).isoformat(),
        }
        if proof is not None:
            proof.evidence[
                "execution_refresh_account_batch" if refresh else "candidate_account_batch"
            ] = account_batch
        try:
            slot, values = int(raw["context"]["slot"]), raw["value"]
            if not refresh and proof is not None:
                proof.identity_slot = proof.reserve_slot = proof.config_slot = slot
                proof.slot_span = 0
            if len(values) != len(addresses):
                raise KeyError("batch length")
            if slot < minimum_slot:
                raise ProofFailure("FAIL_STATE_SYNC", "account context slot regressed")
            accounts = dict(zip(addresses, values, strict=True))
            mint_acc, curve_acc = accounts[mint], accounts[curve]
            if not mint_acc or mint_acc["owner"] not in {TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID}:
                raise ProofFailure("FAIL_IDENTITY", "mint owner unavailable")
            if not curve_acc or curve_acc["owner"] != PUMP_PROGRAM_ID:
                raise ProofFailure("FAIL_IDENTITY", "curve owner mismatch")
            if mint_acc["executable"] or curve_acc["executable"]:
                raise ProofFailure("FAIL_IDENTITY", "executable market account")

            def data(account: dict[str, Any]) -> bytes:
                return base64.b64decode(account["data"][0], validate=True)

            curve_fields, missing = decode_config(PUMP_PROGRAM_ID, data(curve_acc), "BondingCurve")
            if proof is not None:
                proof.evidence["candidate_curve_fields"] = curve_fields
                proof.evidence["candidate_curve_missing_fields"] = missing
            if missing:
                raise ProofFailure("FAIL_FEE", "curve fee fields incomplete: " + ",".join(missing))
            if curve_fields["is_mayhem_mode"] or curve_fields["complete"]:
                raise ProofFailure("FAIL_IDENTITY", "excluded mode or completion")
            if curve_fields["quote_mint"] not in {NATIVE_SOL_MINT, WRAPPED_SOL_MINT}:
                raise ProofFailure("FAIL_IDENTITY", "quote asset unsupported")
            mint_fields = decode_mint_account(data(mint_acc))
            # Holders can burn, so the live mint supply may shrink below the launch
            # supply. Standard (non-Mayhem) fees use the fixed 1B supply in the
            # official SDK (getFee: ONE_BILLION_SUPPLY), so a burn changes nothing here.
            if (
                curve_fields["token_total_supply"] != _STANDARD_SUPPLY
                or mint_fields.supply > _STANDARD_SUPPLY
            ):
                raise ProofFailure("FAIL_FEE", "standard SDK supply invariant unsupported")
            validate_token_extensions(data(mint_acc), mint_acc["owner"], mint=True)
            if not mint_fields.initialized or mint_fields.supply <= 0:
                raise ProofFailure("FAIL_IDENTITY", "mint supply mismatch")
            vault = associated_address(curve, mint, mint_acc["owner"])
            vault_acc = accounts[vault]
            if not vault_acc or vault_acc["owner"] != mint_acc["owner"] or vault_acc["executable"]:
                raise ProofFailure("FAIL_IDENTITY", "vault owner mismatch")
            token = decode_token_account(data(vault_acc))
            validate_token_extensions(data(vault_acc), vault_acc["owner"], mint=False)
            if len(data(vault_acc)) < 165 or data(vault_acc)[108] != 1:
                raise ProofFailure("FAIL_IDENTITY", "vault frozen or uninitialized")
            if token.mint != mint or token.owner != curve:
                raise ProofFailure("FAIL_IDENTITY", "vault authority or mint mismatch")
            branches = [
                name
                for name, present in (
                    ("CASHBACK", curve_fields["is_cashback_coin"]),
                    ("HOLDER_REWARD", curve_fields["is_holder_reward"]),
                    ("SHARED_CREATOR", bool(accounts[addresses[-1]])),
                )
                if present
            ]
            if proof is not None:
                proof.evidence["fee_route_branches"] = branches
                proof.evidence["fee_route_class"] = (
                    "STANDARD_COMPLEX_FEE_ROUTE" if branches else "STANDARD_SIMPLE_FEE_ROUTE"
                )
            if branches:
                raise ProofFailure("FAIL_FEE", "unsupported fee route: " + ",".join(branches))
            records = []
            versions = []
            for key in ("pump_global", "pump_fee"):
                address, owner, name = configs[key]
                account = accounts[address]
                if not account or account["owner"] != owner or account["executable"]:
                    raise ProofFailure("FAIL_CONFIG", "canonical config owner mismatch")
                raw_data = data(account)
                versions.append(hashlib.sha256(raw_data).hexdigest())
                records.append((owner, name, raw_data))
            version = ":".join(versions)
            cached = self.config_cache.get(version)
            if cached is None:
                decoded = [
                    decode_config(owner, raw_data, name) for owner, name, raw_data in records
                ]
                if any(unknown for _, unknown in decoded):
                    raise ProofFailure("FAIL_CONFIG", "config schema incomplete")
                cached = (decoded[0][0], decoded[1][0])
                self.config_cache[version] = cached
            global_state, fee_config = cached
            rates = select_fees(global_state, fee_config, curve_fields, _STANDARD_SUPPLY)
            binding = {
                "mint": mint,
                "curve": curve,
                "vault": vault,
                "token_program": mint_acc["owner"],
                "mint_data_hash": hashlib.sha256(data(mint_acc)).hexdigest(),
                "creator": curve_fields["creator"],
                "creator_fee_bps": curve_fields["creator_fee_bps"],
                "can_edit_creator_fee": curve_fields["can_edit_creator_fee"],
                "config_version": version,
                "quote": curve_fields["quote_mint"],
                "decimals": mint_fields.decimals,
                "config_addresses": [configs[key][0] for key in ("pump_global", "pump_fee")],
            }
            # Current identity/config are independently validated above. Receipt
            # continuity is assessed separately by execution_refresh, not cache presence.
            result = {
                "slot": slot,
                "curve": curve_fields,
                "binding": binding,
                "rates": rates,
                "global": global_state,
                "fee_config": fee_config,
                "vault_amount": token.amount,
                "curve_lamports": curve_acc["lamports"],
                "supply": _STANDARD_SUPPLY,
                "synchronization": "ONE_RPC_BANK_CONTEXT",
            }
            if proof is None:
                result["account_batch"] = account_batch
            if not refresh and proof is not None:
                proof.evidence.update(result)
                proof.evidence["buy_research_quote"] = buy_quote(
                    curve_fields, proof.candidate.buy_budget_raw, rates
                )
                proof.evidence["sell_research_quote"] = sell_quote(
                    curve_fields, proof.candidate.sell_quantity_raw, rates
                )
                proof.evidence["research_quotes_authorize_execution"] = False
            return result
        except ProofFailure:
            raise
        except (KeyError, TypeError, ValueError, IndexError) as error:
            raise ProofFailure(
                "FAIL_OTHER", "account decode failure: " + type(error).__name__
            ) from None

    async def prove(self, candidate: Candidate) -> Proof:
        proof = Proof(candidate, candidate_detected_at=candidate.detected_at)
        if candidate.mint in self.incompatible_markets:
            proof.stage, proof.reason = FunnelStage.REJECTED, "KNOWN_INCOMPATIBLE_LIFECYCLE_OR_MODE"
            proof.costs["total_rpc_requests"] = 0
            return proof
        stage, reason = observational_stage(candidate)
        if stage != FunnelStage.SERIOUS_CANDIDATE:
            if stage == FunnelStage.REJECTED:
                self.invalidate(reason or "candidate excluded", candidate.mint)
            proof.stage, proof.reason = FunnelStage.REJECTED, reason
            proof.costs["total_rpc_requests"] = 0
            return proof
        async with self.lock:
            started = monotonic()
            self.receipts.pop(candidate.mint, None)
            proof.proof_started_at = datetime.now(UTC)
            epoch = self.generation, self.market_generations[candidate.mint]
            try:
                candidate_age = (
                    proof.proof_started_at - candidate.detected_at
                ).total_seconds() * 1000
                if candidate_age < 0 or candidate_age > self.policy.max_proof_age_ms:
                    raise ProofFailure("FAIL_STATE_SYNC", "candidate queue stale or future")
                async with asyncio.timeout(self.policy.timeout_seconds):
                    await self._prove(proof)
                account_time = datetime.fromisoformat(
                    proof.evidence["candidate_account_batch"]["received_at"]
                )
                proof.evidence["proof_age_at_completion_ms"] = (
                    datetime.now(UTC) - account_time
                ).total_seconds() * 1000
                if proof.evidence["proof_age_at_completion_ms"] > self.policy.max_proof_age_ms:
                    raise ProofFailure(
                        "FAIL_STATE_SYNC", "proof account state expired at completion"
                    )
                if epoch != (self.generation, self.market_generations[candidate.mint]):
                    proof.evidence["invalidation_during_proof"] = self.invalidations[-8:]
                    raise ProofFailure("FAIL_CONFIG", "invalidation occurred during proof")
                proof.status, proof.stage = "PASS", FunnelStage.EXECUTION_READY
                proof.trust = dict.fromkeys(TrustDimension, True)
                proof.evidence["trust_at_completion"] = dict(proof.trust)
                self.receipts[candidate.mint] = proof
                self.lineage[candidate.mint] = proof
            except ProofFailure as error:
                proof.status, proof.reason, proof.stage = (
                    error.status,
                    str(error),
                    FunnelStage.REJECTED,
                )
                self.invalidate(str(error), candidate.mint)
            except TimeoutError:
                proof.status, proof.reason, proof.stage = (
                    "FAIL_BUDGET",
                    "proof deadline exhausted",
                    FunnelStage.REJECTED,
                )
            except Exception as error:
                proof.reason, proof.stage = type(error).__name__, FunnelStage.REJECTED
            proof.proof_completed_at = datetime.now(UTC)
            proof.proof_latency_ms = (monotonic() - started) * 1000
            return proof

    async def _prove(self, proof: Proof) -> None:
        candidate = proof.candidate
        curve = curve_address(candidate.mint)
        proof.evidence["native_event_received_at"] = (
            candidate.native_event_received_at or candidate.detected_at
        ).isoformat()
        anchor_tx = None
        # Measured null replies are retried within the existing deadline/read cap.
        # This is availability probing, not a larger reconstruction window.
        for attempt in range(3):
            anchor_tx = await self._read(
                proof,
                "getTransaction",
                [
                    candidate.anchor_signature,
                    {
                        "encoding": "json",
                        "commitment": "confirmed",
                        "maxSupportedTransactionVersion": 0,
                    },
                ],
                "direct_transaction_reads",
            )
            proof.evidence.setdefault("transaction_availability_probes", []).append(
                {
                    "at": datetime.now(UTC).isoformat(),
                    "available": anchor_tx is not None,
                }
            )
            if anchor_tx is not None:
                break
            if attempt < 2:
                await asyncio.sleep(0.15)
        proof.evidence["direct_anchor_transaction"] = anchor_tx
        if anchor_tx is None:
            await self._history(proof, curve)
            raise ProofFailure("FAIL_CONTINUITY", "direct anchor transaction unavailable")
        proof.evidence["direct_getTransaction_available_at"] = datetime.now(UTC).isoformat()
        if anchor_tx.get("slot") != candidate.anchor_slot:
            raise ProofFailure("FAIL_CONTINUITY", "direct anchor slot mismatch")
        signatures = anchor_tx.get("transaction", {}).get("signatures")
        if not isinstance(signatures, list) or candidate.anchor_signature not in signatures:
            raise ProofFailure("FAIL_CONTINUITY", "direct anchor signature mismatch")
        anchor_reconstruction = reconstruct_transaction(anchor_tx)
        proof.evidence["direct_anchor_reconstruction"] = anchor_reconstruction
        if (
            len(anchor_reconstruction) != 1
            or anchor_reconstruction[0]["status"] != "TRANSACTION_SEQUENCE_VERIFIED"
        ):
            raise ProofFailure(
                "FAIL_CONTINUITY", "direct anchor native/physical reconstruction unproven"
            )
        # Derive both canonical vaults locally; no discovery RPC.
        before_curve = await self._history(proof, curve)
        bundle = await self._bundle(proof)
        anchor_events = [
            e
            for _, e in extract_anchor_events(anchor_tx.get("meta", {}).get("logMessages", []))
            if isinstance(e, PumpTrade)
        ]
        if len(anchor_events) != 1 or anchor_events[0] != candidate.anchor:
            raise ProofFailure("FAIL_CONTINUITY", "direct anchor event mismatch")
        event = anchor_events[0]
        direction = 1 if event.is_buy else -1
        anchor_pre = {
            key: getattr(event, key)
            + (
                direction * event.token_amount
                if "token" in key
                else -direction * event.quote_amount
            )
            for key in (
                "virtual_token_reserves",
                "virtual_quote_reserves",
                "real_token_reserves",
                "real_quote_reserves",
            )
        }
        proof.evidence["observed_anchor_parity"] = validate_transaction_parity(
            anchor_tx, event, bundle, anchor_pre, candidate.anchor_signature
        )
        vault = bundle["binding"]["vault"]
        before_vault = await self._history(proof, vault)
        windows: list[dict[str, Any]] = [
            {"signature": candidate.anchor_signature, "slot": candidate.anchor_slot, "err": None}
        ]
        for rows in (before_curve, before_vault):
            # The native anchor is fetched directly. History only discovers successors.
            # A lagging index is safe only if exact terminal/physical bank parity below passes.
            # Failed transactions roll back market writes. Retain them in the
            # four raw fences, but do not spend the successful-state signature
            # budget reconstructing them. A full page still needs its boundary.
            window = [
                row
                for row in rows
                if row["slot"] >= candidate.anchor_slot and row.get("err") is None
            ]
            if (
                len(rows) >= self.policy.max_signatures + 1
                and all(row["slot"] >= candidate.anchor_slot for row in rows)
                and not any(row["signature"] == candidate.anchor_signature for row in rows)
            ):
                raise ProofFailure("FAIL_BUDGET", "successor boundary not reached")
            if len(window) > self.policy.max_signatures:
                raise ProofFailure("FAIL_BUDGET", "recent signature window exhausted")
            windows.extend(window)
        by_sig = {row["signature"]: row for row in windows}
        if len(by_sig) > self.policy.max_signatures:
            raise ProofFailure("FAIL_BUDGET", "union signature budget exhausted")
        transactions: list[tuple[int, str, dict[str, Any], PumpTrade, dict[str, Any]]] = []
        for signature, history_row in by_sig.items():
            if history_row.get("err") is not None or history_row["slot"] > bundle["slot"]:
                raise ProofFailure("FAIL_STATE_SYNC", "history crosses account snapshot")
            tx = (
                anchor_tx
                if signature == candidate.anchor_signature
                else await self._read(
                    proof,
                    "getTransaction",
                    [
                        signature,
                        {
                            "encoding": "json",
                            "commitment": "confirmed",
                            "maxSupportedTransactionVersion": 0,
                        },
                    ],
                    "direct_transaction_reads",
                )
            )
            if tx is None or tx.get("slot") != history_row["slot"]:
                raise ProofFailure("FAIL_CONTINUITY", "transaction metadata missing")
            proof.evidence.setdefault("native_transactions", []).append(tx)
            events = [
                e
                for _, e in extract_anchor_events(tx.get("meta", {}).get("logMessages", []))
                if isinstance(e, PumpTrade)
            ]
            if (
                len(events) != 1
                or events[0].mint != candidate.mint
                or events[0].is_mayhem_mode is not False
            ):
                raise ProofFailure("FAIL_CONTINUITY", "nonstandard or ambiguous transaction")
            recon = reconstruct_transaction(tx)
            proof.evidence.setdefault("reconstructions", []).extend(recon)
            if len(recon) != 1 or recon[0]["status"] != "TRANSACTION_SEQUENCE_VERIFIED":
                raise ProofFailure("FAIL_CONTINUITY", "unexplained native or physical mutation")
            transactions.append((history_row["slot"], signature, tx, events[0], recon[0]))
        # Same-slot multiple transactions lack a trustworthy index in signature RPC.
        if len({row[0] for row in transactions}) != len(transactions):
            raise ProofFailure("FAIL_STATE_SYNC", "same-slot transaction order unproven")
        transactions.sort(key=lambda row: row[0])
        if (
            transactions[0][1] != candidate.anchor_signature
            or transactions[0][3] != candidate.anchor
        ):
            raise ProofFailure("FAIL_CONTINUITY", "observed anchor payload mismatch")
        previous = None
        parities = []
        for _, signature, tx, event, reconstruction in transactions:
            current = {
                "virtual_token_reserves": event.virtual_token_reserves,
                "virtual_quote_reserves": event.virtual_quote_reserves,
                "real_token_reserves": event.real_token_reserves,
                "real_quote_reserves": event.real_quote_reserves,
            }
            direction = 1 if event.is_buy else -1
            pre = {
                key: value
                + (
                    direction * event.token_amount
                    if "token" in key
                    else -direction * event.quote_amount
                )
                for key, value in current.items()
            }
            if previous is not None and pre != previous:
                raise ProofFailure(
                    "FAIL_CONTINUITY", "missing reserve mutation between transactions"
                )
            previous = current
            parities.append(validate_transaction_parity(tx, event, bundle, pre, signature))
            proof.evidence["parity"] = parities
            if (
                reconstruction["reserved_inventory"]
                != bundle["vault_amount"] - bundle["curve"]["real_token_reserves"]
            ):
                raise ProofFailure("FAIL_CONTINUITY", "physical vault inventory invariant changed")
            if (
                reconstruction["nonreserve_lamport_offset"]
                != bundle["curve_lamports"] - bundle["curve"]["real_quote_reserves"]
            ):
                raise ProofFailure("FAIL_CONTINUITY", "physical quote offset changed")
        if previous != {key: bundle["curve"][key] for key in previous or {}}:
            raise ProofFailure(
                "FAIL_STATE_SYNC", "terminal transaction state differs from atomic snapshot"
            )
        after_curve = await self._history(proof, curve)
        after_vault = await self._history(proof, vault)
        if before_curve != after_curve or before_vault != after_vault:
            raise ProofFailure("FAIL_STATE_SYNC", "history fence moved during proof")
        proof.identity_slot = proof.reserve_slot = proof.config_slot = bundle["slot"]
        proof.slot_span = 0
        proof.evidence = {
            **proof.evidence,
            **bundle,
            "parity": parities,
            "buy": buy_quote(bundle["curve"], candidate.buy_budget_raw, bundle["rates"]),
            "sell": sell_quote(bundle["curve"], candidate.sell_quantity_raw, bundle["rates"]),
            "signature_window": list(by_sig),
            "sequence_slot_span": bundle["slot"] - min(row[0] for row in transactions),
            "native_sequence_anchored": True,
            "history_anchor_visible": any(
                r.get("signature") == candidate.anchor_signature for r in after_curve
            ),
            "continuity_scope": "native sequence to current bank; unseen history not certified",
            "execution_refresh_required": True,
            "external_fees": "ESTIMATED external execution costs; separate from reserve math",
        }
        self.stable[candidate.mint] = bundle

    async def execution_refresh(self, proof: Proof, *, decision_at: datetime) -> dict[str, Any]:
        if self.lineage.get(proof.candidate.mint) is not proof or proof.status != "PASS":
            raise ProofFailure("FAIL_OTHER", "no current approved receipt")
        age = (decision_at - (proof.proof_completed_at or decision_at)).total_seconds() * 1000
        now = datetime.now(UTC)
        wall_age = (now - (proof.proof_completed_at or now)).total_seconds() * 1000
        if age < 0 or decision_at > now:
            raise ProofFailure("FAIL_STATE_SYNC", "stale candidate proof")
        proof.decision_at, proof.decision_age_ms = decision_at, age
        invalidation_start = len(self.invalidations)
        try:
            async with asyncio.timeout(self.policy.timeout_seconds):
                fresh = await self._bundle(proof, refresh=True)
        except Exception:
            self.invalidate("execution refresh failed", proof.candidate.mint)
            raise
        proof.execution_refresh_at = datetime.now(UTC)
        if (
            proof.execution_refresh_at - decision_at
        ).total_seconds() * 1000 > self.policy.max_proof_age_ms:
            raise ProofFailure("FAIL_STATE_SYNC", "execution refresh deadline stale")
        old = proof.evidence
        if (
            fresh["vault_amount"] - fresh["curve"]["real_token_reserves"]
            != old["vault_amount"] - old["curve"]["real_token_reserves"]
        ):
            self.invalidate("vault reserve relationship changed", proof.candidate.mint)
            raise ProofFailure("FAIL_CONTINUITY", "execution inventory changed")
        if (
            fresh["curve_lamports"] - fresh["curve"]["real_quote_reserves"]
            != old["curve_lamports"] - old["curve"]["real_quote_reserves"]
        ):
            self.invalidate("quote balance relationship changed", proof.candidate.mint)
            raise ProofFailure("FAIL_CONTINUITY", "execution quote offset changed")
        fresh["buy"] = buy_quote(fresh["curve"], proof.candidate.buy_budget_raw, fresh["rates"])
        fresh["sell"] = sell_quote(
            fresh["curve"], proof.candidate.sell_quantity_raw, fresh["rates"]
        )
        fresh["execution_refresh_at"] = proof.execution_refresh_at
        binding_changed = fresh["binding"] != old["binding"]
        if binding_changed:
            proof.trust[TrustDimension.CONTINUITY] = False
            proof.evidence["new_binding_requires_native_proof"] = True
        for dimension in CURRENT_DIMENSIONS:
            proof.trust[dimension] = True
        if proof.incompatible_mutation:
            proof.trust[TrustDimension.LIFECYCLE] = False
            proof.trust[TrustDimension.MODE] = False
        # Invalidation arriving during an in-flight read may be newer than its bank.
        for record in self.invalidations[invalidation_start:]:
            if record["mint"] not in {"ALL", proof.candidate.mint}:
                continue
            source_slot = (record.get("source") or {}).get("slot")
            if source_slot is None or source_slot >= fresh["slot"]:
                proof.trust.update({d: False for d in record["dimensions"]})
        fresh["trust_dimensions"] = dict(proof.trust)
        fresh["continuity_proven_through_slot"] = proof.reserve_slot
        fresh["refresh_does_not_extend_continuity"] = True
        stale = max(age, wall_age) > self.policy.max_proof_age_ms
        approved = (
            all(proof.trust.get(d, False) for d in TrustDimension)
            and not stale
            and not proof.incompatible_mutation
        )
        fresh["execution_approved"] = approved
        fresh["revalidation_outcome"] = (
            "INCOMPATIBLE_MUTATION_BLOCKED"
            if proof.incompatible_mutation
            else "STILL_BLOCKED_BY_UNPROVEN_CONTINUITY"
            if not proof.trust.get(TrustDimension.CONTINUITY)
            or not proof.trust.get(TrustDimension.STREAM_COVERAGE)
            else "PROOF_STALE_BUT_CURRENT_STATE_VALID"
            if stale
            else "CURRENT_STATE_REVALIDATION_PENDING"
            if not approved
            else "FRESH_STATE_REVALIDATED"
        )
        if approved:
            self.receipts[proof.candidate.mint] = proof
            self.stable[proof.candidate.mint] = fresh
        else:
            self.receipts.pop(proof.candidate.mint, None)
        return fresh


def validate_token_extensions(data: bytes, owner: str, *, mint: bool) -> None:
    minimum = 82 if mint else 165
    if len(data) < minimum:
        raise ProofFailure("FAIL_IDENTITY", "token account truncated")
    if owner == TOKEN_PROGRAM_ID:
        if len(data) != minimum:
            raise ProofFailure("FAIL_IDENTITY", "unexpected legacy token layout")
        return
    if len(data) == minimum:
        return
    if len(data) < 166 or data[165] != (1 if mint else 2):
        raise ProofFailure("FAIL_IDENTITY", "Token-2022 extension header unknown")
    # Metadata/close-authority/group references do not alter trade transfers.
    # Transfer fees, hooks, confidential/frozen/pause and unknown extensions fail.
    allowed = {3, 18, 19, 20, 21, 22, 23} if mint else {7}
    offset = 166
    while offset < len(data):
        if not any(data[offset:]):
            return
        if len(data) - offset < 4:
            raise ProofFailure("FAIL_IDENTITY", "Token-2022 TLV truncated")
        kind, length = (
            int.from_bytes(data[offset : offset + 2], "little"),
            int.from_bytes(data[offset + 2 : offset + 4], "little"),
        )
        offset += 4 + length
        if kind not in allowed or offset > len(data):
            raise ProofFailure("FAIL_IDENTITY", "Token-2022 transfer semantics unvalidated")


def validate_transaction_parity(
    tx: dict[str, Any],
    event: PumpTrade,
    bundle: dict[str, Any],
    pre: dict[str, int],
    signature: str,
) -> dict[str, Any]:
    records = []
    for line in tx["meta"]["logMessages"]:
        if line.startswith("Program data: "):
            try:
                name, fields = decode_record(
                    PUMP_PROGRAM_ID, base64.b64decode(line[14:], validate=True), collection="events"
                )
                if name == "TradeEvent" and fields["mint"] == event.mint:
                    records.append(fields)
            except ValueError:
                continue
    if len(records) != 1:
        raise ProofFailure("FAIL_FEE", "full native fee event unavailable")
    fields = records[0]
    if fields["creator"] != bundle["curve"]["creator"] or any(
        fields.get(key, 0) for key in ("cashback", "holder_rewards", "shareholders")
    ):
        raise ProofFailure("FAIL_FEE", "creator or auxiliary fee routing mismatch")
    curve = {**bundle["curve"], **pre}
    rates = select_fees(bundle["global"], bundle["fee_config"], curve, bundle["supply"])
    if (
        fields["fee_basis_points"] != rates["protocol_bps"]
        or fields["creator_fee_basis_points"] != rates["creator_bps"]
    ):
        raise ProofFailure("FAIL_FEE", "native fee tier or creator override mismatch")
    if fields["fee"] != fee(event.quote_amount, rates["protocol_bps"]) or fields[
        "creator_fee"
    ] != fee(event.quote_amount, rates["creator_bps"]):
        raise ProofFailure("FAIL_FEE", "native integer fee amount mismatch")
    try:
        calls = trade_invocations(tx, event.mint)
    except ValueError as error:
        raise ProofFailure("FAIL_CONTINUITY", str(error)) from error
    if len(calls) != 1 or calls[0]["event"] != event:
        raise ProofFailure("FAIL_FEE", "instruction input ambiguous")
    call = calls[0]
    native = [call["instruction"]]
    raw = decode_base58(native[0]["data"])
    argument = int.from_bytes(raw[8:16], "little")
    limit = int.from_bytes(raw[16:24], "little")
    name = call["name"]
    try:
        if name in {"buy_exact_sol_in", "buy_exact_quote_in_v2"}:
            quote = buy_exact_input(curve, argument, rates)
        else:
            quote = (
                buy_exact_tokens(curve, event.token_amount, rates)
                if event.is_buy
                else sell_quote(curve, event.token_amount, rates)
            )
    except ValueError as error:
        raise ProofFailure("FAIL_FEE", str(error)) from error
    amount = quote["net_curve_input"] if event.is_buy else quote["gross_output"]
    if amount != event.quote_amount:
        raise ProofFailure("FAIL_FEE", "integer curve input/output mismatch")
    message = tx["transaction"]["message"]
    keys = (
        message["accountKeys"]
        + tx["meta"].get("loadedAddresses", {}).get("writable", [])
        + tx["meta"].get("loadedAddresses", {}).get("readonly", [])
    )
    keys = [key["pubkey"] if isinstance(key, dict) else key for key in keys]
    definitions = {bytes(ix["discriminator"]): ix for ix in schema(PUMP_PROGRAM_ID)["instructions"]}
    if len(native) != 1:
        raise ProofFailure("FAIL_FEE", "instruction input ambiguous")
    raw = decode_base58(native[0]["data"])
    definition = definitions[raw[:8]]
    argument = int.from_bytes(raw[8:16], "little")
    limit = int.from_bytes(raw[16:24], "little")
    name = definition["name"]
    if name in {"buy", "buy_v2"}:
        matched = argument == event.token_amount and quote["gross_input"] <= limit
    elif name in {"buy_exact_sol_in", "buy_exact_quote_in_v2"}:
        matched = quote["token_output"] == event.token_amount and event.token_amount >= limit
    elif name in {"sell", "sell_v2"}:
        matched = argument == event.token_amount and quote["net_output"] >= limit
    else:
        matched = False
    if not matched:
        raise ProofFailure("FAIL_FEE", "native instruction quantity or rounding mismatch")
    accounts = [keys[index] for index in native[0]["accounts"]]
    names = [item["name"] for item in definition["accounts"]]
    mapping = dict(zip(names, accounts, strict=False))
    for name, binding_key in (
        ("mint", "mint"),
        ("bonding_curve", "curve"),
        ("associated_bonding_curve", "vault"),
        ("token_program", "token_program"),
    ):
        alias = {
            "mint": "base_mint",
            "associated_bonding_curve": "associated_base_bonding_curve",
            "token_program": "base_token_program",
        }.get(name, name)
        if mapping.get(name, mapping.get(alias)) != bundle["binding"][binding_key]:
            raise ProofFailure("FAIL_IDENTITY", "native canonical account mismatch: " + name)
    if "quote_mint" in mapping and mapping["quote_mint"] not in {NATIVE_SOL_MINT, WRAPPED_SOL_MINT}:
        raise ProofFailure("FAIL_IDENTITY", "native quote mint mismatch")
    configs = config_addresses()
    if (
        mapping.get("global") != configs["pump_global"][0]
        or mapping.get("fee_config") != configs["pump_fee"][0]
    ):
        raise ProofFailure("FAIL_CONFIG", "native config account binding mismatch")
    recipients = [bundle["global"]["fee_recipient"], *bundle["global"]["fee_recipients"]]
    if fields["fee_recipient"] not in recipients or mapping.get("creator_vault") != pda(
        PUMP_PROGRAM_ID, [b"creator-vault", decode_base58(fields["creator"])]
    ):
        raise ProofFailure("FAIL_FEE", "native fee destination binding mismatch")
    if mapping.get("fee_recipient") != fields["fee_recipient"]:
        raise ProofFailure("FAIL_FEE", "instruction and event protocol recipient mismatch")
    buyback_bps = int(bundle["global"]["buyback_basis_points"])
    buyback_fee = fields["fee"] * buyback_bps // 10000
    if fields["buyback_fee_basis_points"] != buyback_bps or fields["buyback_fee"] != buyback_fee:
        raise ProofFailure("FAIL_FEE", "protocol buyback split rounding/config mismatch")

    def balance_delta(address: str) -> int:
        if address not in keys:
            return 0
        index = keys.index(address)
        return int(tx["meta"]["postBalances"][index]) - int(tx["meta"]["preBalances"][index])

    destinations = {
        "protocol_primary": balance_delta(fields["fee_recipient"]),
        "creator_vault": balance_delta(mapping["creator_vault"]),
        "protocol_buyback": sum(
            balance_delta(a) for a in set(bundle["global"]["buyback_fee_recipients"])
        ),
    }
    if destinations != {
        "protocol_primary": fields["fee"] - buyback_fee,
        "creator_vault": fields["creator_fee"],
        "protocol_buyback": buyback_fee,
    }:
        raise ProofFailure("FAIL_FEE", "native fee destination balance delta mismatch")
    user = mapping.get("user")
    if user != event.user:
        raise ProofFailure("FAIL_IDENTITY", "native trader identity mismatch")
    try:
        accounting = execution_accounting(tx, event.mint)
    except ValueError as error:
        raise ProofFailure("FAIL_FEE", str(error)) from error
    refund = 0
    if not event.is_buy:
        ancillary_net = 0
        for movement in accounting["movements"]:
            if movement["asset"] != "SOL" or movement["kind"] in {
                "TRADE_PROCEEDS",
                "PROTOCOL_FEE",
                "CREATOR_FEE",
                "BUYBACK_FEE",
            }:
                continue
            direction = int(movement["destination"] == user) - int(movement["source"] == user)
            ancillary_net += direction * movement["amount"]
            if movement["kind"] == "TOKEN_ACCOUNT_CLOSE_REFUND" and direction == 1:
                refund += movement["amount"]
        actual_quote_transfer = (
            balance_delta(user)
            + (int(tx["meta"].get("fee", 0)) if keys[0] == user else 0)
            - ancillary_net
        )
        if actual_quote_transfer != quote["net_output"]:
            raise ProofFailure(
                "FAIL_FEE", "actual sell quote transfer mismatch or unexplained wallet mutation"
            )
    else:
        recipients_for_buy = {
            bundle["binding"]["curve"],
            mapping["creator_vault"],
            fields["fee_recipient"],
            *bundle["global"]["buyback_fee_recipients"],
        }
        actual_quote_transfer = 0
        for _, ix in call["descendants"]:
            raw_ix = decode_base58(ix["data"])
            acc = [keys[i] for i in ix.get("accounts", [])]
            if keys[ix["programIdIndex"]] == NATIVE_SOL_MINT and raw_ix[:4] == b"\x02\0\0\0":
                if (
                    len(raw_ix) != 12
                    or len(acc) != 2
                    or acc[0] != user
                    or acc[1] not in recipients_for_buy
                ):
                    raise ProofFailure("FAIL_FEE", "unexplained native buy SOL transfer")
                actual_quote_transfer += int.from_bytes(raw_ix[4:], "little")
        if actual_quote_transfer != quote["gross_input"]:
            raise ProofFailure("FAIL_FEE", "actual buy quote transfer mismatch")
    return {
        "transfer_accounting": accounting,
        "execution_alignment": {
            k: call[k] for k in ("top_index", "inner_index", "event_inner_index")
        },
        "signature": signature,
        "side": "buy" if event.is_buy else "sell",
        "instruction": call["name"],
        "native_input_argument_raw": argument,
        "native_limit_raw": limit,
        "quote": quote,
        "rates": rates,
        "native_fee_fields": fields,
        "instruction_accounts": mapping,
        "fee_destination_deltas": destinations,
        "actual_quote_transfer": actual_quote_transfer,
        "sell_rent_refund": refund,
        "pre_reserves": pre,
        "post_reserves": {key: getattr(event, key) for key in pre},
        "native_integer_parity": True,
    }


def proof_cost_summary(proofs: list[Proof]) -> dict[str, Any]:
    attempts = [proof for proof in proofs if proof.proof_started_at is not None]

    def stats(values: list[float]) -> dict[str, float | None]:
        values.sort()
        if not values:
            return dict(average=None, median=None, p90=None, max=None)
        return {
            "average": sum(values) / len(values),
            "median": values[len(values) // 2],
            "p90": values[min(len(values) - 1, (9 * len(values) + 9) // 10 - 1)],
            "max": values[-1],
        }

    return {
        "attempts": len(attempts),
        "statuses": dict(Counter(p.status for p in attempts)),
        "rpc_requests": stats([float(p.costs.get("total_rpc_requests", 0)) for p in attempts]),
        "proof_latency_ms": stats([p.proof_latency_ms or 0 for p in attempts]),
        "rejected_attempts": [p.report() for p in attempts if p.status != "PASS"],
    }


def proof_failure_category(proof: Proof) -> str:
    if proof.status == "PASS":
        return "SUCCESS"
    if proof.status == "FAIL_RPC":
        if (proof.reason or "").startswith("rpc_"):
            return "PROVIDER_RPC_RESPONSE_ERROR"
        return (
            "CAPTURE_BUDGET"
            if proof.reason == "calibration_request_cap"
            else "PROVIDER_TRANSPORT_OR_CAPACITY"
        )
    if proof.reason == "direct anchor transaction unavailable":
        return "PROVIDER_TRANSACTION_AVAILABILITY"
    if proof.reason == "candidate queue stale or future":
        return "PROOF_TIMING"
    return "PROOF_EVIDENCE"
