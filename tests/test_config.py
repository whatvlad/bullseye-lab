from pathlib import Path

import pytest
from pydantic import ValidationError

from memebot.core.config import Settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_settings_are_solana_and_paper_only() -> None:
    settings = Settings(_env_file=None)

    assert settings.network == "solana"
    assert settings.execution_mode == "paper"
    assert "live" not in Settings.model_fields
    assert "private_key" not in Settings.model_fields
    assert "signer" not in Settings.model_fields


def test_example_environment_file_is_valid() -> None:
    settings = Settings(_env_file=PROJECT_ROOT / ".env.example")

    assert settings.execution_mode == "paper"
    assert settings.birdeye_api_key is None
    assert settings.telegram_bot_token is None


def test_safe_summary_never_contains_secrets() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://user:database-secret@localhost/bullseye",
        birdeye_api_key="birdeye-secret",
        pumpportal_api_key="pumpportal-secret",
        telegram_bot_token="telegram-secret",
        x_bearer_token="x-secret",
    )

    rendered = str(settings.safe_summary())

    assert "database-secret" not in rendered
    assert "birdeye-secret" not in rendered
    assert "pumpportal-secret" not in rendered
    assert "telegram-secret" not in rendered
    assert "x-secret" not in rendered
    assert settings.safe_summary()["birdeye_configured"] is True
    assert settings.safe_summary()["pumpportal_configured"] is True


def test_sync_database_driver_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="postgresql://localhost/bullseye")


def test_blank_optional_secrets_are_not_treated_as_configured() -> None:
    settings = Settings(
        _env_file=None,
        birdeye_api_key="",
        pumpportal_api_key="",
        telegram_bot_token="   ",
        x_bearer_token="",
    )

    assert settings.birdeye_api_key is None
    assert settings.pumpportal_api_key is None
    assert settings.telegram_bot_token is None
    assert settings.x_bearer_token is None


def test_live_execution_mode_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, execution_mode="live")


def test_explicit_shadow_mode_still_cannot_enable_live():
    assert Settings(_env_file=None, execution_mode="shadow").execution_mode == "shadow"
