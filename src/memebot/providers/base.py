from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from memebot.events.models import DomainEvent
from memebot.models.common import AwareUtcDatetime


class ProviderCapability(StrEnum):
    TOKEN_DISCOVERY = "token_discovery"
    MEME_LIFECYCLE = "meme_lifecycle"
    TOKEN_TRADES = "token_trades"
    TOKEN_PRICES = "token_prices"
    TOKEN_STATS = "token_stats"
    NEW_PAIRS = "new_pairs"
    LARGE_TRADES = "large_trades"
    WALLET_TRANSACTIONS = "wallet_transactions"
    HOLDER_DATA = "holder_data"
    TOKEN_SECURITY = "token_security"
    RPC_ACCOUNTS = "rpc_accounts"
    RPC_LOGS = "rpc_logs"
    RPC_TRANSACTIONS = "rpc_transactions"


class ProviderDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=64)
    network: str = "solana"
    requested_capabilities: frozenset[ProviderCapability]


class CapabilityReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str = Field(min_length=1, max_length=64)
    checked_at: AwareUtcDatetime
    confirmed: frozenset[ProviderCapability] = frozenset()
    unavailable: frozenset[ProviderCapability] = frozenset()
    unknown: frozenset[ProviderCapability] = frozenset()
    notes: tuple[str, ...] = ()


PublishEvent = Callable[[DomainEvent], Awaitable[int]]


class MarketDataProvider(ABC):
    """Provider boundary for normalized market events.

    Implementations must probe or explicitly configure entitlement. Documentation
    alone is not treated as proof that an account can use a capability.
    """

    @property
    @abstractmethod
    def descriptor(self) -> ProviderDescriptor: ...

    @abstractmethod
    async def probe_capabilities(self) -> CapabilityReport: ...

    @abstractmethod
    async def run(self, publish: PublishEvent) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...
