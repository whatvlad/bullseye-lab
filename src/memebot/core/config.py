from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import AnyHttpUrl, AnyUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    """Typed application settings.

    Secrets and environment-specific endpoints come from the environment. Strategy
    parameters will move to versioned database records in Phase 4; they do not
    belong in source code or in this environment-only settings class.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="BULLSEYE_",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    network: Literal["solana"] = "solana"
    execution_mode: Literal["paper", "shadow"] = "paper"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "console"] = "json"

    database_url: str = "postgresql+asyncpg://bullseye:bullseye@localhost:5432/bullseye"
    database_echo: bool = False

    solana_rpc_http_url: AnyHttpUrl = AnyHttpUrl("https://api.mainnet-beta.solana.com")
    solana_rpc_ws_url: AnyUrl = AnyUrl("wss://api.mainnet-beta.solana.com")
    solana_exit_rpc_http_url: AnyHttpUrl = AnyHttpUrl("https://api.mainnet-beta.solana.com")
    solana_commitment: Literal["processed", "confirmed", "finalized"] = "confirmed"
    solana_rpc_timeout_seconds: float = Field(default=15.0, gt=0, le=120)
    solana_ws_open_timeout_seconds: float = Field(default=15.0, gt=0, le=120)
    solana_ws_ping_interval_seconds: float = Field(default=20.0, gt=0, le=120)
    solana_ws_ping_timeout_seconds: float = Field(default=60.0, gt=0, le=120)
    solana_ws_idle_timeout_seconds: float = Field(default=20.0, gt=0, le=120)
    solana_reconnect_base_seconds: float = Field(default=1.0, gt=0, le=60)
    solana_reconnect_max_seconds: float = Field(default=5.0, gt=0, le=300)
    solana_reconnect_jitter_seconds: float = Field(default=0.5, ge=0, le=10)
    solana_invalid_status_halt_threshold: int = Field(default=3, ge=1, le=100)
    solana_halted_probe_seconds: float = Field(default=900, ge=30, le=86400)
    solana_account_retry_count: int = Field(default=4, ge=1, le=10)
    solana_account_retry_delay_seconds: float = Field(default=0.4, ge=0, le=10)
    solana_executed_stream_enabled: bool = True
    solana_executed_stream_session_bytes: int = Field(default=32_000_000, ge=1_000_000)
    # Explicit opt-in; operational user approval caps this at 128 MB/hour.
    solana_executed_stream_hourly_bytes: int = Field(default=0, ge=0, le=128_000_000)
    pump_final_stretch_percent: Decimal = Field(default=Decimal("80"), ge=0, le=100)
    feature_windows_seconds: tuple[int, ...] = (1, 5, 10, 15, 30, 60, 120, 300, 600)
    feature_snapshot_interval_seconds: int = Field(default=1, ge=1, le=60)
    feature_max_lateness_seconds: int = Field(default=5, ge=0, le=60)
    risk_top1_hard_reject_percent: Decimal = Field(default=Decimal("35"), gt=0, le=100)
    risk_top5_warning_percent: Decimal = Field(default=Decimal("90"), gt=0, le=100)
    risk_top10_warning_percent: Decimal = Field(default=Decimal("98"), gt=0, le=100)
    risk_creator_hard_reject_percent: Decimal = Field(default=Decimal("20"), gt=0, le=100)
    risk_largest_buyer_warning_percent: Decimal = Field(default=Decimal("50"), gt=0, le=100)
    risk_synchronized_buyers_warning_count: int = Field(default=3, ge=2, le=100)
    risk_reassessment_interval_seconds: int = Field(default=10, ge=10, le=86400)
    # 0 disables the local assessment quota; queue capacity still bounds memory.
    risk_assessment_max_per_hour: int = Field(default=180, ge=0, le=10000)
    risk_assessment_max_per_day: int = Field(default=2000, ge=0, le=100000)
    risk_prefilter_window_seconds: int = Field(default=30, ge=1, le=600)
    risk_prefilter_min_trades: int = Field(default=2, ge=1, le=10000)
    risk_prefilter_min_unique_buyers: int = Field(default=1, ge=1, le=10000)
    risk_prefilter_min_flow_imbalance: Decimal = Field(default=Decimal("-0.80"), ge=-1, le=1)
    risk_assessment_workers: int = Field(default=2, ge=1, le=8)
    risk_assessment_queue_size: int = Field(default=500, ge=10, le=10000)
    enabled_providers: frozenset[str] = frozenset({"solana_rpc"})

    pumpportal_api_key: SecretStr | None = None
    pumpportal_ws_url: AnyUrl = AnyUrl("wss://pumpportal.fun/api/data")
    pumpportal_candidate_observation_seconds: int = Field(default=60, ge=5, le=600)
    pumpportal_max_active_token_subscriptions: int = Field(default=4, ge=1, le=1000)
    # 0 enables continuous metered streaming until the provider wallet runs out.
    pumpportal_max_trade_events_per_day: int = Field(default=5000, ge=0, le=10_000_000)
    pumpportal_trade_budget_reserve_percent: Decimal = Field(default=Decimal("10"), ge=0, lt=100)
    pumpportal_candidate_subscription_interval_seconds: int = Field(default=2, ge=0, le=86400)
    pumpportal_max_trade_events_per_candidate: int = Field(default=24, ge=1, le=10000)

    birdeye_api_key: SecretStr | None = None
    birdeye_base_url: AnyHttpUrl = AnyHttpUrl("https://public-api.birdeye.so")
    birdeye_timeout_seconds: float = Field(default=10, gt=0, le=60)
    birdeye_cache_seconds: int = Field(default=300, ge=30, le=3600)
    birdeye_minimum_interval_seconds: float = Field(default=1.1, ge=1, le=60)
    birdeye_monthly_cu_budget: int = Field(default=25000, ge=0, le=1_000_000_000)
    alpha_filter_enabled: bool = True
    research_observation_seconds: int = Field(default=3660, ge=60, le=86400)
    research_control_sample_percent: int = Field(default=10, ge=0, le=100)
    research_max_active_subscriptions: int = Field(default=8, ge=1, le=100)
    alpha_filter_shadow_mode: bool = True
    alpha_birdeye_holder_profiles_per_day: int = Field(default=10, ge=0, le=10000)
    alpha_birdeye_cache_seconds: int = Field(default=21600, ge=60, le=86400)
    alpha_max_dev_supply_percent: Decimal = Field(default=Decimal("20"), ge=0, le=100)
    alpha_max_insider_supply_percent: Decimal = Field(default=Decimal("20"), ge=0, le=100)
    alpha_max_bundler_supply_percent: Decimal = Field(default=Decimal("40"), ge=0, le=100)
    alpha_max_sniper_supply_percent: Decimal = Field(default=Decimal("50"), ge=0, le=100)
    telegram_bot_token: SecretStr | None = None
    telegram_allowed_user_ids: frozenset[int] = frozenset()
    telegram_polling_timeout_seconds: int = Field(default=20, ge=5, le=60)
    telegram_max_concurrent_updates: int = Field(default=8, ge=1, le=100)
    telegram_trade_notifications_enabled: bool = True
    telegram_tracked_wallet_notifications_enabled: bool = True
    telegram_notification_queue_size: int = Field(default=200, ge=10, le=5000)
    telegram_notification_minimum_interval_seconds: float = Field(default=1.0, ge=0.1, le=60)
    telegram_notification_duplicate_cooldown_seconds: float = Field(default=60.0, ge=0, le=3600)
    x_bearer_token: SecretStr | None = None

    ollama_base_url: AnyHttpUrl = AnyHttpUrl("http://localhost:11434")
    ollama_model: str | None = None
    ollama_timeout_seconds: float = Field(default=8, gt=0, le=120)

    starting_capital: Decimal = Field(default=Decimal("1000"), gt=0)
    starting_capital_currency: Literal["USDT", "USD"] = "USDT"
    paper_trading_enabled: bool = True
    pulse_enabled: bool = True
    pulse_presets_file: Path = Path("config/pulse.json")
    pulse_max_data_age_seconds: int = Field(default=60, ge=1, le=300)
    paper_base_position_percent: Decimal = Field(default=Decimal("8"), gt=0, le=100)
    paper_max_position_percent: Decimal = Field(default=Decimal("20"), gt=0, le=100)
    paper_max_open_positions: int = Field(default=8, ge=1, le=1000)
    paper_max_total_exposure_percent: Decimal = Field(default=Decimal("40"), gt=0, le=100)
    paper_daily_loss_limit_percent: Decimal = Field(default=Decimal("10"), gt=0, le=100)
    paper_open_risk_budget_percent: Decimal | None = Field(default=None, gt=0, le=100)
    paper_stop_loss_risk_reserve_percent: Decimal = Field(default=Decimal("30"), gt=0, le=100)
    paper_consecutive_loss_limit: int = Field(default=6, ge=1, le=100)
    paper_loss_cooldown_seconds: int = Field(default=600, ge=1, le=86400)
    paper_mint_reentry_cooldown_seconds: int = Field(default=900, ge=1, le=86400)
    paper_venue_fee_bps: Decimal = Field(default=Decimal("125"), ge=0, le=10000)
    paper_execution_provider_fee_bps: Decimal = Field(default=Decimal("50"), ge=0, le=10000)
    paper_latency_slippage_bps: Decimal = Field(default=Decimal("50"), ge=0, le=10000)
    paper_additional_slippage_bps: Decimal = Field(default=Decimal("50"), ge=0, le=5000)
    paper_adverse_fill_bps: Decimal = Field(default=Decimal("50"), ge=0, le=5000)
    paper_network_fee_sol: Decimal = Field(default=Decimal("0.00001"), ge=0)
    paper_priority_fee_sol: Decimal = Field(default=Decimal("0.0001"), ge=0)
    paper_compute_latency_ms: int = Field(default=50, ge=0, le=60000)
    paper_submission_latency_ms: int = Field(default=750, ge=0, le=60000)
    paper_max_market_staleness_seconds: int = Field(default=5, ge=1, le=300)
    # Operational safety limits, not strategy thresholds or fitted trading parameters.
    paper_entry_max_feed_age_seconds: int = Field(default=5, ge=1, le=300)
    paper_entry_require_rpc: bool = True
    paper_entry_allow_estimated_feed_time: bool = False
    paper_exit_recovery_attempt_timeout_seconds: int = Field(default=30, ge=1, le=120)
    paper_entry_max_source_disagreement_percent: Decimal | None = Field(default=None, gt=0)
    paper_max_quote_price_staleness_seconds: int = Field(default=180, ge=10, le=3600)
    paper_pending_entry_ttl_seconds: int = Field(default=30, ge=5, le=300)
    paper_pending_close_ttl_seconds: int = Field(default=30, ge=5, le=3600)
    paper_max_signal_age_seconds: float = Field(default=12, gt=0, le=60)
    paper_max_signal_price_drift_percent: Decimal = Field(default=Decimal("8"), gt=0, le=100)
    paper_min_position_percent: Decimal = Field(default=Decimal("0.5"), gt=0, le=100)
    paper_risk_per_trade_percent: Decimal = Field(default=Decimal("0.5"), gt=0, le=100)
    paper_adaptive_position_sizing: bool = False
    paper_min_order_amount: Decimal = Field(default=Decimal("10"), gt=0)
    paper_runner_enabled: bool = True
    paper_runner_trailing_activation_percent: Decimal = Field(default=Decimal("50"), ge=0)
    paper_runner_trailing_min_percent: Decimal = Field(default=Decimal("18"), gt=0, le=100)
    paper_runner_trailing_max_percent: Decimal = Field(default=Decimal("30"), gt=0, le=100)
    paper_runner_max_holding_seconds: int = Field(default=7200, ge=60, le=86400)
    paper_hazard_confirmation_seconds: float = Field(default=1.0, ge=0, le=30)
    paper_position_monitor_interval_seconds: float = Field(default=5, ge=1, le=300)
    paper_stop_loss_percent: Decimal = Field(default=Decimal("12"), gt=0, le=100)
    paper_take_profit_percent: Decimal = Field(default=Decimal("100"), gt=0)
    paper_take_profit_fraction: Decimal = Field(default=Decimal("0.5"), gt=0, le=1)
    paper_trailing_activation_percent: Decimal = Field(default=Decimal("12"), ge=0)
    paper_trailing_stop_percent: Decimal = Field(default=Decimal("8"), gt=0, le=100)
    paper_max_holding_seconds: int = Field(default=1800, ge=1)
    paper_stagnation_exit_seconds: int = Field(default=120, ge=10, le=3600)
    paper_stagnation_min_mfe_percent: Decimal = Field(default=Decimal("5"), ge=0, le=100)
    paper_max_entry_price_impact_bps_conservative: Decimal = Field(
        default=Decimal("300"), gt=0, le=10000
    )
    paper_max_entry_price_impact_bps_balanced: Decimal = Field(
        default=Decimal("500"), gt=0, le=10000
    )
    paper_max_entry_price_impact_bps_aggressive: Decimal = Field(
        default=Decimal("800"), gt=0, le=10000
    )
    paper_max_round_trip_cost_bps_conservative: Decimal = Field(
        default=Decimal("700"), gt=0, le=10000
    )
    paper_max_round_trip_cost_bps_balanced: Decimal = Field(default=Decimal("700"), gt=0, le=10000)
    paper_max_round_trip_cost_bps_aggressive: Decimal = Field(
        default=Decimal("900"), gt=0, le=10000
    )
    coingecko_base_url: AnyHttpUrl = AnyHttpUrl("https://api.coingecko.com/api/v3")
    social_trading_weight_enabled: bool = False
    wallet_early_entry_seconds: int = Field(default=30, ge=1, le=3600)
    wallet_candidate_min_launches: int = Field(default=3, ge=2, le=1000)
    wallet_scored_min_launches: int = Field(default=10, ge=3, le=10000)
    wallet_high_confidence_min_launches: int = Field(default=30, ge=5, le=100000)
    wallet_success_expansion_percent: Decimal = Field(default=Decimal(50), gt=0, le=10000)

    @field_validator(
        "birdeye_api_key",
        "pumpportal_api_key",
        "telegram_bot_token",
        "x_bearer_token",
        mode="before",
    )
    @classmethod
    def empty_secret_is_unconfigured(cls, value: object) -> object | None:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("database_url")
    @classmethod
    def validate_async_database_driver(cls, value: str) -> str:
        driver = make_url(value).drivername
        if driver not in {"postgresql+asyncpg", "sqlite+aiosqlite"}:
            raise ValueError(
                "database_url must use postgresql+asyncpg; sqlite+aiosqlite is allowed for tests"
            )
        return value

    @field_validator("solana_rpc_ws_url")
    @classmethod
    def use_alchemy_subscription_endpoint(cls, value: AnyUrl) -> AnyUrl:
        # Alchemy documents a dedicated Solana PubSub endpoint. Retain the
        # existing app key/path and leave other providers untouched.
        parts = urlsplit(str(value))
        if parts.scheme == "wss" and parts.hostname == "solana-mainnet.g.alchemy.com":
            return AnyUrl(urlunsplit(parts._replace(netloc="solana-mainnet.streaming.alchemy.com")))
        return value

    @field_validator("telegram_allowed_user_ids")
    @classmethod
    def validate_telegram_user_ids(cls, value: frozenset[int]) -> frozenset[int]:
        if any(user_id <= 0 for user_id in value):
            raise ValueError("telegram allowed user IDs must be positive")
        return value

    @model_validator(mode="after")
    def validate_feature_windows(self) -> Settings:
        if not self.feature_windows_seconds:
            raise ValueError("feature_windows_seconds cannot be empty")
        if any(window <= 0 or window > 3600 for window in self.feature_windows_seconds):
            raise ValueError("feature windows must be between 1 and 3600 seconds")
        if tuple(sorted(set(self.feature_windows_seconds))) != self.feature_windows_seconds:
            raise ValueError("feature windows must be sorted and unique")
        if self.paper_base_position_percent > self.paper_max_position_percent:
            raise ValueError("paper base position cannot exceed maximum position")
        if self.paper_runner_trailing_min_percent > self.paper_runner_trailing_max_percent:
            raise ValueError("runner trailing minimum cannot exceed maximum")
        if self.paper_min_position_percent > self.paper_max_position_percent:
            raise ValueError("minimum position cannot exceed maximum position")
        return self

    def safe_summary(self) -> dict[str, object]:
        """Return non-secret settings suitable for diagnostics and logs."""
        redacted_database_url = make_url(self.database_url).render_as_string(hide_password=True)
        from memebot.core.fingerprint import code_fingerprint

        excluded = {name for name in type(self).model_fields if name.endswith("_url")}
        excluded.update(
            {
                "birdeye_api_key",
                "pumpportal_api_key",
                "telegram_bot_token",
                "x_bearer_token",
                "telegram_allowed_user_ids",
            }
        )
        parameters = self.model_dump(mode="json", exclude=excluded)
        parameters["enabled_providers"] = sorted(self.enabled_providers)
        from memebot.pulse.filters import presets_digest

        parameters["pulse_presets_digest"] = (
            presets_digest(self.pulse_presets_file) if self.pulse_enabled else None
        )
        return {
            "execution_parameters": parameters,
            "code_fingerprint": code_fingerprint(),
            "environment": self.environment,
            "network": self.network,
            "execution_mode": self.execution_mode,
            "database_url": redacted_database_url,
            "solana_rpc_http_host": self.solana_rpc_http_url.host,
            "solana_rpc_ws_host": self.solana_rpc_ws_url.host,
            "solana_executed_stream_enabled": self.solana_executed_stream_enabled,
            "solana_executed_stream_session_bytes": self.solana_executed_stream_session_bytes,
            "solana_executed_stream_hourly_bytes": self.solana_executed_stream_hourly_bytes,
            "solana_exit_rpc_http_host": self.solana_exit_rpc_http_url.host,
            "solana_commitment": self.solana_commitment,
            "solana_rpc_timeout_seconds": self.solana_rpc_timeout_seconds,
            "solana_ws_open_timeout_seconds": self.solana_ws_open_timeout_seconds,
            "solana_reconnect_base_seconds": self.solana_reconnect_base_seconds,
            "solana_reconnect_max_seconds": self.solana_reconnect_max_seconds,
            "solana_invalid_status_halt_threshold": (self.solana_invalid_status_halt_threshold),
            "solana_halted_probe_seconds": self.solana_halted_probe_seconds,
            "solana_account_retry_count": self.solana_account_retry_count,
            "solana_account_retry_delay_seconds": (self.solana_account_retry_delay_seconds),
            "pump_final_stretch_percent": str(self.pump_final_stretch_percent),
            "feature_windows_seconds": list(self.feature_windows_seconds),
            "feature_snapshot_interval_seconds": self.feature_snapshot_interval_seconds,
            "feature_max_lateness_seconds": self.feature_max_lateness_seconds,
            "risk_top1_hard_reject_percent": str(self.risk_top1_hard_reject_percent),
            "risk_top5_warning_percent": str(self.risk_top5_warning_percent),
            "risk_top10_warning_percent": str(self.risk_top10_warning_percent),
            "risk_creator_hard_reject_percent": str(self.risk_creator_hard_reject_percent),
            "risk_reassessment_interval_seconds": self.risk_reassessment_interval_seconds,
            "risk_assessment_max_per_hour": self.risk_assessment_max_per_hour,
            "risk_assessment_max_per_day": self.risk_assessment_max_per_day,
            "risk_assessment_workers": self.risk_assessment_workers,
            "enabled_providers": sorted(self.enabled_providers),
            "pumpportal_configured": self.pumpportal_api_key is not None,
            "pumpportal_host": self.pumpportal_ws_url.host,
            "pumpportal_candidate_observation_seconds": (
                self.pumpportal_candidate_observation_seconds
            ),
            "pumpportal_max_active_token_subscriptions": (
                self.pumpportal_max_active_token_subscriptions
            ),
            "pumpportal_max_trade_events_per_day": (self.pumpportal_max_trade_events_per_day),
            "pumpportal_trade_budget_reserve_percent": str(
                self.pumpportal_trade_budget_reserve_percent
            ),
            "pumpportal_candidate_subscription_interval_seconds": (
                self.pumpportal_candidate_subscription_interval_seconds
            ),
            "pumpportal_max_trade_events_per_candidate": (
                self.pumpportal_max_trade_events_per_candidate
            ),
            "birdeye_configured": self.birdeye_api_key is not None,
            "birdeye_runtime_mode": (
                "on_demand_rest" if self.birdeye_api_key is not None else "disabled"
            ),
            "birdeye_host": self.birdeye_base_url.host,
            "birdeye_monthly_cu_budget": self.birdeye_monthly_cu_budget,
            "alpha_filter_enabled": self.alpha_filter_enabled,
            "alpha_filter_shadow_mode": self.alpha_filter_shadow_mode,
            "alpha_birdeye_holder_profiles_per_day": (self.alpha_birdeye_holder_profiles_per_day),
            "telegram_configured": self.telegram_bot_token is not None,
            "telegram_access_configured": bool(self.telegram_allowed_user_ids),
            "telegram_allowed_user_count": len(self.telegram_allowed_user_ids),
            "telegram_trade_notifications_enabled": (self.telegram_trade_notifications_enabled),
            "telegram_tracked_wallet_notifications_enabled": (
                self.telegram_tracked_wallet_notifications_enabled
            ),
            "x_configured": self.x_bearer_token is not None,
            "ollama_model_configured": bool(self.ollama_model),
            "starting_capital": str(self.starting_capital),
            "starting_capital_currency": self.starting_capital_currency,
            "paper_trading_enabled": self.paper_trading_enabled,
            "paper_base_position_percent": str(self.paper_base_position_percent),
            "paper_max_position_percent": str(self.paper_max_position_percent),
            "paper_max_open_positions": self.paper_max_open_positions,
            "paper_max_total_exposure_percent": str(self.paper_max_total_exposure_percent),
            "paper_daily_loss_limit_percent": str(self.paper_daily_loss_limit_percent),
            "paper_stop_loss_risk_reserve_percent": str(self.paper_stop_loss_risk_reserve_percent),
            "paper_consecutive_loss_limit": self.paper_consecutive_loss_limit,
            "paper_loss_cooldown_seconds": self.paper_loss_cooldown_seconds,
            "paper_mint_reentry_cooldown_seconds": (self.paper_mint_reentry_cooldown_seconds),
            "paper_venue_fee_bps": str(self.paper_venue_fee_bps),
            "paper_execution_provider_fee_bps": str(self.paper_execution_provider_fee_bps),
            "paper_latency_slippage_bps": str(self.paper_latency_slippage_bps),
            "paper_additional_slippage_bps": str(self.paper_additional_slippage_bps),
            "paper_adverse_fill_bps": str(self.paper_adverse_fill_bps),
            "paper_compute_latency_ms": self.paper_compute_latency_ms,
            "paper_submission_latency_ms": self.paper_submission_latency_ms,
            "paper_max_market_staleness_seconds": (self.paper_max_market_staleness_seconds),
            "paper_entry_max_feed_age_seconds": self.paper_entry_max_feed_age_seconds,
            "paper_entry_require_rpc": self.paper_entry_require_rpc,
            "paper_entry_allow_estimated_feed_time": self.paper_entry_allow_estimated_feed_time,
            "paper_entry_max_source_disagreement_percent": (
                str(self.paper_entry_max_source_disagreement_percent)
                if self.paper_entry_max_source_disagreement_percent is not None
                else None
            ),
            "paper_exit_recovery_attempt_timeout_seconds": (
                self.paper_exit_recovery_attempt_timeout_seconds
            ),
            "paper_pending_entry_ttl_seconds": self.paper_pending_entry_ttl_seconds,
            "paper_pending_close_ttl_seconds": self.paper_pending_close_ttl_seconds,
            "paper_position_monitor_interval_seconds": (
                self.paper_position_monitor_interval_seconds
            ),
            "paper_stop_loss_percent": str(self.paper_stop_loss_percent),
            "paper_take_profit_percent": str(self.paper_take_profit_percent),
            "paper_trailing_stop_percent": str(self.paper_trailing_stop_percent),
            "paper_stagnation_exit_seconds": self.paper_stagnation_exit_seconds,
            "paper_stagnation_min_mfe_percent": str(self.paper_stagnation_min_mfe_percent),
            "paper_max_entry_price_impact_bps": {
                "conservative": str(self.paper_max_entry_price_impact_bps_conservative),
                "balanced": str(self.paper_max_entry_price_impact_bps_balanced),
                "aggressive": str(self.paper_max_entry_price_impact_bps_aggressive),
            },
            "paper_max_round_trip_cost_bps": {
                "conservative": str(self.paper_max_round_trip_cost_bps_conservative),
                "balanced": str(self.paper_max_round_trip_cost_bps_balanced),
                "aggressive": str(self.paper_max_round_trip_cost_bps_aggressive),
            },
            "coingecko_host": self.coingecko_base_url.host,
            "social_trading_weight_enabled": self.social_trading_weight_enabled,
            "wallet_early_entry_seconds": self.wallet_early_entry_seconds,
            "wallet_candidate_min_launches": self.wallet_candidate_min_launches,
            "wallet_scored_min_launches": self.wallet_scored_min_launches,
            "wallet_high_confidence_min_launches": (self.wallet_high_confidence_min_launches),
        }
