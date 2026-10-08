from __future__ import annotations

import argparse
import asyncio
import json
import sys
from decimal import Decimal
from importlib.metadata import PackageNotFoundError, version

from memebot import __version__
from memebot.apps.telegram import check_telegram_bot, run_telegram_bot
from memebot.apps.worker import run_database_check, run_discovery_worker
from memebot.core.clock import utc_now
from memebot.core.config import Settings
from memebot.core.instance import InstanceAlreadyRunning
from memebot.core.logging import configure_logging
from memebot.paper.market_refresh import SolanaRpcMarketSnapshotRefresher
from memebot.providers.birdeye.client import BirdeyeClient
from memebot.providers.pool_lookup import DexScreenerPoolLookup
from memebot.providers.solana.pump_idl import WRAPPED_SOL_MINT
from memebot.providers.solana.rpc import JsonRpcSolanaClient
from memebot.storage.database.control import ControlRepository
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.experiments import ExperimentRepository
from memebot.storage.database.migrations import upgrade_database
from memebot.storage.database.outcomes import OutcomeRecorder
from memebot.storage.database.registry import TokenRegistry
from memebot.storage.database.wallets import WalletIntelligenceRepository
from memebot.strategies.presets import initial_strategy_presets


def _package_version(package: str) -> str | None:
    try:
        return version(package)
    except PackageNotFoundError:
        return None


def _doctor(settings: Settings) -> int:
    supported_python = sys.version_info >= (3, 13)
    report = {
        "application": "bullseye-lab",
        "version": __version__,
        "phase": "9A",
        "python": sys.version.split()[0],
        "python_supported": supported_python,
        "dependencies": {
            package: _package_version(package)
            for package in (
                "pydantic",
                "pydantic-settings",
                "SQLAlchemy",
                "alembic",
                "structlog",
                "httpx",
                "websockets",
                "aiogram",
            )
        },
        "configuration": settings.safe_summary(),
        "external_calls_made": False,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if supported_python else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bullseye",
        description="Bullseye Lab paper-trading research platform",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subcommands = parser.add_subparsers(dest="command")
    subcommands.add_parser("doctor", help="show a redacted local readiness report")
    subcommands.add_parser("show-config", help="show non-secret effective configuration")
    subcommands.add_parser("db-upgrade", help="apply Alembic migrations")
    subcommands.add_parser("db-check", help="check database connectivity and worker wiring")
    subcommands.add_parser("rpc-check", help="check the configured read-only Solana RPC")
    subcommands.add_parser("birdeye-check", help="probe official Birdeye plan capabilities")
    subcommands.add_parser("telegram-check", help="validate the Telegram bot token safely")
    telegram = subcommands.add_parser("telegram", help="run the allowlisted Telegram control panel")
    telegram.add_argument("--run-seconds", type=float, default=None)
    discovery = subcommands.add_parser(
        "discover",
        help="run Pump/PumpSwap discovery until interrupted",
    )
    discovery.add_argument(
        "--run-seconds",
        type=float,
        default=None,
        help="stop after this many seconds (useful for a smoke test)",
    )
    token = subcommands.add_parser("token", help="inspect a token in the local registry")
    token.add_argument("mint")
    subcommands.add_parser("provider-health", help="show persisted provider health")
    features = subcommands.add_parser("features", help="show rolling feature snapshots")
    features.add_argument("mint")
    features.add_argument("--limit", type=int, default=1)
    risk = subcommands.add_parser("risk", help="show evidence-backed risk assessments")
    risk.add_argument("mint")
    risk.add_argument("--limit", type=int, default=1)
    subcommands.add_parser("strategies", help="show versioned strategy configurations")
    subcommands.add_parser(
        "strategies-sync", help="persist current immutable strategy preset versions"
    )
    decisions = subcommands.add_parser(
        "decisions", help="show immutable strategy decisions for a token"
    )
    decisions.add_argument("mint")
    decisions.add_argument("--strategy", default=None)
    decisions.add_argument("--limit", type=int, default=10)
    subcommands.add_parser("portfolio", help="show active paper portfolio and positions")
    subcommands.add_parser(
        "position-marks-check",
        help="read current on-chain prices for open paper positions without trading",
    )
    subcommands.add_parser(
        "positions-reconcile",
        help="close invalid zero-quantity paper position rows",
    )
    sizing = subcommands.add_parser(
        "sizing-set", help="set persistent dynamic paper position sizing bounds"
    )
    sizing.add_argument("--base", type=Decimal, required=True)
    sizing.add_argument("--max", dest="maximum", type=Decimal, required=True)
    risk_controls = subcommands.add_parser(
        "risk-set", help="set persistent paper exit and position risk controls"
    )
    risk_controls.add_argument("--stop-loss", type=Decimal, default=None)
    risk_controls.add_argument("--take-profit", type=Decimal, default=None)
    risk_controls.add_argument("--trailing-stop", type=Decimal, default=None)
    risk_controls.add_argument("--max-open-positions", type=int, default=None)
    subcommands.add_parser("control-show", help="show persistent paper trading controls")
    subcommands.add_parser("entries-resume", help="resume automatic paper entries")
    subcommands.add_parser("entries-pause", help="pause automatic paper entries")
    create_portfolio = subcommands.add_parser(
        "portfolio-create", help="create and activate a new paper portfolio"
    )
    create_portfolio.add_argument("--name", default="Paper portfolio")
    create_portfolio.add_argument("--capital", type=Decimal, required=True)
    create_portfolio.add_argument("--currency", choices=("USD", "USDT"), default="USDT")
    paper_orders = subcommands.add_parser("paper-orders", help="show recent paper orders")
    paper_orders.add_argument("--limit", type=int, default=20)
    subcommands.add_parser("outcome-summary", help="show Phase 7 outcome statistics")
    experiment_start = subcommands.add_parser(
        "experiment-start", help="create an isolated paused paper experiment"
    )
    experiment_start.add_argument("--name", required=True)
    experiment_start.add_argument("--capital", type=Decimal, required=True)
    experiment_start.add_argument("--currency", choices=("USD", "USDT"), default="USDT")
    experiment_start.add_argument("--notes", default=None)
    subcommands.add_parser("experiment-stop", help="stop the active closed-out experiment")
    experiments = subcommands.add_parser("experiments", help="list paper experiments")
    experiments.add_argument("--limit", type=int, default=20)
    experiment_report = subcommands.add_parser(
        "experiment-report", help="show robust metrics for an isolated experiment"
    )
    experiment_report.add_argument("--name", default=None)
    decision_outcomes = subcommands.add_parser(
        "decision-outcomes", help="show taken and skipped decision outcomes"
    )
    decision_outcomes.add_argument("--limit", type=int, default=20)
    trade_outcomes = subcommands.add_parser(
        "trade-outcomes", help="show complete paper-trade outcomes"
    )
    trade_outcomes.add_argument("--limit", type=int, default=20)
    wallets = subcommands.add_parser("wallets", help="rank observed and seeded wallets")
    wallets.add_argument("--limit", type=int, default=20)
    wallets.add_argument("--seeded", action="store_true")
    wallet = subcommands.add_parser("wallet", help="show auditable wallet metrics")
    wallet.add_argument("address")
    wallet_seed = subcommands.add_parser("wallet-seed", help="add a manual seed wallet")
    wallet_seed.add_argument("address")
    wallet_seed.add_argument("--label", default=None)
    wallet_unseed = subcommands.add_parser(
        "wallet-unseed", help="remove a wallet's manual seed flag"
    )
    wallet_unseed.add_argument("address")
    wallet_backfill = subcommands.add_parser(
        "wallet-backfill", help="project stored trades into Phase 8 wallet metrics"
    )
    wallet_backfill.add_argument("--limit", type=int, default=2000)
    return parser


async def _rpc_check(settings: Settings) -> int:
    rpc = JsonRpcSolanaClient(
        str(settings.solana_rpc_http_url),
        timeout_seconds=settings.solana_rpc_timeout_seconds,
    )
    try:
        health = await rpc.health()
    finally:
        await rpc.close()
    print(json.dumps(health.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0 if health.healthy else 1


async def _birdeye_check(settings: Settings) -> int:
    if settings.birdeye_api_key is None:
        print(json.dumps({"configured": False}, indent=2, sort_keys=True))
        return 1
    client = BirdeyeClient(
        str(settings.birdeye_base_url),
        settings.birdeye_api_key,
        timeout_seconds=settings.birdeye_timeout_seconds,
        minimum_interval_seconds=settings.birdeye_minimum_interval_seconds,
    )
    try:
        report = await client.probe(WRAPPED_SOL_MINT)
    finally:
        await client.close()
    print(
        json.dumps(
            {
                "authenticated": report.authenticated,
                "available": sorted(report.available),
                "unavailable": report.unavailable,
                "credits": report.credits,
                "probed_at": report.probed_at,
                "api_key_exposed": False,
            },
            indent=2,
            sort_keys=True,
            default=str,
        )
    )
    return 0 if report.authenticated else 1


async def _inspect_database(settings: Settings, *, mint: str | None = None) -> int:
    database = Database(create_database_engine(settings.database_url, echo=False))
    registry = TokenRegistry(database.sessions)
    try:
        if mint is None:
            payload: object = await registry.provider_health()
        else:
            payload = await registry.inspect_token(mint)
    finally:
        await database.dispose()
    if payload is None:
        print(json.dumps({"found": False, "mint": mint}, indent=2, sort_keys=True))
        return 1
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


async def _inspect_features(settings: Settings, mint: str, limit: int) -> int:
    database = Database(create_database_engine(settings.database_url, echo=False))
    registry = TokenRegistry(database.sessions)
    try:
        payload = await registry.latest_features(mint, limit=limit)
    finally:
        await database.dispose()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload else 1


async def _inspect_risk(settings: Settings, mint: str, limit: int) -> int:
    database = Database(create_database_engine(settings.database_url, echo=False))
    registry = TokenRegistry(database.sessions)
    try:
        payload = await registry.latest_risk(mint, limit=limit)
    finally:
        await database.dispose()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload else 1


async def _inspect_strategies(settings: Settings) -> int:
    database = Database(create_database_engine(settings.database_url, echo=False))
    registry = TokenRegistry(database.sessions)
    try:
        payload = await registry.strategy_configurations()
    finally:
        await database.dispose()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload else 1


async def _sync_strategies(settings: Settings) -> int:
    database = Database(create_database_engine(settings.database_url, echo=False))
    registry = TokenRegistry(database.sessions)
    try:
        configurations = initial_strategy_presets()
        await registry.ensure_strategy_configurations(configurations)
        payload = {
            "synced": [
                {
                    "strategy_key": item.key,
                    "version": item.version,
                    "version_id": str(item.version_id),
                }
                for item in configurations
            ]
        }
    finally:
        await database.dispose()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


async def _inspect_decisions(
    settings: Settings,
    mint: str,
    *,
    limit: int,
    strategy_key: str | None,
) -> int:
    database = Database(create_database_engine(settings.database_url, echo=False))
    registry = TokenRegistry(database.sessions)
    try:
        payload = await registry.latest_decisions(mint, limit=limit, strategy_key=strategy_key)
    finally:
        await database.dispose()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload else 1


async def _inspect_portfolio(settings: Settings) -> int:
    database = Database(create_database_engine(settings.database_url, echo=False))
    registry = TokenRegistry(database.sessions)
    try:
        payload = await registry.paper_portfolio_report()
    finally:
        await database.dispose()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload is not None else 1


async def _check_position_marks(settings: Settings) -> int:
    """Probe on-chain position marks without writing to the paper portfolio."""
    database = Database(create_database_engine(settings.database_url, echo=False))
    registry = TokenRegistry(database.sessions)
    rpc = JsonRpcSolanaClient(
        str(settings.solana_rpc_http_url),
        timeout_seconds=settings.solana_rpc_timeout_seconds,
    )
    refresher = SolanaRpcMarketSnapshotRefresher(
        rpc, commitment=settings.solana_commitment, pool_lookup=DexScreenerPoolLookup()
    )
    results: list[dict[str, object]] = []
    try:
        for position in await registry.open_positions():
            market = await registry.paper_market_context(position.mint, as_of=utc_now())
            if market is None:
                results.append({"mint": position.mint, "status": "market_context_missing"})
                continue
            refreshed = await refresher.refresh_with_diagnostics(market)
            price = refreshed.market.observed_price_raw if refreshed.status == "refreshed" else None
            results.append(
                {
                    "mint": position.mint,
                    "market": refreshed.market.market,
                    "status": refreshed.status,
                    "detail": refreshed.detail,
                    "source_slot": refreshed.market.source_slot,
                    "entry_price_raw": str(position.entry_price_raw),
                    "onchain_price_raw": str(price) if price is not None else None,
                    "return_percent": str(
                        ((price / position.entry_price_raw - Decimal(1)) * Decimal(100)).quantize(
                            Decimal("0.01")
                        )
                    )
                    if price is not None
                    else None,
                }
            )
    finally:
        await rpc.close()
        await database.dispose()
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0 if all(item["status"] == "refreshed" for item in results) else 1


async def _reconcile_positions(settings: Settings) -> int:
    database = Database(create_database_engine(settings.database_url, echo=False))
    registry = TokenRegistry(database.sessions)
    outcomes = OutcomeRecorder(database.sessions)
    try:
        repaired_positions = await registry.reconcile_zero_quantity_positions()
        repaired_outcomes = await outcomes.reconcile_positions()
    finally:
        await database.dispose()
    print(
        json.dumps(
            {
                "zero_quantity_positions_closed": repaired_positions,
                "trade_outcomes_reconciled": repaired_outcomes,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


async def _set_sizing(settings: Settings, *, base: Decimal, maximum: Decimal) -> int:
    database = Database(create_database_engine(settings.database_url, echo=False))
    controls = ControlRepository(database.sessions)
    try:
        control = await controls.update_sizing(
            base_position_percent=base,
            max_position_percent=maximum,
            user_id=0,
        )
    finally:
        await database.dispose()
    print(
        json.dumps(
            {
                "base_position_percent": str(control.base_position_percent),
                "max_position_percent": str(control.max_position_percent),
                "score_scaled_sizing": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


async def _show_control(settings: Settings) -> int:
    database = Database(create_database_engine(settings.database_url, echo=False))
    controls = ControlRepository(database.sessions)
    try:
        control = await controls.get()
    finally:
        await database.dispose()
    if control is None:
        print(json.dumps({"found": False}, indent=2))
        return 1
    print(
        json.dumps(
            {
                "entries_paused": control.entries_paused,
                "active_strategy_key": control.active_strategy_key,
                "base_position_percent": str(control.base_position_percent),
                "max_position_percent": str(control.max_position_percent),
                "max_open_positions": control.max_open_positions,
                "stop_loss_percent": str(control.stop_loss_percent),
                "take_profit_percent": str(control.take_profit_percent),
                "trailing_stop_percent": str(control.trailing_stop_percent),
                "max_holding_seconds": control.max_holding_seconds,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


async def _set_entries_paused(settings: Settings, *, paused: bool) -> int:
    database = Database(create_database_engine(settings.database_url, echo=False))
    controls = ControlRepository(database.sessions)
    try:
        control = await controls.set_paused(paused, user_id=0)
    finally:
        await database.dispose()
    print(json.dumps({"entries_paused": control.entries_paused}, indent=2))
    return 0


async def _set_risk_controls(
    settings: Settings,
    *,
    stop_loss: Decimal | None,
    take_profit: Decimal | None,
    trailing_stop: Decimal | None,
    max_open_positions: int | None,
) -> int:
    database = Database(create_database_engine(settings.database_url, echo=False))
    controls = ControlRepository(database.sessions)
    try:
        control = await controls.update_risk(
            stop_loss_percent=stop_loss,
            take_profit_percent=take_profit,
            trailing_stop_percent=trailing_stop,
            max_open_positions=max_open_positions,
            user_id=0,
        )
    except ValueError as error:
        print(json.dumps({"ok": False, "error": str(error)}, indent=2))
        return 1
    finally:
        await database.dispose()
    print(
        json.dumps(
            {
                "stop_loss_percent": str(control.stop_loss_percent),
                "take_profit_percent": str(control.take_profit_percent),
                "trailing_stop_percent": str(control.trailing_stop_percent),
                "max_open_positions": control.max_open_positions,
            },
            indent=2,
        )
    )
    return 0


async def _create_portfolio(
    settings: Settings, *, name: str, capital: Decimal, currency: str
) -> int:
    database = Database(create_database_engine(settings.database_url, echo=False))
    registry = TokenRegistry(database.sessions)
    try:
        portfolio = await registry.create_paper_portfolio(
            name=name, initial_cash=capital, currency=currency
        )
    finally:
        await database.dispose()
    print(
        json.dumps(
            {
                "portfolio_id": str(portfolio.portfolio_id),
                "currency": portfolio.currency,
                "initial_cash": str(portfolio.initial_cash),
                "cash_balance": str(portfolio.cash_balance),
                "active": True,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


async def _inspect_paper_orders(settings: Settings, limit: int) -> int:
    database = Database(create_database_engine(settings.database_url, echo=False))
    registry = TokenRegistry(database.sessions)
    try:
        payload = await registry.latest_paper_orders(limit=limit)
    finally:
        await database.dispose()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload else 1


async def _inspect_outcomes(settings: Settings, *, kind: str, limit: int = 20) -> int:
    database = Database(create_database_engine(settings.database_url, echo=False))
    outcomes = OutcomeRecorder(database.sessions)
    try:
        if kind == "summary":
            payload: object = await outcomes.summary()
        elif kind == "decisions":
            payload = await outcomes.latest_decisions(limit=limit)
        else:
            payload = await outcomes.latest_trades(limit=limit)
    finally:
        await database.dispose()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


async def _experiment_command(
    settings: Settings,
    *,
    action: str,
    name: str | None = None,
    capital: Decimal | None = None,
    currency: str = "USDT",
    notes: str | None = None,
    limit: int = 20,
) -> int:
    database = Database(create_database_engine(settings.database_url, echo=False))
    experiments = ExperimentRepository(database.sessions)
    try:
        if action == "start":
            assert name is not None and capital is not None
            payload: object = await experiments.start(
                name=name,
                initial_cash=capital,
                currency=currency,
                settings_snapshot=settings.safe_summary(),
                notes=notes,
            )
        elif action == "stop":
            payload = await experiments.stop()
        elif action == "list":
            payload = await experiments.list(limit=limit)
        else:
            payload = await experiments.report(name)
    except ValueError as error:
        print(json.dumps({"ok": False, "error": str(error)}, indent=2))
        return 1
    finally:
        await database.dispose()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _wallet_repository(settings: Settings, database: Database) -> WalletIntelligenceRepository:
    return WalletIntelligenceRepository(
        database.sessions,
        early_entry_seconds=settings.wallet_early_entry_seconds,
        candidate_min_launches=settings.wallet_candidate_min_launches,
        scored_min_launches=settings.wallet_scored_min_launches,
        high_confidence_min_launches=settings.wallet_high_confidence_min_launches,
        success_expansion_percent=settings.wallet_success_expansion_percent,
    )


async def _inspect_wallets(
    settings: Settings,
    *,
    address: str | None = None,
    limit: int = 20,
    seeded_only: bool = False,
) -> int:
    database = Database(create_database_engine(settings.database_url, echo=False))
    wallets = _wallet_repository(settings, database)
    try:
        payload: object = (
            await wallets.wallet_report(address)
            if address is not None
            else await wallets.ranked_wallets(limit=limit, seeded_only=seeded_only)
        )
    finally:
        await database.dispose()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload is not None else 1


async def _set_wallet_seed(
    settings: Settings, *, address: str, enabled: bool, label: str | None = None
) -> int:
    database = Database(create_database_engine(settings.database_url, echo=False))
    wallets = _wallet_repository(settings, database)
    try:
        payload = await wallets.set_seed(address, enabled=enabled, label=label)
    finally:
        await database.dispose()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


async def _backfill_wallets(settings: Settings, *, limit: int) -> int:
    database = Database(create_database_engine(settings.database_url, echo=False))
    wallets = _wallet_repository(settings, database)
    try:
        processed = await wallets.backfill_existing(limit=limit)
    finally:
        await database.dispose()
    print(json.dumps({"processed": processed, "external_calls_made": False}, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    settings = Settings()
    configure_logging(settings.log_level, settings.log_format)

    if arguments.command in {None, "doctor"}:
        return _doctor(settings)
    if arguments.command == "show-config":
        print(json.dumps(settings.safe_summary(), indent=2, sort_keys=True))
        return 0
    if arguments.command == "db-upgrade":
        upgrade_database(settings.database_url)
        return 0
    if arguments.command == "db-check":
        asyncio.run(run_database_check(settings))
        return 0
    if arguments.command == "rpc-check":
        return asyncio.run(_rpc_check(settings))
    if arguments.command == "position-marks-check":
        return asyncio.run(_check_position_marks(settings))
    if arguments.command == "positions-reconcile":
        return asyncio.run(_reconcile_positions(settings))
    if arguments.command == "sizing-set":
        return asyncio.run(_set_sizing(settings, base=arguments.base, maximum=arguments.maximum))
    if arguments.command == "risk-set":
        values = (
            arguments.stop_loss,
            arguments.take_profit,
            arguments.trailing_stop,
            arguments.max_open_positions,
        )
        if all(value is None for value in values):
            parser.error("risk-set requires at least one option")
        return asyncio.run(
            _set_risk_controls(
                settings,
                stop_loss=arguments.stop_loss,
                take_profit=arguments.take_profit,
                trailing_stop=arguments.trailing_stop,
                max_open_positions=arguments.max_open_positions,
            )
        )
    if arguments.command == "control-show":
        return asyncio.run(_show_control(settings))
    if arguments.command == "entries-resume":
        return asyncio.run(_set_entries_paused(settings, paused=False))
    if arguments.command == "entries-pause":
        return asyncio.run(_set_entries_paused(settings, paused=True))
    if arguments.command == "birdeye-check":
        return asyncio.run(_birdeye_check(settings))
    if arguments.command == "telegram-check":
        payload = asyncio.run(check_telegram_bot(settings))
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if arguments.command == "telegram":
        if arguments.run_seconds is not None and arguments.run_seconds <= 0:
            parser.error("--run-seconds must be greater than zero")
        try:
            asyncio.run(run_telegram_bot(settings, run_seconds=arguments.run_seconds))
        except KeyboardInterrupt:
            return 130
        return 0
    if arguments.command == "discover":
        run_seconds = arguments.run_seconds
        if run_seconds is not None and run_seconds <= 0:
            parser.error("--run-seconds must be greater than zero")
        try:
            asyncio.run(run_discovery_worker(settings, run_seconds=run_seconds))
        except KeyboardInterrupt:
            return 130
        return 0
    if arguments.command == "token":
        return asyncio.run(_inspect_database(settings, mint=arguments.mint))
    if arguments.command == "provider-health":
        return asyncio.run(_inspect_database(settings))
    if arguments.command == "features":
        if arguments.limit <= 0 or arguments.limit > 100:
            parser.error("--limit must be between 1 and 100")
        return asyncio.run(_inspect_features(settings, arguments.mint, arguments.limit))
    if arguments.command == "risk":
        if arguments.limit <= 0 or arguments.limit > 100:
            parser.error("--limit must be between 1 and 100")
        return asyncio.run(_inspect_risk(settings, arguments.mint, arguments.limit))
    if arguments.command == "strategies":
        return asyncio.run(_inspect_strategies(settings))
    if arguments.command == "strategies-sync":
        return asyncio.run(_sync_strategies(settings))
    if arguments.command == "decisions":
        if arguments.limit <= 0 or arguments.limit > 100:
            parser.error("--limit must be between 1 and 100")
        return asyncio.run(
            _inspect_decisions(
                settings,
                arguments.mint,
                limit=arguments.limit,
                strategy_key=arguments.strategy,
            )
        )
    if arguments.command == "portfolio":
        return asyncio.run(_inspect_portfolio(settings))
    if arguments.command == "portfolio-create":
        if arguments.capital <= 0:
            parser.error("--capital must be greater than zero")
        return asyncio.run(
            _create_portfolio(
                settings,
                name=arguments.name,
                capital=arguments.capital,
                currency=arguments.currency,
            )
        )
    if arguments.command == "paper-orders":
        if arguments.limit <= 0 or arguments.limit > 100:
            parser.error("--limit must be between 1 and 100")
        return asyncio.run(_inspect_paper_orders(settings, arguments.limit))
    if arguments.command == "outcome-summary":
        return asyncio.run(_inspect_outcomes(settings, kind="summary"))
    if arguments.command == "experiment-start":
        if arguments.capital <= 0:
            parser.error("--capital must be greater than zero")
        return asyncio.run(
            _experiment_command(
                settings,
                action="start",
                name=arguments.name,
                capital=arguments.capital,
                currency=arguments.currency,
                notes=arguments.notes,
            )
        )
    if arguments.command == "experiment-stop":
        return asyncio.run(_experiment_command(settings, action="stop"))
    if arguments.command == "experiments":
        if arguments.limit <= 0 or arguments.limit > 100:
            parser.error("--limit must be between 1 and 100")
        return asyncio.run(_experiment_command(settings, action="list", limit=arguments.limit))
    if arguments.command == "experiment-report":
        return asyncio.run(_experiment_command(settings, action="report", name=arguments.name))
    if arguments.command in {"decision-outcomes", "trade-outcomes"}:
        if arguments.limit <= 0 or arguments.limit > 100:
            parser.error("--limit must be between 1 and 100")
        kind = "decisions" if arguments.command == "decision-outcomes" else "trades"
        return asyncio.run(_inspect_outcomes(settings, kind=kind, limit=arguments.limit))
    if arguments.command == "wallets":
        if arguments.limit <= 0 or arguments.limit > 100:
            parser.error("--limit must be between 1 and 100")
        return asyncio.run(
            _inspect_wallets(settings, limit=arguments.limit, seeded_only=arguments.seeded)
        )
    if arguments.command == "wallet":
        return asyncio.run(_inspect_wallets(settings, address=arguments.address))
    if arguments.command == "wallet-seed":
        return asyncio.run(
            _set_wallet_seed(
                settings,
                address=arguments.address,
                enabled=True,
                label=arguments.label,
            )
        )
    if arguments.command == "wallet-unseed":
        return asyncio.run(_set_wallet_seed(settings, address=arguments.address, enabled=False))
    if arguments.command == "wallet-backfill":
        if arguments.limit <= 0 or arguments.limit > 100000:
            parser.error("--limit must be between 1 and 100000")
        return asyncio.run(_backfill_wallets(settings, limit=arguments.limit))
    parser.error(f"unknown command: {arguments.command}")
    return 2


def entrypoint() -> None:
    try:
        result = main()
    except InstanceAlreadyRunning as error:
        print(str(error), file=sys.stderr)
        result = 2
    raise SystemExit(result)
