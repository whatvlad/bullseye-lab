"""Record PumpSwap trades for freshly graduated Pump coins (research only, never trades).

The running bot already writes each migration to `token_lifecycle_events`
(lifecycle `post_graduation`, market_address = PumpSwap pool). This script polls that table,
subscribes to logs of each new SOL-quoted pool for --hours (default 2), decodes PumpSwap
buy/sell events with the bot's pinned IDL decoder and appends them to
analysis/pumpswap/trades_YYYYMMDD.jsonl. One WebSocket, one subscription per pool, so the
traffic is a small fraction of the whole PumpSwap stream (~4.5 GB/h).

With --paper it also paper-trades each coin it catches right at graduation
(memebot.paper.graduation: 0.1 SOL, sell at +30% / -15% net or after 30 min) and sends each
fill to Telegram and analysis/graduation_paper/fills.jsonl. Paper only.

Run in its own console:  .venv\\Scripts\\python.exe -u analysis\\pumpswap_recorder.py
Stop with Ctrl+C or by closing the window. Never prints the RPC URL.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import websockets
from sqlalchemy import text

from memebot.core.config import Settings
from memebot.paper.graduation import GraduationPaperTrader, event_fee_bps
from memebot.telegram.history import coin_links
from memebot.providers.solana.pump_idl import (
    PUMP_AMM_PROGRAM_ID,
    PUMP_PROGRAM_ID,
    PumpMigration,
    WRAPPED_SOL_MINT,
    PumpSwapTrade,
    decode_anchor_event,
)
from memebot.storage.database.engine import create_database_engine

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "analysis" / "pumpswap"
PAPER_LEDGER = ROOT / "analysis" / "graduation_paper" / "fills.jsonl"
NEW_POOLS_SQL = """
select * from (
  select distinct on (market_address) market_address, t.mint,
    extract(epoch from e.source_event_at) as graduated_at
  from token_lifecycle_events e join tokens t on t.id = e.token_id
  where e.lifecycle = 'post_graduation' and e.quote_mint = :wsol
    and e.market_address is not null and e.source_event_at >= :since
  order by market_address, e.source_event_at
) newest order by graduated_at desc
"""
# Pump.fun migration authority: present in every bonding-curve -> PumpSwap migration
# (checked on 3 migration txs, 2026-10-09). Lets the recorder find graduations without the bot.
MIGRATION_ACCOUNT = "39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg"
MIGRATION_REQUEST_ID = 1
IDLE_SECONDS = 600  # free the slot of a pool that stopped trading


class Recorder:
    def __init__(self, hours: float, max_pools: int, hourly_mb: float,
                 trader: GraduationPaperTrader | None = None, quiet: bool = False) -> None:
        self.trader = trader
        self.quiet = quiet  # inside the bot: no "watching"/status lines on the console
        self.hourly_bytes = hourly_mb * 1e6
        self.hour_key = int(time.time() // 3600)
        self.hour_bytes = 0
        self.window = hours * 3600
        self.max_pools = max_pools
        self.pools: dict[str, dict] = {}  # pool -> {mint, graduated_at, sub_id, until}
        self.by_sub: dict[int, str] = {}
        self.done: set[str] = set()  # pools already watched (expired or idle)
        self.migration_sub: int | None = None
        self.pending: dict[int, str] = {}  # request id -> pool
        self.next_id = 100
        self.bytes = 0
        self.trades = 0
        self.started = time.monotonic()

    def out_file(self):
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        return (OUT_DIR / f"trades_{datetime.now(UTC):%Y%m%d}.jsonl").open("a", encoding="utf-8")

    def over_budget(self) -> bool:
        key = int(time.time() // 3600)
        if key != self.hour_key:
            self.hour_key, self.hour_bytes = key, 0
        return self.hour_bytes >= self.hourly_bytes

    async def pause_for_budget(self, ws) -> None:
        """Hourly traffic cap reached: drop every pool until the next clock hour.

        Pools with an open paper position keep their subscription until it closes.
        """
        for pool, info in self.pools.items():
            if not self.busy(pool):
                info["until"] = 0
        await self.expire(ws)
        self.say(f"{datetime.now():%H:%M:%S} hourly traffic cap reached; paused until next hour")

    async def poll_new_pools(self, engine, ws) -> None:
        if self.over_budget():
            return
        since = datetime.now(UTC) - timedelta(seconds=self.window)
        async with engine.connect() as conn:
            rows = (await conn.execute(text(NEW_POOLS_SQL),
                                       {"wsol": WRAPPED_SOL_MINT, "since": since})).all()
        for pool, mint, graduated_at in rows:
            if self.add_pool(pool, mint, float(graduated_at)):
                await self.subscribe(ws, pool)

    async def subscribe(self, ws, pool: str) -> None:
        self.next_id += 1
        self.pending[self.next_id] = pool
        await ws.send(json.dumps({"jsonrpc": "2.0", "id": self.next_id, "method": "logsSubscribe",
                                  "params": [{"mentions": [pool]}, {"commitment": "confirmed"}]}))

    def busy(self, pool: str) -> bool:
        return self.trader is not None and self.trader.busy(pool)

    def droppable(self) -> bool:
        return any(not self.busy(pool) for pool in self.pools)

    async def expire(self, ws) -> None:
        now = time.time()
        for pool, info in list(self.pools.items()):
            if self.busy(pool) and now - info["last_trade"] <= IDLE_SECONDS:
                continue
            if info["until"] <= now or now - info["last_trade"] > IDLE_SECONDS:
                if info["sub_id"] is not None:
                    self.next_id += 1
                    await ws.send(json.dumps({"jsonrpc": "2.0", "id": self.next_id,
                                              "method": "logsUnsubscribe",
                                              "params": [info["sub_id"]]}))
                    self.by_sub.pop(info["sub_id"], None)
                del self.pools[pool]
                self.done.add(pool)

    def add_pool(self, pool: str, mint: str, graduated_at: float) -> bool:
        until = graduated_at + self.window
        if pool in self.pools or pool in self.done or until <= time.time():
            return False
        if len(self.pools) >= self.max_pools or self.over_budget():
            return False
        self.pools[pool] = {"mint": mint, "graduated_at": graduated_at, "until": until,
                            "sub_id": None, "last_trade": time.time()}
        self.say(f"{datetime.now():%H:%M:%S} watching {mint} (pool {pool[:6]}…)")
        return True

    def migrations(self, value: dict) -> list[PumpMigration]:
        found = []
        for line in value.get("logs") or []:
            if line.startswith("Program data: "):
                try:
                    event = decode_anchor_event(PUMP_PROGRAM_ID,
                                                base64.b64decode(line[14:], validate=True))
                except Exception:  # noqa: BLE001
                    continue
                if isinstance(event, PumpMigration) and event.quote_mint in (
                    WRAPPED_SOL_MINT, "11111111111111111111111111111111"
                ):
                    found.append(event)
        return found

    def handle(self, raw: str, sink) -> list[str]:
        """Record trades; return pools of newly seen migrations (to subscribe)."""
        self.bytes += len(raw)
        self.hour_bytes += len(raw)
        message = json.loads(raw)
        if message.get("id") == MIGRATION_REQUEST_ID:
            self.migration_sub = message.get("result")
            return []
        params0 = message.get("params") or {}
        if self.migration_sub is not None and params0.get("subscription") == self.migration_sub:
            value0 = (params0.get("result") or {}).get("value") or {}
            if value0.get("err"):
                return []
            added = []
            for migration in self.migrations(value0):
                now = time.time()
                if self.add_pool(migration.pool, migration.mint, now):
                    added.append(migration.pool)
                    if self.trader is not None:
                        self.trader.on_graduation(migration.pool, migration.mint, now, now=now)
            return added
        if "id" in message and message["id"] in self.pending:
            pool = self.pending.pop(message["id"])
            if pool in self.pools and isinstance(message.get("result"), int):
                self.pools[pool]["sub_id"] = message["result"]
                self.by_sub[message["result"]] = pool
            return []
        params = message.get("params") or {}
        pool = self.by_sub.get(params.get("subscription"))
        result = params.get("result") or {}
        value = result.get("value") or {}
        if pool is None or value.get("err"):
            return []
        received = time.time()
        for index, line in enumerate(value.get("logs") or []):
            if not line.startswith("Program data: "):
                continue
            try:
                data = base64.b64decode(line[14:], validate=True)
                event = decode_anchor_event(PUMP_AMM_PROGRAM_ID, data)
            except Exception:  # noqa: BLE001 - events of other programs in the same tx
                continue
            if not isinstance(event, PumpSwapTrade) or event.pool != pool:
                continue
            info = self.pools[pool]
            info["last_trade"] = received
            sink.write(json.dumps({
                "received_at": round(received, 3), "event_ts": event.timestamp,
                "slot": (result.get("context") or {}).get("slot"), "sig": value.get("signature"),
                "log_index": index, "pool": pool, "mint": info["mint"],
                "graduated_at": info["graduated_at"], "side": "buy" if event.is_buy else "sell",
                "base_amount": event.base_amount, "quote_amount": event.quote_amount,
                "pool_base": event.pool_base_token_reserves,
                "pool_quote": event.pool_quote_token_reserves, "user": event.user,
            }) + "\n")
            self.trades += 1
            if self.trader is not None:
                for fill in self.trader.on_trade(
                    pool, received, "buy" if event.is_buy else "sell", event.base_amount,
                    event.quote_amount, event.pool_base_token_reserves,
                    event.pool_quote_token_reserves, event_fee_bps(data),
                ):
                    print(f"{datetime.now():%H:%M:%S} PAPER {json.dumps(fill)}", flush=True)
        return []

    def say(self, text_: str) -> None:
        if not self.quiet:
            print(text_, flush=True)

    def status(self) -> str:
        hours = max(1e-9, (time.monotonic() - self.started) / 3600)
        return (f"{datetime.now():%H:%M:%S} pools={len(self.pools)} trades={self.trades} "
                f"traffic={self.bytes / 1e6:.1f} MB ({self.bytes / 1e6 / hours:.0f} MB/hour)")


async def run(args) -> None:
    settings = Settings(pumpportal_api_key=None)
    engine = create_database_engine(settings.database_url)
    trader = None
    signals = getattr(args, "signals", False)
    quiet = getattr(args, "quiet", False)
    send = telegram_notifier(settings)
    if args.paper or signals:
        trader = GraduationPaperTrader(
            PAPER_LEDGER,
            # Signal mode: paper fills are a silent score (ledger only); the signal is the alert.
            notify=(lambda _text: None) if signals else send,
            signal=graduation_signal(engine, send) if signals else None,
        )
        if not quiet:
            print(f"Paper trading ON: {trader.size_sol} SOL per graduated coin, "
                  f"+{trader.take_profit:.0f}% / -{trader.stop_loss:.0f}%. Fills: {PAPER_LEDGER}",
                  flush=True)
    recorder = Recorder(args.hours, args.max_pools, args.hourly_mb, trader, quiet=quiet)
    print(f"PumpSwap recorder: new graduated pools, {args.hours} h each, max {args.max_pools} "
          f"at once. Output: {OUT_DIR}", flush=True)
    try:
        while True:
            try:
                async with websockets.connect(str(settings.solana_rpc_ws_url), max_size=2**24,
                                              ping_interval=20) as ws:
                    await ws.send(json.dumps({  # graduations, found without the trading bot
                        "jsonrpc": "2.0", "id": MIGRATION_REQUEST_ID, "method": "logsSubscribe",
                        "params": [{"mentions": [MIGRATION_ACCOUNT]}, {"commitment": "confirmed"}],
                    }))
                    for info in recorder.pools.values():  # resubscribe after a reconnect
                        info["sub_id"] = None
                    recorder.by_sub.clear()
                    for pool in list(recorder.pools):
                        await recorder.subscribe(ws, pool)
                    last_poll = last_status = 0.0
                    with recorder.out_file() as sink:
                        while True:
                            now = time.monotonic()
                            if now - last_poll >= 10:
                                await recorder.expire(ws)
                                await recorder.poll_new_pools(engine, ws)
                                sink.flush()
                                last_poll = now
                            if now - last_status >= 300:
                                recorder.say(recorder.status())
                                last_status = now
                            try:
                                raw = await asyncio.wait_for(ws.recv(), timeout=5)
                            except TimeoutError:
                                continue
                            for pool in recorder.handle(raw, sink):
                                await recorder.subscribe(ws, pool)
                            if recorder.droppable() and recorder.over_budget():
                                await recorder.pause_for_budget(ws)
            except (OSError, websockets.ConnectionClosed) as error:
                recorder.say(f"{datetime.now():%H:%M:%S} connection lost "
                             f"({type(error).__name__}); reconnecting in 3 s")
                await asyncio.sleep(3)
    finally:
        recorder.say(recorder.status())
        await engine.dispose()


def graduation_signal(engine, send):
    """Signal-mode alert for a real graduation: console line + Telegram (name looked up)."""
    tasks: set[asyncio.Task] = set()

    async def alert(mint: str, opening_lamports: int) -> None:
        name = symbol = None
        try:
            async with engine.connect() as conn:
                row = (await conn.execute(text("select name, symbol from tokens where mint = :m"),
                                          {"m": mint})).first()
            if row is not None:
                name, symbol = row
        except Exception:  # noqa: BLE001 - the alert matters more than the name
            pass
        label = f"{name or 'Unknown'} ({symbol})" if symbol else (name or "Unknown name")
        send(
            "🎓 GRADUATED SIGNAL (PumpSwap)\n\n"
            f"Token: {label}\nMint: {mint}\n"
            f"Pool opened with {opening_lamports / 1e9:.0f} SOL · fees ~1.25% per side\n\n"
            "Plan: buy now, take profit +30%, stop -15%, out within 30 min.\n"
            "Tested on 31 coins: +6.7% per trade, but only when bought within seconds; "
            "30 s later it turned negative. Paper score is tracked automatically.\n\n"
            + coin_links(mint)
        )

    def on_signal(pool: str, mint: str, opening_lamports: int) -> None:
        print(f"{datetime.now():%H:%M:%S}  SIGNAL graduated  {mint}", flush=True)
        task = asyncio.get_running_loop().create_task(alert(mint, opening_lamports))
        tasks.add(task)
        task.add_done_callback(tasks.discard)

    return on_signal


def telegram_notifier(settings: Settings):
    """Fire-and-forget Telegram messages to the allowed users (paper fills only)."""
    if settings.telegram_bot_token is None or not settings.telegram_allowed_user_ids:
        return lambda _text: None
    from aiogram import Bot

    bot = Bot(token=settings.telegram_bot_token.get_secret_value())
    tasks: set[asyncio.Task] = set()

    async def send(text_: str) -> None:
        for user_id in settings.telegram_allowed_user_ids:
            try:
                await bot.send_message(user_id, text_)
            except Exception as error:  # noqa: BLE001 - never stop recording for Telegram
                print(f"telegram send failed ({type(error).__name__})", flush=True)

    def notify(text_: str) -> None:
        task = asyncio.get_running_loop().create_task(send(text_))
        tasks.add(task)
        task.add_done_callback(tasks.discard)

    return notify


def main() -> None:
    parser = argparse.ArgumentParser(description="Record PumpSwap trades of new graduates.")
    parser.add_argument("--hours", type=float, default=2.0, help="watch each pool this long")
    parser.add_argument("--max-pools", type=int, default=5)
    parser.add_argument("--hourly-mb", type=float, default=170, help="traffic cap per clock hour")
    parser.add_argument("--signals", action="store_true",
                        help="Telegram signal per real graduation (paper score kept silently)")
    parser.add_argument("--paper", action="store_true",
                        help="paper-trade coins caught at graduation (0.1 SOL, +30%%/-15%%)")
    try:
        asyncio.run(run(parser.parse_args()))
    except KeyboardInterrupt:
        print("Recorder stopped.")


if __name__ == "__main__":
    main()
