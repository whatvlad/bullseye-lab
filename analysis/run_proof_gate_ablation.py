"""Retained-data ablation; no HTTP, fabricated historical responses or orders."""
import asyncio
import base64
import hashlib
import json
from collections import Counter
from copy import deepcopy
from dataclasses import fields
from datetime import UTC, datetime
from pathlib import Path

from memebot.paper.candidate_proof import Candidate, CandidateProofService, Proof, ProofFailure, validate_transaction_parity
from memebot.paper.standard_math import buy_quote, sell_quote
from memebot.providers.solana._yellowstone_generated import geyser_pb2
from memebot.providers.solana.alchemy_evidence import rpc_packet
from memebot.providers.solana.execution_accounting import execution_accounting
from memebot.providers.solana.pump import extract_anchor_events
from memebot.providers.solana.pump_idl import PumpTrade
from memebot.research.proof_gate_ablation import CORE, POLICIES, evaluate, transaction_write_scope, scoped_invalidation
from memebot.research.pumpfun_sequence import reconstruct_transaction

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATHS = ['analysis/prospective_full_proofs.json','analysis/prospective_history_boundaries.json',
    'analysis/prospective_execution_refresh.json','analysis/prospective_capture_execution_proofs.json',
    'analysis/prospective_capture_packets.jsonl','analysis/early_watch_32.json',
    'analysis/live_execution_proofs_run3.json','analysis/live_historical_forensics.json',
    'analysis/prospective_proof_gate.json']


def read(name):
    return json.loads((ROOT/name).read_text())


def write(name, data):
    (ROOT/('analysis/'+name+'.json')).write_text(json.dumps(data,indent=2,default=str)+'\n')


def candidate(raw):
    c = deepcopy(raw)
    c['anchor'] = PumpTrade(**c['anchor'])
    for k in ('detected_at','native_event_received_at'):
        if c.get(k): c[k] = datetime.fromisoformat(c[k])
    return Candidate(**{k:v for k,v in c.items() if k in {f.name for f in fields(Candidate)}})


async def decode_bank(c, batch):
    if not batch:
        return None, 'MISSING_RETAINED_ATOMIC_BANK'
    class Offline:
        async def _call(self, method, params):
            assert method == 'getMultipleAccounts' and params[0] == batch['addresses']
            return deepcopy(batch['response'])
    try:
        return await CandidateProofService(Offline())._bundle(Proof(c)), None
    except (ProofFailure, AssertionError, KeyError, ValueError) as error:
        return None, str(error)


def terminal_states(e, c):
    txs = e.get('native_transactions', [])
    if e.get('parity'):
        return e['parity'][-1]['post_reserves']
    # Do not fabricate sequence order from RPC response iteration order.
    if len({t['transaction']['signatures'][0] for t in txs}) > 1:
        return None
    event = c.anchor
    return {k:getattr(event,k) for k in ('virtual_token_reserves','virtual_quote_reserves',
                                        'real_token_reserves','real_quote_reserves')}


async def retained_case(case_id, q, certificate=None, refresh=None, truth='NOT_ESTABLISHED', provenance=None):
    e = q['evidence']
    c = candidate(q['candidate'])
    tx = e.get('direct_anchor_transaction')
    bank, bank_error = await decode_bank(c, e.get('candidate_account_batch'))
    fresh_batch = e.get('execution_refresh_account_batch')
    fresh, fresh_error = await decode_bank(c, fresh_batch)
    facts = {k:None for p in POLICIES.values() for k in p.requirements}
    reasons = {}
    facts['standard_supported_route'] = not (c.multi_event or c.complete or c.migrated or
        c.anchor.is_mayhem_mode is not False or c.venue != 'pump_fun')
    if e.get('fee_route_branches'): facts['standard_supported_route'] = False
    facts['exact_anchor'] = (tx.get('slot') == c.anchor_slot and c.anchor_signature in
                            tx['transaction']['signatures']) if tx else None
    if tx:
        reconstruction = reconstruct_transaction(tx)
        facts['exact_reconstruction'] = len(reconstruction)==1 and reconstruction[0]['status']=='TRANSACTION_SEQUENCE_VERIFIED'
        reasons['reconstruction'] = reconstruction
        try:
            ledger = execution_accounting(tx,c.mint)
            facts['exact_physical_accounting'] = True
            reasons['accounting'] = ledger
        except (ValueError,KeyError) as error:
            facts['exact_physical_accounting'] = False
            reasons['accounting_error'] = str(error)
        if bank:
            event = c.anchor
            sign = 1 if event.is_buy else -1
            pre = {k:getattr(event,k)+(sign*event.token_amount if 'token' in k else -sign*event.quote_amount)
                   for k in ('virtual_token_reserves','virtual_quote_reserves','real_token_reserves','real_quote_reserves')}
            try:
                reasons['parity'] = validate_transaction_parity(tx,event,bank,pre,c.anchor_signature)
                facts['exact_parity'] = True
            except (ProofFailure,ValueError,KeyError) as error:
                facts['exact_parity'] = False
                reasons['parity_error'] = str(error)
    facts['canonical_identity_config'] = True if bank else False if bank_error!='MISSING_RETAINED_ATOMIC_BANK' else None
    facts['compatible_lifecycle_mode'] = (not bank['curve']['complete'] and not bank['curve']['is_mayhem_mode']) if bank else None
    facts['refresh_retained'] = True if fresh_batch else None
    facts['refresh_identity_config'] = True if fresh else False if fresh_batch else None
    facts['refresh_binding_compatible'] = (bank['binding']==fresh['binding']) if bank and fresh else None
    if bank and fresh:
        facts['current_state_consistent'] = (
            bank['vault_amount']-bank['curve']['real_token_reserves']==fresh['vault_amount']-fresh['curve']['real_token_reserves'] and
            bank['curve_lamports']-bank['curve']['real_quote_reserves']==fresh['curve_lamports']-fresh['curve']['real_quote_reserves'] and
            fresh['slot'] >= bank['slot'])
        # Recompute executable math from the actual refreshed bank, not last trade price.
        try:
            reasons['refresh_quotes'] = {'buy':buy_quote(fresh['curve'],c.buy_budget_raw,fresh['rates']),
                                        'sell':sell_quote(fresh['curve'],c.sell_quantity_raw,fresh['rates'])}
        except ValueError as error:
            facts['current_state_consistent'] = False
            reasons['refresh_quote_error'] = str(error)
        start = (refresh or {}).get('request_at') or q.get('decision_at')
        received = fresh_batch.get('received_at')
        if start and received:
            age = (datetime.fromisoformat(received)-datetime.fromisoformat(str(start))).total_seconds()*1000
            proof_age = (datetime.fromisoformat(str(q['proof_completed_at']))-
                         datetime.fromisoformat(e['candidate_account_batch']['received_at'])).total_seconds()*1000
            facts['refresh_fresh'] = 0<=age<=2000 and 0<=proof_age<=2000
            reasons['refresh_request_age_ms'] = age
    fences = e.get('history_reads', [])
    for i in range(4):
        facts['fence_'+str(i+1)] = (True if i<2 else fences[i]['rows']==fences[i-2]['rows']) if i<len(fences) else None
    # B's bank-before and bank-after curve fences use exact raw agreement.
    facts['fence_before_bank'] = facts['fence_1']
    facts['fence_after_bank'] = facts['fence_3']
    terminal = terminal_states(e,c)
    facts['terminal_bank_equal'] = (terminal=={k:bank['curve'][k] for k in terminal}) if terminal and bank else None
    facts['bounded_continuity'] = True if e.get('native_sequence_anchored') else None
    if q.get('reason') and any(s in q['reason'] for s in ('same-slot','terminal transaction','missing reserve','successor boundary','signature window')):
        facts['bounded_continuity'] = False
    facts['certified_stream_window'] = (certificate['status']=='COMPLETE_FOR_WINDOW') if certificate else None
    # The retained certificates explicitly do not certify all-program mutation closure.
    facts['relevant_mutation_window_closed'] = None
    facts['strict_refresh_approved'] = (refresh or {}).get('result',{}).get('execution_approved',None)
    if e.get('passive_refresh'): facts['strict_refresh_approved'] = e['passive_refresh'].get('execution_approved')
    facts['strict_invalidation_clear'] = not bool(q.get('incompatible_mutation'))
    if refresh and refresh.get('result') and not all(refresh['result'].get('trust_dimensions',{}).values()):
        facts['strict_invalidation_clear'] = False
        facts['no_unknown_protected_mutation'] = None
    elif q.get('reason') and ('invalidation' in q['reason'] or 'gap' in q['reason']):
        facts['strict_invalidation_clear'] = False
    else:
        facts['no_unknown_protected_mutation'] = True if q['status']=='PASS' and facts['strict_refresh_approved'] else None
    policy_results = {name:evaluate(facts,name) for name in POLICIES}
    if truth=='NOT_ESTABLISHED':
        if facts['exact_physical_accounting'] is False or facts['exact_reconstruction'] is False:
            truth='KNOWN_UNPROVABLE'
        elif facts['refresh_retained'] is None:
            truth='MISSING_EVIDENCE'
    if policy_results['CURRENT_STATE_ONLY_RESEARCH']['shadow_pass'] and not policy_results['STRICT']['shadow_pass']:
        truth = 'KNOWN_UNPROVABLE'
    result = {'id':case_id,'mint':c.mint,'signature':c.anchor_signature,
              'source':provenance,'truth_class':truth,'facts':facts,'rechecked_evidence':reasons,
              'bank_error':bank_error,'refresh_error':fresh_error,
              'binding_difference':{k:{'before':bank['binding'].get(k),'after':fresh['binding'].get(k)}
                    for k in bank['binding'] if fresh and bank['binding'].get(k)!=fresh['binding'].get(k)} if bank else None,
              'recorded_STRICT_pre_refresh':q['status'], 'policies':policy_results,
              'recorded_refresh_failure':e.get('passive_refresh_failure'),
              'mandatory_refresh_source':fresh_batch.get('received_at') if fresh_batch else None,
              'all_outputs_non_authorizing':True}
    return result


def metric(rows, policy):
    accepted = [r for r in rows if r['policies'][policy]['shadow_pass']]
    return {'cases':len(rows),'SHADOW_PASS':len(accepted),
            'ADDITIONAL_PASS':sum(not r['policies']['STRICT']['shadow_pass'] for r in accepted),
            'KNOWN_UNSAFE_ACCEPTED':sum(r['truth_class']=='KNOWN_UNSAFE' for r in accepted),
            'KNOWN_UNPROVABLE_ACCEPTED':sum(r['truth_class']=='KNOWN_UNPROVABLE' for r in accepted),
            'MISSING_EVIDENCE_ACCEPTED':sum(r['truth_class']=='MISSING_EVIDENCE' for r in accepted),
            'UNCHANGED_SAFE_REJECTION':sum(not r['policies'][policy]['shadow_pass'] and
                      not r['policies']['STRICT']['shadow_pass'] and r['truth_class'] in
                      ('KNOWN_UNSAFE','KNOWN_UNPROVABLE','MISSING_EVIDENCE') for r in rows),
            'accepted_ids':[r['id'] for r in accepted],
            'safety_claim':'Acceptance never proves safety; unchanged safe rejection means rejecting defective evidence, not certifying market safety'}


async def main():
    prospective = read('analysis/prospective_full_proofs.json')
    history = read('analysis/prospective_history_boundaries.json')['candidates']
    refresh_records = read('analysis/prospective_execution_refresh.json')['candidates']
    current = []
    for i,r in enumerate(prospective['candidate_stages']):
        # After-refresh snapshot retains the real refresh response; qualification is unchanged.
        current.append(await retained_case('prospective_'+str(i),r['NEW'],r['window_certificate'],r['refresh'],
                     provenance='analysis/prospective_full_proofs.json#/candidate_stages/'+str(i)))
    retained = []
    for i,r in enumerate(read('analysis/early_watch_32.json')['pairs']):
        truth = 'KNOWN_UNPROVABLE' if i in (3,5,10,12) else 'MISSING_EVIDENCE'
        retained.append(await retained_case('retained_'+str(i),r['NEW'],r['window_certificate'],truth=truth,
                                            provenance='analysis/early_watch_32.json#/pairs/'+str(i)))
    original = []
    for i,q in enumerate(read('analysis/live_execution_proofs_run3.json')['candidate_proofs']):
        if q['status']=='PASS':
            original.append(await retained_case('original_live_SELL_'+str(i),q,
                           provenance='analysis/live_execution_proofs_run3.json#/candidate_proofs/'+str(i)))
    # Contract fixtures are labeled synthetic. They never invent historical responses.
    base = {k:True for p in POLICIES.values() for k in p.requirements}
    contract_specs = {
        'malformed_identity':('canonical_identity_config',False,'KNOWN_UNSAFE'),
        'malformed_config':('refresh_identity_config',False,'KNOWN_UNSAFE'),
        'stale_refresh':('refresh_fresh',False,'KNOWN_UNSAFE'),
        'migration_completion':('compatible_lifecycle_mode',False,'KNOWN_UNSAFE'),
        'mayhem_or_pumpswap':('standard_supported_route',False,'KNOWN_UNSAFE'),
        'multi_event_ambiguity':('exact_reconstruction',False,'KNOWN_UNPROVABLE'),
        'router_redistribution':('exact_physical_accounting',False,'KNOWN_UNPROVABLE'),
        'missing_WSOL_state':('exact_physical_accounting',None,'MISSING_EVIDENCE'),
        'missing_refresh':('refresh_retained',None,'MISSING_EVIDENCE'),
        'config_binding_changed':('refresh_binding_compatible',False,'KNOWN_UNSAFE'),
        'history_truncated':('bounded_continuity',False,'KNOWN_UNPROVABLE'),
        'same_slot_order_ambiguity':('bounded_continuity',False,'KNOWN_UNPROVABLE'),
        'terminal_bank_mismatch':('terminal_bank_equal',False,'KNOWN_UNPROVABLE'),
        'unknown_global_mutation':('strict_invalidation_clear',False,'KNOWN_UNPROVABLE'),
        'uncertified_window':('relevant_mutation_window_closed',None,'ALTERNATIVE_HISTORY_CLOSURE'),
    }
    contract = []
    for name,(key,value,truth) in contract_specs.items():
        facts = {**base,key:value}
        if name=='unknown_global_mutation':facts['no_unknown_protected_mutation']=None
        if key in ('bounded_continuity','terminal_bank_equal'):facts['relevant_mutation_window_closed']=None
        contract.append({'id':'contract_'+name,'source':'EXPLICIT_SYNTHETIC_POLICY_CONTRACT_NOT_HISTORICAL_TRUTH',
                         'truth_class':truth,'facts':facts,'policies':{p:evaluate(facts,p) for p in POLICIES}})
    # Known historical problematic native packets lack their historical banks/refreshes.
    diagnostic = []
    for i,row in enumerate(read('analysis/live_historical_forensics.json').get('rows',[])):
        facts = {k:None for p in POLICIES.values() for k in p.requirements}
        packet = row.get('transaction')
        reconstructed = reconstruct_transaction(packet) if packet else None
        if reconstructed:
            facts['exact_reconstruction'] = len(reconstructed)==1 and reconstructed[0]['status']=='TRANSACTION_SEQUENCE_VERIFIED'
        ledger = None
        ledger_error = None
        if packet:
            try:
                ledger = execution_accounting(packet,row['mint'])
                facts['exact_physical_accounting'] = True
            except (ValueError,KeyError) as error:
                ledger_error = str(error)
                facts['exact_physical_accounting'] = False
        diagnostic.append({'id':'historical_bad_state_'+str(i),'source':
                  'analysis/live_historical_forensics.json#/rows/'+str(i), 'truth_class':'MISSING_EVIDENCE',
                  'original_reason':row.get('original_reason'),'historical_causality_proven':row.get('historical_causality_proven'),
                  'native_packet_retained':bool(row.get('transaction')),
                  'packet_reconstruction':reconstructed,'packet_accounting':ledger,
                  'packet_accounting_error':ledger_error,
                  'missing_truth':'historical canonical bank/config and final refresh not retained',
                  'facts':facts,'policies':{p:evaluate(facts,p) for p in POLICIES}})
    natural = current+retained+original+diagnostic
    supported = [r for r,raw in zip(current,prospective['candidate_stages'])
                 if raw['dominant_final_blocker']!='UNSUPPORTED_ROUTE']
    ablation = {'mode':'OFFLINE_SHADOW_NO_AUTHORIZATION','STRICT_changed':False,
            'policies':{p:POLICIES[p].requirements for p in POLICIES},
            'prospective_20':{'counts':{p:metric(current,p) for p in POLICIES},'cases':current},
            'supported_16':{'counts':{p:metric(supported,p) for p in POLICIES},'case_ids':[r['id'] for r in supported]},
            'retained_17':{'counts':{p:metric(retained,p) for p in POLICIES},'cases':retained},
            'original_live_SELL':original,'historical_bad_execution_diagnostic':diagnostic,
            'natural_corpus_counts':{p:metric(natural,p) for p in POLICIES},
            'synthetic_contract_counts':{p:metric(contract,p) for p in POLICIES},'synthetic_contracts':contract,
            'retained_synchronization_cases':[{'case_id':'prospective_'+str(i), **h['synchronization'],
                    'primary_classification':'INDEX_LAG' if any(p['availability']=='AVAILABLE_AT_PROOF_TIME'
                           for p in h['synchronization']['stream_packets_matching_bank_post_state']) else 'STREAM_DELIVERY_LAG',
                    'secondary_classification':'REAL_STATE_MOVEMENT',
                    'current_state_policy_safety':'UNKNOWN without the missing final refresh',
                    'unsafe_current_snapshot_demonstrated':False}
                    for i,h in enumerate(history) if h['synchronization'].get('exact_bank_minus_terminal_delta') and
                       any(h['synchronization']['exact_bank_minus_terminal_delta'].values())],
            'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCE_PATHS}}
    ablation['prospective_policy_funnels'] = {p:[{'requirement':key,
          'demonstrated_true':sum(r['facts'].get(key) is True for r in current),
          'contradicted':sum(r['facts'].get(key) is False for r in current),
          'missing_unknown':sum(r['facts'].get(key) is None for r in current)}
          for key in POLICIES[p].requirements] for p in POLICIES}
    write('proof_gate_ablation',ablation)
    # Independent final fence effects: compare each fence's own address history.
    contributions = []
    for number in range(1,5):
        fail = [i for i,h in enumerate(history) if h['fences'][number-1]['status']=='MOVED']
        unique = [i for i in fail if not any(f['status']=='MOVED' for f in history[i]['fences'] if f['fence']!=number)]
        stage_rejections = ([3] if number==2 else fail) if number>1 else []
        contributions.append({'fence':number,'role':('curve discovery before bank' if number==1 else
                 'vault discovery after initial bank receipt' if number==2 else
                 'curve final history equality' if number==3 else 'vault final history equality'),
              'received_candidates':sum(h['fences'][number-1]['status']!='NOT_ATTEMPTED_AFTER_REJECTION' for h in history),
              'independent_raw_changes':fail,'uniquely_changed_fence_candidates':unique,
              'stage_rejections':stage_rejections,'stage_rejection_count':len(stage_rejections),
              'first_two_fence_role_limitation':'A received discovery fence can return index-lagged history without immediately failing; sequence/bank guards resolve it later',
              'known_unsafe_uniquely_caught':0,
              'known_unsafe_unique_count_limitation':'No final unsafe execution ground truth; successful history mutation is not automatically unsafe current state',
              'equivalent_certified_Yellowstone_mutation_closure_cases':0,
              'atomic_bank_supersedes':'Only instantaneous state; not missed/round-trip mutations or ordered continuity',
              'refresh_supersedes':'Only current-state/identity/fee snapshot, not arbitrary unknown concurrent write reach'})
    history_result={'contributions':contributions,'cases':history,'all_fences_indivisible':False,
           'controlled_single_fence_removal':{str(n):{'pre_refresh_additional_candidates':
               [i for i,h in enumerate(history) if h['fences'][n-1]['status']=='MOVED' and
                all(f['status'] in ('RECEIVED','MATCHED') for f in h['fences'] if f['fence']!=n)],
               'full_additional_PASS':0,'refresh_missing_for_new_cases':True} for n in range(1,5)},
           'replacement_justified':False,'certified_stream_windows_in_current_20':0,
           'retained_17_observed_trade_window_certificates':2,
           'protected_mutation_window_certificates':0}
    write('history_fence_ablation',history_result)
    # The triggering packets were not captured by the narrow watch stream.
    raw = {}
    for line in (ROOT/'analysis/prospective_capture_packets.jsonl').read_text().splitlines():
        row=json.loads(line)
        if row.get('record_kind')=='provider_protobuf':raw.setdefault(row['signature'],row)
    target=next(r for r in refresh_records if r['attempted'])
    target_case=next(r for r in current if r['mint']==target['mint'])
    binding=prospective['candidate_stages'][0]['NEW']['evidence']['binding']
    protected={binding[k] for k in ('mint','curve','vault')}|set(binding['config_addresses'])
    native_mapping = prospective['candidate_stages'][0]['NEW']['evidence']['observed_anchor_parity']['instruction_accounts']
    protected.update(native_mapping[k] for k in ('creator_vault','sharing_config','associated_creator_vault',
             'associated_bonding_curve','associated_base_bonding_curve','associated_quote_bonding_curve')
             if k in native_mapping)
    protected.add(binding['creator'])
    triggers=[]
    for invocation in target['concurrent_invalidation_context']:
        signature=invocation['source']['signature']
        row=raw.get(signature)
        packet=rpc_packet(geyser_pb2.SubscribeUpdate.FromString(base64.b64decode(row['raw_protobuf_base64']))) if row else None
        scope=transaction_write_scope(packet,protected)
        triggers.append({'signature':signature,'slot':invocation['source']['slot'],'recorded_invalidation':invocation,
               'scope_evidence':scope,'actual_instruction':'UNKNOWN_FULL_PACKET_ABSENT' if not packet else 'see packet envelope',
               'safe_modes':{mode:{'revoke':scoped_invalidation(scope,mode),'preserve_safely':not scoped_invalidation(scope,mode)}
                      for mode in ('GLOBAL_VENUE_INVALIDATION','ACCOUNT_SCOPED_INVALIDATION','MARKET_SCOPED_INVALIDATION')}})
    synthetic_scope = [{'name':'unrelated_user_write','scope':{'scope':'PROVEN_NO_PROTECTED_WRITES'},'must_revoke':False},
        {'name':'other_curve_with_readonly_shared_config','scope':{'scope':'PROVEN_NO_PROTECTED_WRITES'},'must_revoke':False},
        {'name':'writable_candidate_curve','scope':{'scope':'MAY_WRITE_PROTECTED'},'must_revoke':True},
        {'name':'writable_global_config','scope':{'scope':'MAY_WRITE_PROTECTED'},'must_revoke':True},
        {'name':'writable_fee_config','scope':{'scope':'MAY_WRITE_PROTECTED'},'must_revoke':True},
        {'name':'creator_binding_or_lifecycle_write','scope':{'scope':'MAY_WRITE_PROTECTED'},'must_revoke':True},
        {'name':'missing_instruction_scope','scope':{'scope':'UNKNOWN'},'must_revoke':True}]
    scope_metrics={}
    for mode in ('GLOBAL_VENUE_INVALIDATION','ACCOUNT_SCOPED_INVALIDATION','MARKET_SCOPED_INVALIDATION'):
        scope_metrics[mode]={'real_trigger_count':len(triggers),'real_revocations':sum(t['safe_modes'][mode]['revoke'] for t in triggers),
            'demonstrated_false_collateral_invalidations':0,'real_collateral_truth':'UNKNOWN for both packets; do not equate unchanged bank with no write ability',
            'unsafe_missed_invalidations_demonstrated':0,'sole_receipt_safely_preserved':False,
            'synthetic_collateral_revocations':sum(scoped_invalidation(s['scope'],mode) and not s['must_revoke'] for s in synthetic_scope),
            'synthetic_unsafe_missed':sum(not scoped_invalidation(s['scope'],mode) and s['must_revoke'] for s in synthetic_scope)}
    invalidation={'sole_SELL':target['mint'],'trigger_instructions':triggers,'metrics':scope_metrics,
            'retained_account_refresh_unchanged':True,'scope_truth':'UNKNOWN',
            'unknown_reach_cannot_be_proven_from_refresh_equality':True,
            'scoped_design':'Only complete privilege envelopes excluding every protected market/config/creator address may avoid collateral invalidation. Unknown or shared writable config falls back to VENUE.',
            'synthetic_adversarial_scope_cases':synthetic_scope,'paper_policy_D_result':target_case['policies']['CURRENT_STATE_ONLY_RESEARCH'],
            'paper_policy_D_caveat':'Accepts current bank but ignores unresolved concurrent scope; KNOWN_UNPROVABLE_ACCEPTED, not a safely preserved receipt'}
    write('invalidation_scope_ablation',invalidation)
    minimum={'status':'PROPOSED_NOT_ACTIVATED','live_enabled':False,'orders_authorized':False,
           'minimum_evidence':['verified canonical identity/config at atomic bank and final refresh',
             'supported standard Pump.fun simple SOL route and compatible lifecycle/mode',
             'exact anchor instruction/event/reserve and price/fee parity', 'every physical token/SOL movement explained',
             'fresh executable buy/sell quotes recomputed from final atomic state',
             'fail-closed unknown protected/config/creator mutation reach',
             'bounded ordered mutation continuity ending at bank, or independently certified equivalent closure',
             'unchanged STRICT four-fence fallback until equivalent closure is validated'],
           'empirically_justified_removed_checks':[], 'D_recommended':False,
           'paper_shadow_measurement_only_possible':True,'relaxed_paper_execution_experiment_ready':False,
           'blockers':['B/C certified relevant mutation windows absent','D admits an unresolved scope case',
                       '19 prospective final refreshes absent','triggering unknown instruction packets absent',
                       'no full safe natural prospective proof'],
           'next_prerequisite':'Retain full privilege evidence for triggering invalidations and certify ordered relevant mutation closure; no higher RPC/watch budgets inferred'}
    write('minimum_safe_paper_gate',minimum)
    print(json.dumps({'prospective':{p:metric(current,p)['SHADOW_PASS'] for p in POLICIES},
         'supported_16':{p:metric(supported,p)['SHADOW_PASS'] for p in POLICIES},
         'contract_metrics':{p:metric(contract,p) for p in POLICIES}}))


if __name__=='__main__':asyncio.run(main())
