import json
import struct

from memebot.paper.graduation import (
    GraduationPaperTrader,
    buy_tokens,
    event_fee_bps,
    reserves_after,
    sell_lamports,
)
from memebot.providers.solana.pump_idl import BUY_EVENT_DISCRIMINATOR

SOL = 1_000_000_000


def test_round_trip_costs_about_two_fees():
    base, quote = 200_000_000 * 10**6, 85 * SOL
    tokens = buy_tokens(base, quote, SOL // 10, 125)
    back = sell_lamports(base - tokens, quote + (SOL // 10) * 10_000 // 10_125, tokens, 125)
    loss = 1 - back / (SOL // 10)
    assert 0.024 < loss < 0.027  # 2 x 1.25% fee plus a tiny price impact


def test_event_reserves_are_pre_trade():
    assert reserves_after("buy", 10, 5, 1000, 500) == (990, 505)
    assert reserves_after("sell", 10, 5, 1000, 500) == (1010, 495)


def test_fee_bps_read_from_event_layout():
    body = struct.pack("<q", 0) + struct.pack("<7Q", 1, 2, 3, 4, 5, 6, 7)
    body += struct.pack("<QQQQQQ", 2, 0, 93, 0, 0, 0) + bytes(32 * 7) + struct.pack("<Q", 30)
    assert event_fee_bps(BUY_EVENT_DISCRIMINATOR + body) == 125
    assert event_fee_bps(b"\x00" * 8 + body) is None


def _trader(tmp_path, messages):
    return GraduationPaperTrader(tmp_path / "fills.jsonl", notify=messages.append)


def test_buys_after_latency_and_takes_profit(tmp_path):
    messages: list[str] = []
    trader = _trader(tmp_path, messages)
    base, quote = 200_000_000 * 10**6, 85 * SOL
    assert trader.on_graduation("P", "MINT", 100.0, now=100.0)
    assert trader.on_trade("P", 100.5, "buy", 1, 1, base, quote, 125) == []  # within latency
    fills = trader.on_trade("P", 101.0, "buy", 1, 1, base, quote, 125)
    assert fills[0]["event"] == "buy" and trader.busy("P")
    # A big buy pushes the price ~+40%: exit is scheduled, filled after the latency.
    state = trader.pools["P"]
    assert (
        trader.on_trade(
            "P", 110.0, "buy", 0, 0, state.base * 85 // 100, state.quote * 118 // 100, 125
        )
        == []
    )
    assert state.exit_reason == "take_profit"
    fills = trader.on_trade("P", 111.0, "buy", 0, 0, state.base, state.quote, 125)
    assert fills[0]["event"] == "sell" and fills[0]["pnl_percent"] > 25
    assert not trader.busy("P")
    lines = (tmp_path / "fills.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(x)["event"] for x in lines] == ["buy", "sell"]
    assert "PAPER BUY" in messages[0] and "PAPER SELL" in messages[1]


def test_stop_loss_and_late_coins_are_skipped(tmp_path):
    trader = _trader(tmp_path, [])
    assert not trader.on_graduation("OLD", "M", 0.0, now=60.0)  # not caught at graduation
    base, quote = 200_000_000 * 10**6, 85 * SOL
    trader.on_graduation("P", "M", 0.0, now=0.0)
    trader.on_trade("P", 1.0, "buy", 0, 0, base, quote, 125)
    state = trader.pools["P"]
    trader.on_trade("P", 5.0, "sell", 0, 0, state.base * 120 // 100, state.quote * 80 // 100, 125)
    assert state.exit_reason == "stop_loss"
    fills = trader.on_trade("P", 6.0, "sell", 0, 0, state.base, state.quote, 125)
    assert fills[0]["reason"] == "stop_loss" and fills[0]["pnl_percent"] < -15


def test_dust_and_large_pools_are_not_traded(tmp_path):
    trader = _trader(tmp_path, [])
    trader.on_graduation("DUST", "M", 0.0, now=0.0)
    assert trader.on_trade("DUST", 1.0, "buy", 0, 0, 10**12, SOL // 10, 125) == []
    assert not trader.busy("DUST")
    trader.on_graduation("BIG", "M", 0.0, now=0.0)
    assert trader.on_trade("BIG", 1.0, "buy", 0, 0, 10**15, 3000 * SOL, 125) == []
    assert not trader.busy("BIG")


def test_signal_only_for_real_graduations(tmp_path):
    seen: list[tuple[str, str, int]] = []
    trader = GraduationPaperTrader(
        tmp_path / "f.jsonl", signal=lambda pool, mint, sol: seen.append((pool, mint, sol))
    )
    trader.on_graduation("DUST", "D", 0.0, now=0.0)
    trader.on_trade("DUST", 0.2, "buy", 0, 0, 10**12, SOL // 10, 125)
    trader.on_graduation("REAL", "R", 0.0, now=0.0)
    trader.on_trade("REAL", 0.2, "buy", 0, 0, 200_000_000 * 10**6, 70 * SOL, 125)
    trader.on_trade("REAL", 0.4, "buy", 0, 0, 200_000_000 * 10**6, 70 * SOL, 125)
    assert seen == [("REAL", "R", 70 * SOL)]
