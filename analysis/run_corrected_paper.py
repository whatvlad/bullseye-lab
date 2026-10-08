"""Bounded entry collection using the existing worker, with exposure-safe draining."""
import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select

from memebot.apps.worker import run_discovery_worker
from memebot.core.config import Settings
from memebot.core.logging import configure_logging
from memebot.storage.database.control import ControlRepository
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.experiments import ExperimentRepository
from memebot.storage.database.models import ExperimentRunRecord, PaperPortfolioRecord, PaperPositionRecord

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "analysis/paper_corrected_run_state.json"


async def main(seconds, target, primary_ws=False):
    settings = Settings(pumpportal_api_key=None)
    if primary_ws:
        from urllib.parse import urlsplit, urlunsplit
        parsed = urlsplit(str(settings.solana_rpc_http_url))
        settings = Settings(pumpportal_api_key=None,
            solana_rpc_ws_url=urlunsplit(("wss", parsed.netloc, parsed.path, parsed.query, "")))
    assert settings.execution_mode == "paper" and settings.paper_trading_enabled
    assert settings.ollama_model is None, "This baseline requires the existing non-LLM strategy"
    configure_logging("INFO", "json")
    database = Database(create_database_engine(settings.database_url))
    controls, experiments = ControlRepository(database.sessions), ExperimentRepository(database.sessions)
    state = {"status": "starting", "entry_window_seconds": seconds, "target_completed": target,
             "live_enabled": False, "runner_edge_prospective_v1": "BLOCKED",
             "thresholds_changed": False, "created_at": datetime.now(UTC).isoformat()}
    ready_event = asyncio.Event()

    def save():
        STATE.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")

    async def ready():
        await controls.set_paused(True, user_id=0)
        async with database.sessions() as session, session.begin():
            assert not await session.scalar(select(func.count()).select_from(PaperPositionRecord)
                .where(PaperPositionRecord.status == "open")), "Existing exposure requires protection"
            active_portfolio = await session.scalar(select(PaperPortfolioRecord).where(PaperPortfolioRecord.active.is_(True)))
            old = await session.scalar(select(ExperimentRunRecord).where(ExperimentRunRecord.status == "active"))
            if old and active_portfolio and old.portfolio_id != active_portfolio.id:
                # Repair the known historical Telegram reset without pretending its config is verified.
                old.status, old.stopped_at = "stopped", active_portfolio.created_at
                linked = await session.scalar(select(ExperimentRunRecord).where(ExperimentRunRecord.portfolio_id == active_portfolio.id))
                if linked is None:
                    snapshot = dict(old.configuration_snapshot_json)
                    snapshot["historical_attribution_repair"] = {
                        "parent_experiment_id": str(old.id),
                        "configuration_certainty": "UNVERIFIED_LEGACY_RESET_COHORT",
                        "repaired_at": datetime.now(UTC).isoformat(),
                    }
                    session.add(ExperimentRunRecord(
                        name="paper-legacy-reset-" + active_portfolio.id.hex[:8], status="stopped",
                        portfolio_id=active_portfolio.id, strategy_key=old.strategy_key,
                        strategy_version_id=old.strategy_version_id, application_version=old.application_version,
                        configuration_snapshot_json=snapshot, started_at=active_portfolio.created_at,
                        stopped_at=datetime.now(UTC), notes="Historical reset cohort retained and linked; copied config is unverified."
                    ))
                    state["repaired_legacy_portfolio_id"] = str(active_portfolio.id)
        if await experiments.active():
            await experiments.stop()
        summary = settings.safe_summary()
        summary.pop("database_url", None)
        experiment = await experiments.start(
            name="standard-pump-paper-corrected-" + datetime.now(UTC).strftime("%Y%m%d-%H%M%S"),
            initial_cash=settings.starting_capital, currency=settings.starting_capital_currency,
            settings_snapshot=summary,
            notes=f"Corrected operational PAPER baseline; {seconds}s entry window, target {target} closed if natural. "
                  "Unchanged entry scores, costs, sizing and daily breaker. LIVE disabled; runner experiment blocked.",
        )
        state.update(status="collecting", experiment_name=experiment["name"], portfolio_id=experiment["portfolio_id"],
                     started_at=experiment["started_at"], configuration_snapshot=experiment["configuration_snapshot"])
        save()
        await controls.set_paused(False, user_id=0)
        ready_event.set()
        print(json.dumps({"corrected_paper": "collecting", "name": experiment["name"]}), flush=True)

    worker = asyncio.create_task(run_discovery_worker(settings, on_ready=ready))
    readiness = asyncio.create_task(ready_event.wait())
    try:
        done, _ = await asyncio.wait([worker, readiness], return_when=asyncio.FIRST_COMPLETED)
        if worker in done:
            await worker
            raise RuntimeError("worker ended before ready")
        deadline = asyncio.get_running_loop().time() + seconds
        drained_since = None
        from uuid import UUID
        pid = UUID(state["portfolio_id"])
        while True:
            async with database.sessions() as session:
                statuses = dict((await session.execute(select(PaperPositionRecord.status, func.count())
                    .where(PaperPositionRecord.portfolio_id == pid).group_by(PaperPositionRecord.status))).all())
            state.update(closed_positions=statuses.get("closed", 0), open_positions=statuses.get("open", 0))
            if state["status"] == "collecting" and (
                asyncio.get_running_loop().time() >= deadline or state["closed_positions"] >= target
            ):
                await controls.set_paused(True, user_id=0)
                state.update(status="draining", entries_paused_at=datetime.now(UTC).isoformat(),
                             bound_reason="target_reached" if state["closed_positions"] >= target else "entry_window_elapsed")
            if state["status"] == "draining" and state["open_positions"] == 0:
                drained_since = drained_since or asyncio.get_running_loop().time()
                if asyncio.get_running_loop().time() - drained_since >= 5:
                    break
            else:
                drained_since = None
            save()
            done, _ = await asyncio.wait([worker], timeout=5)
            if done:
                await worker
                raise RuntimeError("worker ended during collection or exit recovery")
        state["status"] = "complete"
    except BaseException as error:
        state.update(status="interrupted" if isinstance(error, asyncio.CancelledError) else "failed", error_type=type(error).__name__)
        raise
    finally:
        await controls.set_paused(True, user_id=0)
        worker.cancel()
        readiness.cancel()
        await asyncio.gather(worker, readiness, return_exceptions=True)
        if state.get("portfolio_id") and not state.get("open_positions"):
            await experiments.stop()
        state["ended_at"] = datetime.now(UTC).isoformat()
        save()
        await database.dispose()
    print(json.dumps({k: state.get(k) for k in ("status", "portfolio_id", "closed_positions", "open_positions", "bound_reason")}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-seconds", type=float, default=1800)
    parser.add_argument("--target-closed", type=int, default=50)
    parser.add_argument("--primary-ws", action="store_true", help="Use acknowledged WSS of the existing primary RPC for this bounded run only")
    args = parser.parse_args()
    if args.run_seconds <= 0 or args.target_closed <= 0:
        parser.error("bounds must be positive")
    asyncio.run(main(args.run_seconds, args.target_closed, args.primary_ws))
