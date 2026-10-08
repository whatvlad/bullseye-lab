from uuid import NAMESPACE_URL, uuid5

from memebot.events.models import TokenLifecycleChanged
from memebot.models.market import MarketLifecycle, MarketValidationState

from .models import ExecutionMarketSnapshot


def recovery_event(market: ExecutionMarketSnapshot) -> TokenLifecycleChanged:
    return TokenLifecycleChanged(
        event_id=uuid5(NAMESPACE_URL, f"bullseye:recovered:{market.mint}:{market.market}"),
        provider="bullseye_rpc_market_recovery",
        source_event_at=market.observed_at,
        source_slot=market.source_slot,
        mint=market.mint,
        lifecycle=MarketLifecycle.POST_GRADUATION,
        validation_state=MarketValidationState.VERIFIED_MARKET_DATA,
        bonding_progress_percent=100,
        market=market.market,
        quote_mint=market.quote_asset,
        real_token_reserves=market.real_token_reserves_raw,
        real_quote_reserves=market.real_quote_reserves_raw,
        reason="completed_curve_recovered_to_rpc_verified_pumpswap",
    )
