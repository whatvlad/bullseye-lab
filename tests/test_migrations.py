import sqlite3

from memebot.storage.database.migrations import upgrade_database


def test_initial_migration_upgrades_empty_database(tmp_path) -> None:
    database_path = tmp_path / "migration.sqlite3"
    database_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"

    upgrade_database(database_url)

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()

    assert {
        "tokens",
        "markets",
        "domain_events",
        "provider_health",
        "token_lifecycle_events",
        "token_trades",
        "market_feature_snapshots",
        "token_risk_assessments",
        "strategy_configurations",
        "strategy_decisions",
        "paper_portfolios",
        "paper_positions",
        "paper_orders",
        "trading_control",
        "token_controls",
        "pending_paper_actions",
        "experiment_runs",
    } <= tables
    assert revision == ("20261009_0018",)
