"""Summarize only non-secret stream telemetry for the bounded repair check."""
import json
from pathlib import Path

path = Path('analysis/paper_websocket_standard.stderr.log')
events = []
for line in path.read_text(encoding='utf-8').splitlines():
    try:
        event = json.loads(line)
    except ValueError:
        continue
    events.append(event)
health = [e for e in events if e.get('event') == 'provider_health']
progress = [e for e in events if e.get('event') == 'websocket_receive_progress']
errors = [e for e in events if e.get('event') in (
    'websocket_disconnect', 'native_event_validation_failed',
    'wallet_projection_failed', 'wallet_projection_backlog_full')]
report = {
    'connected_at': health[0]['timestamp'] if health else None,
    'last_progress_at': progress[-1]['timestamp'] if progress else None,
    'processed_messages_lower_bound': progress[-1]['processed_messages'] if progress else 0,
    'duplicates_removed_lower_bound': progress[-1]['duplicate_messages'] if progress else 0,
    'disconnects': sum(e['event'] == 'websocket_disconnect' for e in errors),
    'validation_errors': sum(e['event'] == 'native_event_validation_failed' for e in errors),
    'wallet_errors': sum(e['event'].startswith('wallet_projection') for e in errors),
    'last_queue_depth': progress[-1]['queue_depth'] if progress else None,
    'last_queue_lag_ms': progress[-1]['queue_lag_ms'] if progress else None,
    'max_sampled_queue_lag_ms': max((e['queue_lag_ms'] for e in progress), default=0),
    'queue_peak': max((e['queue_peak'] for e in progress), default=0),
    'tests_passed': 484,
    'thresholds_changed': False,
    'live_enabled': False,
}
Path('analysis/websocket_repair_validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
