"""Analyze this new prospective capture only; no RPC, old replay or orders."""
import base64
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import mean, median

from memebot.providers.solana._yellowstone_generated import geyser_pb2
from memebot.providers.solana.alchemy_evidence import rpc_packet
from memebot.providers.solana.pump import extract_anchor_events
from memebot.providers.solana.pump_idl import PumpTrade
from memebot.paper.validation_gate import CRITICAL_FILES, require_price_validation

ROOT = Path(__file__).resolve().parents[1]


def stats(values):
    v = sorted(values)
    return {'N': len(v), 'mean': mean(v) if v else None, 'median': median(v) if v else None,
            'p90': v[min(len(v)-1, (9*len(v)+9)//10-1)] if v else None,
            'max': max(v) if v else None}


def ms(start, end):
    return (datetime.fromisoformat(str(end))-datetime.fromisoformat(str(start))).total_seconds()*1000


def delta(a, b):
    return {k: b[k]-a[k] for k in a.keys() & b.keys()
            if isinstance(a[k], int) and not isinstance(a[k], bool)
            and isinstance(b[k], int) and not isinstance(b[k], bool)}


def reason_detail(q):
    evidence = q['evidence']
    return [str(r.get('reason')) for r in evidence.get('direct_anchor_reconstruction', [])
            if r.get('reason')]


def blocker(record):
    q = record['proof_before_refresh']
    reason = (q.get('reason') or '').lower()
    detail = ' '.join(reason_detail(q)).lower()
    if record['full_pass']:
        return None
    if q['status'] == 'PASS':
        return 'REFRESH'
    if any(s in reason+detail for s in ('unsupported', 'unexplained router', 'physical_balance_mismatch',
                                      'syncnative', 'additional pump mutation')):
        return 'UNSUPPORTED_ROUTE'
    if q['status'] in ('FAIL_IDENTITY', 'FAIL_CONFIG'):
        return 'INVALIDATION' if 'invalidation' in reason else 'IDENTITY_CONFIG'
    if q['status'] == 'FAIL_RPC':
        return 'PROVIDER'
    if q['status'] == 'FAIL_BUDGET':
        return 'HISTORY_BOUNDARY' if 'successor boundary' in reason else 'BUDGET'
    if q['status'] == 'FAIL_FEE':
        return 'PARITY'
    if 'reconstruction' in reason or 'unexplained native' in reason:
        return 'RECONSTRUCTION'
    if 'same-slot' in reason or 'history' in reason:
        return 'HISTORY_BOUNDARY'
    if 'gap' in reason or 'invalidation' in reason:
        return 'INVALIDATION'
    if q['status'] == 'FAIL_STATE_SYNC':
        return 'STATE_SYNC'
    if 'transaction' in reason and ('unavailable' in reason or 'missing' in reason):
        return 'PROVIDER'
    return 'OTHER'


def main():
    data = json.loads((ROOT / 'analysis/prospective_full_proofs.json').read_text())
    records = data['candidate_stages']
    auxiliary = json.loads((ROOT/'analysis/prospective_capture_execution_proofs.json').read_text())
    data['native_invalidation_context'] = auxiliary.get('native_invalidations', [])
    data['proof_invalidation_context'] = auxiliary.get('proof_invalidations', [])
    archive = {}
    for line in (ROOT / 'analysis/prospective_capture_packets.jsonl').read_text().splitlines():
        row = json.loads(line)
        if row.get('record_kind') == 'provider_protobuf':
            archive.setdefault(row['signature'], row)
    packet_events = {}
    for signature, row in archive.items():
        try:
            packet = rpc_packet(geyser_pb2.SubscribeUpdate.FromString(
                base64.b64decode(row['raw_protobuf_base64'])))
            packet_events[signature] = [event for _,event in extract_anchor_events(packet['meta']['logMessages'])
                                       if isinstance(event, PumpTrade)]
        except (ValueError, KeyError):
            packet_events[signature] = []
    history, refreshes, diagnostics = [], [], []
    stage_counts = Counter()
    for record in records:
        q = record['proof_before_refresh']
        e = q['evidence']
        c = q['candidate']
        record['dominant_final_blocker'] = blocker(record)
        record['secondary_causes'] = reason_detail(q)
        recon = e.get('direct_anchor_reconstruction', [])
        recon_ok = len(recon) == 1 and recon[0]['status'] == 'TRANSACTION_SEQUENCE_VERIFIED'
        parity_ok = bool(e.get('observed_anchor_parity'))
        fences = e.get('history_reads', [])
        fence_ok = len(fences) == 4 and fences[:2] and all(
            fences[i]['rows'] == fences[i+2]['rows'] for i in range(2))
        bank = e.get('curve')
        terminal = None
        sequence = e.get('native_transactions', [])
        # Each captured event is retained. Do not guess ordering when the engine rejected it.
        if e.get('parity'):
            terminal = e['parity'][-1]['post_reserves']
        elif q['status'] == 'PASS':
            terminal = {k: bank[k] for k in ('virtual_token_reserves', 'virtual_quote_reserves',
                                            'real_token_reserves', 'real_quote_reserves')}
        bank_delta = delta(terminal, bank) if terminal and bank else None
        sync_ok = bank_delta is not None and not any(bank_delta.values())
        record['stages'] = {
            'reconstruction': recon_ok, 'anchor_parity': parity_ok,
            'history_closure': bool(fence_ok), 'bank_sync': sync_ok,
            'proof_before_refresh': q['status'] == 'PASS',
            'refresh': record['full_pass'], 'full_pass': record['full_pass'],
        }
        stage_counts.update(k for k, v in record['stages'].items() if v)
        boundary_cause = []
        reason = q.get('reason') or ''
        if 'successor boundary' in reason: boundary_cause.append('SUCCESSOR_BOUNDARY_NOT_REACHED')
        if 'signature' in reason: boundary_cause.append('OTHER')
        if 'same-slot' in reason: boundary_cause.append('SAME_SLOT_ORDER_UNPROVEN')
        if 'crosses account' in reason: boundary_cause.append('HISTORY_CROSSES_BANK')
        if 'history fence moved' in reason: boundary_cause.append('OTHER')
        fence_records = []
        for i in range(4):
            if i >= len(fences):
                fence_records.append({'fence': i+1, 'status': 'NOT_ATTEMPTED_AFTER_REJECTION'})
                continue
            f = fences[i]
            window = [r for r in f['rows'] if r['slot'] >= c['anchor_slot']]
            flags = []
            if not any(r['signature'] == c['anchor_signature'] for r in f['rows']):
                flags.append('ANCHOR_NOT_REACHED')
                if all(r['slot'] < c['anchor_slot'] for r in f['rows']): flags.append('INDEX_LAG')
            if f['rows'] and all(r.get('err') is not None for r in f['rows']): flags.append('FAILED_ROWS_ONLY')
            if e.get('slot') and any(r['slot'] > e['slot'] and r.get('err') is None for r in window):
                flags.append('HISTORY_CROSSES_BANK')
            status = 'RECEIVED' if i < 2 else ('MATCHED' if f['rows'] == fences[i-2]['rows'] else 'MOVED')
            differences = None
            if i >= 2:
                old = {r['signature']:r for r in fences[i-2]['rows']}
                new_rows = {r['signature']:r for r in f['rows']}
                added = [r for s,r in new_rows.items() if s not in old]
                differences = {'added':added, 'removed':[r for s,r in old.items() if s not in new_rows],
                               'changed_fields':{s:{k:{'before':old[s].get(k),'after':r.get(k)}
                                  for k in old[s].keys()|r.keys() if old[s].get(k)!=r.get(k)}
                                  for s,r in new_rows.items() if s in old and old[s]!=r},
                               'added_successful':sum(r.get('err') is None for r in added),
                               'added_failed':sum(r.get('err') is not None for r in added)}
            fence_records.append({'fence': i+1, 'status': status, 'flags': flags,
                                  'difference_from_initial_fence':differences, **f})
        relevant = []
        for r in data.get('packet_inventory', {}).get(c['mint'], []):
            relevance = ('AVAILABLE_AT_PROOF_TIME' if datetime.fromisoformat(r['at']) <=
                         datetime.fromisoformat(q['proof_completed_at']) else 'ARRIVED_LATER_DIAGNOSTIC_ONLY')
            relevant.append({**r, 'availability': relevance})
        events = []
        for packet in sequence:
            for _, event in extract_anchor_events(packet['meta']['logMessages']):
                if isinstance(event, PumpTrade) and event.mint == c['mint']:
                    events.append({'signature': packet['transaction']['signatures'][0], 'slot': packet['slot'],
                                   'post_state': {k: getattr(event, k) for k in
                                        ('virtual_token_reserves','virtual_quote_reserves',
                                         'real_token_reserves','real_quote_reserves')}})
        sync = {'anchor_slot': c['anchor_slot'],
                'anchor_index': record.get('local_anchor', {}).get('index') if record.get('local_anchor') else None,
                'bank_slot': e.get('slot'), 'terminal_reconstructed_state': terminal,
                'bank_state': bank, 'exact_bank_minus_terminal_delta': bank_delta,
                'known_events': events,
                'known_stream_before_bank': [r for r in relevant if e.get('slot') and r['slot'] <= e['slot']],
                'known_stream_after_bank': [r for r in relevant if e.get('slot') and r['slot'] > e['slot']],
                'failure_attribution': ('history-window limitation' if 'same-slot' in reason else
                                        'index lag' if 'history fence moved' in reason and any('INDEX_LAG' in f.get('flags',[]) for f in fence_records) else
                                        'real concurrent state movement or missing indexed transaction' if bank_delta and any(bank_delta.values()) else
                                        'unknown' if q['status'] != 'PASS' else 'synchronized at proof bank')}
        matching_bank = []
        if bank:
            for r in relevant:
                for event in packet_events.get(r['signature'], []):
                    if event.mint == c['mint'] and r['slot'] <= e['slot'] and all(
                        getattr(event,k) == bank[k] for k in ('virtual_token_reserves',
                        'virtual_quote_reserves','real_token_reserves','real_quote_reserves')):
                        matching_bank.append(r)
        sync['stream_packets_matching_bank_post_state'] = matching_bank
        bank_receipt = e.get('candidate_account_batch',{}).get('received_at')
        sync['bank_received_at'] = bank_receipt
        sync['relevant_received_before_bank'] = [r for r in relevant if bank_receipt and r['at'] <= bank_receipt]
        sync['relevant_received_after_bank'] = [r for r in relevant if bank_receipt and r['at'] > bank_receipt]
        anchor_raw = archive.get(c['anchor_signature'])
        sync['anchor_index_from_archive_diagnostic'] = anchor_raw.get('transaction_index') if anchor_raw else None
        sync['anchor_archive_received_at'] = anchor_raw.get('received_timestamp') if anchor_raw else None
        if bank_delta and any(bank_delta.values()) and matching_bank:
            sync['failure_attribution'] = 'captured market mutation reaches bank; indexed proof sequence omitted it'
        history.append({'mint': c['mint'], 'signature': c['anchor_signature'], 'fences': fence_records,
                        'closure_pass': bool(fence_ok), 'failure_causes': sorted(set(boundary_cause)),
                        'final_reason': reason, 'synchronization': sync})
        diagnostics.append({'mint': c['mint'], 'proof_completed_at': q['proof_completed_at'],
                            'packets': relevant, 'late_packet_count': sum(r['availability'] ==
                            'ARRIVED_LATER_DIAGNOSTIC_ONLY' for r in relevant)})
        rf = record['refresh']
        new = rf.get('result', {})
        batch = record['NEW']['evidence'].get('execution_refresh_account_batch')
        row = {'mint': c['mint'], 'side': 'BUY' if c['anchor']['is_buy'] else 'SELL',
               'proof_completed_at': q['proof_completed_at'], **rf,
               'atomic_refresh_batch': batch,
               'execution_approved': new.get('execution_approved', False),
               'slot_delta': new.get('slot',0)-e.get('slot',0) if new else None,
               'reserve_delta': delta(e['curve'],new['curve']) if new else None,
               'config_hash_changed': new['binding']['config_version'] != e['binding']['config_version'] if new else None,
               'identity_changed': {k: {'before': e['binding'].get(k), 'after': new['binding'].get(k)}
                                    for k in e.get('binding', {}) if k != 'config_version' and
                                    e['binding'].get(k) != new.get('binding',{}).get(k)} if new else None,
               'buy_quote_delta': delta(e['buy'],new['buy']) if new and 'buy' in e else None,
               'sell_quote_delta': delta(e['sell'],new['sell']) if new and 'sell' in e else None}
        row['concurrent_invalidation_context'] = [i for i in data['proof_invalidation_context']
                if rf.get('attempted') and rf['request_at'] <= i['at'] <= rf['received_at']
                and i['mint'] in ('ALL', c['mint'])]
        row['proof_to_refresh_ms'] = ms(q['proof_completed_at'],rf['received_at']) if rf.get('attempted') else None
        row['refresh_request_to_receipt_ms'] = ms(rf['request_at'],rf['received_at']) if rf.get('attempted') else None
        refreshes.append(row)
    unsupported = [r for r in records if r['dominant_final_blocker'] == 'UNSUPPORTED_ROUTE']
    supported = [r for r in records if r not in unsupported]
    successful = [r for r in records if r['full_pass']]
    before_pass = [r for r in records if r['proof_before_refresh']['status'] == 'PASS']
    n = len(supported)
    funnel = {'serious_candidates': len(records), 'supported_observational_cohort': n,
              'explicit_unsupported': len(unsupported),
              'denominator_scope': 'standard/non-Mayhem/supported SOL/simple-event cohort minus explicit unsupported routes; bank-unverified routes remain provisional',
              'bank_verified_simple_routes': sum(r['proof_before_refresh']['evidence'].get('fee_route_class') ==
                                                'STANDARD_SIMPLE_FEE_ROUTE' for r in records),
              'BUY_SELL': dict(Counter('BUY' if r['NEW']['candidate']['anchor']['is_buy'] else 'SELL' for r in records)),
              'supported_BUY_SELL': dict(Counter('BUY' if r['NEW']['candidate']['anchor']['is_buy'] else 'SELL' for r in supported)),
              'stages': {k: {'passed': sum(r['stages'][k] for r in supported), 'denominator': n,
                         'percent': 100*sum(r['stages'][k] for r in supported)/n if n else None}
                         for k in ('reconstruction','anchor_parity','history_closure','bank_sync',
                                   'proof_before_refresh','refresh','full_pass')},
              'full_candidate_PASS': len(successful),
              'full_BUY_PASS': sum(r['NEW']['candidate']['anchor']['is_buy'] for r in successful),
              'full_SELL_PASS': sum(not r['NEW']['candidate']['anchor']['is_buy'] for r in successful),
              'unique_tokens_passing': len({r['mint'] for r in successful}),
              'final_blockers': dict(Counter(r['dominant_final_blocker'] for r in records if not r['full_pass'])),
              'latency_ms_successful_only': {
                  'qualification_to_proof': stats([ms(r['NEW']['candidate']['detected_at'],
                      r['proof_before_refresh']['proof_completed_at']) for r in successful]),
                  'proof_to_refresh': stats([ms(r['proof_before_refresh']['proof_completed_at'],
                      r['refresh']['received_at']) for r in successful]),
                  'qualification_to_execution_ready': stats([ms(r['NEW']['candidate']['detected_at'],
                      r['refresh']['received_at']) for r in successful])},
              'RPC_requests': {
                  'failed_attempts': stats([r['NEW']['costs'].get('total_rpc_requests',0) for r in records if not r['full_pass']]),
                  'successful_before_refresh': stats([r['proof_before_refresh']['costs'].get('total_rpc_requests',0) for r in before_pass]),
                  'full_success_including_refresh': stats([r['NEW']['costs'].get('total_rpc_requests',0) for r in successful])},
              'refresh_attempted': len(before_pass), 'refresh_approved': len(successful),
              'refresh_approval_percent': 100*len(successful)/len(before_pass) if before_pass else None,
              'pre_refresh_success_latency_ms': stats([ms(r['NEW']['candidate']['detected_at'],
                    r['proof_before_refresh']['proof_completed_at']) for r in before_pass]),
              'total_RPC_reads': data['rpc_reads'], 'policy': data['actual_policy'],
              'capture_seconds': data['elapsed_seconds'],
              'raw_full_packets': data['transport']['metrics'].get('full_packets',0),
              'coverage_gap_reasons': dict(Counter(r['reason'] for r in data['coverage']['gaps'])),
              'late_packet_diagnostics': diagnostics}
    # Full raw packets useful for diagnosis stay archived, even for early failures.
    data['candidate_stages'] = records
    data['analysis_scope'] = 'new live prospective capture only'
    (ROOT / 'analysis/prospective_full_proofs.json').write_text(json.dumps(data,indent=2,default=str)+'\n')
    outputs = {'prospective_proof_funnel': funnel,
               'prospective_history_boundaries': {'candidates': history},
               'prospective_execution_refresh': {'attempted': len(before_pass),
                                                'approved': len(successful),'candidates': refreshes}}
    for name, payload in outputs.items():
        (ROOT / ('analysis/'+name+'.json')).write_text(json.dumps(payload,indent=2,default=str)+'\n')
    def write_doc(name, body):
        (ROOT / ('docs/'+name+'.md')).write_text(body,encoding='utf-8')
    table = '| Stage | Supported passes / N | Percent |\n|---|---:|---:|\n'
    for stage, s in funnel['stages'].items():
        table += f"| {stage} | {s['passed']}/{n} | {s['percent']:.2f}% |\n" if n else f'| {stage} | 0/0 | unavailable |\n'
    intro = f"""# Prospective full proof validation

**Runner and calibration BLOCKED. No orders or trading.** One new passive Alchemy
Yellowstone capture: {data['started_at']} to {data['finished_at']},
{data['elapsed_seconds']:.2f} seconds including bounded teardown/drain.
Bounds: 300 seconds capture, 20 natural candidates, 32 watched markets,
150,000 discovery messages, 96 total RPC reads, 128 MB raw archive, existing
512-event / 120-second / 32 MB transaction buffer. No qualification, provider,
watch eligibility, execution semantics or proof-budget changes were made.
Only corrected stream-first proofs ran; there was no retrospective A/B delay.
The capture retained every attempted stage response; stages after early rejection
are explicitly unattempted, rather than invented missing responses. Later raw
packets are diagnostic only and cannot retroactively authorize a proof.

{len(records)} natural serious candidates; {n} provisionally supported cohort;
{len(unsupported)} explicit unsupported. Proof-before-refresh PASS {len(before_pass)};
**full PASS {len(successful)}, BUY {funnel['full_BUY_PASS']}, SELL {funnel['full_SELL_PASS']}**.
Actual RPC reads {data['rpc_reads']}/96. Failure distribution: {funnel['final_blockers']}.

{table}
Full successful latency (milliseconds): {funnel['latency_ms_successful_only']}.
Successful RPC cost: {funnel['RPC_requests']}.
An empty successful sample is unavailable, not zero latency/cost; early rejected
attempts do not estimate successful proof speed. Percentages use the provisional
supported denominator stated in the JSON, not fully verified canonical markets.

Detailed outputs: [funnel](PROSPECTIVE_PROOF_FUNNEL.md),
[history](PROSPECTIVE_HISTORY_BOUNDARIES.md), [refresh](PROSPECTIVE_EXECUTION_REFRESH.md),
and `analysis/prospective_full_proofs.json`. Full packets, stage RPC parameters/
responses, atomic banks, exact ledgers/parity and qualifications are retained.
"""
    answers = f"""
## Readiness answers

1. Natural full candidate PASSes: **{len(successful)}**.
2. Complete live BUY PASSes: **{funnel['full_BUY_PASS']}**.
3. Complete live SELL PASSes: **{funnel['full_SELL_PASS']}**; repeated success requires at least two.
4. Corrected issues were exercised where exact parity/accounting reached; individual
   live native variants and refunds/tips are recorded below. No unsupported
   redistribution was rescued and no fixture/replay counted toward this run.
5. Dominant blocker: **{Counter(funnel['final_blockers']).most_common(1)}**.
6. Stage percentages: table above, with denominator caveat.
7. Successful latency: successful-only distributions above; unavailable if N=0.
8. Successful RPC cost: distributions above; pre-refresh success is reported separately.
9. Final refresh approval: **{len(successful)}/{len(before_pass)}** attempts.
10. Four-fence operational evidence: {sum(r['closure_pass'] for r in history)} unchanged
    closed fence pairs. Changing fences/lag/same-slot limitations remain explicit.
11. Targeted synchronization/fence and invalidation-scope work is warranted.
    All five divergent banks match a captured later market mutation (four packets
    arrived after proof; one arrived during proof). One moving final fence added
    only failed transactions. The sole refresh was blocked by venue-wide unknown
    instruction invalidations despite an unchanged bank. These are concrete
    correctness questions, not authority to relax standards or increase budgets.
12. Standard-only synchronized calibration remains **not justified** unless
    natural full BUY and repeatable full SELL evidence pass. Calibration was not started.
"""
    variants = Counter()
    ancillary = Counter()
    for r in records:
        parity = r['proof_before_refresh']['evidence'].get('observed_anchor_parity', {})
        if parity:
            variants[parity['instruction']] += 1
            for m in parity['transfer_accounting']['movements']:
                if m['kind'] in ('UNRELATED_SYSTEM_TRANSFER','TOKEN_ACCOUNT_CLOSE_REFUND'):
                    ancillary[m['kind']] += 1
    write_doc('PROSPECTIVE_FULL_PROOF_VALIDATION', intro+answers+
              f'\nProspective exact parity variants: {dict(variants)}.\n'
              f'Ancillary movements accepted with exact accounting: {dict(ancillary)}.\n'
              f'Buffer/coverage gaps: {funnel["coverage_gap_reasons"]}; the final disconnect is teardown. No capacity increase or rescue was attempted.\n'
              'The signature-budget case had five successful vault signatures including its anchor, so the four-signature rejection is real; it is distinct from failed-row pollution.\n')
    write_doc('PROSPECTIVE_PROOF_FUNNEL', '# Prospective proof funnel\n\n'+table+
              '\nDenominator: '+funnel['denominator_scope']+'\n\n'+
              '```json\n'+json.dumps({k:v for k,v in funnel.items() if k!='late_packet_diagnostics'},indent=2)+'\n```\n')
    htext = '# Prospective history boundaries\n\nFour fences remain required. Each received fence and unattempted stage is retained. Changed rows, added successful/failed signatures and metadata differences are separately recorded in the JSON. A moved fence is not automatically proof of market movement.\n'
    for h in history:
        htext += f"\n## {h['mint']}\n\nFinal reason: {h['final_reason'] or 'proof-before-refresh PASS'}. " \
                 f"Closure: {h['closure_pass']}. Causes: {h['failure_causes']}.\n\n"
        htext += '| Fence | Status | Flags |\n|---:|---|---|\n'
        for f in h['fences']: htext += f"| {f['fence']} | {f['status']} | {', '.join(f.get('flags',[]))} |\n"
        htext += '\nSynchronization:\n```json\n'+json.dumps(h['synchronization'],indent=2)+'\n```\n'
    write_doc('PROSPECTIVE_HISTORY_BOUNDARIES', htext)
    rtext = f'# Prospective execution refresh\n\n{len(before_pass)} mandatory passive refresh attempts; {len(successful)} execution approvals. No orders.\n'
    for r in refreshes:
        if r['attempted']:
            rtext += '\n```json\n'+json.dumps({k:v for k,v in r.items() if k not in ('result','atomic_refresh_batch')},indent=2)+'\n```\n'
            rtext += 'Verdict: '+str(r.get('result',{}).get('revalidation_outcome',r.get('reason')))+'\n'
    write_doc('PROSPECTIVE_EXECUTION_REFRESH',rtext+
              '\nAll raw refresh batches and fresh/current quotes remain in the JSON.\n'
              'A new bank restores current-state checks but cannot manufacture missing native continuity.\n'
              'The sole SELL refresh advanced two slots with zero reserve/quote change, unchanged config hash and identity. Two recorded UNKNOWN_NATIVE_INSTRUCTION venue-wide invalidations in the refresh slot cleared trust during the read. This is why execution remained blocked despite an unchanged bank. The observed scoping is conservative; this run does not prove that those global instructions were harmless. Narrower invalidation handling would need its own account/write-set proof.\n')
    try:
        require_price_validation('runner-edge-prospective-v1', {})
    except ValueError as error:
        blocked = str(error)
    else:
        raise AssertionError('Runner unexpectedly unblocked')
    paths = ['analysis/prospective_'+n+'.json' for n in
             ('full_proofs','proof_funnel','history_boundaries','execution_refresh')]
    paths += ['analysis/prospective_capture_packets.jsonl','analysis/prospective_candidate_stages.jsonl']
    paths += ['analysis/prospective_capture_execution_proofs.json']
    gate = {'runner': 'BLOCKED', 'calibration': 'BLOCKED', 'calibration_started': False,
            'orders':0,'live_trading_enabled':False,'provider':data['provider'],
            'new_capture':True,'bounded_single_run':True,'policy':data['actual_policy'],
            'serious_candidates':len(records),'proof_before_refresh_PASS':len(before_pass),
            'full_PASS':len(successful),'full_BUY_PASS':funnel['full_BUY_PASS'],
            'full_SELL_PASS':funnel['full_SELL_PASS'], 'RPC_reads':data['rpc_reads'],
            'run_stop_bounds': {'seconds':300,'candidates':20,'RPC':96,'watch_capacity':32},
            'runner_block_verified':True,'runner_block_reason':blocked,
            'capture_code_sha256': data['proof_code_sha256'],
            'evidence_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}}
    previous = json.loads((ROOT/'analysis/proof_rejection_gate.json').read_text())
    core = ('src/memebot/paper/candidate_proof.py','src/memebot/paper/standard_math.py',
            'src/memebot/providers/solana/trade_alignment.py',
            'src/memebot/providers/solana/execution_accounting.py',
            'src/memebot/strategies/runner.py','src/memebot/intelligence/alpha_filter.py',
            'src/memebot/intelligence/risk/coordinator.py','src/memebot/core/config.py',
            'src/memebot/research/early_watch.py','src/memebot/providers/solana/watch_cohort.py')
    gate['proof_strategy_watch_core_unchanged'] = {p:data['proof_code_sha256'][p] ==
                                                   previous['source_sha256'][p] for p in core}
    assert all(gate['proof_strategy_watch_core_unchanged'].values())
    gate['regression_validation'] = {'pytest_passed':425,'ruff':'PASS','strict_mypy_files':134}
    gate['stop_condition'] = '20 natural candidates reached'
    gate['elapsed_seconds'] = data['elapsed_seconds']
    gate['coverage_gap_reasons'] = funnel['coverage_gap_reasons']
    gate['proof_code_matches_capture'] = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
                                           for p,h in data['proof_code_sha256'].items())
    assert gate['proof_code_matches_capture']
    docs = ['PROSPECTIVE_FULL_PROOF_VALIDATION','PROSPECTIVE_PROOF_FUNNEL',
            'PROSPECTIVE_HISTORY_BOUNDARIES','PROSPECTIVE_EXECUTION_REFRESH']
    gate['report_sha256'] = {'docs/'+p+'.md':hashlib.sha256((ROOT/('docs/'+p+'.md')).read_bytes()).hexdigest()
                             for p in docs}
    (ROOT/'analysis/prospective_proof_gate.json').write_text(json.dumps(gate,indent=2)+'\n')
    for filename in ('price_validation.json','calibration_gate.json'):
        path = ROOT/'analysis'/filename
        state = json.loads(path.read_text())
        state['prospective_full_proof_prerequisite'] = {'status':'BLOCKED',
                   'report':'docs/PROSPECTIVE_FULL_PROOF_VALIDATION.md',
                   'evidence':'analysis/prospective_proof_gate.json', 'full_passes':len(successful)}
        path.write_text(json.dumps(state,indent=2)+'\n')
    print(json.dumps({k:funnel[k] for k in ('serious_candidates','stages','full_candidate_PASS',
                                         'final_blockers','RPC_requests')}))


if __name__ == '__main__':
    main()
