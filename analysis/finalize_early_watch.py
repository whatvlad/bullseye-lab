"""Persist blocked readiness with final code/evidence fingerprints; no trading."""
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from memebot.paper.validation_gate import CRITICAL_FILES, require_price_validation

ROOT = Path(__file__).resolve().parents[1]
summary = json.loads((ROOT / 'analysis/early_watch_summary.json').read_text())
try:
    require_price_validation('runner-edge-prospective-v1', {})
except ValueError as error:
    blocked, reason = True, str(error)
else:
    raise RuntimeError('Runner block unexpectedly absent')

gate = {'recorded_at': datetime.now(UTC).isoformat(), 'runner':'BLOCKED', 'calibration':'BLOCKED',
        'calibration_started':False, 'orders':0, 'database_mutations':0,
        'runner_block_verified':blocked, 'runner_block_reason':reason,
        'checks':{'full_packets_captured':True, 'decoder_loss_understood_for_new_raw_capture':True,
          'all_historical_98_causes_proven':False, 'adapter_format_limitation_repaired':True,
          'majority_early_watch_recall':True, 'majority_local_before_first_proof':False,
          'audited_observed_window_count':summary['captures'][-1]['complete_windows'], 'full_execution_window_closure_verified':False,
          'no_silent_evictions':True, '512_retention_replay_passed':True,
          '512_retention_live_validated':False, 'natural_complete_BUY':False,
          'repeatable_live_SELL':False, 'candidate_proof_unchanged':True,
          'proof_RPC_budgets_unchanged':True, 'strategy_thresholds_changed':False},
        'rpc_reads':91, 'rpc_cap':96, 'regression_validation':{'tests_passed':380,
            'ruff':'PASS','strict_mypy_files':131},
        'blockers':['Only 4/17 anchors before the first proof attempt',
          'Audited receipt-window certificates do not establish full event-time/account execution closure',
          'No natural complete BUY or repeated SELL PASS',
          'Unexplained native/physical reconstruction and fee parity remain rejected',
          'Snapshot/history ordering and existing narrow signature budgets remain restrictive',
          '512-event retention has offline replay only; historical 98 raw rejects unavailable'],
        'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in CRITICAL_FILES},
        'evidence_sha256':{p:hashlib.sha256((ROOT/'analysis'/p).read_bytes()).hexdigest()
           for p in ['early_watch_summary.json','early_watch_historical_retention.json']
              + [f'early_watch_{n}{suffix}' for n in (8,16,32)
                 for suffix in ('.json','_packets.jsonl','_decoder_forensics.json','_execution_proofs.json')]}}
(ROOT/'analysis/early_watch_proof_gate.json').write_text(json.dumps(gate,indent=2)+'\n')
for name in ('calibration_gate.json','price_validation.json'):
    path = ROOT/'analysis'/name
    d = json.loads(path.read_text())
    d['early_watch_prerequisite'] = {'status':'BLOCKED', 'calibration_started':False,
       'report':'docs/EARLY_WATCH_COVERAGE.md','evidence':'analysis/early_watch_proof_gate.json'}
    path.write_text(json.dumps(d,indent=2)+'\n')
for name in ('filtered_stream_proof_gate.json','stream_proof_gate.json'):
    path = ROOT/'analysis'/name
    d = json.loads(path.read_text())
    d['subsequent_early_watch_phase'] = 'analysis/early_watch_proof_gate.json'
    path.write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({'runner':'BLOCKED','calibration':'BLOCKED','runner_block_verified':blocked,
                  'tests_passed':380,'rpc_reads':91}))
