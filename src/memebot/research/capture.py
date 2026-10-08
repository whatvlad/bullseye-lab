from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import text

from memebot.core.config import Settings
from memebot.storage.database.engine import create_database_engine

QUERIES = {
    "portfolios": (
        "SELECT id,name,initial_cash,cash_balance,realized_pnl,active,currency "
        "FROM paper_portfolios"
    ),
    "positions": "SELECT * FROM paper_positions ORDER BY opened_at",
    "trades": "SELECT * FROM trade_outcomes ORDER BY entry_at",
    "filled_orders": "SELECT * FROM paper_orders WHERE status='filled' ORDER BY filled_at",
    "data_counts": "SELECT count(*),min(source_event_at),max(source_event_at) FROM token_trades",
    "controls": (
        "SELECT entries_paused,active_strategy_key,base_position_percent,max_position_percent,"
        "max_open_positions,stop_loss_percent,updated_at FROM trading_control"
    ),
    "order_counts": (
        "SELECT status,side,rejection_reason,exit_reason,count(*) "
        "FROM paper_orders GROUP BY 1,2,3,4"
    ),
    "provider_health": (
        "SELECT provider,state,error_code,rate_limited,reconnect_count FROM provider_health"
    ),
    "event_counts": (
        "SELECT event_type,provider,count(*),min(ingested_at),max(ingested_at) "
        "FROM domain_events GROUP BY 1,2"
    ),
    "health_errors": (
        "SELECT provider,payload->>'error_code' AS error_code,count(*) "
        "FROM domain_events WHERE event_type='provider.health_updated' GROUP BY 1,2"
    ),
    "decision_coverage": (
        "SELECT strategy_key,action,count(*),"
        "count(*) FILTER (WHERE horizon_returns_json::jsonb ? '300') AS observed_5m "
        "FROM decision_outcomes GROUP BY 1,2"
    ),
}


async def capture(destination: Path) -> dict[str, object]:
    settings = Settings()
    report: dict[str, object] = {"configuration": settings.safe_summary()}
    engine = create_database_engine(settings.database_url)
    try:
        async with engine.connect() as connection:
            await connection.execute(
                text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            )
            await connection.execute(text("SET LOCAL statement_timeout = '60s'"))
            for label, query in QUERIES.items():
                result = await connection.execute(text(query))
                report[label] = [dict(row) for row in result.mappings()]
    finally:
        await engine.dispose()
    await asyncio.to_thread(destination.parent.mkdir, parents=True, exist_ok=True)
    await asyncio.to_thread(
        destination.write_text, json.dumps(report, default=str, indent=2), encoding="utf-8"
    )
    return {label: len(value) for label, value in report.items() if isinstance(value, list)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only forensic PostgreSQL snapshot")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(asyncio.run(capture(args.output))))
    except Exception as error:
        parser.exit(1, f"Capture failed: {type(error).__name__}; no trading state changed.\n")


if __name__ == "__main__":
    main()
