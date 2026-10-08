from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from memebot.core.clock import utc_now
from memebot.core.config import Settings
from memebot.paper.models import ExecutionMarketSnapshot
from memebot.providers.price.base import QuotePriceProvider
from memebot.providers.price.coingecko import QuotePriceError
from memebot.providers.solana.pump_idl import WRAPPED_SOL_MINT
from memebot.storage.database.models import (
    MarketFeatureSnapshotRecord,
    MarketRecord,
    TokenRecord,
    TokenRiskAssessmentRecord,
    TokenTradeRecord,
)

from .filters import SUPPORTED_PROTOCOLS, TABS, evaluate, load_presets, number


def aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def stage(lifecycle: str) -> str | None:
    if lifecycle in {"new_launch", "bonding_curve"}:
        return "newPairs"
    if lifecycle in {"final_stretch", "graduation"}:
        return "finalStretch"
    if lifecycle in {"post_graduation", "mature"}:
        return "migrated"
    return None


def market_row(
    token: TokenRecord,
    feature: MarketFeatureSnapshotRecord | None,
    trade: TokenTradeRecord | None,
    risk: TokenRiskAssessmentRecord | None,
    *,
    now: datetime,
    sol_usd: Decimal | None,
    max_age: float,
    market_venue: str | None = None,
    market: ExecutionMarketSnapshot | None = None,
) -> dict[str, Any]:
    evidence = {
        item.get("code"): item.get("value")
        for item in (risk.evidence_json if risk else [])
        if item.get("availability") == "available"
    }
    supply = number(evidence.get("mint_supply_raw")) or number(
        (token.metadata_json or {}).get("token_total_supply")
    )
    tab = stage(token.current_lifecycle)
    quote = (
        "sol"
        if trade is not None
        and (trade.quote_mint or trade.quote_asset)
        in {WRAPPED_SOL_MINT, "SOL", "11111111111111111111111111111111"}
        else "unknown"
    )
    price = None
    same_market = trade is not None and trade.market_address == token.current_market
    if trade is not None and same_market and quote == "sol":
        if trade.virtual_token_reserves and trade.virtual_quote_reserves:
            price = Decimal(trade.virtual_quote_reserves) / Decimal(trade.virtual_token_reserves)
        elif trade.real_token_reserves and trade.real_quote_reserves:
            price = Decimal(
                trade.real_quote_reserves + (trade.virtual_quote_reserves or 0)
            ) / Decimal(trade.real_token_reserves)
    age = (now - aware(trade.source_event_at)).total_seconds() if trade else None
    liquidity = trade.real_quote_reserves if trade and same_market else None
    if market is not None and market.mint == token.mint:
        tab = stage(market.lifecycle.value)
        market_venue = market.venue.value
        quote = "sol" if market.quote_asset == WRAPPED_SOL_MINT else "unknown"
        price = market.observed_price_raw if market.observed_price_raw > 0 else None
        age = (now - aware(market.observed_at)).total_seconds()
        liquidity = market.real_quote_reserves_raw
    stale = price is None or age is None or not 0 <= age <= max_age
    dollars = sol_usd / Decimal(1_000_000_000) if sol_usd is not None and quote == "sol" else None
    window = (
        next((item for item in feature.windows_json if item.get("window_seconds") == 300), {})
        if feature
        else {}
    )
    if feature is None or (now - aware(feature.observed_at)).total_seconds() > max_age:
        window = {}
    volume = number(window.get("total_volume_quote_raw"))
    return {
        "mint": token.mint,
        "name": token.name,
        "symbol": token.symbol,
        "tab": tab,
        "protocol": "pumpAmm"
        if market_venue == "pump_swap"
        else "pump"
        if market_venue == "pump_fun"
        else "unknown",
        "quote": quote,
        "stale": stale,
        "data_age_seconds": age,
        "age": Decimal(
            str((now - aware(token.source_created_at or token.first_seen_at)).total_seconds())
        )
        / 60,
        "marketCap": price * supply * dollars
        if price is not None and supply is not None and dollars is not None and not stale
        else None,
        "liquidity": Decimal(liquidity) * dollars
        if liquidity is not None and dollars is not None and not stale
        else None,
        "volume": volume * dollars if volume is not None and dollars is not None else None,
        "txns": window.get("trade_count"),
        "numBuys": window.get("buy_count"),
        "numSells": window.get("sell_count"),
        "top10Holders": number(evidence.get("top10_holder_percent")),
        "devHolding": number(evidence.get("creator_holding_percent")),
        "bondingCurve": feature.bonding_progress_percent if feature and not stale else None,
        "risk_allowed": risk.allowed if risk else None,
        "risk_reasons": (risk.hard_reject_reasons + risk.critical_unknowns)
        if risk
        else ["risk_not_assessed"],
        "source": "observed Pump/PumpSwap reserves + RPC supply + SOL/USD",
    }


class PulseService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        settings: Settings,
        quotes: QuotePriceProvider,
    ) -> None:
        self._sessions = sessions
        self._settings = settings
        self._quotes = quotes
        self.presets = load_presets(settings.pulse_presets_file)

    async def snapshot(
        self, *, mint: str | None = None, market: ExecutionMarketSnapshot | None = None
    ) -> dict[str, Any]:
        now = utc_now()
        sol_usd = None
        try:
            quote = await self._quotes.quote_price("USD")
            if (
                0
                <= (now - aware(quote.provenance.observed_at)).total_seconds()
                <= self._settings.paper_max_quote_price_staleness_seconds
            ):
                sol_usd = quote.price
        except QuotePriceError:
            pass
        async with self._sessions() as session:
            feature_id = (
                select(MarketFeatureSnapshotRecord.event_id)
                .where(
                    MarketFeatureSnapshotRecord.token_id == TokenRecord.id,
                    MarketFeatureSnapshotRecord.observed_at <= now,
                )
                .order_by(MarketFeatureSnapshotRecord.observed_at.desc())
                .limit(1)
                .correlate(TokenRecord)
                .scalar_subquery()
            )
            trade_id = (
                select(TokenTradeRecord.event_id)
                .where(
                    TokenTradeRecord.token_id == TokenRecord.id,
                    TokenTradeRecord.source_event_at <= now,
                )
                .order_by(TokenTradeRecord.source_event_at.desc())
                .limit(1)
                .correlate(TokenRecord)
                .scalar_subquery()
            )
            query = (
                select(
                    TokenRecord,
                    MarketFeatureSnapshotRecord,
                    TokenTradeRecord,
                    TokenRiskAssessmentRecord,
                    MarketRecord.venue,
                )
                .outerjoin(
                    MarketFeatureSnapshotRecord, MarketFeatureSnapshotRecord.event_id == feature_id
                )
                .outerjoin(TokenTradeRecord, TokenTradeRecord.event_id == trade_id)
                .outerjoin(MarketRecord, MarketRecord.address == TokenRecord.current_market)
                .outerjoin(
                    TokenRiskAssessmentRecord,
                    TokenRiskAssessmentRecord.event_id == TokenRecord.risk_assessment_event_id,
                )
            )
            if mint:
                query = query.where(TokenRecord.mint == mint)
            else:
                query = query.where(TokenRecord.last_seen_at >= now - timedelta(hours=24))
            records = (
                await session.execute(query.order_by(TokenRecord.last_seen_at.desc()).limit(301))
            ).all()
        groups: dict[str, list[dict[str, Any]]] = {tab: [] for tab in TABS}
        rejected: dict[str, list[dict[str, Any]]] = {tab: [] for tab in TABS}
        for token, feature, trade, risk, venue in records[:300]:
            row = market_row(
                token,
                feature,
                trade,
                risk,
                now=now,
                sol_usd=sol_usd,
                max_age=self._settings.pulse_max_data_age_seconds,
                market_venue=venue,
                market=market,
            )
            tab = row["tab"]
            if tab not in groups:
                continue
            result = evaluate(self.presets[tab], row)
            row["filter_reasons"] = result.reasons
            (groups if result.matched else rejected)[tab].append(row)
        unsupported = sorted(
            {
                key
                for preset in self.presets.values()
                for key, enabled in preset["filters"].get("protocols", {}).items()
                if enabled and key not in SUPPORTED_PROTOCOLS
            }
        )
        return {
            "observed_at": now.isoformat(),
            "groups": groups,
            "rejected": rejected,
            "unsupported_protocols": unsupported,
            "sol_usd": sol_usd,
            "scanned": min(len(records), 300),
            "truncated": len(records) > 300,
            "window_seconds": 300,
        }

    async def entry_rejection(
        self, mint: str, *, market: ExecutionMarketSnapshot | None = None
    ) -> str | None:
        snapshot = await self.snapshot(mint=mint, market=market)
        for tab in TABS:
            if snapshot["groups"][tab]:
                return None
            if snapshot["rejected"][tab]:
                return "pulse:" + str(snapshot["rejected"][tab][0]["filter_reasons"][0])
        return "pulse:stage_or_market_unavailable"
