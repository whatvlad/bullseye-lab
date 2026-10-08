"""Read-only local trading audit. Does not start workers or change trading state."""
import asyncio
import json
from pathlib import Path

from sqlalchemy import text

from memebot.core.config import Settings
from memebot.storage.database.engine import create_database_engine


async def main():
    settings = Settings()
    result = {}
    result['settings'] = {k: v for k, v in settings.model_dump(mode='json').items()
                          if k.startswith(('paper_', 'risk_', 'pumpportal_candidate',
                                           'pumpportal_max', 'alpha_', 'feature_'))}
    result['pumpportal_configured'] = settings.pumpportal_api_key is not None
    engine = create_database_engine(settings.database_url)
    queries = {
        'portfolios': 'SELECT name,id,initial_cash,cash_balance,realized_pnl,active,created_at FROM paper_portfolios ORDER BY created_at',
        'controls': 'SELECT entries_paused,active_strategy_key,base_position_percent,max_position_percent,max_open_positions,stop_loss_percent,take_profit_percent,trailing_stop_percent,max_holding_seconds,updated_at FROM trading_control',
        'experiments': 'SELECT name,status,portfolio_id,strategy_key,strategy_version_id,started_at,stopped_at,configuration_snapshot_json FROM experiment_runs ORDER BY started_at',
        'trades': 'SELECT * FROM trade_outcomes ORDER BY entry_at',
        'filled_orders': "SELECT * FROM paper_orders WHERE status='filled' ORDER BY created_at",
        'order_counts': 'SELECT portfolio_id,status,side,rejection_reason,exit_reason,count(*) FROM paper_orders GROUP BY 1,2,3,4,5',
        'data_counts': 'SELECT count(*),min(source_event_at),max(source_event_at) FROM token_trades',
        'strategies': 'SELECT * FROM strategy_configurations',
        'positions': 'SELECT * FROM paper_positions',
        'entry_decision_outcomes': 'SELECT d.* FROM decision_outcomes d WHERE decision_event_id IN (SELECT entry_decision_event_id FROM trade_outcomes)',
        'post_exit_coverage': '''SELECT o.position_id, count(t.event_id) AS observations,
            min(t.source_event_at) AS first_observed_at, max(t.source_event_at) AS last_observed_at,
            max(t.price_raw) AS max_price, min(t.price_raw) AS min_price
            FROM trade_outcomes o LEFT JOIN token_trades t ON t.token_id=o.token_id
            AND t.source_event_at>o.exit_at AND t.source_event_at<=o.exit_at+interval '1 hour'
            WHERE o.exit_at IS NOT NULL GROUP BY o.position_id''',
        'exit_trigger_trades': '''SELECT o.event_id AS order_event_id, t.* FROM paper_orders o
            JOIN token_trades t ON t.event_id=o.trigger_event_id WHERE o.status='filled' AND o.side='sell' ''',
        'decision_coverage': '''SELECT strategy_key, execution_status, count(*) AS n,
            count(*) FILTER (WHERE horizon_returns_json::jsonb ? '300') AS observed_5m,
            count(*) FILTER (WHERE horizon_returns_json::jsonb ? '3600') AS observed_1h
            FROM decision_outcomes GROUP BY 1,2''',
    }
    try:
        async with engine.connect() as connection:
            await connection.execute(text('SET TRANSACTION READ ONLY'))
            await connection.execute(text("SET LOCAL statement_timeout = '30s'"))
            for label, query in queries.items():
                rows = await connection.execute(text(query))
                result[label] = [dict(row) for row in rows.mappings()]
                print(label, len(result[label]), flush=True)
    except Exception as error:
        result['database_error'] = type(error).__name__
        print('DATABASE_ERROR', type(error).__name__, flush=True)
    finally:
        await engine.dispose()
    destination = Path(__file__).with_name('audit-data-2026-09-13.json')
    destination.write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Saved', destination)
    for label in ('controls', 'portfolios', 'data_counts'):
        print(label, json.dumps(result.get(label), default=str))


if __name__ == '__main__':
    asyncio.run(main())
