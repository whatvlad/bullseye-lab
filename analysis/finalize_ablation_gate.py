import hashlib,json
from pathlib import Path
from memebot.paper.validation_gate import require_price_validation,RUNNER_EXPERIMENT
r=Path('C:/Bullseye')
old=json.loads((r/'analysis/prospective_proof_gate.json').read_text())
a=json.loads((r/'analysis/proof_gate_ablation.json').read_text())
checks={p:hashlib.sha256((r/p).read_bytes()).hexdigest()==h for p,h in old['capture_code_sha256'].items()}
assert all(checks.values()),[p for p,v in checks.items() if not v]
try:
 require_price_validation(RUNNER_EXPERIMENT,{},root=r)
except ValueError as e:
 block=str(e)
else:
 raise AssertionError('runner block missing')
paths=['docs/PROOF_GATE_ABLATION.md','docs/HISTORY_FENCE_ABLATION.md','docs/INVALIDATION_SCOPE_ABLATION.md','docs/MINIMUM_SAFE_PAPER_GATE.md','analysis/proof_gate_ablation.json','analysis/history_fence_ablation.json','analysis/invalidation_scope_ablation.json','analysis/minimum_safe_paper_gate.json','analysis/run_proof_gate_ablation.py','analysis/write_ablation_reports.py','src/memebot/research/proof_gate_ablation.py','tests/test_proof_gate_ablation.py']
gate={'status':'MEASURED_NOT_ACTIVATED','STRICT_changed':False,'production_hash_checks':checks,'production_hashes_unchanged':True,'runner':'BLOCKED','calibration':'BLOCKED','runner_block_verified':True,'runner_block_reason':block,'new_gate_activated':False,'relaxed_paper_execution_experiment_ready':False,'offline_shadow_measurement_only':True,'orders':0,'live_trading_enabled':False,'new_provider_calls':0,'new_capture':False,'strategy_qualification_changed':False,'RPC_watch_budgets_changed':False,'supported_16_counts':a['supported_16']['counts'],'natural_corpus_counts':a['natural_corpus_counts'],'validation':{'pytest':'447 passed','ruff':'PASS','mypy':'PASS: 135 source files'},'blockers':json.loads((r/'analysis/minimum_safe_paper_gate.json').read_text())['blockers'],'source_sha256':a['source_sha256'],'artifact_sha256':{p:hashlib.sha256((r/p).read_bytes()).hexdigest() for p in paths}}
(r/'analysis/ablation_gate.json').write_text(json.dumps(gate,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'unchanged_production_files':len(checks),'runner_block':block,'required_artifacts':9}))
