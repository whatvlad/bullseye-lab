from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from memebot.models.common import AwareUtcDatetime, SolanaAddress

Commitment = Literal["processed", "confirmed", "finalized"]


class RpcHealth(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    healthy: bool
    checked_at: AwareUtcDatetime
    latency_ms: float = Field(ge=0)
    error: str | None = Field(default=None, max_length=512)


class RpcAccount(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    address: SolanaAddress
    slot: int = Field(ge=0)
    owner: SolanaAddress
    lamports: int = Field(ge=0)
    executable: bool
    data_base64: str


class RpcTokenBalance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    address: SolanaAddress
    amount_raw: int = Field(ge=0)


class RpcTokenBalances(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    slot: int = Field(ge=0)
    balances: tuple[RpcTokenBalance, ...]


class SolanaRpcProvider(Protocol):
    """Vendor-neutral read-only Solana RPC contract for Phase 1 adapters."""

    async def health(self) -> RpcHealth: ...

    async def get_account(
        self,
        address: SolanaAddress,
        commitment: Commitment,
    ) -> RpcAccount | None: ...

    async def get_transaction(
        self,
        signature: str,
        commitment: Commitment,
    ) -> dict[str, object] | None: ...

    async def get_multiple_accounts(
        self,
        addresses: list[SolanaAddress],
        commitment: Commitment,
    ) -> tuple[RpcAccount | None, ...]: ...

    async def get_token_largest_accounts(
        self,
        mint: SolanaAddress,
        commitment: Commitment,
    ) -> RpcTokenBalances: ...

    async def get_token_accounts_by_owner(
        self,
        owner: SolanaAddress,
        mint: SolanaAddress,
        commitment: Commitment,
    ) -> RpcTokenBalances: ...

    async def close(self) -> None: ...
