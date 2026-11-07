from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from memebot.apps import bot_process
from memebot.apps.worker import console_fill_line
from memebot.core.instance import instance_lock


def test_bot_running_follows_the_discovery_lock(tmp_path):
    assert not bot_process.bot_running(tmp_path)
    with instance_lock("discover", directory=tmp_path):
        assert bot_process.bot_running(tmp_path)
    assert not bot_process.bot_running(tmp_path)


def test_stop_request_round_trip(tmp_path):
    assert not bot_process.stop_requested(tmp_path)
    bot_process.request_stop(tmp_path)
    assert bot_process.stop_requested(tmp_path)
    bot_process.clear_stop_request(tmp_path)
    bot_process.clear_stop_request(tmp_path)  # idempotent
    assert not bot_process.stop_requested(tmp_path)


def test_bot_command_matches_manual_start():
    assert "analysis\\run_operational_paper.py --continuous" in bot_process.BOT_COMMAND
    assert "2> analysis\\paper_run.err.log" in bot_process.BOT_COMMAND


def _event(side: str, effect: str, exit_reason: str | None):
    fill = SimpleNamespace(
        filled_at=datetime(2026, 10, 9, 10, 41, 2, tzinfo=UTC),
        gross_quote_amount_raw=Decimal(500_000_000),
        gross_portfolio_amount=Decimal("85.1"),
        portfolio_currency="USDT",
    )
    result = SimpleNamespace(
        side=SimpleNamespace(value=side),
        position_effect=SimpleNamespace(value=effect),
        exit_reason=exit_reason,
        fill=fill,
    )
    return SimpleNamespace(result=result, mint="MintAddress111")


def test_console_fill_line_is_one_short_line():
    buy = console_fill_line(_event("buy", "open", None))  # type: ignore[arg-type]
    assert "BUY  0.5000 SOL (85.10 USDT)  MintAddress111  entry" in buy
    sell = console_fill_line(_event("sell", "partial_close", "take_profit"))  # type: ignore[arg-type]
    assert "SELL partial  0.5000 SOL" in sell and sell.endswith("take_profit")
    assert "\n" not in buy + sell


def test_previous_log_is_archived_not_lost(tmp_path):
    assert bot_process.archive_previous_log(tmp_path) is None
    log = tmp_path / "analysis" / "paper_run.err.log"
    log.parent.mkdir()
    log.write_text('{"event": "insider_facts"}\n', encoding="utf-8")
    archived = bot_process.archive_previous_log(tmp_path)
    assert archived is not None and archived.parent.name == "logs"
    assert archived.read_text(encoding="utf-8").startswith('{"event"')
    assert not log.exists()
