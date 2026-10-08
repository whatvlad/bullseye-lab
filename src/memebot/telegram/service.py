from __future__ import annotations

from decimal import Decimal
from typing import Any

from memebot.core.config import Settings
from memebot.events.models import PaperOrderCompleted
from memebot.paper.manual import ManualPaperTradingService
from memebot.providers.birdeye.client import BirdeyeError
from memebot.providers.birdeye.market import BirdeyeMarketDataProvider
from memebot.providers.price.base import QuotePriceProvider
from memebot.providers.price.coingecko import QuotePriceError
from memebot.pulse.service import PulseService
from memebot.storage.database.control import ControlRepository, TradingControlSnapshot
from memebot.storage.database.outcomes import OutcomeRecorder
from memebot.storage.database.pending import PendingPaperAction
from memebot.storage.database.registry import TokenRegistry
from memebot.storage.database.wallets import WalletIntelligenceRepository
from memebot.strategies.presets import initial_strategy_presets


class TelegramControlService:
    """Telegram-facing application service; handlers contain no trading logic."""

    def __init__(
        self,
        settings: Settings,
        registry: TokenRegistry,
        controls: ControlRepository,
        manual_trading: ManualPaperTradingService,
        quote_prices: QuotePriceProvider,
        outcomes: OutcomeRecorder,
        wallets: WalletIntelligenceRepository,
        birdeye: BirdeyeMarketDataProvider | None = None,
        pulse: PulseService | None = None,
    ) -> None:
        self._settings = settings
        self._registry = registry
        self._controls = controls
        self._manual = manual_trading
        self._quote_prices = quote_prices
        self._outcomes = outcomes
        self._wallets = wallets
        self._birdeye = birdeye
        self._pulse = pulse

    async def pulse(self) -> dict[str, Any] | None:
        return await self._pulse.snapshot() if self._pulse is not None else None

    async def initialize(self) -> None:
        presets = initial_strategy_presets()
        active = next(item for item in presets if item.active_for_execution)
        await self._registry.ensure_strategy_configurations(presets)
        await self._registry.ensure_default_paper_portfolio(
            initial_cash=self._settings.starting_capital,
            currency=self._settings.starting_capital_currency,
        )
        await self._controls.ensure(
            active_strategy_key=active.key,
            base_position_percent=self._settings.paper_base_position_percent,
            max_position_percent=self._settings.paper_max_position_percent,
            max_open_positions=self._settings.paper_max_open_positions,
            stop_loss_percent=self._settings.paper_stop_loss_percent,
            take_profit_percent=self._settings.paper_take_profit_percent,
            trailing_stop_percent=self._settings.paper_trailing_stop_percent,
            max_holding_seconds=self._settings.paper_max_holding_seconds,
        )

    async def dashboard(self) -> dict[str, Any]:
        provider_health = await self._registry.provider_health()
        if self._settings.pumpportal_api_key is not None:
            provider_health = [
                item for item in provider_health if item["provider"] != "solana_rpc_pump"
            ]
        return {
            "portfolio": await self._portfolio_report(),
            "control": await self._controls.get(),
            "provider_health": provider_health,
        }

    async def portfolio(self) -> dict[str, Any] | None:
        return await self._portfolio_report()

    async def paper_history(self, page: int = 0) -> dict[str, Any]:
        return await self._registry.paper_history(page)

    async def paper_position_history(
        self, position_id: str, page: int = 0
    ) -> dict[str, Any] | None:
        return await self._registry.paper_position_history(position_id, page)

    async def paper_history_csv(self) -> bytes:
        return await self._registry.paper_history_csv()

    async def paper_history_archive(self) -> bytes:
        return await self._registry.paper_history_archive()

    async def _portfolio_report(self) -> dict[str, Any] | None:
        report = await self._registry.paper_portfolio_report()
        if report is None:
            return None
        try:
            sol_in_currency = await self._quote_prices.quote_price(report["currency"])
            sol_in_usd = await self._quote_prices.quote_price("USD")
        except QuotePriceError as error:
            report["display_rate_error"] = str(error)
        else:
            report["display_rates"] = {
                "sol_in_portfolio_currency": str(sol_in_currency.price),
                "sol_usd": str(sol_in_usd.price),
                "observed_at": sol_in_usd.provenance.observed_at.isoformat(),
            }
        return report

    async def create_portfolio(self, capital: Decimal) -> dict[str, Any]:
        if capital <= 0 or capital > Decimal("1000000000"):
            raise ValueError("capital_out_of_range")
        snapshot = await self._registry.create_paper_portfolio(
            name=f"Telegram paper {capital}",
            initial_cash=capital,
            currency=self._settings.starting_capital_currency,
            settings_snapshot=self._settings.safe_summary(),
        )
        return {
            "portfolio_id": str(snapshot.portfolio_id),
            "currency": snapshot.currency,
            "initial_cash": str(snapshot.initial_cash),
            "cash_balance": str(snapshot.cash_balance),
        }

    async def strategies(self) -> list[dict[str, Any]]:
        return await self._registry.strategy_configurations()

    async def strategy_comparison(self) -> list[dict[str, Any]]:
        return await self._controls.strategy_comparison()

    async def select_strategy(self, key: str, *, user_id: int) -> TradingControlSnapshot:
        return await self._controls.set_active_strategy(key, user_id=user_id)

    async def signals(self) -> list[dict[str, Any]]:
        return await self._controls.latest_signals(limit=10)

    async def outcome_summary(self) -> dict[str, Any]:
        return await self._outcomes.summary()

    async def daily_journal(self) -> dict[str, Any]:
        report = await self._outcomes.daily_report()
        report["alpha_candidates"] = await self._registry.latest_alpha_filter_snapshots(limit=5)
        return report

    async def wallets(self) -> list[dict[str, Any]]:
        return await self._wallets.ranked_wallets(limit=20)

    async def wallet(self, address: str) -> dict[str, Any] | None:
        return await self._wallets.wallet_report(address)

    async def set_wallet_seed(
        self, address: str, *, enabled: bool, label: str | None = None
    ) -> dict[str, Any]:
        return await self._wallets.set_seed(address, enabled=enabled, label=label)

    async def set_paused(self, paused: bool, *, user_id: int) -> TradingControlSnapshot:
        return await self._controls.set_paused(paused, user_id=user_id)

    async def settings(self) -> TradingControlSnapshot:
        control = await self._controls.get()
        if control is None:
            raise RuntimeError("trading_control_not_initialized")
        return control

    async def update_risk(
        self, field: str, value: Decimal, *, user_id: int
    ) -> TradingControlSnapshot:
        if field == "stop_loss":
            return await self._controls.update_risk(stop_loss_percent=value, user_id=user_id)
        if field == "take_profit":
            return await self._controls.update_risk(take_profit_percent=value, user_id=user_id)
        if field == "trailing_stop":
            return await self._controls.update_risk(trailing_stop_percent=value, user_id=user_id)
        if field == "max_positions":
            if value != value.to_integral_value():
                raise ValueError("max_positions_must_be_integer")
            return await self._controls.update_risk(max_open_positions=int(value), user_id=user_id)
        raise ValueError("unknown_risk_setting")

    async def update_sizing(
        self, base: Decimal, maximum: Decimal, *, user_id: int
    ) -> TradingControlSnapshot:
        return await self._controls.update_sizing(
            base_position_percent=base,
            max_position_percent=maximum,
            user_id=user_id,
        )

    async def manual_buy(self, mint: str, amount: Decimal, *, user_id: int) -> dict[str, Any]:
        return (await self._manual.buy(mint, amount, user_id=user_id)).model_dump(mode="json")

    async def manual_sell(
        self, mint: str, *, user_id: int, force_stale: bool = False
    ) -> dict[str, Any]:
        result = await self._manual.sell(mint, user_id=user_id, force_stale=force_stale)
        if isinstance(result, PaperOrderCompleted):
            return result.model_dump(mode="json")
        assert isinstance(result, PendingPaperAction)
        return {
            "kind": "pending_paper_action",
            "action_id": str(result.id),
            "action": result.action,
            "status": "waiting_for_fresh_market",
            "mint": result.mint,
            "expires_at": result.expires_at.isoformat(),
        }

    async def close_all_positions(
        self, *, user_id: int, force_stale: bool = False
    ) -> dict[str, Any]:
        await self._controls.set_paused(True, user_id=user_id)
        report = await self._registry.paper_portfolio_report()
        positions = [] if report is None else report.get("positions") or []
        filled = 0
        pending = 0
        failed = 0
        for position in positions:
            try:
                result = await self._manual.sell(
                    str(position["mint"]),
                    user_id=user_id,
                    force_stale=force_stale,
                )
            except (ValueError, RuntimeError):
                failed += 1
            else:
                if isinstance(result, PaperOrderCompleted):
                    if result.result.status.value == "filled":
                        filled += 1
                    else:
                        failed += 1
                else:
                    pending += 1
        return {
            "total": len(positions),
            "filled": filled,
            "pending": pending,
            "failed": failed,
            "force_stale": force_stale,
        }

    async def set_token_control(
        self,
        kind: str,
        mint: str,
        enabled: bool,
        *,
        user_id: int,
    ) -> None:
        if kind == "watchlist":
            await self._controls.set_token_control(mint, watchlisted=enabled, user_id=user_id)
            return
        if kind == "blacklist":
            await self._controls.set_token_control(
                mint,
                blacklisted=enabled,
                reason="Telegram operator control" if enabled else None,
                user_id=user_id,
            )
            return
        raise ValueError("unknown_token_control_kind")

    async def token_controls(self, kind: str) -> list[dict[str, Any]]:
        return await self._controls.token_controls(kind=kind)

    async def token_detail(self, mint: str) -> dict[str, Any]:
        local = await self._registry.inspect_token(mint)
        result: dict[str, Any] = {"local": local, "birdeye": None}
        if self._birdeye is not None:
            try:
                market = await self._birdeye.token_snapshot(mint)
            except BirdeyeError as error:
                result["birdeye_error"] = error.code
            else:
                result["birdeye"] = {
                    "price_usd": str(market.price_usd) if market.price_usd is not None else None,
                    "liquidity_usd": (
                        str(market.liquidity_usd) if market.liquidity_usd is not None else None
                    ),
                    "market_cap_usd": (
                        str(market.market_cap_usd) if market.market_cap_usd is not None else None
                    ),
                    "volume_24h_usd": (
                        str(market.volume_24h_usd) if market.volume_24h_usd is not None else None
                    ),
                    "observed_at": market.observed_at,
                    "provider": market.provider,
                }
        return result

    async def close(self) -> None:
        await self._manual.close()
        if self._birdeye is not None:
            await self._birdeye.close()
