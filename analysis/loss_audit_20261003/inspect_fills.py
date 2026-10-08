import json
from decimal import Decimal as D
from pathlib import Path
s = json.loads(Path('analysis/loss_audit_20261003/snapshot.json').read_text(encoding='utf-8'))
tokens = {t['mint']: t for t in s['tokens']}
for t in s['outcomes']:
    orders = [o for o in s['filled_orders'] if o['mint'] == t['mint'] and
              (o['event_id'] == t['entry_order_event_id'] or (o['side'] == 'sell' and t['entry_at'] <= o['filled_at'] <= t['exit_at']))]
    buy = next(o for o in orders if o['side'] == 'buy')['fill_json']
    sell = [o for o in orders if o['side'] == 'sell'][-1]['fill_json']
    ev = {r['code']: r['value'] for r in buy['evidence']}
    p = next(p for p in s['positions'] if p['id'] == t['position_id'])
    print(json.dumps({'coin': tokens[t['mint']]['symbol'], 'mint': t['mint'],
        'ref_change_pct': str((D(sell['reference_price']) / D(buy['reference_price'])-1)*100),
        'round_trip_cost_pct': str(D(ev.get('estimated_round_trip_cost_bps', 0))/100),
        'buy_impact_pct': str(D(buy['price_impact'])/100),
        'sell_impact_pct': str(D(sell['price_impact'])/100),
        'signal_to_fill_s': str((__import__('datetime').datetime.fromisoformat(buy['filled_at'])-__import__('datetime').datetime.fromisoformat(buy['signal_at'])).total_seconds()),
        'feed_age_ms': buy['feed_age_ms'], 'entry_quality': buy['data_quality'],
        'peak_stats': (p['execution_mark_json'] or {}).get('executable_statistics'),
        'buy_model': buy.get('execution_state', {}).get('model', 'curve'),
        'sell_model': sell.get('execution_state', {}).get('model', 'curve'),
    }))
print('SETTINGS')
c=json.loads(Path('analysis/loss_audit_20261003/current_settings.json').read_text(encoding='utf-8'))['execution_parameters']
print(json.dumps({k:v for k,v in c.items() if any(word in k for word in ('fee', 'slippage', 'adverse', 'trailing', 'round_trip', 'signal_age', 'stop_loss', 'risk_per_trade', 'stagnation'))}))
print('FEATURE EXAMPLE')
print(json.dumps(s['outcomes'][-1]['feature_snapshot_json'], indent=2)[:8000])
