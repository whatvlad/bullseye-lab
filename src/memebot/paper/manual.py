from __future__ import annotations

import asyncio
from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

from memebot.core.clock import utc_now
from memebot.core.config import Settings
from memebot.events.models import PaperOrderCompleted
from memebot.models.market import LaunchVenue, MarketLifecycle
from memebot.models.paper import (
    PaperOrderResult,
    PaperOrderSide,
    PaperOrderStatus,
    PositionEffect,
)
from memebot.providers.price.base import QuotePriceProvider
from memebot.providers.price.coingecko import QuotePriceError
from memebot.providers.solana.pump_idl import WRAPPED_SOL_MINT
from memebot.storage.database.control import ControlRepository
from memebot.storage.database.outcomes import OutcomeRecorder
from memebot.storage.database.pending import (
    PendingPaperAction,
    PendingPaperActionRepository,
)
from memebot.storage.database.registry import TokenRegistry

from .execution import ExecutionPolicy, PaperFillSimulator
from .market_refresh import MarketSnapshotRefresher
from .models import ExecutionMarketSnapshot, PortfolioSnapshot
from .price_safety import entry_data_block, with_price_evidence
from .risk_governor import PortfolioRiskGovernor


class ManualPaperTradingService:
    """Operator-requested paper orders; no signer, transaction, or live adapter exists."""

    def __init__(
        self,
        settings: Settings,
        registry: TokenRegistry,
        controls: ControlRepository,
        quote_prices: QuotePriceProvider,
        outcomes: OutcomeRecorder,
        pending: PendingPaperActionRepository,
        market_refresher: MarketSnapshotRefresher | None = None,
        exit_market_refresher: MarketSnapshotRefresher | None = None,
        *,
        require_atomic_pump_state: bool = False,
    ) -> None:
        self._registry = registry
        self._controls = controls
        self._quote_prices = quote_prices
        self._outcomes = outcomes
        self._pending = pending
        self._market_refresher = market_refresher
        self._exit_market_refresher = exit_market_refresher or market_refresher
        self._settings = settings
        self._pending_close_ttl_seconds = settings.paper_pending_close_ttl_seconds
        self._entry_lock = asyncio.Lock()
        self._minimum_order_amount = settings.paper_min_order_amount
        self._execution_seconds = (
            settings.paper_compute_latency_ms + settings.paper_submission_latency_ms
        ) / 1000
        self._risk_governor = PortfolioRiskGovernor(settings, registry)
        self._simulator = PaperFillSimulator(
            ExecutionPolicy(
                venue_fee_bps=settings.paper_venue_fee_bps,
                latency_slippage_bps=settings.paper_latency_slippage_bps,
                network_fee_sol=settings.paper_network_fee_sol,
                priority_fee_sol=settings.paper_priority_fee_sol,
                compute_latency_ms=settings.paper_compute_latency_ms,
                submission_latency_ms=settings.paper_submission_latency_ms,
                max_market_staleness_seconds=settings.paper_max_market_staleness_seconds,
                max_quote_price_staleness_seconds=(
                    settings.paper_max_quote_price_staleness_seconds
                ),
                execution_provider_fee_bps=settings.paper_execution_provider_fee_bps,
                require_atomic_pump_state=require_atomic_pump_state,
                additional_slippage_bps=settings.paper_additional_slippage_bps,
                adverse_fill_bps=settings.paper_adverse_fill_bps,
            )
        )

    async def buy(self, mint: str, amount: Decimal, *, user_id: int) -> PaperOrderCompleted:
        async with self._entry_lock:
            return await self._buy(mint, amount, user_id=user_id)

    async def _buy(self, mint: str, amount: Decimal, *, user_id: int) -> PaperOrderCompleted:
        if amount <= 0:
            raise ValueError("paper_amount_must_be_positive")
        portfolio = await self._required_portfolio()
        control = await self._controls.get()
        if control is None:
            raise RuntimeError("trading_control_not_initialized")
        market = await self._registry.paper_market_context(mint, as_of=utc_now())
        scope_block = entry_data_block(market, utc_now(), self._settings) if market else None
        if market is not None and scope_block is None:
            market = await self._refresh_market(market)
        result: PaperOrderResult
        if scope_block is not None:
            result = _rejection(PaperOrderSide.BUY, amount, scope_block)
        elif amount < self._minimum_order_amount:
            result = _rejection(PaperOrderSide.BUY, amount, "order_below_minimum_amount")
        elif await self._controls.is_blacklisted(mint):
            result = _rejection(PaperOrderSide.BUY, amount, "token_blacklisted")
        elif await self._registry.open_position(mint) is not None:
            result = _rejection(PaperOrderSide.BUY, amount, "position_already_open")
        elif portfolio.open_position_count >= control.max_open_positions:
            result = _rejection(PaperOrderSide.BUY, amount, "maximum_open_positions_reached")
        elif not await self._risk_allows(mint):
            result = _rejection(PaperOrderSide.BUY, amount, "risk_gate_not_approved")
        elif market is None:
            result = _rejection(PaperOrderSide.BUY, amount, "market_state_unavailable")
        elif market.quote_asset != WRAPPED_SOL_MINT:
            result = _rejection(PaperOrderSide.BUY, amount, "unsupported_quote_asset")
        else:
            risk_assessment = await self._risk_governor.assess_entry(mint, amount, as_of=utc_now())
            if not risk_assessment.allowed:
                result = _rejection(
                    PaperOrderSide.BUY,
                    amount,
                    risk_assessment.rejection_reason or "portfolio_risk_gate_rejected",
                )
            else:
                result = await self._simulate_buy(market, portfolio, amount)
        event = _event(
            portfolio=portfolio,
            mint=mint,
            market=market,
            strategy_key=control.active_strategy_key,
            result=result,
            user_id=user_id,
        )
        if await self._registry.handle(event):
            await self._outcomes.handle(event)
        return event

    async def sell(
        self, mint: str, *, user_id: int, force_stale: bool = False
    ) -> PaperOrderCompleted | PendingPaperAction:
        portfolio = await self._required_portfolio()
        control = await self._controls.get()
        if control is None:
            raise RuntimeError("trading_control_not_initialized")
        position = await self._registry.open_position(mint)
        if position is None:
            raise ValueError("open_position_not_found")
        market = await self._registry.paper_market_context(mint, as_of=utc_now())
        if market is not None:
            market = await self._refresh_market(market, for_exit=True)
        requested = max(position.remaining_cost_basis, Decimal("0.00000001"))
        if market is None:
            result = _rejection(PaperOrderSide.SELL, requested, "market_state_unavailable")
        elif market.quote_asset != WRAPPED_SOL_MINT:
            result = _rejection(PaperOrderSide.SELL, requested, "unsupported_quote_asset")
        else:
            try:
                quote = await self._quote_prices.quote_price(portfolio.currency)
            except QuotePriceError:
                result = _rejection(PaperOrderSide.SELL, requested, "quote_price_unavailable")
            else:
                decision_at = utc_now()
                market = replace(market, decision_price=market.observed_price_raw)
                await asyncio.sleep(self._execution_seconds)
                market = await self._refresh_market(market, for_exit=True)
                result = self._simulator.simulate_sell(
                    market,
                    quote,
                    token_amount_raw=position.token_quantity_raw,
                    position_effect=PositionEffect.CLOSE,
                    exit_reason=("manual_paper_force_sell" if force_stale else "manual_paper_sell"),
                    signal_at=market.observed_at,
                    decision_at=decision_at,
                    executed_at=utc_now(),
                    allow_stale_market=force_stale,
                )
        if result.rejection_reason == "market_snapshot_stale" and not force_stale:
            return await self._pending.enqueue(
                portfolio_id=portfolio.portfolio_id,
                mint=mint,
                action="manual_close",
                ttl_seconds=self._pending_close_ttl_seconds,
                requested_by_user_id=user_id,
            )
        event = _event(
            portfolio=portfolio,
            mint=mint,
            market=market,
            strategy_key=position.strategy_key,
            result=result,
            user_id=user_id,
        )
        if await self._registry.handle(event):
            await self._outcomes.handle(event)
        if force_stale and result.status == PaperOrderStatus.FILLED:
            await self._pending.cancel_manual_close(portfolio.portfolio_id, mint)
        return event

    async def _simulate_buy(
        self,
        market: ExecutionMarketSnapshot,
        portfolio: PortfolioSnapshot,
        amount: Decimal,
    ) -> PaperOrderResult:
        if amount > portfolio.cash_balance:
            return _rejection(PaperOrderSide.BUY, amount, "portfolio_cash_insufficient")
        try:
            quote = await self._quote_prices.quote_price(portfolio.currency)
        except QuotePriceError:
            return _rejection(PaperOrderSide.BUY, amount, "quote_price_unavailable")
        decision_at = utc_now()
        market = replace(market, decision_price=market.observed_price_raw)
        data_block = entry_data_block(market, decision_at, self._settings)
        if data_block is not None:
            return _rejection(PaperOrderSide.BUY, amount, data_block)
        await asyncio.sleep(self._execution_seconds)
        market = await self._refresh_market(market)
        data_block = entry_data_block(market, utc_now(), self._settings)
        if data_block is not None:
            return _rejection(PaperOrderSide.BUY, amount, data_block)
        result = self._simulator.simulate_buy(
            market,
            quote,
            requested_portfolio_amount=amount,
            signal_at=market.observed_at,
            decision_at=decision_at,
            executed_at=utc_now(),
        )
        if result.fill is not None:
            non_curve_fees = (
                (result.fill.network_fee_quote_raw + result.fill.execution_provider_fee_quote_raw)
                / Decimal(1_000_000_000)
                * quote.price
            )
            if result.fill.gross_portfolio_amount + non_curve_fees > portfolio.cash_balance:
                return _rejection(
                    PaperOrderSide.BUY,
                    amount,
                    "portfolio_cash_insufficient_for_fees",
                )
        return result

    async def _risk_allows(self, mint: str) -> bool:
        records = await self._registry.latest_risk(mint, limit=1)
        return bool(records and records[0]["allowed"] is True)

    async def _required_portfolio(self) -> PortfolioSnapshot:
        portfolio = await self._registry.active_paper_portfolio()
        if portfolio is None:
            raise RuntimeError("active_paper_portfolio_not_found")
        return portfolio

    async def _refresh_market(
        self, market: ExecutionMarketSnapshot, *, for_exit: bool = False
    ) -> ExecutionMarketSnapshot:
        refresher = self._exit_market_refresher if for_exit else self._market_refresher
        if refresher is None:
            return market
        return await refresher.refresh(market)

    async def close(self) -> None:
        await self._quote_prices.close()


def _event(
    *,
    portfolio: PortfolioSnapshot,
    mint: str,
    market: ExecutionMarketSnapshot | None,
    strategy_key: str,
    result: PaperOrderResult,
    user_id: int,
) -> PaperOrderCompleted:
    now = utc_now()
    result = with_price_evidence(result, market, now)
    trigger_id = uuid4()
    return PaperOrderCompleted(
        event_id=uuid4(),
        provider="bullseye_telegram_manual_paper",
        source_event_at=result.fill.filled_at if result.fill is not None else now,
        correlation_id=trigger_id,
        source_slot=market.source_slot if market is not None else None,
        portfolio_id=portfolio.portfolio_id,
        mint=mint,
        trigger_event_id=trigger_id,
        strategy_key=strategy_key,
        market=market.market if market is not None else None,
        venue=market.venue if market is not None else LaunchVenue.UNKNOWN,
        lifecycle=(market.lifecycle if market is not None else MarketLifecycle.UNKNOWN),
        result=result,
    )


def _rejection(side: PaperOrderSide, amount: Decimal, reason: str) -> PaperOrderResult:
    return PaperOrderResult(
        side=side,
        status=PaperOrderStatus.REJECTED,
        position_effect=PositionEffect.NONE,
        requested_portfolio_amount=max(amount, Decimal("0.00000001")),
        rejection_reason=reason,
    )
