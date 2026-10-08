"""Replay only recorded responses. No HTTP, database, discovery or orders.

Historical clock is scoped to replay; no receipt is exported for execution.
Missing responses are terminal evidence gaps, never duplicated or synthesized.
"""
import asyncio
import base64
import hashlib
import json
from collections import Counter
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import memebot.paper.candidate_proof as engine
from memebot.paper.standard_math import buy_exact_input, buy_exact_tokens, buy_quote, select_fees
from memebot.providers.solana._yellowstone_generated import geyser_pb2
from memebot.providers.solana.alchemy_evidence import rpc_packet
from memebot.providers.solana.canonical import curve_address
from memebot.providers.solana.encoding import decode_base58
from memebot.providers.solana.execution_accounting import execution_accounting
from memebot.providers.solana.pump import extract_anchor_events
from memebot.providers.solana.pump_idl import PumpTrade
from memebot.providers.solana.trade_alignment import account_keys, trade_invocations
from memebot.research.pumpfun_sequence import reconstruct_transaction

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'analysis/early_watch_32.json'
ARCHIVE = ROOT / 'analysis/early_watch_32_packets.jsonl'
SUMMARY = ROOT / 'analysis/early_watch_summary.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReplayClock(datetime):
    current = datetime.now(UTC)

    @classmethod
    def now(cls, tz=None):
        return cls.current if tz else cls.current.replace(tzinfo=None)


class RecordedRpc:
    """One consumption per recorded fence/bank; no fallback to another candidate."""
    def __init__(self, original, raw_packets):
        self.original = original
        self.evidence = original['evidence']
        self.histories = deepcopy(self.evidence.get('history_reads', []))
        self.bank = deepcopy(self.evidence.get('candidate_account_batch'))
        self.calls = []
        self.used = []
        self.transactions = {}
        for tx in [self.evidence['direct_anchor_transaction'],
                   *self.evidence.get('native_transactions', [])]:
            self.transactions[tx['transaction']['signatures'][0]] = tx
        end = datetime.fromisoformat(original['proof_started_at'])
        self.local = {sig: row for sig, row in raw_packets.items()
                      if datetime.fromisoformat(row['received_timestamp']) <= end}

    async def _call(self, method, params):
        self.calls.append({'method': method, 'params': params})
        if method == 'getTransaction':
            signature = params[0]
            if signature in self.transactions:
                self.used.append({'signature': signature, 'source': 'original_proof_response'})
                return deepcopy(self.transactions[signature])
            row = self.local.get(signature)
            if row:
                self.used.append({'signature': signature, 'source': 'retained_raw_packet',
                                 'received_at': row['received_timestamp']})
                return rpc_packet(geyser_pb2.SubscribeUpdate.FromString(
                    base64.b64decode(row['raw_protobuf_base64'])))
            raise engine.ProofFailure('FAIL_MISSING_EVIDENCE', 'MISSING_REPLAY_TRANSACTION:' + signature)
        if method == 'getSignaturesForAddress':
            if not self.histories:
                raise engine.ProofFailure('FAIL_MISSING_EVIDENCE', 'MISSING_REPLAY_HISTORY_FENCE')
            row = self.histories.pop(0)
            if row['address'] != params[0]:
                raise engine.ProofFailure('FAIL_MISSING_EVIDENCE', 'REPLAY_HISTORY_ORDER_MISMATCH')
            ReplayClock.current = datetime.fromisoformat(row['received_at'])
            return row['rows']
        if method == 'getMultipleAccounts':
            if not self.bank or self.bank['addresses'] != params[0]:
                raise engine.ProofFailure('FAIL_MISSING_EVIDENCE', 'MISSING_REPLAY_ATOMIC_BANK')
            row, self.bank = self.bank, None
            ReplayClock.current = datetime.fromisoformat(row['received_at'])
            return row['response']
        raise AssertionError(method)


def category(status, reason):
    if status == 'PASS':
        return 'PASS'
    if status == 'FAIL_MISSING_EVIDENCE':
        return 'missing_evidence'
    if status == 'FAIL_FEE':
        return 'fee/parity'
    if status == 'FAIL_STATE_SYNC':
        return 'sync'
    if status == 'FAIL_BUDGET':
        return 'budget'
    if status == 'FAIL_CONTINUITY' and ('reconstruction' in reason or 'mutation' in reason):
        return 'reconstruction'
    return 'other'


async def analyze():
    data = json.loads(INPUT.read_text())
    raw = {}
    for line in ARCHIVE.read_text().splitlines():
        row = json.loads(line)
        if row.get('record_kind') == 'provider_protobuf':
            raw.setdefault(row['signature'], row)
    audited = set(json.loads(SUMMARY.read_text())['captures'][-1]['complete_window_mints_audited'])
    results = []
    # Strongest certificates first; output retains original candidate numbering.
    order = sorted(enumerate(data['pairs']), key=lambda pair: pair[1]['mint'] not in audited)
    for index, pair in order:
        original = pair['NEW']
        c = deepcopy(original['candidate'])
        c['anchor'] = PumpTrade(**c['anchor'])
        for key in ('detected_at', 'native_event_received_at'):
            if c.get(key):
                c[key] = datetime.fromisoformat(c[key])
        candidate = engine.Candidate(**c)
        ev = original['evidence']
        tx = ev['direct_anchor_transaction']
        keys = account_keys(tx)
        calls = trade_invocations(tx, candidate.mint)
        call = calls[0]
        try:
            accounting = execution_accounting(tx, candidate.mint)
        except ValueError as error:
            accounting = {'status': str(error).split(':')[0], 'reason': str(error)}
        reconstruction = reconstruct_transaction(tx)
        bank = {k: ev[k] for k in ('curve', 'global', 'fee_config', 'supply', 'binding') if k in ev}
        parities = []
        unique_txs = {t['transaction']['signatures'][0]: t
                      for t in [tx, *ev.get('native_transactions', [])]}
        integer_case = None
        for sig, packet in unique_txs.items():
            event = next(e for _, e in extract_anchor_events(packet['meta']['logMessages'])
                         if isinstance(e, PumpTrade) and e.mint == candidate.mint)
            direction = 1 if event.is_buy else -1
            pre = {k: getattr(event, k) + (direction * event.token_amount if 'token' in k
                    else -direction * event.quote_amount)
                   for k in ('virtual_token_reserves', 'virtual_quote_reserves',
                             'real_token_reserves', 'real_quote_reserves')}
            if len(bank) != 5:
                parities.append({'signature': sig, 'status': 'MISSING_ATOMIC_BANK'})
                continue
            try:
                result = engine.validate_transaction_parity(packet, event, bank, pre, sig)
                parities.append({'signature': sig, 'status': 'EXACT', 'result': result})
            except engine.ProofFailure as error:
                parities.append({'signature': sig, 'status': error.status, 'reason': str(error)})
            if index in (4, 14, 15) and sig == candidate.anchor_signature:
                state = {**bank['curve'], **pre}
                rates = select_fees(bank['global'], bank['fee_config'], state, bank['supply'])
                gross = int.from_bytes(decode_base58(call['instruction']['data'])[8:16], 'little')
                native = buy_exact_input(state, gross, rates)
                inverse = buy_exact_tokens(state, event.token_amount, rates)
                sdk = buy_quote(state, gross, rates)
                integer_case = {'pre_state': pre, 'instruction_variant': call['name'], 'gross': gross,
                                'rates': rates, 'native_formula': native, 'old_inverse': inverse,
                                'sdk_construction_quote': sdk,
                                'native_actual_net': event.quote_amount,
                                'native_actual_tokens': event.token_amount,
                                'old_minus_native_net_raw': inverse['net_curve_input'] - event.quote_amount,
                                'sdk_minus_native_tokens_raw': sdk['token_output'] - event.token_amount}
        rpc = RecordedRpc(original, raw)
        ReplayClock.current = datetime.fromisoformat(original['proof_started_at'])
        with patch.object(engine, 'datetime', ReplayClock):
            proof = await engine.CandidateProofService(rpc).prove(candidate)
        after = category(proof.status, proof.reason or '')
        if index in (3, 10, 12):
            classification = 'UNKNOWN'
            cause = 'PHYSICAL_BALANCE_MISMATCH: unresolved direct router-owned balance redistribution'
        elif index == 5:
            classification = 'MISSING_EVIDENCE'
            cause = 'MISSING_PACKET: intermediate wrapped-SOL rent/token state; additional Pump mutation unsupported'
        elif index == 2:
            classification = 'TRUE_SAFETY_REJECTION'
            cause = ('Original misleading history-crosses-snapshot rejection was a failed row; '
                     'after filtering, same-slot order remains unproven at that boundary and '
                     'the two successful retained events do not reach the atomic terminal bank')
        elif index in (0, 6):
            classification = 'MISSING_EVIDENCE'
            cause = 'Failed signatures polluted budget, but truncated pages/ordering or missing fences prevent equivalent full proof'
        else:
            classification = 'PROOF_ENGINE_FALSE_NEGATIVE'
            cause = ('PROOF_ENGINE_LIMITATION: CPI alignment and ancillary accounting' if index in (7, 9, 13)
                     else 'Native exact-input rounding differs from inverse exact-token arithmetic' if index in (4, 14, 15)
                     else 'Exact user proceeds require explicit tip/rent/account-close adjustments')
        packets = []
        for sig, packet in unique_txs.items():
            row = raw.get(sig)
            packets.append({'signature': sig, 'slot': packet['slot'],
                            'transaction_index': row['transaction_index'] if row else None,
                            'received_timestamp': row['received_timestamp'] if row else None,
                            'evidence_source': 'raw_archive_and_original_proof' if row else 'original_proof_response',
                            'packet_sha256': hashlib.sha256(json.dumps(packet, sort_keys=True).encode()).hexdigest()})
        row = raw.get(candidate.anchor_signature)
        physical = {'lamports': [dict(account=k, pre=tx['meta']['preBalances'][i],
                                     post=tx['meta']['postBalances'][i],
                                     delta=tx['meta']['postBalances'][i] - tx['meta']['preBalances'][i])
                                for i, k in enumerate(keys)],
                    'pre_token_balances': tx['meta']['preTokenBalances'],
                    'post_token_balances': tx['meta']['postTokenBalances'],
                    'network_fee': tx['meta']['fee']}
        results.append({'case': index, 'mint': candidate.mint, 'curve': curve_address(candidate.mint),
                        'signature': candidate.anchor_signature, 'slot': candidate.anchor_slot,
                        'transaction_index': row['transaction_index'] if row else None,
                        'event_index': candidate.event_ordinal, 'side': 'BUY' if candidate.anchor.is_buy else 'SELL',
                        'alignment': {k: call[k] for k in ('top_index', 'inner_index', 'stack_height',
                                                         'event_inner_index', 'name', 'mapping')},
                        'proof_started_at': original['proof_started_at'],
                        'proof_completed_at': original['proof_completed_at'],
                        'full_packets_retained': packets,
                        'original_local_packets_used': ev.get('stream_packets', []),
                        'local_available_at_start': [sig for sig, r in raw.items()
                            if sig in unique_txs and r['received_timestamp'] <= datetime.fromisoformat(
                                original['proof_started_at']).isoformat()],
                        'history_fences': ev.get('history_reads', []),
                        'account_bank': ev.get('candidate_account_batch'),
                        'fee_route': ev.get('fee_route_class', 'UNKNOWN_NO_ATOMIC_BANK'),
                        'window_certificate': pair['window_certificate'],
                        'audited_complete_window': candidate.mint in audited,
                        'observed_span_seconds': c['quality_evidence']['metric']['observation_span_seconds'],
                        'physical_balances': physical, 'accounting_after': accounting,
                        'reconstruction_before': ev.get('direct_anchor_reconstruction'),
                        'reconstruction_after': reconstruction, 'parity_after': parities,
                        'integer_parity_case': integer_case, 'classification': classification, 'cause': cause,
                        'before': {'status': original['status'], 'reason': original['reason'],
                                   'category': category(original['status'], original['reason'])},
                        'after': {'status': proof.status, 'reason': proof.reason, 'category': after,
                                  'evidence': proof.evidence, 'consumed_requests': rpc.calls,
                                  'transactions_reused': rpc.used, 'receipt_exported': False}})
    results.sort(key=lambda r: r['case'])
    before = Counter(r['before']['category'] for r in results)
    after = Counter(r['after']['category'] for r in results)
    for key in ('PASS', 'reconstruction', 'fee/parity', 'sync', 'budget', 'missing_evidence', 'other'):
        before.setdefault(key, 0)
        after.setdefault(key, 0)
    output = {'runner': 'BLOCKED', 'calibration': 'BLOCKED', 'orders': 0, 'provider_calls': 0,
              'freshness': 'historical clock only; no current execution authorization',
              'policy': engine.ProofPolicy().__dict__, 'before': dict(before), 'after': dict(after),
              'classifications': dict(Counter(r['classification'] for r in results)),
              'audited_complete_windows': len(audited),
              'window_count_correction': 'Five provisional; three spans <10s; two audited, not three',
              'input_sha256': {str(p.relative_to(ROOT)): digest(p) for p in (INPUT, ARCHIVE, SUMMARY)},
              'candidates': results}
    destination = ROOT / 'analysis/proof_rejection_forensics.json'
    destination.write_text(json.dumps(output, indent=2, default=str) + '\n')
    print(json.dumps({k: output[k] for k in ('before', 'after', 'classifications', 'audited_complete_windows')}))


if __name__ == '__main__':
    asyncio.run(analyze())
