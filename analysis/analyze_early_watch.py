"""Offline bounded-capture analysis. No credentials, HTTP or database access."""
import base64
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import median

from memebot.providers.solana._yellowstone_generated import geyser_pb2 as proto
from memebot.providers.solana.alchemy_evidence import rpc_packet
from memebot.providers.solana.evidence_stream import EvidenceBuffer, normalize_transaction
from memebot.research.packet_forensics import inspect_packet

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = ('UNSUPPORTED_TX_VERSION', 'MISSING_META', 'ACCOUNT_KEY_RESOLUTION',
              'LOOKUP_TABLE_ERROR', 'INNER_INSTRUCTION_PARSE', 'BALANCE_SCHEMA',
              'PROGRAM_FILTER_MISMATCH', 'MALFORMED_PACKET', 'ADAPTER_BUG', 'OTHER', 'UNKNOWN')


def describe(values):
    values = sorted(values)
    return {'min': values[0], 'median': median(values), 'max': values[-1]} if values else None


reports = []
for cap in (8, 16, 32):
    d = json.loads((ROOT / f'analysis/early_watch_{cap}.json').read_text())
    duration = d['elapsed_seconds']
    transport = d['transport']['metrics']
    discovery = d['discovery_breakdown']
    counts, old_version_rejects = Counter(), 0
    events, examples, kinds, market_bytes = [], defaultdict(list), Counter(), Counter()
    for line in (ROOT / f'analysis/early_watch_{cap}_packets.jsonl').read_text().splitlines():
        row = json.loads(line)
        if row.get('record_kind') != 'provider_protobuf':
            continue
        raw = base64.b64decode(row['raw_protobuf_base64'])
        update = proto.SubscribeUpdate.FromString(raw)
        at = datetime.fromisoformat(row['received_timestamp'])
        result = inspect_packet(update, at)
        category = result['category']
        counts[category] += 1
        old_version_rejects += update.transaction.transaction.transaction.message.HasField('config')
        kinds['V1' if update.transaction.transaction.transaction.message.HasField('config') else 'LEGACY_V0'] += 1
        if len(examples[category]) < 3:
            examples[category].append({'sha256': hashlib.sha256(raw).hexdigest(), 'signature':row['signature']})
        if result['usable']:
            event = normalize_transaction(rpc_packet(update), slot=row['slot'], signature=row['signature'],
                index=row['transaction_index'], source='offline_retained_raw', commitment='confirmed', received_at=at)
            events.append(event)
    replay = []
    for count_limit in (128, 256, 512):
        buffer = EvidenceBuffer(seconds=120, max_events=8192, per_market=count_limit, max_bytes=32_000_000)
        peak_bytes = 0
        for event in events:
            buffer.add(event)
            peak_bytes = max(peak_bytes, buffer.total_bytes)
        overflow = [e for e in buffer.evictions if 'OVERFLOW' in e['reason']]
        candidate_intersections = []
        for e in overflow:
            for pair in d['pairs']:
                cert = pair['window_certificate']
                if pair['mint'] == e['mint'] and cert['required_start'] <= e['received_at'] <= cert['end'] and e['evicted_at'] <= cert['end']:
                    candidate_intersections.append(e)
        replay.append({'limit':count_limit, 'overflow_events':len(overflow),
                       'evicted_before_relevant_candidate_window_end':len(candidate_intersections),
                       'peak_retained_bytes':peak_bytes,
                       'scope':'all usable retained packets; may include packets received after watch removal'})
    for mint, inventory in d['packet_inventory'].items():
        market_bytes[mint] = sum(e['bytes'] for e in inventory)
    bandwidth = {}
    for name, byte_count, messages in (
        ('DISCOVERY', d['meter']['decoded_application_bytes'], discovery['logsNotification_messages'] + discovery.get('ack_or_error_messages',0)),
        ('EARLY_WATCH_TRANSACTIONS', transport['transaction_bytes'], transport['transaction_messages']),
        ('ACCOUNTS', transport.get('account_bytes',0), transport.get('account_messages',0)),
        ('CONTROL_SLOTS', sum(v for k,v in transport.items() if k.endswith('_bytes') and k not in ['transaction_bytes','account_bytes']), sum(v for k,v in transport.items() if k.endswith('_messages') and k not in ['transaction_messages','account_messages']))):
        bandwidth[name] = {'bytes':byte_count, 'messages':messages, 'MB_per_hour':byte_count*3600/duration/1e6,
            'messages_per_hour':messages*3600/duration, 'bytes_per_launch':byte_count/d['launches'],
            'bytes_per_early_watch_market':byte_count/d['watched_markets'],
            'bytes_per_serious_candidate':byte_count/len(d['pairs']) if d['pairs'] else None}
    paired = {}
    for name in ('OLD','NEW'):
        proofs = [p[name] for p in d['pairs'] if name in p]
        paired[name] = {'attempts':len(proofs), 'statuses':dict(Counter(p['status'] for p in proofs)),
             'reasons':dict(Counter(p['reason'] for p in proofs)),
             'rpc_reads':sum(p['costs'].get('total_rpc_requests',0) for p in proofs),
             'local_transaction_hits':sum(p['costs'].get('local_transaction_hits',0) for p in proofs)}
    serious = {p['mint'] for p in d['pairs']}
    removals = Counter(x['reason'] for x in d['early_watch']['removals'])
    audited_complete = []
    for pair in d['pairs']:
        if pair['window_certificate']['status'] != 'COMPLETE_FOR_WINDOW':
            continue
        metric = pair['NEW']['candidate']['quality_evidence']['metric']
        if float(metric['observation_span_seconds']) >= float(metric['window_seconds']):
            audited_complete.append(pair['mint'])
    row = {'capacity':cap, 'duration_seconds':duration, 'launches':d['launches'], 'standard_launches':d['standard_launches'],
        'watched_markets':d['watched_markets'], 'serious_candidates':len(d['pairs']),
        'recall':d['serious_early_watch_recall'], 'local_before_first_proof':sum(p['local_before_retrospective'] for p in d['pairs']),
        'local_before_stream_proof':sum(p['local_before_stream_proof'] for p in d['pairs']),
        'complete_windows_reported_at_capture':sum(p['window_certificate']['status']=='COMPLETE_FOR_WINDOW' for p in d['pairs']),
        'complete_windows':len(audited_complete),
        'complete_window_mints_audited':audited_complete,
        'certificate_audit':f'Short observed spans cannot certify the full configured feature window. {sum(p["window_certificate"]["status"] == "COMPLETE_FOR_WINDOW" for p in d["pairs"]) - len(audited_complete)} provisional windows downgraded; raw pilot report preserved.',
        'missing_window_conditions':dict(Counter(r for p in d['pairs'] for r in p['window_certificate']['reasons'])),
        'active_watch_count_distribution_event_weighted':d['early_watch']['active_count_distribution'],
        'max_active':max(int(n) for n in d['early_watch']['active_count_distribution']),
        'capacity_admission_reject_attempts':d['early_watch']['metrics'].get('capacity_admission_rejects',0),
        'serious_candidates_previously_capacity_rejected':sum(p['early_watch']['capacity_rejected_before_serious'] for p in d['pairs']),
        'removal_reasons':dict(removals), 'filter_updates':len(d['transport']['filter_history']),
        'filter_updates_per_second':len(d['transport']['filter_history'])/duration,
        'false_watch_markets_in_bounded_capture':d['false_watch_markets'],
        'false_watch_transaction_bytes':sum(v for k,v in market_bytes.items() if k not in serious),
        'per_market_bytes':dict(market_bytes),
        'watch_to_serious_ms':describe([p['early_watch']['watch_to_serious_ms'] for p in d['pairs'] if p['early_watch']['watch_to_serious_ms'] is not None]),
        'watch_to_serious_events':describe([p['early_watch']['events_watch_to_serious'] for p in d['pairs'] if p['early_watch']['watch_to_serious_ms'] is not None]),
        'watch_to_serious_bytes':describe([p['early_watch']['bytes_watch_to_serious'] for p in d['pairs'] if p['early_watch']['watch_to_serious_ms'] is not None]),
        'full_packets':sum(counts.values()), 'signed_v1_packets':kinds['V1'],
        'adapter_rejects_at_capture':d['classifications'].get('UNSUPPORTED_TX_VERSION',0),
        'post_repair_classifications':dict(counts), 'rejection_catalog':{k:counts[k] for k in CATEGORIES},
        'representative_hashes':dict(examples), 'retention_replay':replay,
        'bandwidth':bandwidth, 'paired':paired, 'buffer_metrics':d['coverage']['metrics'],
        'discovery_breakdown':discovery}
    reports.append(row)
summary = {'runner':'BLOCKED', 'calibration':'BLOCKED', 'orders':0, 'proof_rules_unchanged':True,
           'captures':reports, 'limits':{'total_paired_rpc_reads':91,'rpc_budget_unchanged':96,
           'proof_rpc_budget':12,'history_fences':4,'final_atomic_refresh_required':True},
           'historical_98_rejections':'Raw packets absent; exact cause and fixable fraction unprovable.'}
(ROOT / 'analysis/early_watch_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
for r in reports:
    print(json.dumps({k:r[k] for k in ('capacity','serious_candidates','recall','local_before_first_proof','local_before_stream_proof','complete_windows','max_active','capacity_admission_reject_attempts','retention_replay','paired')}))
