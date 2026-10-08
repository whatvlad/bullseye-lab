"""Synthetic reproduction of an unstable sell-MAD hazard signal. No database or network."""
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from memebot.events.models import TokenTrade, TradeSide
from memebot.intelligence.features.engine import RollingFeatureEngine
from memebot.paper.dump_hazard import has_dump_hazard


engine = RollingFeatureEngine((30,))
base = datetime(2026, 9, 13, tzinfo=UTC)
amounts = [('buy', '0.1'), ('sell', '1'), ('sell', '1'),
           ('buy', '0.1'), ('sell', '1'), ('sell', '1.0001')]
for index, (side, sol) in enumerate(amounts):
    amount = Decimal(sol) * 1_000_000_000
    trade = TokenTrade(event_id=UUID(int=index + 1), provider='audit_synthetic',
        source_event_at=base + timedelta(seconds=index),
        mint='So11111111111111111111111111111111111111112',
        signature='7' * 32, side=TradeSide(side), token_amount=amount,
        quote_amount=amount, quote_asset='SOL')
    snapshot = engine.ingest_trade(trade)
assert snapshot is not None
metric = snapshot.windows[0]
result = {'synthetic_only': True, 'unchanged_price': str(metric.price_change_percent),
          'last_sell_increase_percent': '0.01',
          'latest_sell_size_mad_score': str(metric.latest_sell_size_mad_score),
          'flow_imbalance': str(metric.flow_imbalance),
          'dump_hazard': has_dump_hazard(trade, snapshot)}
assert result['dump_hazard'] is True
assert metric.price_change_percent == 0
assert metric.latest_sell_size_mad_score == 999
print(json.dumps(result, indent=2))
