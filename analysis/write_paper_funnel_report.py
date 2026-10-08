import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

a=json.loads(Path('analysis/current_paper_funnel_audit.json').read_text(encoding='utf-8'))
t=json.loads(Path('analysis/current_paper_entry_timing.json').read_text(encoding='utf-8'))
f=json.loads(Path('analysis/current_paper_feed_delay.json').read_text(encoding='utf-8'))
assert a['active_decisions']==sum(a['decision_actions'].values())
assert a['deterministic_entry_qualified_decisions']==a['policy_evaluations_successful']+a['policy_failures']
assert a['policy_evaluations_successful']==a['policy_vetoes']+a['policy_buy_approvals']
assert a['policy_buy_approvals']==a['filled_buys']+sum(a['buy_execution_rejections'].values())
# This frozen 2/3 October 2026 snapshot is during Dublin's UTC+1 period.
assert a['snapshot_end'].startswith('2026-10-02')
local=timezone(timedelta(hours=1))
start=datetime.fromisoformat(a['started_at']).astimezone(local)
end=datetime.fromisoformat(a['snapshot_end']).astimezone(local)
lines=[
 '# Current PAPER entry bottleneck audit', '',
 f"Experiment: `{a['experiment']}`. Snapshot window: {start.isoformat()} to {end.isoformat()} (Europe/Dublin). Duration: {a['hours']*60:.1f} minutes.", '',
 'Read-only investigation. The running worker, entry thresholds, model, and controls were not changed or paused. Counts are a bounded snapshot; the bot continues running.', '',
 '## Finding', '',
 'The most frequent pre-qualification category is deterministic risk rejection. Once the strategy and local model approve an entry, the dominant actual execution blocker is signal expiry: eight of nine approved buys fail the 25-second signal-age check. The zero-trade conclusion of the earlier 15-minute experiment does not describe this longer run: the model has now approved buys and one buy/sell cycle completed.', '',
 '| Funnel stage | Decisions |', '|---|---:|',
 f"| Active strategy decisions | {a['active_decisions']} |",
 f"| Deterministic skips | {a['decision_providers']['bullseye_strategy_runner']-a['decision_actions'].get('watch',0)} |",
 f"| Watch only | {a['decision_actions'].get('watch',0)} |",
 f"| Deterministic entry-qualified; sent to local policy | {a['deterministic_entry_qualified_decisions']} |",
 f"| Local policy explicit veto | {a['policy_vetoes']} |",
 f"| Local policy unavailable/invalid response | {a['policy_failures']} |",
 f"| Local policy buy approval | {a['policy_buy_approvals']} |",
 f"| Buy execution rejected | {sum(a['buy_execution_rejections'].values())} |",
 f"| Filled buys | {a['filled_buys']} |",
 f"| Filled sells | {a['filled_sells']} |", '',
 f"Distinct risk-assessed candidate coins: {a['distinct_candidate_coins']}. Approved entries involve {a['final_entry_distinct_coins']} distinct coins. Counts of decisions are not counts of launches or independent opportunities.", '',
 '## Deterministic rejections', '',
 'Counts overlap: one decision can have several reasons. They cannot be added as disjoint rejection stages.', '',
 '| Category | Decisions with category | Decisions with only this category |', '|---|---:|---:|']
lines += [f"| {k} | {v} | {a['exclusive_skip_categories'].get(k,0)} |" for k,v in a['deterministic_skip_categories'].items()]
lines += ['', 'Hard concentration reasons: largest-holder threshold >=35% appears in 178 decisions; creator-holding threshold >=20% in 76 decisions. Missing risk data also prevents approval. The exclusive-category count is not a promise of an additional trade: score, local policy, and execution would still need to pass.', '',
          '## Approved-entry expiry evidence', '',
          'Seven buys have `entry_signal_expired`; one has `entry_signal_expired_before_fill`. Every recorded buy execution rejection in this snapshot is expiry. No market-cap, price-impact, fee, portfolio-capacity, or canonical-state rejection was recorded for these nine approved buys.', '',
          '| Mint prefix | Outcome | Signal age before model, s | Local receipt delay, s | Decision-to-order, s | Signal age at order, s |', '|---|---|---:|---:|---:|---:|']
lines += [f"| {r['mint'][:8]} | {r['reason'] or r['status']} | {r['signal_age_at_risk_seconds']:.2f} | {r['feature_receipt_delay_seconds']:.2f} | {r['decision_to_order_seconds']:.2f} | {r['signal_age_at_order_seconds']:.2f} |" for r in t['orders']]
std=f['standard_non_mayhem_pump_trades']
lines += ['', f"Across {std['n']} standard non-Mayhem Pump.fun trade events, source-to-local-processing receipt delay is p50 {std['p50_seconds']:.2f}s, p95 {std['p95_seconds']:.2f}s, maximum {std['max_seconds']:.2f}s. {std['over_25s']} events ({100*std['over_25s']/std['n']:.1f}%) already exceed 25 seconds at receipt. Estimated source timestamps were excluded; this snapshot has none.", '',
          'The decision timestamp is inherited from collected risk facts before the model request. Decision-to-order time includes local inference, queueing and execution preparation. It is not an isolated measurement of model inference. Recorded risk fact collection completes roughly 0.4–0.7 seconds after local receipt for these approved buys; the large initial delay predates it.', '',
          'The native provider receive loop awaits notification normalization and publication. EventBus awaits handlers, including persistence and downstream work. This permits local receive backlog. The stored timestamps cannot prove how much delay is upstream provider delivery versus local backlog; assigning all delay to the provider or Ollama would overclaim.', '',
          'All nine approved decisions have unavailable observational latest price in the retained feature snapshot. Exact current execution price is separately refreshed; missing observation price can also affect discretionary vetoes and scoring quality. It is not listed as the direct execution rejection of these buys.', '',
          '## Current status and next fix', '',
          f"Entries paused: {a['entries_paused']}. Open positions: {a['open_positions']}. One position closed with realized PnL {a['positions'][0]['realized_pnl']} in portfolio currency. No profitability inference is justified by one trade.", '',
          'The next concrete fix should target acquisition/processing age and revalidate against fresh observed features before an approved order. Preserve the final atomic refresh and stale-signal protection. Increasing the 25-second limit alone would admit older evidence rather than resolve the demonstrated delay. Local-policy vetoes and its 12 failures are an additional earlier bottleneck, but this audit cannot classify those failures further without retained error logs.', '',
          'Machine evidence: analysis/current_paper_funnel_audit.json; analysis/current_paper_entry_timing.json; analysis/current_paper_feed_delay.json.', '']
Path('docs/CURRENT_PAPER_ENTRY_BOTTLENECK.md').write_text('\n'.join(lines),encoding='utf-8')
print({'report':'docs/CURRENT_PAPER_ENTRY_BOTTLENECK.md','funnel_reconciled':True,'hours':a['hours']})
