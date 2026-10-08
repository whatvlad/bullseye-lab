"""Consistent marginal marks; a trade's average fill is not a spot quote."""

from decimal import Decimal

from memebot.events.models import TokenTrade


def trade_mark(event: TokenTrade) -> Decimal:
    if event.normalized_state.state_source == "native_event":
        # Invalid observation is retained only as an explicitly historical trade
        # average. Features/outcomes never use this fallback as current state.
        return event.normalized_state.observational_price or event.quote_amount / event.token_amount
    if event.virtual_token_reserves and event.virtual_quote_reserves:
        return Decimal(event.virtual_quote_reserves) / Decimal(event.virtual_token_reserves)
    if event.real_token_reserves and event.real_quote_reserves:
        quote = event.real_quote_reserves + (event.virtual_quote_reserves or 0)
        return Decimal(quote) / Decimal(event.real_token_reserves)
    # Explicit fallback for historical/vendor trades without reserves.
    return event.quote_amount / event.token_amount
