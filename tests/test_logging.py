from memebot.core.logging import REDACTED, redact_sensitive_fields


def test_sensitive_fields_are_redacted_recursively() -> None:
    event = {
        "event": "provider_started",
        "api_key": "top-secret",
        "token": "public-mint",
        "nested": {"authorization": "Bearer hidden", "mint": "public-address"},
        "items": [{"telegram_bot_token": "hidden-too"}],
    }

    redacted = redact_sensitive_fields(None, "info", event)

    assert redacted["api_key"] == REDACTED
    assert redacted["token"] == "public-mint"
    assert redacted["nested"]["authorization"] == REDACTED
    assert redacted["nested"]["mint"] == "public-address"
    assert redacted["items"][0]["telegram_bot_token"] == REDACTED
