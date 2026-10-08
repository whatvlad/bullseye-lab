"""Summarize the read-only audit export without touching the database."""
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import median


def number(value):
    return float(value or 0)


def stats(rows):
    pnl = [number(x['realized_pnl']) for x in rows]
    wins = [x for x in pnl if x > 0]
    losses = [x for x in pnl if x < 0]
    return {'n': len(rows), 'wins': len(wins), 'pnl': sum(pnl),
            'win_rate': 100 * len(wins) / len(rows) if rows else None,
            'profit_factor': sum(wins) / -sum(losses) if losses else None,
            'mean_win': sum(wins) / len(wins) if wins else None,
            'mean_loss': sum(losses) / len(losses) if losses else None,
            'mean_pnl_percent': sum(number(x['pnl_percent']) for x in rows) / len(rows) if rows else None,
            'median_holding_seconds': median(number(x['holding_seconds']) for x in rows) if rows else None,
            'median_mfe': median(number(x['mfe_percent']) for x in rows) if rows else None,
            'median_mae': median(number(x['mae_percent']) for x in rows) if rows else None,
            'mfe_ge_25': sum(number(x['mfe_percent']) >= 25 for x in rows),
            'mfe_ge_100': sum(number(x['mfe_percent']) >= 100 for x in rows),
            'pnl_without_largest_winner': sum(pnl) - max(wins, default=0)}


def main():
    data = json.loads(Path('docs/audit-data-2026-09-13.json').read_text(encoding='utf-8'))
    trades = [x for x in data['trades'] if x['status'] == 'closed']
    portfolios = {x['id']: x for x in data['portfolios']}
    fills = {x['event_id']: x for x in data['filled_orders']}
    triggers = {x['order_event_id']: x for x in data['exit_trigger_trades']}
    coverage = {x['position_id']: x for x in data['post_exit_coverage']}
    report = {'all_trades_mixed_history': stats(trades), 'by_portfolio': [], 'by_exit': {},
              'experiments': [], 'recent_trades': [], 'price_discrepancies': []}
    for pid, portfolio in portfolios.items():
        group = [x for x in trades if x['portfolio_id'] == pid]
        if group:
            report['by_portfolio'].append(dict(name=portfolio['name'], **stats(group)))
    for reason in sorted({x['exit_reason'] for x in trades}, key=str):
        group = [x for x in trades if x['exit_reason'] == reason]
        report['by_exit'][reason] = stats(group)
    for experiment in data['experiments']:
        group = [x for x in trades if x['portfolio_id'] == experiment['portfolio_id']]
        orders = [x for x in data['filled_orders'] if x['portfolio_id'] == experiment['portfolio_id']]
        latencies = [(datetime.fromisoformat(x['filled_at']) - datetime.fromisoformat(x['signal_at'])).total_seconds() for x in orders if x['side'] == 'buy']
        report['experiments'].append(dict(name=experiment['name'], strategy=experiment['strategy_key'],
            start=experiment['started_at'], end=experiment['stopped_at'],
            version_id=experiment['strategy_version_id'], **stats(group),
            exit_reasons=dict(Counter(x['exit_reason'] for x in group)),
            fees=sum(number(x['fill_json']['total_fee_portfolio']) for x in orders),
            median_signal_to_fill_seconds=median(latencies) if latencies else None,
            post_exit_with_any_data=sum(coverage[x['position_id']]['observations'] > 0 for x in group)))
    for trade in trades:
        exit_order = fills.get(trade['exit_order_event_id'])
        trigger = triggers.get(trade['exit_order_event_id'])
        row = {k:trade[k] for k in ('mint','entry_at','exit_reason','realized_pnl','pnl_percent','holding_seconds','mfe_percent','mae_percent')}
        row['portfolio'] = portfolios[trade['portfolio_id']]['name']
        row['post_exit'] = coverage[trade['position_id']]
        row['entry_cost'] = trade['entry_cost_portfolio']
        row['entry_score'] = (trade['score_snapshot_json'] or {}).get('final_score')
        if exit_order:
            row['exit_snapshot_return_percent'] = (number(exit_order['fill_json']['observed_price_raw']) / number(trade['actual_entry_price_raw']) - 1) * 100
        if trigger:
            row['exit_trigger_return_percent'] = (number(trigger['price_raw']) / number(trade['actual_entry_price_raw']) - 1) * 100
            row['trigger_minus_fill_snapshot_percent'] = (number(trigger['price_raw']) / number(exit_order['fill_json']['observed_price_raw']) - 1) * 100
            row['trigger_age_at_decision_seconds'] = (datetime.fromisoformat(exit_order['decision_at']) - datetime.fromisoformat(trigger['source_event_at'])).total_seconds()
            if abs(row['trigger_minus_fill_snapshot_percent']) > 10:
                report['price_discrepancies'].append(row)
        if trade['entry_at'] >= '2026-08-25':
            report['recent_trades'].append(row)
    report['decision_coverage'] = data['decision_coverage']
    latest_id = next(x['portfolio_id'] for x in data['experiments'] if x['name'] == 'baseline-v5-fixed')
    latest_trades = [x for x in trades if x['portfolio_id'] == latest_id]
    report['latest_by_exit'] = {reason: stats([x for x in latest_trades if x['exit_reason'] == reason]) for reason in {x['exit_reason'] for x in latest_trades}}
    report['latest_score_buckets'] = {str(low): stats([x for x in latest_trades if low <= number((x['score_snapshot_json'] or {}).get('final_score')) < low + 10]) for low in (50,60,70,80,90)}
    quality = []
    for trade in latest_trades:
        order = fills.get(trade['exit_order_event_id'])
        trigger = triggers.get(trade['exit_order_event_id'])
        if not trigger or not order:
            continue
        row = dict(mint=trade['mint'], reason=trade['exit_reason'],
            trigger_before_entry_fill_seconds=(datetime.fromisoformat(trade['entry_at']) - datetime.fromisoformat(trigger['source_event_at'])).total_seconds(),
            snapshot_return_percent=(number(order['fill_json']['observed_price_raw']) / number(trade['actual_entry_price_raw']) - 1) * 100,
            signal_return_percent=(number(trigger['price_raw']) / number(trade['actual_entry_price_raw']) - 1) * 100)
        if number(trigger.get('virtual_token_reserves')) > 0:
            reserve_price = number(trigger['virtual_quote_reserves']) / number(trigger['virtual_token_reserves'])
            row['same_event_reserve_return_percent'] = (reserve_price / number(trade['actual_entry_price_raw']) - 1) * 100
        quality.append(row)
    report['latest_quality'] = quality
    report['latest_before_fill_exit_triggers'] = sum(x['trigger_before_entry_fill_seconds'] > 0 for x in quality)
    report['latest_stops_refreshed_above_stop'] = sum(x['reason'] == 'stop_loss' and x['snapshot_return_percent'] > -12 for x in quality)
    report['latest_positions_with_zero_mfe_and_mae'] = sum(number(x['mfe_percent']) == number(x['mae_percent']) == 0 for x in latest_trades)
    report['latest_wallet_missing'] = sum(any(c['name'] == 'wallet' and c['availability'] != 'available' for c in x['score_snapshot_json']['components']) for x in latest_trades)
    report['latest_reserve_velocity_missing'] = sum(all(w.get('quote_reserve_velocity_raw_per_second') is None for w in x['feature_snapshot_json']['windows']) for x in latest_trades)
    report['post_exit_with_any_data'] = sum(x['observations'] > 0 for x in coverage.values())
    report['position_outcome_missing'] = [{'mint':x['mint'], 'status':x['status'], 'pnl':x['realized_pnl'], 'portfolio':portfolios[x['portfolio_id']]['name']} for x in data['positions'] if x['id'] not in {t['position_id'] for t in data['trades']}]
    Path('docs/audit-metrics-2026-09-13.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    for key in ('latest_by_exit','latest_score_buckets','latest_before_fill_exit_triggers','latest_stops_refreshed_above_stop','latest_positions_with_zero_mfe_and_mae','latest_wallet_missing','latest_reserve_velocity_missing','latest_quality'):
        print(key, json.dumps(report[key], indent=2))


if __name__ == '__main__':
    main()
