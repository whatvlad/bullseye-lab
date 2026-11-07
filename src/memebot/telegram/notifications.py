from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from decimal import Decimal
from time import monotonic
from typing import Any

from aiogram import Bot
from aiogram.types import BufferedInputFile

from memebot.core.logging import get_logger
from memebot.events.models import (
    DomainEvent,
    PaperActionExpired,
    PaperActionPending,
    PaperOrderCompleted,
    ProviderHealthUpdated,
    StrategyDecisionCreated,
)
from memebot.models.paper import PaperOrderStatus
from memebot.models.strategy import StrategyDecisionAction
from memebot.telegram.charts import pnl_text
from memebot.telegram.history import coin_identity, coin_links
from memebot.telegram.views import short_mint

_LAMPORTS_PER_SOL = 1_000_000_000


class TelegramTradeNotifier:
    """Non-blocking, rate-limited paper-trading activity notifications."""

    def __init__(
        self,
        token: str,
        user_ids: frozenset[int],
        *,
        queue_size: int = 200,
        minimum_interval_seconds: float = 1.0,
        duplicate_cooldown_seconds: float = 60.0,
        event_notifications_enabled: bool = True,
        token_lookup: Callable[[str], Awaitable[dict[str, Any] | None]] | None = None,
        chart_lookup: Callable[[str, str], Awaitable[tuple[bytes | None, str] | None]]
        | None = None,
        position_lookup: Callable[[str, str], Awaitable[dict[str, Any] | None]] | None = None,
        fills_only: bool = False,
    ) -> None:
        self._bot = Bot(token=token)
        self._user_ids = user_ids
        self._queue: asyncio.Queue[tuple[str | None, str, str | None]] = asyncio.Queue(
            maxsize=queue_size
        )
        self._token_lookup = token_lookup
        self._chart_lookup = chart_lookup
        self._position_lookup = position_lookup
        self._fills_only = fills_only
        self._minimum_interval = minimum_interval_seconds
        self._duplicate_cooldown = duplicate_cooldown_seconds
        self._event_notifications_enabled = event_notifications_enabled
        self._recent: dict[str, float] = {}
        self._partials: dict[str, PaperOrderCompleted] = {}
        self._task: asyncio.Task[None] | None = None
        self._logger = get_logger("memebot.telegram_notifications")

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="telegram-trade-notifier")
            self.enqueue_text(
                "🟢 Bullseye market worker is online.\n"
                "Use Start trading / Stop trading in the dashboard.\n\n"
                "Paper mode only — no real transaction can be sent."
            )

    def enqueue_event(self, event: DomainEvent) -> None:
        if not self._event_notifications_enabled:
            return
        if self._fills_only and not (
            isinstance(event, PaperOrderCompleted) and event.result.fill is not None
        ):
            return
        formatted = notification_for_event(event)
        if formatted is None:
            return
        dedupe_key, message = formatted
        now = monotonic()
        previous = self._recent.get(dedupe_key)
        if previous is not None and now - previous < self._duplicate_cooldown:
            return
        self._recent[dedupe_key] = now
        chart = None
        if isinstance(event, PaperOrderCompleted) and event.result.fill is not None:
            effect = event.result.position_effect.value
            if effect == "close":
                chart = str(event.portfolio_id)
            elif effect == "partial_close" and self._position_lookup is not None:
                self._partials[str(event.event_id)] = event
                chart = f"partial:{event.event_id}"
        self._enqueue(message, getattr(event, "mint", None), chart)

    def enqueue_text(self, message: str) -> None:
        self._enqueue(message, None)

    def enqueue_signal(self, message: str, mint: str) -> None:
        """Signal-mode alert: always sent (ignores fills-only); name and links are added."""
        self._enqueue(message, mint)

    def _enqueue(self, message: str, mint: str | None, chart: str | None = None) -> None:
        try:
            self._queue.put_nowait((mint, message, chart))
        except asyncio.QueueFull:
            self._logger.warning("telegram_notification_queue_full")

    async def close(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        await self._bot.session.close()

    async def _run(self) -> None:
        while True:
            mint, message, chart = await self._queue.get()
            try:
                photo = None
                if chart and chart.startswith("partial:") and mint and self._position_lookup:
                    partial = self._partials.pop(chart.removeprefix("partial:"), None)
                    try:
                        summary = (
                            await asyncio.wait_for(
                                self._position_lookup(str(partial.portfolio_id), mint), 5
                            )
                            if partial is not None
                            else None
                        )
                    except Exception:
                        summary = None
                    if partial is not None and summary is not None:
                        message = partial_sell_message(partial, summary)
                elif chart and mint and self._chart_lookup:
                    try:
                        rendered = await asyncio.wait_for(self._chart_lookup(chart, mint), 10)
                    except Exception:
                        rendered = None
                    if rendered is not None:
                        # The trade card replaces the plain fill text on a full close.
                        photo, message = rendered
                        mint = None
                if mint and self._token_lookup:
                    try:
                        info = await asyncio.wait_for(self._token_lookup(mint), timeout=2)
                    except Exception:
                        info = None
                    message = message.replace(
                        f"Token: {mint}", "Token: " + coin_identity(mint, info)
                    )
                if mint:
                    message += "\n\n" + coin_links(mint)
                for user_id in self._user_ids:
                    try:
                        if photo is not None:
                            await self._bot.send_photo(
                                user_id,
                                BufferedInputFile(photo, filename="trade.png"),
                                caption=message[:1024],
                            )
                        else:
                            await self._bot.send_message(user_id, message)
                    except Exception as error:
                        self._logger.warning(
                            "telegram_notification_failed",
                            user_id=user_id,
                            error_type=type(error).__name__,
                        )
                await asyncio.sleep(self._minimum_interval)
            finally:
                self._queue.task_done()


def notification_for_event(event: DomainEvent) -> tuple[str, str] | None:
    if isinstance(event, StrategyDecisionCreated):
        return _decision_notification(event)
    if isinstance(event, PaperActionPending):
        action = "paper entry" if event.action == "entry" else "manual paper close"
        return (
            f"pending:{event.action}:{event.mint}",
            "⏳ Waiting for fresh market data\n\n"
            f"Token: {event.mint}\n"
            f"Action: {action}\n"
            "The next fresh trade will trigger execution checks.\n"
            f"Timeout: {event.expires_at.isoformat()}\n\n"
            "No real transaction was created.",
        )
    if isinstance(event, PaperActionExpired):
        action = "paper entry" if event.action == "entry" else "manual paper close"
        follow_up = (
            "A new strategy signal can try again."
            if event.action == "entry"
            else "Refresh Positions and press Close again; force close remains available."
        )
        return (
            f"expired:{event.action}:{event.mint}:{event.event_id}",
            "⌛ Market-data wait expired\n\n"
            f"Token: {event.mint}\n"
            f"Action: {action}\n"
            "Why: no usable fresh pool snapshot arrived before the deadline.\n"
            f"{follow_up}\n\n"
            "No real transaction was created.",
        )
    if isinstance(event, PaperOrderCompleted):
        return _order_notification(event)
    if isinstance(event, ProviderHealthUpdated):
        state = event.state.value.upper()
        detail = f"\nReason: {_humanize(event.error_code)}" if event.error_code else ""
        return (
            f"provider:{event.provider}:{event.state.value}",
            f"🔌 Data provider: {event.provider}\nStatus: {state}{detail}",
        )
    return None


def tracked_wallet_notification(activity: dict[str, Any]) -> str:
    label = activity.get("label") or short_mint(str(activity["wallet"]))
    token = activity.get("symbol") or activity.get("name") or short_mint(str(activity["mint"]))
    side = str(activity["side"]).upper()
    amount = Decimal(str(activity["quote_amount_sol"]))
    realized = activity.get("realized_pnl_sol")
    unrealized = activity.get("unrealized_pnl_sol")
    pnl_lines = []
    if realized is not None:
        pnl_lines.append(f"Observed realized P&L: {Decimal(str(realized)):+,.4f} SOL")
    if unrealized is not None:
        pnl_lines.append(f"Estimated unrealized P&L: {Decimal(str(unrealized)):+,.4f} SOL")
    return (
        f"{'🟢' if side == 'BUY' else '🔴'} Tracked wallet {side}\n\n"
        f"Wallet: {label}\n"
        f"Token: {token}\nMint: {activity['mint']}\n"
        f"Amount: {amount:,.4f} SOL\n"
        + ("\n".join(pnl_lines) + "\n" if pnl_lines else "")
        + f"Time: {activity['occurred_at']}\n"
        f"Transaction: https://solscan.io/tx/{activity['signature']}\n\n"
        "Observation only — Bullseye did not copy this trade."
    )


def _decision_notification(event: StrategyDecisionCreated) -> tuple[str, str] | None:
    if not event.active_strategy or event.action == StrategyDecisionAction.SKIP:
        return None
    action = (
        "paper buy candidate — execution checks started"
        if event.action == StrategyDecisionAction.ENTER_CANDIDATE
        else "watch only — no purchase"
    )
    score = f"{event.score.final_score:.2f}/100" if event.score.final_score is not None else "n/a"
    reasons = "\n".join(f"• {_humanize(item)}" for item in event.reasons[:4])
    components = sorted(
        (item for item in event.score.components if item.score is not None),
        key=lambda item: item.contribution or 0,
        reverse=True,
    )[:3]
    component_text = "\n".join(
        f"• {_humanize(item.name).title()}: {item.score:.1f}/100" for item in components
    )
    message = (
        "📡 Paper-trading decision\n\n"
        f"Token: {event.mint}\n"
        f"Decision: {action}\n"
        f"Strategy: {_humanize(event.strategy_key).title()}\n"
        f"Score: {score}\n"
        f"Market regime: {_humanize(event.regime.value)}\n\n"
        f"Why:\n{reasons or '• No explanation recorded'}"
    )
    if component_text:
        message += f"\n\nStrongest score components:\n{component_text}"
    return f"decision:{event.mint}:{event.action.value}", message


def new_pair_signal(event: StrategyDecisionCreated, risk_warnings: tuple[str, ...] = ()) -> str:
    """Manual-trading signal for a bonding-curve entry candidate (signal mode)."""
    evidence: dict[str, object] = {
        item.code: item.value for component in event.score.components for item in component.evidence
    }

    def number(code: str, digits: int = 1) -> str:
        value = evidence.get(code)
        try:
            return f"{float(str(value)):.{digits}f}"
        except (TypeError, ValueError):
            return "n/a"

    score = f"{event.score.final_score:.0f}" if event.score.final_score is not None else "n/a"
    flags = ", ".join(_humanize(item) for item in risk_warnings) or "none"
    return (
        "🎯 NEW PAIR SIGNAL (bonding curve)\n\n"
        f"Token: {event.mint}\n"
        f"Score {score} · curve {number('bonding_progress_percent', 0)}% · "
        f"{number('trade_count', 0)} trades and {number('price_change_percent')}% in 10 s · "
        f"buy flow {number('flow_imbalance', 2)}\n"
        f"Risk flags: {flags}\n\n"
        "Fast 10-second spike. Auto-trading these lost ~8% per trade in tests: "
        "only buy if the chart and narrative convince you."
    )


def _order_notification(event: PaperOrderCompleted) -> tuple[str, str]:
    result = event.result
    side = result.side.value.upper()
    if result.status == PaperOrderStatus.REJECTED:
        message = (
            "⚠️ Paper order rejected\n\n"
            f"Token: {event.mint}\n"
            f"Action: {side}\n"
            f"Why: {_humanize(result.rejection_reason)}\n"
            "Result: no position change"
        )
        return (
            "order:rejected:"
            f"{event.mint}:{result.side.value}:{result.rejection_reason}:{result.exit_reason}",
            message,
        )
    else:
        fill = result.fill
        assert fill is not None
        sol_amount = fill.gross_quote_amount_raw / _LAMPORTS_PER_SOL
        reason = _humanize(result.exit_reason) if result.exit_reason else "strategy entry signal"
        degraded = ""
        if fill.fill_quality.value == "degraded":
            market_age = next(
                (
                    item.value
                    for item in fill.evidence
                    if item.code == "forced_stale_market_age_seconds"
                ),
                "unknown",
            )
            degraded = (
                f"\nFill quality: DEGRADED (snapshot age: {market_age}s)"
                "\nP&L uses the last known reserves."
            )
        message = (
            f"{'🟢' if side == 'BUY' else '🔴'} Paper {side} filled\n\n"
            f"Token: {event.mint}\n"
            f"Amount: {sol_amount:,.4f} SOL · "
            f"{fill.gross_portfolio_amount:,.2f} {fill.portfolio_currency}\n"
            f"Fees: {fill.total_fee_portfolio:,.2f} {fill.portfolio_currency}\n"
            f"Price impact: {fill.price_impact_bps / 100:.2f}%\n"
            f"Why: {reason}\n"
            f"Position: {_humanize(result.position_effect.value)}\n\n"
            f"Simulated execution only.{degraded}"
        )
    return f"order:{event.event_id}", message


def partial_sell_message(event: PaperOrderCompleted, summary: dict[str, Any]) -> str:
    fill = event.result.fill
    assert fill is not None
    currency = summary["currency"] or fill.portfolio_currency
    remaining = Decimal(str(summary["remaining_tokens"]))
    sold_percent = fill.token_amount_raw / (fill.token_amount_raw + remaining) * 100
    entry = summary.get("entry_price")
    change = f" at {(fill.actual_fill_price_raw / entry - 1) * 100:+.1f}%" if entry else ""
    reason = _humanize(event.result.exit_reason) if event.result.exit_reason else "partial sell"
    realized = Decimal(str(summary["realized_pnl"]))
    sold_cost = fill.gross_portfolio_amount - fill.total_fee_portfolio - realized
    locked = realized / sold_cost * 100 if sold_cost > 0 else None
    sol_price = fill.quote_price_in_portfolio_currency
    return (
        f"🟡 {reason.capitalize()}\n\n"
        f"Token: {event.mint}\n"
        f"Sold: {sold_percent:.0f}% for {fill.gross_portfolio_amount:,.2f} {currency}{change}"
        f" (fee {fill.total_fee_portfolio:,.2f})\n"
        f"Locked profit: {pnl_text(realized, currency, sol_price, locked)}\n"
        f"Still open: {100 - sold_percent:.0f}% · cost "
        f"{Decimal(str(summary['remaining_cost_basis'])):,.2f} {currency}\n\n"
        "Simulated execution only."
    )


def _humanize(value: str | None) -> str:
    if not value:
        return "not recorded"
    head, separator, tail = value.partition(":")
    readable = head.replace("_", " ")
    return f"{readable}: {tail}" if separator else readable
