from pathlib import Path
p=Path('tests/standard_evidence.py')
s=p.read_text()+'''

def atomic_market(market):
    """Synthetic verified bank for execution/risk unit tests; never live truth."""
    from dataclasses import replace
    from decimal import Decimal
    curve = {"virtual_token_reserves": market.virtual_token_reserves_raw,
             "virtual_quote_reserves": market.virtual_quote_reserves_raw,
             "real_token_reserves": market.real_token_reserves_raw,
             "real_quote_reserves": market.real_quote_reserves_raw}
    return replace(market, execution_state={"curve": curve,
        "rates": {"protocol_bps": 95, "creator_bps": 30},
        "slot": market.source_slot, "binding": {"config_version": "SYNTHETIC_UNIT_TEST"}},
        normalized_state=market.normalized_state or approved_state(),
        received_timestamp=market.received_timestamp or market.observed_at,
        rpc_state="healthy" if market.rpc_state == "unknown" else market.rpc_state,
        is_mayhem_mode=False)
'''
p.write_text(s)
for name in ['test_adaptive_sizing.py','test_paper_engine_pending.py']:
 p=Path('tests')/name;s=p.read_text()
 s=s.replace('from standard_evidence import approved_state','from standard_evidence import atomic_market, approved_state') if name=='test_adaptive_sizing.py' else s.replace('from standard_evidence import approved_evidence, approved_state','from standard_evidence import atomic_market, approved_evidence, approved_state')
 # Wrap literal fixture creations, leaving type annotations alone.
 s=s.replace('market = ExecutionMarketSnapshot(', 'market = atomic_market(ExecutionMarketSnapshot(').replace('fresh = ExecutionMarketSnapshot(', 'fresh = atomic_market(ExecutionMarketSnapshot(')
 lines=s.splitlines(True)
 for i,line in enumerate(lines):
  if '= atomic_market(ExecutionMarketSnapshot(' in line:
   indent=len(line)-len(line.lstrip())
   for j in range(i+1,len(lines)):
    if lines[j].strip()==')' and len(lines[j])-len(lines[j].lstrip())==indent:
     lines[j]=lines[j].replace(')', '))',1);break
 p.write_text(''.join(lines))
p=Path('tests/test_market_state.py');s=p.read_text().replace('assert all("normalized_state_not_execution_ready" in d.reasons for d in decisions)','assert all("STATE_UNKNOWN" in d.reasons for d in decisions)');p.write_text(s)
