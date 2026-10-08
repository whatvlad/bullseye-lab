from __future__ import annotations

import asyncio

from aiogram import Bot
from aiogram.types import BotCommand

from memebot.core.config import Settings
from memebot.core.instance import instance_lock
from memebot.core.logging import get_logger
from memebot.paper.manual import ManualPaperTradingService
from memebot.paper.market_refresh import (
    CurrentPaperMarketRefresher,
    FallbackMarketSnapshotRefresher,
)
from memebot.providers.birdeye.client import BirdeyeClient
from memebot.providers.birdeye.market import BirdeyeMarketDataProvider
from memebot.providers.price.coingecko import CoinGeckoQuotePriceProvider
from memebot.providers.solana.rpc import JsonRpcSolanaClient
from memebot.pulse.service import PulseService
from memebot.storage.database.control import ControlRepository
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.outcomes import OutcomeRecorder
from memebot.storage.database.paper_history import PaperHistoryRepository
from memebot.storage.database.pending import PendingPaperActionRepository
from memebot.storage.database.registry import TokenRegistry
from memebot.storage.database.wallets import WalletIntelligenceRepository
from memebot.telegram.app import build_dispatcher
from memebot.telegram.markers_server import start_markers_server
from memebot.telegram.service import TelegramControlService


async def run_telegram_bot(settings: Settings, *, run_seconds: float | None = None) -> None:
    with instance_lock("telegram"):
        await _run_telegram_bot(settings, run_seconds=run_seconds)


async def _run_telegram_bot(settings: Settings, *, run_seconds: float | None = None) -> None:
    token = _required_token(settings)
    logger = get_logger("memebot.telegram")
    database = Database(create_database_engine(settings.database_url, echo=settings.database_echo))
    registry = TokenRegistry(
        database.sessions, max_mark_age_seconds=settings.paper_max_market_staleness_seconds
    )
    controls = ControlRepository(database.sessions)
    outcomes = OutcomeRecorder(database.sessions)
    pending = PendingPaperActionRepository(database.sessions)
    wallets = WalletIntelligenceRepository(
        database.sessions,
        early_entry_seconds=settings.wallet_early_entry_seconds,
        candidate_min_launches=settings.wallet_candidate_min_launches,
        scored_min_launches=settings.wallet_scored_min_launches,
        high_confidence_min_launches=settings.wallet_high_confidence_min_launches,
        success_expansion_percent=settings.wallet_success_expansion_percent,
    )
    quote_prices = CoinGeckoQuotePriceProvider(str(settings.coingecko_base_url))
    rpc = JsonRpcSolanaClient(
        str(settings.solana_rpc_http_url),
        timeout_seconds=settings.solana_rpc_timeout_seconds,
    )
    exit_rpc = JsonRpcSolanaClient(
        str(settings.solana_exit_rpc_http_url),
        timeout_seconds=settings.solana_rpc_timeout_seconds,
    )
    manual = ManualPaperTradingService(
        settings,
        registry,
        controls,
        quote_prices,
        outcomes,
        pending,
        require_atomic_pump_state=True,
        market_refresher=CurrentPaperMarketRefresher(rpc),
        exit_market_refresher=FallbackMarketSnapshotRefresher(
            CurrentPaperMarketRefresher(exit_rpc, for_exit=True),
            CurrentPaperMarketRefresher(rpc, for_exit=True),
        ),
    )
    birdeye = _birdeye_provider(settings)
    service = TelegramControlService(
        settings,
        registry,
        controls,
        manual,
        quote_prices,
        outcomes,
        wallets,
        birdeye,
        pulse=PulseService(database.sessions, settings, quote_prices)
        if settings.pulse_enabled
        else None,
    )
    bot = Bot(token=token)
    dispatcher = build_dispatcher(service, allowed_user_ids=settings.telegram_allowed_user_ids)
    markers = None
    try:
        if settings.chart_markers_port:
            try:
                markers = await start_markers_server(
                    PaperHistoryRepository(database.sessions).chart_markers,
                    settings.chart_markers_port,
                )
            except OSError as error:
                logger.warning("chart_markers_unavailable", error_type=type(error).__name__)
        await database.healthcheck()
        await service.initialize()
        await bot.delete_webhook(drop_pending_updates=False)
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="Open Bullseye control panel"),
                BotCommand(
                    command="history", description="All paper trades and full token addresses"
                ),
                BotCommand(command="pulse", description="New pairs, final stretch and migrated"),
                BotCommand(command="whoami", description="Show your numeric Telegram user ID"),
                BotCommand(command="cancel", description="Cancel current input"),
            ]
        )
        identity = await bot.get_me()
        logger.info(
            "telegram_bot_starting",
            bot_id=identity.id,
            bot_username=identity.username,
            allowed_user_count=len(settings.telegram_allowed_user_ids),
            execution_mode=settings.execution_mode,
            birdeye_enabled=birdeye is not None,
        )
        polling = dispatcher.start_polling(
            bot,
            polling_timeout=settings.telegram_polling_timeout_seconds,
            tasks_concurrency_limit=settings.telegram_max_concurrent_updates,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
        if run_seconds is None:
            await polling
        else:
            try:
                async with asyncio.timeout(run_seconds):
                    await polling
            except TimeoutError:
                logger.info("telegram_bot_time_limit_reached", run_seconds=run_seconds)
    finally:
        if markers is not None:
            markers.close()
        await service.close()
        await rpc.close()
        await exit_rpc.close()
        await bot.session.close()
        await database.dispose()


async def check_telegram_bot(settings: Settings) -> dict[str, object]:
    bot = Bot(token=_required_token(settings))
    try:
        identity = await bot.get_me()
    finally:
        await bot.session.close()
    return {
        "healthy": True,
        "bot_id": identity.id,
        "bot_username": identity.username,
        "allowed_user_count": len(settings.telegram_allowed_user_ids),
        "access_configured": bool(settings.telegram_allowed_user_ids),
    }


def _required_token(settings: Settings) -> str:
    if settings.telegram_bot_token is None:
        raise RuntimeError("telegram_bot_token_not_configured")
    return settings.telegram_bot_token.get_secret_value()


def _birdeye_provider(settings: Settings) -> BirdeyeMarketDataProvider | None:
    if settings.birdeye_api_key is None:
        return None
    return BirdeyeMarketDataProvider(
        BirdeyeClient(
            str(settings.birdeye_base_url),
            settings.birdeye_api_key,
            timeout_seconds=settings.birdeye_timeout_seconds,
            minimum_interval_seconds=settings.birdeye_minimum_interval_seconds,
        ),
        cache_seconds=settings.birdeye_cache_seconds,
    )
