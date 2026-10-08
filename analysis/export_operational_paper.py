"""Export the actual isolated PAPER cohort; undefined metrics stay null."""
import asyncio
import json
from collections import Counter
from datetime import datetime, UTC
from decimal import Decimal
from pathlib import Path
from statistics import median
from uuid import UUID

from sqlalchemy import select, inspect
from memebot.core.config import Settings
from memebot.paper.standard_math import sell_quote
from memebot.eligibility import paper_candidate_rejection
from memebot.market_state import NormalizedMarketState
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.experiments import ExperimentRepository
from memebot.storage.database.control import ControlRepository
from memebot.storage.database.models import (
    DomainEventRecord, DecisionOutcomeRecord, PaperOrderRecord,
    TradeOutcomeRecord, PaperPositionRecord,
)

ROOT = Path(__file__).resolve().parents[1]
D = Decimal


def row(record):
    return {col.key: getattr(record, col.key) for col in inspect(type(record)).columns}


def write(name, data):
    (ROOT / 'analysis' / name).write_text(json.dumps(data, indent=2, default=str), encoding='utf-8')


def dec(value):
    return D(str(value or 0))


def evidence(fill):
    return {item['code']: item['value'] for item in fill.get('evidence', [])}


def decomposition(orders):
    buys = [o for o in orders if o.side == 'buy' and o.fill_json]
    sells = [o for o in orders if o.side == 'sell' and o.fill_json]
    if len(buys) != 1 or not sells:
        return None
    entry = buys[0].fill_json
    ev = evidence(entry)
    try:
        q0, qa = dec(ev['unadjusted_token_amount_raw']), dec(entry['token_amount_raw'])
        unit = dec(entry['quote_price_in_portfolio_currency']) / D(10**9)
        entry_curve_cost = (dec(entry['gross_quote_amount_raw']) -
                            dec(entry['venue_fee_quote_raw'])) * unit
        counterfactual = actual = D(0)
        for order in sells:
            fill = order.fill_json
            state = fill['execution_state']
            quantity = int(q0 * dec(fill['token_amount_raw']) / qa)
            gross = sell_quote(state['curve'], quantity, state['rates'])['gross_output']
            exit_unit = dec(fill['quote_price_in_portfolio_currency']) / D(10**9)
            counterfactual += D(gross) * exit_unit
            actual += dec(fill['gross_portfolio_amount'])
        fees = sum((dec(o.fill_json['total_fee_portfolio']) for o in buys + sells), D(0))
        return {'strategy_price_pnl_before_fees_friction': counterfactual - entry_curve_cost,
                'execution_friction_cost': counterfactual - actual,
                'fees': fees, 'basis': 'same exit banks; undo configured buy/sell friction'}
    except (KeyError, ValueError, ArithmeticError):
        return None


async def main():
    run = json.loads((ROOT / 'analysis/paper_run_state.json').read_text(encoding='utf-8'))
    if not run.get('portfolio_id'):
        raise RuntimeError('No actual experiment portfolio exists')
    pid = UUID(run['portfolio_id'])
    start = datetime.fromisoformat(run['observation_started_at'])
    end = datetime.fromisoformat(run.get('ended_at', datetime.now(UTC).isoformat()))
    settings = Settings(pumpportal_api_key=None, telegram_bot_token=None)
    db = Database(create_database_engine(settings.database_url))
    try:
        async with db.sessions() as session:
            async def cohort(cls):
                return list(await session.scalars(select(cls).where(cls.portfolio_id == pid)))
            orders, outcomes, positions = await cohort(PaperOrderRecord), await cohort(TradeOutcomeRecord), await cohort(PaperPositionRecord)
            decisions = list(await session.scalars(select(DecisionOutcomeRecord).where(
                DecisionOutcomeRecord.decided_at >= start, DecisionOutcomeRecord.decided_at <= end,
                DecisionOutcomeRecord.active_strategy.is_(True))))
            events = list(await session.scalars(select(DomainEventRecord).where(
                DomainEventRecord.ingested_at >= start, DomainEventRecord.ingested_at <= end,
                DomainEventRecord.provider == 'solana_rpc_pump')))
            evidence_ids = [o.event_id for o in orders] + [d.decision_event_id for d in decisions]
            retained = {r.event_id: r.payload for r in await session.scalars(
                select(DomainEventRecord).where(DomainEventRecord.event_id.in_(evidence_ids)))} if evidence_ids else {}
            risk_ids = [UUID(p['risk_event_id']) for p in retained.values() if p.get('risk_event_id')]
            risk_banks = {str(r.event_id): r.payload.get('current_execution_state') for r in await session.scalars(
                select(DomainEventRecord).where(DomainEventRecord.event_id.in_(risk_ids)))} if risk_ids else {}
        report = await ExperimentRepository(db.sessions).report(run['experiment_name'])
        by_position = {p.id: p for p in positions}
        trades = []
        for trade in outcomes:
            item = row(trade)
            item['position'] = row(by_position[trade.position_id])
            linked = [o for o in orders if o.mint == trade.mint
                      and (o.event_id == trade.entry_order_event_id or
                           (o.side == 'sell' and o.filled_at is not None and o.filled_at >= trade.entry_at
                            and (trade.exit_at is None or o.filled_at <= trade.exit_at)))]
            item['orders'] = [row(o) for o in linked]
            item['execution_decomposition'] = decomposition(linked) if trade.status == 'closed' else None
            stats = (by_position[trade.position_id].execution_mark_json or {}).get('executable_statistics')
            item['executable_mfe_mae'] = stats
            item['observed_mfe_mae_basis'] = 'stream observations; not executable PnL'
            if stats and stats.get('peak_at'):
                item['entry_to_executable_peak_seconds'] = (datetime.fromisoformat(stats['peak_at']) - trade.entry_at).total_seconds()
            trades.append(item)
        fills = [o for o in orders if o.fill_json]
        closed = sorted([t for t in trades if t['status'] == 'closed'], key=lambda t: t['exit_at'])
        pnls = [dec(t['realized_pnl']) for t in closed]
        wins, losses = [p for p in pnls if p > 0], [p for p in pnls if p < 0]
        fees_all = sum((dec(o.fill_json['total_fee_portfolio']) for o in fills), D(0))
        decomps = [t['execution_decomposition'] for t in closed if t['execution_decomposition']]
        complete_decomposition = len(decomps) == len(closed)
        fees_closed = sum((dec(o['fill_json']['total_fee_portfolio']) for t in closed
                           for o in t['orders'] if o['fill_json']), D(0))
        friction = sum((dec(d['execution_friction_cost']) for d in decomps), D(0)) if complete_decomposition else None
        unique = {e.payload.get('mint') for e in events if e.payload.get('mint')}
        event_counts = Counter(e.event_type for e in events)
        screens = Counter()
        standard = set()
        observations = {}
        for event in events:
            raw = event.payload.get('normalized_state')
            mint = event.payload.get('mint')
            if not raw or not mint:
                continue
            provenance = NormalizedMarketState(**raw).evidence()
            rejection = paper_candidate_rejection(provenance)
            screens[rejection or 'CURRENT_VERIFICATION_CANDIDATE'] += 1
            if rejection is None:
                standard.add(mint)
            observations[mint] = {'mint': mint, 'last_seen_at': event.ingested_at,
                                  'cheap_scope_rejection': rejection, 'price_evidence': provenance}
        peak = equity = dec(run['initial_cash'])
        drawdown = D(0)
        for pnl in pnls:
            equity += pnl
            peak = max(peak, equity)
            drawdown = max(drawdown, peak - equity)
        candidate_rows = []
        policy_evaluations = policy_vetoes = policy_failures = 0
        for decision in decisions:
            item = row(decision)
            raw_decision = retained.get(decision.decision_event_id, {})
            item['price_evidence'] = raw_decision.get('price_evidence', {})
            item['pre_risk_verification_bank'] = risk_banks.get(raw_decision.get('risk_event_id'))
            linked_order = next((o for o in orders if o.decision_event_id == decision.decision_event_id), None)
            item['current_execution_state'] = linked_order.fill_json.get('execution_state') if linked_order and linked_order.fill_json else None
            item['paper_fill'] = linked_order.fill_json if linked_order else None
            item['execution_state_status'] = 'final_fill_bank_retained' if item['current_execution_state'] else 'no_final_fill_bank; candidate may have been vetoed before execution'
            if raw_decision.get('provider') == 'bullseye_ollama_policy':
                policy_evaluations += 1
                if 'ollama_unavailable_no_entry' in decision.decision_reasons:
                    policy_failures += 1
                elif decision.action == 'skip':
                    policy_vetoes += 1
            candidate_rows.append(item)
        order_rows = []
        for order in orders:
            item = row(order)
            item['rejection_price_evidence'] = retained.get(order.event_id, {}).get('result', {}).get('price_evidence', {})
            order_rows.append(item)
        performance = {
            'run': run, 'exported_at': datetime.now(UTC).isoformat(),
            'observed_markets': len(unique), 'native_event_counts': dict(event_counts),
            'standard_markets_reaching_cheap_scope_screen': len(standard),
            'scope_trade_event_counts': dict(screens),
            'serious_candidate_markets': len({d.mint for d in decisions}),
            'active_strategy_decisions': len(decisions),
            'configured_local_policy_evaluations': policy_evaluations,
            'configured_local_policy_vetoes': policy_vetoes,
            'configured_local_policy_failures': policy_failures,
            'entered_trades': len(trades), 'completed_trades': len(closed),
            'open_trades': len(trades) - len(closed),
            'win_rate_percent': D(100) * len(wins) / len(closed) if closed else None,
            'average_win': sum(wins, D(0)) / len(wins) if wins else None,
            'average_loss': sum(losses, D(0)) / len(losses) if losses else None,
            'net_pnl_completed': sum(pnls, D(0)),
            'gross_pnl_completed_before_fees': sum(pnls, D(0)) + fees_closed if fees_closed is not None else None,
            'profit_factor': sum(wins, D(0)) / abs(sum(losses, D(0))) if losses else None,
            'expectancy_per_trade': sum(pnls, D(0)) / len(closed) if closed else None,
            'total_fees_all_fills': fees_all, 'fees_completed': fees_closed,
            'execution_friction_completed': friction,
            'strategy_price_pnl_before_fees_friction': sum((dec(d['strategy_price_pnl_before_fees_friction']) for d in decomps), D(0)) if complete_decomposition else None,
            'decomposition_complete': complete_decomposition,
            'median_holding_seconds': median([t['holding_seconds'] for t in closed]) if closed else None,
            'median_entry_to_executable_peak_seconds': median([t['entry_to_executable_peak_seconds'] for t in closed if t.get('entry_to_executable_peak_seconds') is not None]) if any(t.get('entry_to_executable_peak_seconds') is not None for t in closed) else None,
            'median_executable_mfe_percent': median([dec(t['executable_mfe_mae']['mfe_percent']) for t in closed if t.get('executable_mfe_mae')]) if any(t.get('executable_mfe_mae') for t in closed) else None,
            'median_executable_mae_percent': median([dec(t['executable_mfe_mae']['mae_percent']) for t in closed if t.get('executable_mfe_mae')]) if any(t.get('executable_mfe_mae') for t in closed) else None,
            'median_observed_mfe_percent': median([dec(t['mfe_percent']) for t in closed]) if closed else None,
            'median_observed_mae_percent': median([dec(t['mae_percent']) for t in closed]) if closed else None,
            'maximum_realized_drawdown': drawdown if closed else None,
            'drawdown_basis': 'closed-trade realized equity; no fabricated unavailable marks',
            'best_setup': report['segments']['closed_trades_by_score'] if closed else None,
            'losses_by_exit_reason': report['segments']['closed_trades_by_exit'] if closed else None,
            'positive_expectancy_evidence': 'insufficient sample' if len(closed) < 100 else 'requires statistical assessment',
            'decision_actions': report['segments']['decision_actions'],
            'decision_reasons': report['segments']['decision_reasons'],
            'execution_rejections': report['execution']['rejection_reasons'],
            'risk_unknowns': report['segments']['risk_critical_unknowns'],
        }
        write('paper_trades.json', {'run': run, 'trades': trades, 'orders': order_rows})
        write('paper_candidates.json', {'run': run, 'definition': 'active strategy decisions following risk assessment; prefilter markets counted separately', 'candidates': candidate_rows, 'observed_market_mints': sorted(unique), 'latest_scope_observations': list(observations.values())})
        write('paper_performance.json', performance)
        assumptions = {k: str(getattr(settings, k)) for k in [
            'paper_additional_slippage_bps', 'paper_adverse_fill_bps', 'paper_latency_slippage_bps',
            'paper_execution_provider_fee_bps', 'paper_network_fee_sol', 'paper_priority_fee_sol',
            'paper_compute_latency_ms', 'paper_submission_latency_ms',
            'paper_max_market_staleness_seconds', 'paper_min_order_amount', 'paper_risk_per_trade_percent',
            'paper_base_position_percent', 'paper_max_position_percent', 'ollama_model']}
        assumptions.update(protocol_creator_fees='exact integers from each atomic bank/config',
                           external_fees='estimated configurable costs', price_model_version=3,
                           final_atomic_refresh_required=True, live_enabled=False,
                           historical_proof='diagnostic unless explicit incompatibility',
                           strategy_thresholds_changed=False, provider='existing native discovery, explicitly approved')
        write('paper_execution_assumptions.json', assumptions)
        def display(value):
            return 'N/A (insufficient completed evidence)' if value is None else str(value)
        metric_names = {
            'Observed native markets': 'observed_markets',
            'Standard markets passing cheap scope screen': 'standard_markets_reaching_cheap_scope_screen',
            'Serious candidate markets': 'serious_candidate_markets',
            'Active strategy decisions': 'active_strategy_decisions',
            'Paper trades entered': 'entered_trades', 'Paper trades completed': 'completed_trades',
            'Open trades': 'open_trades', 'Win rate (%)': 'win_rate_percent',
            'Average win': 'average_win', 'Average loss': 'average_loss',
            'Net completed PnL': 'net_pnl_completed', 'Gross before fees': 'gross_pnl_completed_before_fees',
            'Profit factor': 'profit_factor', 'Expectancy per trade': 'expectancy_per_trade',
            'Maximum realized drawdown': 'maximum_realized_drawdown',
            'All incurred fees': 'total_fees_all_fills', 'Completed-trade friction': 'execution_friction_completed',
            'Median holding seconds': 'median_holding_seconds',
            'Median executable MFE (%)': 'median_executable_mfe_percent',
            'Median executable MAE (%)': 'median_executable_mae_percent',
            'Median entry-to-executable-peak seconds': 'median_entry_to_executable_peak_seconds',
            'Local policy evaluations': 'configured_local_policy_evaluations',
            'Local policy vetoes': 'configured_local_policy_vetoes',
            'Local policy failures': 'configured_local_policy_failures',
        }
        lines = ['# Bounded standard Pump.fun PAPER results', '',
                 f"Experiment: `{run['experiment_name']}`. Status: **{run['status']}**.", '',
                 f"Observation began {run['observation_started_at']}; export/end {run.get('ended_at', performance['exported_at'])}.",
                 f"Declared observation duration: {run['bounded_seconds'] if run['bounded_seconds'] is not None else 'continuous'} seconds; the run end timestamp also captures shutdown/drain.", '',
                 'The active existing strategy is aggressive. Entry thresholds, risk/alpha/Pulse qualification and configured local policy are preserved. Native discovery was explicitly approved. Live trading remained disabled.', '',
                 '| Measurement | Actual result |', '|---|---|']
        lines += [f'| {label} | {display(performance[key])} |' for label,key in metric_names.items()]
        lines += ['', 'PnL and fees are in the configured portfolio currency. Completed-trade statistics exclude open exposure. Zero cash movement from zero fills is not evidence of a zero-risk or profitable strategy.', '',
                  '## Qualification and execution', '',
                  'Serious candidate markets are distinct mints receiving active strategy decisions after risk assessment. Repeated decisions do not count as new markets. Observed markets include cheap out-of-scope observations and are not all eligible launches.', '',
                  'Decision reasons (multiple reasons may apply to one decision):', '',
                  '```json', json.dumps(performance['decision_reasons'], indent=2), '```', '',
                  'Execution rejection counts:', '', '```json', json.dumps(performance['execution_rejections'], indent=2), '```', '',
                  '## Required conclusions', '',
                  '1. The PAPER discovery/risk/strategy pipeline ran against real market data; exact fills are regression-validated. ' + ('Natural fills were obtained.' if trades else 'No natural fill was obtained, so a live-data buy/sell execution cycle remains unproven.'),
                  f"2. Observed {len(unique)} markets; {performance['serious_candidate_markets']} serious candidate markets.",
                  f'3. Entered {len(trades)} PAPER trades.', f'4. Completed {len(closed)} PAPER trades.',
                  f"5. Win rate: {display(performance['win_rate_percent'])}.",
                  f"6. Net completed PnL: {display(performance['net_pnl_completed'])}.",
                  f"7. Profit factor: {display(performance['profit_factor'])}.",
                  f"8. Expectancy: {display(performance['expectancy_per_trade'])}.",
                  f"9. Maximum realized drawdown: {display(performance['maximum_realized_drawdown'])}.",
                  f"10. Fees across all fills: {fees_all}; completed friction: {display(friction)}.",
                  '11. Best setup: ' + ('score segments are available in paper_performance.json; this small sample does not establish superiority.' if closed else 'cannot rank without completed trades.'),
                  '12. Most costly failure: ' + ('exit-reason segments are retained; the sample does not establish causality.' if closed else 'cannot rank monetary losses without trades; qualification/veto counts are separate.'),
                  '13. Positive expectancy: insufficient evidence from this bounded sample.',
                  '14. Next: extend the same frozen PAPER configuration and examine documented qualification and local-policy vetoes before proposing a profitability change. No threshold reduction is justified by this sample alone.', '',
                  '## Integrity limits', '',
                  'Rejected candidates retain decision features, score/risk snapshots, reasons and observational outcomes where available. A veto before final execution has no final fill bank or executable result; those fields remain null. After this measured window, additive telemetry was added to retain the already-read pre-risk curve/config bank for future candidates, without extra RPC or strategy changes. It cannot recover the unretained banks of this cohort; pre_risk_verification_bank is null here. Missing observational prices cannot support precise rejected-opportunity returns.', '',
                  'Old historical fills are not retroactively validated. This run does not establish profitability, executable historical MFE, source-disagreement calibration or live-trading readiness. The earlier runner-edge-prospective-v1 research experiment remains unactivated.', '',
                  'Entries are paused at bounded shutdown. Open exposure, if present, remains durable and requires continued monitoring; it is not reported as a synthetic closed position.', '',
                  'Artifacts: analysis/paper_trades.json, paper_candidates.json, paper_performance.json and paper_execution_assumptions.json. Validation: 457 tests, Ruff, mypy (135 source files).', '']
        (ROOT / 'docs/PAPER_STRATEGY_RESULTS.md').write_text('\n'.join(lines), encoding='utf-8')
        print(json.dumps({k: performance[k] for k in ['observed_markets','serious_candidate_markets','entered_trades','completed_trades','net_pnl_completed']}, default=str))
        control = await ControlRepository(db.sessions).get()
        active = await ExperimentRepository(db.sessions).active()
        print(json.dumps({'entries_paused': control.entries_paused if control else None,
                          'active_experiment': active['name'] if active else None}))
    finally:
        await db.dispose()


if __name__ == '__main__':
    asyncio.run(main())
