"""Read-only canonical identity and shared fee/config bootstrap; no order methods."""

from __future__ import annotations

import asyncio
import base64
import hashlib
from dataclasses import dataclass
from typing import Any

from memebot.market_state import MarketIdentity

from .base import Commitment, RpcAccount, SolanaRpcProvider
from .canonical import (
    associated_address,
    config_addresses,
    curve_address,
    pool_address_and_bump,
    pool_authority,
)
from .encoding import BorshDecodeError, BorshReader
from .idl_schema import decode_type, schema
from .pump_idl import (
    NATIVE_SOL_MINT,
    PUMP_AMM_PROGRAM_ID,
    PUMP_PROGRAM_ID,
    TOKEN_2022_PROGRAM_ID,
    TOKEN_PROGRAM_ID,
    WRAPPED_SOL_MINT,
    BondingCurveAccount,
    PoolAccount,
    decode_bonding_curve_account,
    decode_mint_account,
    decode_token_account,
)


def account_data(account: RpcAccount) -> bytes:
    return base64.b64decode(account.data_base64, validate=True)


def decode_config(program: str, data: bytes, name: str) -> tuple[dict[str, Any], list[str]]:
    definition = next(a for a in schema(program)["accounts"] if a["name"] == name)
    if data[:8] != bytes(definition["discriminator"]):
        raise BorshDecodeError("config discriminator mismatch")
    fields = next(t["type"]["fields"] for t in schema(program)["types"] if t["name"] == name)
    reader = BorshReader(data[8:])
    values: dict[str, Any] = {}
    for index, field in enumerate(fields):
        try:
            values[field["name"]] = decode_type(program, field["type"], reader)
        except BorshDecodeError as error:
            if str(error) != "truncated Borsh payload":
                raise
            return values, [f["name"] for f in fields[index:]]
    return values, []


class ReadOnlyConfigCache:
    def __init__(
        self,
        rpc: SolanaRpcProvider,
        commitment: Commitment,
        *,
        venues: tuple[str, ...] = ("pump_fun",),
    ) -> None:
        self.rpc = rpc
        self.commitment = commitment
        self.records: dict[str, dict[str, Any]] = {}
        self.generation: dict[str, int] | None = None
        self.reads = 0
        self.lock = asyncio.Lock()
        self.venues = venues

    async def ensure(self, generation: dict[str, int]) -> None:
        async with self.lock:
            await self._ensure(generation)

    async def _ensure(self, generation: dict[str, int]) -> None:
        # An excluded venue's config churn must not cause standard config reads.
        if "pump_swap" not in self.venues:
            generation = {
                key: value for key, value in generation.items() if key != PUMP_AMM_PROGRAM_ID
            }
        if self.generation == generation:
            return
        self.generation = dict(generation)
        addresses = {
            key: value
            for key, value in config_addresses().items()
            if (key.startswith("pump_") and "pump_fun" in self.venues)
            or (key.startswith("swap_") and "pump_swap" in self.venues)
        }
        self.reads += 1
        try:
            accounts = await self.rpc.get_multiple_accounts(
                [item[0] for item in addresses.values()], self.commitment
            )
            for (key, (address, owner, name)), account in zip(
                addresses.items(), accounts, strict=True
            ):
                record: dict[str, Any] = {
                    "address": address,
                    "program": owner,
                    "status": "UNKNOWN",
                    "fields": {},
                    "unknown_fields": [],
                    "slot": None,
                }
                if (
                    account is not None
                    and account.address == address
                    and account.owner == owner
                    and not account.executable
                ):
                    try:
                        data = account_data(account)
                        fields, missing = decode_config(owner, data, name)
                        record.update(
                            status="VERIFIED_ONCHAIN",
                            fields=fields,
                            unknown_fields=missing,
                            schema_complete=not missing,
                            slot=account.slot,
                            version=hashlib.sha256(data).hexdigest(),
                        )
                    except (BorshDecodeError, ValueError, KeyError):
                        record["error"] = "CONFIG_DECODE_FAILURE"
                else:
                    record["error"] = "CONFIG_OWNER_ADDRESS_OR_ACCOUNT_UNAVAILABLE"
                self.records[key] = record
        except Exception as error:
            self.records = {
                key: {"address": value[0], "status": "UNKNOWN", "error": type(error).__name__}
                for key, value in addresses.items()
            }

    def version(self, venue: str) -> str | None:
        keys = ("pump_global", "pump_fee") if venue == "pump_fun" else ("swap_global", "swap_fee")
        records = [self.records.get(key, {}) for key in keys]
        if not all(
            row.get("status") == "VERIFIED_ONCHAIN" and row.get("schema_complete")
            for row in records
        ):
            return None
        return hashlib.sha256(":".join(str(row["version"]) for row in records).encode()).hexdigest()


@dataclass(frozen=True)
class IdentityBootstrapResult:
    identity: MarketIdentity | None
    checks: dict[str, bool | None]
    error: str | None = None
    mint_supply: int | None = None
    reserved_token_inventory: int | None = None


async def bootstrap_curve(
    rpc: SolanaRpcProvider,
    commitment: Commitment,
    *,
    mint: str,
    account: RpcAccount,
    curve: BondingCurveAccount,
    config_version: str | None,
    standard_only: bool = True,
) -> IdentityBootstrapResult:
    derived = curve_address(mint)
    checks: dict[str, bool | None] = {
        "standard_mode": not standard_only or curve.is_mayhem_mode is False,
        "curve_pda": derived == account.address,
        "program_owner": account.owner == PUMP_PROGRAM_ID,
        "quote_asset": curve.quote_mint in {NATIVE_SOL_MINT, WRAPPED_SOL_MINT},
        "completion_known": True,
        "migration_state": not curve.complete,
    }
    if not all(checks.values()):
        return IdentityBootstrapResult(None, checks, "CURVE_PDA_OWNER_QUOTE_OR_COMPLETION_MISMATCH")
    legacy = associated_address(derived, mint, TOKEN_PROGRAM_ID)
    modern = associated_address(derived, mint, TOKEN_2022_PROGRAM_ID)
    mint_account, legacy_vault, modern_vault = await rpc.get_multiple_accounts(
        [mint, legacy, modern], commitment
    )
    checks["mint_owner"] = mint_account is not None and mint_account.owner in {
        TOKEN_PROGRAM_ID,
        TOKEN_2022_PROGRAM_ID,
    }
    checks["mint_address"] = mint_account is not None and mint_account.address == mint
    if not checks["mint_owner"] or mint_account is None:
        return IdentityBootstrapResult(None, checks, "MINT_OWNER_UNAVAILABLE")
    mint_state = decode_mint_account(account_data(mint_account))
    vault = legacy_vault if mint_account.owner == TOKEN_PROGRAM_ID else modern_vault
    checks["mint_supply"] = mint_state.initialized and mint_state.supply == curve.token_total_supply
    checks["vault_owner"] = vault is not None and vault.owner == mint_account.owner
    checks["vault_address"] = vault is not None and vault.address == associated_address(
        derived, mint, mint_account.owner
    )
    checks["vault_slot"] = vault is not None and vault.slot >= account.slot
    checks["mint_slot"] = mint_account.slot >= account.slot
    if vault is None or not checks["vault_owner"]:
        return IdentityBootstrapResult(None, checks, "CURVE_VAULT_UNAVAILABLE")
    balance = decode_token_account(account_data(vault))
    checks["vault_binding"] = balance.mint == mint and balance.owner == derived
    inventory = balance.amount - curve.real_token_reserves
    checks["inventory_nonnegative"] = inventory >= 0
    if not all(checks.values()):
        return IdentityBootstrapResult(
            None, checks, "CURVE_MINT_VAULT_IDENTITY_MISMATCH", mint_state.supply, inventory
        )
    identity = MarketIdentity(
        "pump_fun",
        PUMP_PROGRAM_ID,
        derived,
        mint,
        curve.quote_mint,
        vault.address,
        None,
        derived,
        False,
        curve.virtual_quote_reserves - curve.real_quote_reserves,
        curve.virtual_token_reserves - curve.real_token_reserves,
        config_version,
        canonical_verified=True,
        config_verified=config_version is not None,
        execution_assumptions_verified=False,
        creator=curve.creator,
        token_program=mint_account.owner,
        config_references=tuple(config_addresses()[key][0] for key in ("pump_global", "pump_fee")),
    )
    return IdentityBootstrapResult(
        identity, checks, mint_supply=mint_state.supply, reserved_token_inventory=inventory
    )


async def bootstrap_pool(
    rpc: SolanaRpcProvider,
    commitment: Commitment,
    *,
    account: RpcAccount,
    pool: PoolAccount,
    base_vault: RpcAccount,
    quote_vault: RpcAccount,
    config_version: str | None,
) -> IdentityBootstrapResult:
    derived, bump = pool_address_and_bump(pool.index, pool.creator, pool.base_mint, pool.quote_mint)
    authority = pool_authority(pool.base_mint)
    checks: dict[str, bool | None] = {
        "pool_pda": derived == account.address,
        "pool_bump": pool.pool_bump == bump,
        "program_owner": account.owner == PUMP_AMM_PROGRAM_ID,
        "base_vault_pda": pool.pool_base_token_account
        == associated_address(derived, pool.base_mint, base_vault.owner),
        "quote_vault_pda": pool.pool_quote_token_account
        == associated_address(derived, pool.quote_mint, quote_vault.owner),
        "canonical_creator": pool.index == 0 and pool.creator == authority,
        "quote_asset": pool.quote_mint == WRAPPED_SOL_MINT,
    }
    if not all(checks.values()):
        return IdentityBootstrapResult(None, checks, "POOL_CANONICAL_PDA_OR_VAULT_MISMATCH")
    source_curve = curve_address(pool.base_mint)
    base_mint, quote_mint, curve_account = await rpc.get_multiple_accounts(
        [pool.base_mint, pool.quote_mint, source_curve], commitment
    )
    checks["mint_owners"] = (
        base_mint is not None
        and quote_mint is not None
        and base_mint.owner == base_vault.owner
        and quote_mint.owner == quote_vault.owner
    )
    checks["auxiliary_addresses"] = (
        base_mint is not None
        and base_mint.address == pool.base_mint
        and quote_mint is not None
        and quote_mint.address == pool.quote_mint
        and curve_account is not None
        and curve_account.address == source_curve
    )
    checks["auxiliary_slots"] = all(
        item is not None and item.slot >= account.slot
        for item in (base_mint, quote_mint, curve_account)
    )
    checks["vault_bindings"] = (
        base_vault.address == pool.pool_base_token_account
        and quote_vault.address == pool.pool_quote_token_account
        and base_vault.owner in {TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID}
        and quote_vault.owner in {TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID}
        and decode_token_account(account_data(base_vault)).mint == pool.base_mint
        and decode_token_account(account_data(base_vault)).owner == derived
        and decode_token_account(account_data(quote_vault)).mint == pool.quote_mint
        and decode_token_account(account_data(quote_vault)).owner == derived
    )
    checks["mints_initialized"] = (
        base_mint is not None
        and quote_mint is not None
        and decode_mint_account(account_data(base_mint)).initialized
        and decode_mint_account(account_data(quote_mint)).initialized
    )
    checks["migration_source"] = (
        curve_account is not None and curve_account.owner == PUMP_PROGRAM_ID
    )
    if curve_account is not None and checks["migration_source"]:
        curve = decode_bonding_curve_account(account_data(curve_account))
        checks["migration_source"] = curve.complete
        checks["creator_relation"] = curve.creator == pool.coin_creator
    else:
        checks["creator_relation"] = None
    if not all(checks.values()) or base_mint is None:
        return IdentityBootstrapResult(None, checks, "POOL_MINT_OR_MIGRATION_BINDING_UNPROVEN")
    mint_state = decode_mint_account(account_data(base_mint))
    identity = MarketIdentity(
        "pump_swap",
        PUMP_AMM_PROGRAM_ID,
        derived,
        pool.base_mint,
        pool.quote_mint,
        base_vault.address,
        quote_vault.address,
        None,
        True,
        pool.virtual_quote_reserves,
        0,
        config_version,
        canonical_verified=True,
        config_verified=config_version is not None,
        execution_assumptions_verified=False,
        creator=pool.coin_creator,
        token_program=base_mint.owner,
        source_curve=source_curve,
        config_references=tuple(config_addresses()[key][0] for key in ("swap_global", "swap_fee")),
    )
    return IdentityBootstrapResult(identity, checks, mint_supply=mint_state.supply)
