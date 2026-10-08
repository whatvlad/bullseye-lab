"""Audit retained PAPER fills only; no database or provider calls, no strategy replay."""
from collections import Counter
from datetime import datetime, timezone, timedelta
from decimal import Decimal as D
import csv
import json
from pathlib import Path
from statistics import median

from memebot.paper.standard_math import sell_quote
from memebot.paper.migration_exit import migration_sell_quote

ROOT = Path(__file__).resolve().parent
BPS = D(10000)
UNIT = D(10**9)
LOCAL = timezone(timedelta(hours=1), 'Europe/Dublin (2026-10-03)')


def dec(value):
    return D(str(value))


def timestamp(value):
    return datetime.fromisoformat(value)


def ev(fill):
    return {item['code']: item['value'] for item in fill['evidence']}


def analyze(folder, label):
    snapshot = json.loads((folder / 'snapshot.json').read_text(encoding='utf-8'))
    tokens = {token['mint']: token for token in snapshot['tokens']}
    positions = {position['id']: position for position in snapshot['positions']}
    evidence = {record['event_id']: record['payload'] for record in snapshot['evidence']}
    trades = []
    for index, trade in enumerate(snapshot['outcomes'], 1):
        assert trade['status'] == 'closed', 'Open exposure requires a separate unrealized analysis'
        orders = [order for order in snapshot['filled_orders'] if order['mint'] == trade['mint']
                  and (order['event_id'] == trade['entry_order_event_id']
                       or (order['side'] == 'sell' and trade['entry_at'] <= order['filled_at'] <= trade['exit_at']))]
        entry = next(order['fill_json'] for order in orders if order['side'] == 'buy')
        exits = [order['fill_json'] for order in orders if order['side'] == 'sell']
        entry_ev = ev(entry)
        q0 = dec(entry_ev['unadjusted_token_amount_raw'])
        qa = dec(entry['token_amount_raw'])
        entry_unit = dec(entry['quote_price_in_portfolio_currency']) / UNIT
        entry_curve_cost = (dec(entry['gross_quote_amount_raw']) - dec(entry['venue_fee_quote_raw'])) * entry_unit
        original_cost = dec(entry['gross_portfolio_amount']) + (
            dec(entry['network_fee_quote_raw']) + dec(entry['execution_provider_fee_quote_raw'])) * entry_unit
        actual_proceeds = sum((dec(fill['gross_portfolio_amount']) - dec(fill['total_fee_portfolio']) for fill in exits), D(0))
        replay_net = actual_proceeds - original_cost
        pnl = dec(trade['realized_pnl'])
        assert abs(replay_net - pnl) < D('0.00000002'), (trade['mint'], replay_net, pnl)
        assert sum((dec(fill['token_amount_raw']) for fill in exits), D(0)) == qa
        curve_exit = actual_gross = spot_exit = D(0)
        for fill in exits:
            state = fill['execution_state']
            quantity = int(q0 * dec(fill['token_amount_raw']) / qa)
            quote = (migration_sell_quote(state, quantity) if state.get('model') == 'canonical_pumpswap_exit'
                     else sell_quote(state['curve'], quantity, state['rates']))
            exit_unit = dec(fill['quote_price_in_portfolio_currency']) / UNIT
            curve_exit += D(quote['gross_output']) * exit_unit
            actual_gross += dec(fill['gross_portfolio_amount'])
            spot_exit += D(quantity) * dec(fill['reference_price']) * exit_unit
        venue = sum((dec(fill['venue_fee_quote_raw']) * dec(fill['quote_price_in_portfolio_currency']) / UNIT for fill in [entry, *exits]), D(0))
        provider = sum((dec(fill['execution_provider_fee_quote_raw']) * dec(fill['quote_price_in_portfolio_currency']) / UNIT for fill in [entry, *exits]), D(0))
        network = sum((dec(fill['network_fee_quote_raw']) * dec(fill['quote_price_in_portfolio_currency']) / UNIT for fill in [entry, *exits]), D(0))
        fees = venue + provider + network
        friction = curve_exit - actual_gross
        curve_pnl = curve_exit - entry_curve_cost
        spot_entry = q0 * dec(entry['reference_price']) * entry_unit
        spot_pnl = spot_exit - spot_entry
        impact = (entry_curve_cost - spot_entry) + (spot_exit - curve_exit)
        assert abs((curve_pnl - friction - fees) - pnl) < D('0.00000002')
        assert abs(spot_pnl - impact - curve_pnl) < D('0.00000002')
        state = entry['execution_state']
        immediate_quote = sell_quote(state['curve'], int(qa), state['rates'])
        friction_bps = dec(entry['slippage'])
        immediate_gross = D(immediate_quote['gross_output']) * (1 - friction_bps/BPS)
        # Integer rounding matches the simulator's sell-side ROUND_DOWN.
        immediate_gross = D(int(immediate_gross))
        immediate_price_loss = (1 - immediate_gross / qa / dec(entry['actual_fill_price_raw'])) * 100
        stop_net_proceeds = (dec(entry['gross_portfolio_amount']) * D('.88')
                            * (1 - D(state['rates']['protocol_bps'] + state['rates']['creator_bps']) / BPS
                               - dec(entry['execution_provider_fee_quote_raw']) / dec(entry['gross_quote_amount_raw']))
                            - dec(entry['network_fee_quote_raw']) * entry_unit)
        score = trade['score_snapshot_json']
        window = next(metric for metric in trade['feature_snapshot_json']['windows'] if metric['window_seconds'] == 10)
        position = positions[trade['position_id']]
        mark = position['execution_mark_json'] or {}
        decision = evidence.get(trade['entry_decision_event_id'], {})
        quality = decision.get('price_evidence') or trade['feature_snapshot_json'].get('price_evidence', {})
        symbol = tokens[trade['mint']].get('symbol') or trade['mint'][:8]
        item = {
            'cohort': label, 'number': index, 'symbol': symbol, 'mint': trade['mint'],
            'entry_at_utc': trade['entry_at'], 'exit_at_utc': trade['exit_at'],
            'entry_at_dublin': timestamp(trade['entry_at']).astimezone(LOCAL).isoformat(),
            'holding_seconds': (timestamp(trade['exit_at']) - timestamp(trade['entry_at'])).total_seconds(),
            'entry_cost_usdt': original_cost, 'net_pnl_usdt': pnl, 'pnl_percent': dec(trade['pnl_percent']),
            'exit_reason': trade['exit_reason'], 'sell_count': len(exits),
            'round_trip_cost_percent': dec(entry_ev['estimated_round_trip_cost_bps'])/100,
            'immediate_gross_price_loss_percent': immediate_price_loss,
            'approx_net_loss_at_exact_gross_12pct_stop_percent': (1 - stop_net_proceeds/original_cost) * 100,
            'signal_to_fill_seconds': (timestamp(entry['filled_at']) - timestamp(entry['signal_at'])).total_seconds(),
            'decision_to_fill_seconds': (timestamp(entry['filled_at']) - timestamp(entry['decision_at'])).total_seconds(),
            'feed_age_ms': entry['feed_age_ms'], 'atomic_price_age_ms': entry['price_age_ms'],
            'fixed_simulated_latency_ms': entry['simulated_latency_ms'],
            'buy_price_impact_percent': dec(entry['price_impact_bps'])/100,
            'final_reference_price_change_percent': (dec(exits[-1]['reference_price'])/dec(entry['reference_price']) - 1)*100,
            'final_gross_fill_price_change_percent': (dec(exits[-1]['actual_fill_price_raw'])/dec(entry['actual_fill_price_raw']) - 1)*100,
            'recorded_observed_mfe_percent': trade['mfe_percent'], 'recorded_observed_mae_percent': trade['mae_percent'],
            'executable_statistics': mark.get('executable_statistics'),
            'retained_mark_at': mark.get('market_observed_at'), 'retained_mark_signal_at': mark.get('signal_at'),
            'retained_mark_to_sell_seconds': (timestamp(exits[-1]['filled_at'])-timestamp(mark['market_observed_at'])).total_seconds() if mark.get('market_observed_at') else None,
            'decision_price': decision.get('decision_price'), 'buy_decision_price': entry['decision_price'],
            'window_price_change_percent': window.get('price_change_percent'),
            'score': score['final_score'], 'score_completeness_percent': score['component_completeness_percent'],
            'feature_price_source': quality.get('price_source'),
            'feature_continuity_status': quality.get('continuity_status'),
            'feature_state_reason': quality.get('state_reason'), 'feature_state_quality': quality.get('state_quality'),
            'feature_observational_trust': quality.get('observational_trust'),
            'buy_fill_quality': entry['data_quality'], 'exit_model': exits[-1]['execution_state'].get('model', 'standard_curve'),
            'decomposition': {'spot_reserve_move_and_sol_fx_pnl': spot_pnl,
                              'curve_price_impact_cost': impact,
                              'curve_price_pnl_before_fees_friction': curve_pnl,
                              'configured_friction_cost': friction, 'venue_fees': venue,
                              'modeled_provider_fees': provider, 'modeled_network_fees': network,
                              'total_fees': fees, 'replayed_net_pnl': replay_net,
                              'basis': 'retained execution banks, undo configured friction; same exit times and proportional sell quantities'},
        }
        trades.append(item)
    portfolio = snapshot['portfolio']
    sums = {key: sum((item['decomposition'][key] for item in trades), D(0))
            for key in trades[0]['decomposition'] if key != 'basis'}
    pnl = sum((item['net_pnl_usdt'] for item in trades), D(0))
    assert pnl == dec(portfolio['realized_pnl'])
    assert dec(portfolio['cash_balance']) == dec(portfolio['initial_cash']) + pnl
    reject_by_mint = Counter(order['mint'] for order in snapshot['exit_rejections'])
    summary = {
        'label': label, 'snapshot_captured_at': snapshot['captured_at'], 'portfolio_id': portfolio['id'],
        'portfolio_created_at': portfolio['created_at'], 'active': portfolio['active'],
        'initial_cash_usdt': portfolio['initial_cash'], 'cash_usdt': portfolio['cash_balance'],
        'net_pnl_usdt': pnl, 'closed_positions': len(trades), 'filled_orders': len(snapshot['filled_orders']),
        'open_positions': sum(position['status'] == 'open' for position in snapshot['positions']),
        'wins': sum(item['net_pnl_usdt'] > 0 for item in trades),
        'losses': sum(item['net_pnl_usdt'] < 0 for item in trades),
        'positions_with_missing_price_change': sum(item['window_price_change_percent'] is None for item in trades),
        'positions_with_score_completeness_100': sum(dec(item['score_completeness_percent']) == 100 for item in trades),
        'median_signal_to_fill_seconds': median(item['signal_to_fill_seconds'] for item in trades),
        'median_decision_to_fill_seconds': median(item['decision_to_fill_seconds'] for item in trades),
        'round_trip_cost_percent_min': min(item['round_trip_cost_percent'] for item in trades),
        'round_trip_cost_percent_max': max(item['round_trip_cost_percent'] for item in trades),
        'immediate_gross_price_loss_percent_min': min(item['immediate_gross_price_loss_percent'] for item in trades),
        'immediate_gross_price_loss_percent_max': max(item['immediate_gross_price_loss_percent'] for item in trades),
        'hold_under_10_seconds': sum(item['holding_seconds'] < 10 for item in trades),
        'entry_cost_total_usdt': sum((item['entry_cost_usdt'] for item in trades), D(0)),
        'decomposition': sums, 'ledger_reconciles': True,
        'exit_rejections': dict(Counter(order['rejection_reason'] for order in snapshot['exit_rejections'])),
        'exit_rejections_by_mint': dict(reject_by_mint),
        'retained_fill_quality_counts': dict(Counter(order['fill_json']['data_quality'] for order in snapshot['filled_orders'])),
        'final_exit_reasons': dict(Counter(item['exit_reason'] for item in trades)),
        'experiment_portfolio_id': snapshot['run']['portfolio_id'],
        'experiment_attached_to_this_portfolio': snapshot['run']['portfolio_id'] == portfolio['id'],
    }
    return {'summary': summary, 'trades': trades}


def main():
    cohorts = [analyze(ROOT / 'current_1248', 'previous'), analyze(ROOT / 'current_1250', 'current')]
    (ROOT/'findings.json').write_text(json.dumps({'cohorts': cohorts}, indent=2, default=str), encoding='utf-8')
    rows = [{key:value for key,value in item.items() if key not in ('decomposition', 'executable_statistics')}
            | {f'decomposition_{key}':value for key,value in item['decomposition'].items() if key != 'basis'}
            for cohort in cohorts for item in cohort['trades']]
    with (ROOT/'trades.csv').open('w', newline='', encoding='utf-8-sig') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for cohort in cohorts:
        print(json.dumps(cohort['summary'], default=str))
        for item in cohort['trades']:
            print(json.dumps({key:item[key] for key in ('number', 'symbol', 'net_pnl_usdt', 'pnl_percent',
                  'entry_cost_usdt', 'holding_seconds', 'signal_to_fill_seconds', 'decision_to_fill_seconds',
                  'feature_continuity_status', 'feature_state_reason', 'retained_mark_to_sell_seconds',
                  'final_reference_price_change_percent', 'final_gross_fill_price_change_percent', 'executable_statistics')}, default=str))


if __name__ == '__main__':
    main()
