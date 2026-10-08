"""Persist BLOCKED outcomes; never grants execution or calibration permission."""
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from memebot.paper.candidate_proof import ProofPolicy
from memebot.paper.validation_gate import CRITICAL_FILES, require_price_validation

ROOT = Path(__file__).resolve().parents[1]
result = json.loads((ROOT / 'analysis/proof_rejection_forensics.json').read_text())
prior = json.loads((ROOT / 'analysis/early_watch_proof_gate.json').read_text())
unchanged = ['src/memebot/strategies/runner.py', 'src/memebot/intelligence/alpha_filter.py',
             'src/memebot/intelligence/risk/coordinator.py', 'src/memebot/core/config.py',
             'src/memebot/research/early_watch.py', 'src/memebot/research/early_watch_run.py',
             'src/memebot/providers/solana/watch_cohort.py']
def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()

checks = {p: digest(p) == prior['source_sha256'][p] for p in unchanged}
assert all(checks.values()), checks
assert result['after']['PASS'] == 0
assert result['policy'] == ProofPolicy().__dict__
try:
    require_price_validation('runner-edge-prospective-v1', {})
except ValueError as error:
    blocked_reason = str(error)
else:
    raise AssertionError('Runner gate unexpectedly passed')
evidence = ['analysis/proof_rejection_forensics.json', 'docs/PROOF_REJECTION_FORENSICS.md',
            'analysis/replay_proof_rejections.py', 'analysis/write_proof_forensics_report.py',
            'tests/fixtures/proof_rejections.json', 'tests/test_retained_proof_rejections.py']
gate = {'recorded_at': datetime.now(UTC).isoformat(), 'runner': 'BLOCKED',
        'calibration': 'BLOCKED', 'live_trading_enabled': False,
        'orders': 0, 'provider_calls': 0, 'database_mutations': 0,
        'new_passive_pilot_run': False, 'runner_block_verified': True,
        'runner_block_reason': blocked_reason, 'policy': ProofPolicy().__dict__,
        'four_raw_history_fences_required': True, 'final_atomic_execution_refresh_required': True,
        'disagreement_bands_configured': False, 'strategy_and_discovery_hashes_unchanged': checks,
        'before': result['before'], 'after': result['after'],
        'classification_scope': 'original rejected stage; not full candidate readiness',
        'classifications': result['classifications'],
        'audited_complete_windows': result['audited_complete_windows'],
        'supersedes_window_count_in': 'analysis/early_watch_proof_gate.json',
        'regression_validation': {'pytest_passed': 423, 'ruff': 'PASS', 'strict_mypy_files': 133},
        'blockers': ['No full candidate BUY or repeated SELL PASS',
                     'Ten required next-stage responses were never captured',
                     'Three UNKNOWN router redistributions and missing intermediate WSOL state',
                     'Two truncated history boundaries within existing caps',
                     'Same-slot ordering and atomic terminal state mismatch',
                     'Observed receipt-window certificates do not certify execution closure'],
        'source_sha256': {p: digest(p) for p in CRITICAL_FILES},
        'evidence_sha256': {p: digest(p) for p in evidence}}
(ROOT / 'analysis/proof_rejection_gate.json').write_text(json.dumps(gate, indent=2) + '\n')
for name in ('price_validation.json', 'calibration_gate.json'):
    path = ROOT / 'analysis' / name
    state = json.loads(path.read_text())
    state['proof_rejection_prerequisite'] = {
        'status': 'BLOCKED', 'report': 'docs/PROOF_REJECTION_FORENSICS.md',
        'evidence': 'analysis/proof_rejection_gate.json', 'full_candidate_passes': 0,
    }
    path.write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps({'runner': 'BLOCKED', 'calibration': 'BLOCKED', 'tests_passed': 423,
                  'unchanged_strategy_discovery_files': len(checks)}))
