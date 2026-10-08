from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from memebot.models.common import ProviderProvenance


class QuotePrice(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    quote_asset: str = Field(min_length=1, max_length=44)
    portfolio_currency: str = Field(min_length=3, max_length=8)
    price: Decimal = Field(gt=0)
    provenance: ProviderProvenance


class QuotePriceProvider(Protocol):
    async def quote_price(self, portfolio_currency: str) -> QuotePrice: ...

    async def close(self) -> None: ...
