from __future__ import annotations

from decimal import Decimal

from aiogram import Dispatcher, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardMarkup, Message

from memebot.pulse.views import pulse_keyboard, pulse_view
from memebot.telegram.access import AllowlistMiddleware
from memebot.telegram.history import detail_keyboard, detail_view, history_keyboard, history_view
from memebot.telegram.keyboards import (
    back_keyboard,
    confirm_close_all_keyboard,
    confirm_close_keyboard,
    dashboard_keyboard,
    manual_keyboard,
    pending_close_keyboard,
    portfolio_keyboard,
    positions_keyboard,
    settings_keyboard,
    strategy_keyboard,
    token_control_keyboard,
    wallets_keyboard,
)
from memebot.telegram.service import TelegramControlService
from memebot.telegram.views import (
    close_all_confirmation,
    close_all_result_view,
    comparison_view,
    daily_journal_view,
    dashboard_view,
    manual_result_view,
    outcomes_view,
    parse_decimal,
    portfolio_view,
    position_close_confirmation,
    positions_view,
    settings_view,
    signals_view,
    strategies_view,
    token_controls_view,
    wallet_detail_view,
    wallets_view,
)


class OperatorInput(StatesGroup):
    waiting = State()


def build_dispatcher(
    service: TelegramControlService, *, allowed_user_ids: frozenset[int]
) -> Dispatcher:
    dispatcher = Dispatcher()
    public = Router(name="telegram_public")
    protected = Router(name="telegram_protected")
    protected.message.middleware(AllowlistMiddleware(allowed_user_ids))
    protected.callback_query.middleware(AllowlistMiddleware(allowed_user_ids))

    @public.message(Command("whoami"))
    async def whoami(message: Message) -> None:
        user_id = message.from_user.id if message.from_user is not None else None
        await message.answer(f"Your Telegram user ID: {user_id}")

    @protected.message(CommandStart())
    async def start(message: Message) -> None:
        await _send_dashboard(message, service)

    @protected.message(Command("cancel"))
    async def cancel(message: Message, state: FSMContext) -> None:
        await state.clear()
        await _send_dashboard(message, service)

    @protected.message(Command("history"))
    async def history_command(message: Message) -> None:
        payload = await service.paper_history()
        await message.answer(
            history_view(payload), reply_markup=history_keyboard(payload), parse_mode=None
        )

    @protected.callback_query(F.data.startswith("history:"))
    async def history_navigation(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        await query.answer()
        if parts == ["history", "export"]:
            if isinstance(query.message, Message):
                await query.message.answer_document(
                    BufferedInputFile(
                        await service.paper_history_archive(), filename="bullseye_paper_history.zip"
                    ),
                    caption="Вся история PAPER: positions.csv — позиции и PnL; "
                    "orders.csv — исполнения и отклонённые заявки.",
                )
        elif len(parts) == 3 and parts[1] == "chart" and isinstance(query.message, Message):
            card = await service.position_card(parts[2])
            if card is None:
                await query.message.answer("Позиция не найдена.")
            elif card[0] is None:
                await query.message.answer(card[1], parse_mode=None)
            else:
                await query.message.answer_photo(
                    BufferedInputFile(card[0], filename="trade.png"), caption=card[1][:1024]
                )
        elif len(parts) == 3 and parts[1] == "page" and parts[2].isdigit():
            payload = await service.paper_history(int(parts[2]))
            await _edit(query, history_view(payload), history_keyboard(payload))
        elif len(parts) == 4 and parts[1] == "coin" and parts[3].isdigit():
            detail = await service.paper_position_history(parts[2], int(parts[3]))
            if detail is None:
                await _edit(query, "Позиция не найдена.", back_keyboard())
            else:
                await _edit(query, detail_view(detail), detail_keyboard(detail))

    @protected.message(Command("pulse"))
    async def pulse_command(message: Message) -> None:
        await message.answer(
            pulse_view(await service.pulse()), reply_markup=pulse_keyboard(), parse_mode=None
        )

    @protected.callback_query(F.data.startswith("pulse:"))
    async def pulse_navigation(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        if (
            len(parts) != 3
            or parts[1] not in {"all", "newPairs", "finalStretch", "migrated"}
            or not parts[2].isdigit()
        ):
            await query.answer("Некорректный список")
            return
        await query.answer()
        tab, page = parts[1], min(int(parts[2]), 100)
        await _edit(query, pulse_view(await service.pulse(), tab, page), pulse_keyboard(tab, page))

    @protected.callback_query(F.data.startswith("nav:"))
    async def navigation(query: CallbackQuery) -> None:
        target = (query.data or "").split(":", maxsplit=1)[1]
        if target == "dashboard":
            payload = await service.dashboard()
            control = payload["control"]
            paused = bool(control and control.entries_paused)
            await _edit(query, dashboard_view(payload), dashboard_keyboard(paused))
        elif target == "portfolio":
            await _edit(query, portfolio_view(await service.portfolio()), portfolio_keyboard())
        elif target == "positions":
            portfolio = await service.portfolio()
            positions = [] if portfolio is None else portfolio.get("positions") or []
            await _edit(query, positions_view(portfolio), positions_keyboard(positions))
        elif target == "strategies":
            await _edit(
                query,
                strategies_view(await service.strategies(), await service.settings()),
                strategy_keyboard(),
            )
        elif target == "comparison":
            await _edit(
                query,
                comparison_view(await service.strategy_comparison()),
                back_keyboard("strategies"),
            )
        elif target == "signals":
            await _edit(query, signals_view(await service.signals()), back_keyboard())
        elif target == "outcomes":
            await _edit(query, outcomes_view(await service.outcome_summary()), back_keyboard())
        elif target == "journal":
            await _edit(query, daily_journal_view(await service.daily_journal()), back_keyboard())
        elif target == "wallets":
            wallets = await service.wallets()
            await _edit(query, wallets_view(wallets), wallets_keyboard(wallets))
        elif target == "manual":
            await _edit(
                query,
                "🧾 Manual paper trading\n\nAll orders remain simulated.",
                manual_keyboard(),
            )
        elif target in {"watchlist", "blacklist"}:
            await _edit(
                query,
                token_controls_view(target, await service.token_controls(target)),
                token_control_keyboard(target),
            )
        elif target == "settings":
            await _edit(query, settings_view(await service.settings()), settings_keyboard())
        await query.answer()

    @protected.callback_query(F.data.startswith("control:"))
    async def control_action(query: CallbackQuery) -> None:
        paused = (query.data or "") == "control:pause"
        await service.set_paused(paused, user_id=query.from_user.id)
        payload = await service.dashboard()
        await _edit(query, dashboard_view(payload), dashboard_keyboard(paused))
        await query.answer(
            "New buys stopped; protective exits remain active"
            if paused
            else "Paper trading started"
        )

    @protected.callback_query(F.data.startswith("portfolio:new:"))
    async def create_portfolio(query: CallbackQuery) -> None:
        capital = Decimal((query.data or "").rsplit(":", maxsplit=1)[1])
        await service.create_portfolio(capital)
        await _edit(query, portfolio_view(await service.portfolio()), portfolio_keyboard())
        await query.answer("New paper portfolio activated")

    @protected.callback_query(F.data.startswith("strategy:set:"))
    async def select_strategy(query: CallbackQuery) -> None:
        key = (query.data or "").rsplit(":", maxsplit=1)[1]
        await service.select_strategy(key, user_id=query.from_user.id)
        await _edit(
            query,
            strategies_view(await service.strategies(), await service.settings()),
            strategy_keyboard(),
        )
        await query.answer(f"{key.title()} selected")

    @protected.callback_query(F.data.startswith("position:confirm:"))
    async def confirm_position_close(query: CallbackQuery) -> None:
        mint = (query.data or "").removeprefix("position:confirm:")
        portfolio = await service.portfolio()
        positions = [] if portfolio is None else portfolio.get("positions") or []
        position = next((item for item in positions if item["mint"] == mint), None)
        if position is None:
            await _edit(query, "This paper position is no longer open.", back_keyboard())
            await query.answer("Position already closed")
            return
        assert portfolio is not None
        await _edit(
            query,
            position_close_confirmation(position, portfolio),
            confirm_close_keyboard(mint),
        )
        await query.answer()

    @protected.callback_query(F.data == "positions:close_all:confirm")
    async def confirm_close_all(query: CallbackQuery) -> None:
        portfolio = await service.portfolio()
        positions = [] if portfolio is None else portfolio.get("positions") or []
        if portfolio is None or not positions:
            await _edit(query, "There are no open paper positions.", back_keyboard("positions"))
            await query.answer("No open positions")
            return
        await _edit(query, close_all_confirmation(portfolio), confirm_close_all_keyboard())
        await query.answer()

    @protected.callback_query(
        F.data.in_({"positions:close_all:execute", "positions:close_all:force"})
    )
    async def close_all(query: CallbackQuery) -> None:
        force = (query.data or "").endswith(":force")
        result = await service.close_all_positions(
            user_id=query.from_user.id,
            force_stale=force,
        )
        await _edit(query, close_all_result_view(result), back_keyboard("positions"))
        await query.answer("Close-all processed; new entries paused")

    @protected.callback_query(F.data.startswith("position:close:"))
    async def close_position(query: CallbackQuery) -> None:
        mint = (query.data or "").removeprefix("position:close:")
        try:
            result = await service.manual_sell(mint, user_id=query.from_user.id)
        except (ValueError, RuntimeError) as error:
            await query.answer(f"Close failed: {error}", show_alert=True)
            return
        queued = result.get("kind") == "pending_paper_action"
        await _edit(
            query,
            manual_result_view(result),
            pending_close_keyboard(mint) if queued else back_keyboard("positions"),
        )
        await query.answer(
            "Waiting for the next fresh trade" if queued else "Full paper sell processed"
        )

    @protected.callback_query(F.data.startswith("position:force:"))
    async def force_close_position(query: CallbackQuery) -> None:
        mint = (query.data or "").removeprefix("position:force:")
        try:
            result = await service.manual_sell(
                mint,
                user_id=query.from_user.id,
                force_stale=True,
            )
        except (ValueError, RuntimeError) as error:
            await query.answer(f"Force close failed: {error}", show_alert=True)
            return
        await _edit(query, manual_result_view(result), back_keyboard("positions"))
        await query.answer("Forced paper close processed")

    @protected.callback_query(F.data.startswith("wallet:detail:"))
    async def wallet_detail(query: CallbackQuery) -> None:
        address = (query.data or "").removeprefix("wallet:detail:")
        await _edit(
            query,
            wallet_detail_view(await service.wallet(address)),
            back_keyboard("wallets"),
        )
        await query.answer()

    @protected.callback_query(F.data.startswith("prompt:"))
    async def prompt(query: CallbackQuery, state: FSMContext) -> None:
        action = (query.data or "").removeprefix("prompt:")
        await state.set_state(OperatorInput.waiting)
        await state.update_data(action=action)
        prompts = {
            "capital": "Send the new starting capital, for example: 1000",
            "risk:stop_loss": "Send stop-loss percent, for example: 12",
            "risk:take_profit": "Send take-profit percent, for example: 50",
            "risk:trailing_stop": "Send trailing-stop percent, for example: 15",
            "risk:max_positions": "Send maximum open positions, for example: 10",
            "sizing": "Send fixed position twice (score scaling is off): 8 8",
            "manual:buy": "Send token mint and paper amount: <mint> <amount>",
            "manual:sell": "Send token mint to close the full paper position.",
            "token:watchlist:add": "Send mint to add to the watchlist.",
            "token:watchlist:remove": "Send mint to remove from the watchlist.",
            "token:blacklist:add": "Send mint to add to the blacklist.",
            "token:blacklist:remove": "Send mint to remove from the blacklist.",
            "wallet:seed": "Send wallet address and optional label: <address> [label]",
            "wallet:unseed": "Send wallet address to stop tracking it.",
        }
        await _edit(query, prompts.get(action, "Send a value or /cancel."), back_keyboard())
        await query.answer()

    @protected.message(OperatorInput.waiting, F.text)
    async def process_input(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        action = str(data.get("action", ""))
        try:
            response = await _apply_input(service, action, message.text or "", message)
        except (ValueError, RuntimeError) as error:
            await message.answer(f"Input rejected: {error}. Try again or use /cancel.")
            return
        await state.clear()
        await message.answer(response, reply_markup=back_keyboard())

    @protected.message()
    async def fallback(message: Message) -> None:
        await message.answer("Use /start to open the Bullseye control panel.")

    dispatcher.include_routers(public, protected)
    return dispatcher


async def _apply_input(
    service: TelegramControlService,
    action: str,
    text: str,
    message: Message,
) -> str:
    user_id = message.from_user.id if message.from_user is not None else 0
    if action == "capital":
        await service.create_portfolio(parse_decimal(text))
        return portfolio_view(await service.portfolio())
    if action.startswith("risk:"):
        field = action.split(":", maxsplit=1)[1]
        return settings_view(await service.update_risk(field, parse_decimal(text), user_id=user_id))
    if action == "sizing":
        parts = text.replace(",", ".").split()
        if len(parts) != 2:
            raise ValueError("expected_base_and_maximum_percent")
        return settings_view(
            await service.update_sizing(Decimal(parts[0]), Decimal(parts[1]), user_id=user_id)
        )
    if action == "manual:buy":
        parts = text.split()
        if len(parts) != 2:
            raise ValueError("expected_mint_and_amount")
        return manual_result_view(
            await service.manual_buy(parts[0], parse_decimal(parts[1]), user_id=user_id)
        )
    if action == "manual:sell":
        return manual_result_view(await service.manual_sell(text.strip(), user_id=user_id))
    if action.startswith("token:"):
        _, kind, operation = action.split(":")
        await service.set_token_control(
            kind,
            text.strip(),
            operation == "add",
            user_id=user_id,
        )
        return token_controls_view(kind, await service.token_controls(kind))
    if action == "wallet:seed":
        address, separator, label = text.strip().partition(" ")
        wallet = await service.set_wallet_seed(
            address, enabled=True, label=label.strip() if separator else None
        )
        return wallet_detail_view(wallet)
    if action == "wallet:unseed":
        wallet = await service.set_wallet_seed(text.strip(), enabled=False)
        return wallet_detail_view(wallet)
    raise ValueError("unknown_action")


async def _send_dashboard(message: Message, service: TelegramControlService) -> None:
    payload = await service.dashboard()
    control = payload["control"]
    await message.answer(
        dashboard_view(payload),
        reply_markup=dashboard_keyboard(bool(control and control.entries_paused)),
    )


async def _edit(
    query: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup,
) -> None:
    if isinstance(query.message, Message):
        try:
            await query.message.edit_text(text, reply_markup=reply_markup)
        except TelegramBadRequest as error:
            if "message is not modified" not in str(error).lower():
                raise
