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
    ) -> None:
        self._bot = Bot(token=token)
        self._user_ids = user_ids
        self._queue: asyncio.Queue[tuple[str | None, str, str | None]] = asyncio.Queue(
            maxsize=queue_size
        )
        self._token_lookup = token_lookup
        self._chart_lookup = chart_lookup
        self._minimum_interval = minimum_interval_seconds
        self._duplicate_cooldown = duplicate_cooldown_seconds
        self._event_notifications_enabled = event_notifications_enabled
        self._recent: dict[str, float] = {}
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
        formatted = notification_for_event(event)
        if formatted is None:
            return
        dedupe_key, message = formatted
        now = monotonic()
        previous = self._recent.get(dedupe_key)
        if previous is not None and now - previous < self._duplicate_cooldown:
            return
        self._recent[dedupe_key] = now
        chart = (
            str(event.portfolio_id)
            if isinstance(event, PaperOrderCompleted)
            and event.result.fill is not None
            and event.result.position_effect.value == "close"
            else None
        )
        self._enqueue(message, getattr(event, "mint", None), chart)

    def enqueue_text(self, message: str) -> None:
        self._enqueue(message, None)

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
                if chart and mint and self._chart_lookup:
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


def _humanize(value: str | None) -> str:
    if not value:
        return "not recorded"
    head, separator, tail = value.partition(":")
    readable = head.replace("_", " ")
    return f"{readable}: {tail}" if separator else readable
