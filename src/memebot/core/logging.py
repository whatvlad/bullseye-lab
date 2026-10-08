from __future__ import annotations

import logging
import sys
from collections.abc import Mapping, MutableMapping
from typing import Any, Literal, cast

import structlog

REDACTED = "[REDACTED]"
_SENSITIVE_KEYS = {
    "api_key",
    "authorization",
    "birdeye_api_key",
    "database_password",
    "database_url",
    "password",
    "private_key",
    "secret",
    "solana_rpc_http_url",
    "solana_rpc_ws_url",
    "telegram_bot_token",
    "x_bearer_token",
}


def _redact_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            key: REDACTED if str(key).lower() in _SENSITIVE_KEYS else _redact_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(item) for item in value)
    return value


def redact_sensitive_fields(
    _logger: object,
    _method_name: str,
    event_dict: MutableMapping[str, Any],
) -> Mapping[str, Any]:
    """Redact known secret-bearing fields before rendering any log event."""
    return cast(dict[str, Any], _redact_value(event_dict))


def configure_logging(
    level: str = "INFO",
    output_format: Literal["json", "console"] = "json",
) -> None:
    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        redact_sensitive_fields,
        structlog.processors.format_exc_info,
    ]
    renderer: structlog.types.Processor
    if output_format == "json":
        renderer = structlog.processors.JSONRenderer(sort_keys=True)
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    logging.basicConfig(format="%(message)s", level=level, stream=sys.stderr, force=True)
    # HTTP clients include the complete request URL in INFO records. RPC query
    # strings can contain credentials, so transport libraries stay warning-only.
    for noisy_logger in ("httpx", "httpcore", "websockets"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
    structlog.configure(
        processors=[*processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "memebot") -> structlog.stdlib.BoundLogger:
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))
