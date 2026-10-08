from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def dashboard_keyboard(paused: bool) -> InlineKeyboardMarkup:
    pause_text = "▶️ Start trading" if paused else "⏹ Stop trading"
    pause_data = "control:resume" if paused else "control:pause"
    return _keyboard(
        ("💼 Portfolio", "nav:portfolio"),
        ("📊 Positions", "nav:positions"),
        ("📚 История сделок", "history:page:0"),
        ("📡 Signals", "nav:signals"),
        ("📡 Pulse", "pulse:all:0"),
        ("📈 Outcomes", "nav:outcomes"),
        ("📓 Daily journal", "nav:journal"),
        ("🧭 Wallets", "nav:wallets"),
        ("🧠 Strategies", "nav:strategies"),
        (pause_text, pause_data),
        ("🧾 Manual paper", "nav:manual"),
        ("👁 Watchlist", "nav:watchlist"),
        ("⛔ Blacklist", "nav:blacklist"),
        ("⚙️ Settings", "nav:settings"),
        columns=2,
    )


def portfolio_keyboard() -> InlineKeyboardMarkup:
    return _keyboard(
        ("100", "portfolio:new:100"),
        ("500", "portfolio:new:500"),
        ("1000", "portfolio:new:1000"),
        ("2500", "portfolio:new:2500"),
        ("10000", "portfolio:new:10000"),
        ("Custom", "prompt:capital"),
        ("⬅️ Dashboard", "nav:dashboard"),
        columns=3,
    )


def strategy_keyboard() -> InlineKeyboardMarkup:
    return _keyboard(
        ("Conservative", "strategy:set:conservative"),
        ("Balanced", "strategy:set:balanced"),
        ("Aggressive", "strategy:set:aggressive"),
        ("Compare", "nav:comparison"),
        ("⬅️ Dashboard", "nav:dashboard"),
        columns=1,
    )


def settings_keyboard() -> InlineKeyboardMarkup:
    return _keyboard(
        ("Stop loss", "prompt:risk:stop_loss"),
        ("Take profit", "prompt:risk:take_profit"),
        ("Trailing stop", "prompt:risk:trailing_stop"),
        ("Max positions", "prompt:risk:max_positions"),
        ("Position sizing", "prompt:sizing"),
        ("⬅️ Dashboard", "nav:dashboard"),
        columns=2,
    )


def manual_keyboard() -> InlineKeyboardMarkup:
    return _keyboard(
        ("Paper buy", "prompt:manual:buy"),
        ("Paper sell", "prompt:manual:sell"),
        ("⬅️ Dashboard", "nav:dashboard"),
        columns=1,
    )


def positions_keyboard(positions: list[dict[str, object]]) -> InlineKeyboardMarkup:
    buttons = [
        (
            f"🔴 Close {_position_label(item)}",
            f"position:confirm:{item['mint']}",
        )
        for item in positions[:15]
    ]
    if positions:
        buttons.append(("🛑 Close all positions", "positions:close_all:confirm"))
    buttons.append(("🔄 Refresh", "nav:positions"))
    buttons.append(("⬅️ Dashboard", "nav:dashboard"))
    return _keyboard(*buttons, columns=1)


def confirm_close_all_keyboard() -> InlineKeyboardMarkup:
    return _keyboard(
        ("✅ Close all with fresh RPC", "positions:close_all:execute"),
        ("🔄 Retry all with fresh RPC", "positions:close_all:force"),
        ("Cancel", "nav:positions"),
        columns=1,
    )


def _position_label(position: dict[str, object]) -> str:
    symbol = position.get("symbol")
    if symbol:
        value = str(symbol)
        return value if value.startswith("$") else f"${value}"
    name = position.get("name")
    if name:
        return str(name)[:20]
    return f"{str(position['mint'])[:6]}…"


def confirm_close_keyboard(mint: str) -> InlineKeyboardMarkup:
    return _keyboard(
        ("✅ Close with fresh RPC", f"position:close:{mint}"),
        ("🔄 Retry with fresh RPC", f"position:force:{mint}"),
        ("Cancel", "nav:positions"),
        columns=1,
    )


def pending_close_keyboard(mint: str) -> InlineKeyboardMarkup:
    return _keyboard(
        ("🔄 Retry with fresh RPC", f"position:force:{mint}"),
        ("📊 Back to positions", "nav:positions"),
        columns=1,
    )


def wallets_keyboard(wallets: list[dict[str, object]]) -> InlineKeyboardMarkup:
    buttons = [
        (
            f"{'⭐' if item.get('seeded') else '▫️'} "
            f"{str(item['address'])[:6]}… · {item.get('alpha_score') or 'n/a'}",
            f"wallet:detail:{item['address']}",
        )
        for item in wallets[:15]
    ]
    buttons.extend(
        [
            ("Track wallet", "prompt:wallet:seed"),
            ("Stop tracking", "prompt:wallet:unseed"),
            ("🔄 Refresh", "nav:wallets"),
            ("⬅️ Dashboard", "nav:dashboard"),
        ]
    )
    return _keyboard(*buttons, columns=1)


def token_control_keyboard(kind: str) -> InlineKeyboardMarkup:
    return _keyboard(
        ("Add", f"prompt:token:{kind}:add"),
        ("Remove", f"prompt:token:{kind}:remove"),
        ("⬅️ Dashboard", "nav:dashboard"),
        columns=2,
    )


def back_keyboard(target: str = "dashboard") -> InlineKeyboardMarkup:
    return _keyboard(("⬅️ Back", f"nav:{target}"), columns=1)


def _keyboard(*buttons: tuple[str, str], columns: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for index in range(0, len(buttons), columns):
        rows.append(
            [
                InlineKeyboardButton(text=text, callback_data=data)
                for text, data in buttons[index : index + columns]
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)
