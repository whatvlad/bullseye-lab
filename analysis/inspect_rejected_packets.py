"""Offline instruction/balance inspection of the retained seventeen cases."""
import json
from pathlib import Path
from memebot.providers.solana.encoding import decode_base58
from memebot.providers.solana.idl_schema import schema
from memebot.providers.solana.pump_idl import PUMP_PROGRAM_ID, NATIVE_SOL_MINT
from memebot.paper.standard_math import buy_exact_tokens, buy_quote, select_fees

d=json.loads(Path('analysis/early_watch_32.json').read_text())
definitions={bytes(i['discriminator']):i for i in schema(PUMP_PROGRAM_ID)['instructions']}
for n,p in enumerate(d['pairs']):
 q=p['NEW']; ev=q['evidence']; tx=ev['direct_anchor_transaction']; m=tx['transaction']['message']; meta=tx['meta']; keys=m['accountKeys']+meta.get('loadedAddresses',{}).get('writable',[])+meta.get('loadedAddresses',{}).get('readonly',[])
 curve=p['NEW']['candidate']['anchor']['mint']; print('\nCASE',n,q['candidate']['mint'],q['reason'])
 for ixidx,ix in enumerate(m['instructions']):
  raw=decode_base58(ix['data']); prog=keys[ix['programIdIndex']]; definition=definitions.get(raw[:8],{}) if prog==PUMP_PROGRAM_ID else {}; acc=[keys[i] for i in ix['accounts']]; print('OUTER',ixidx,prog,definition.get('name'),raw.hex(),acc)
 for group in meta['innerInstructions']:
  print('INNER',group['index'],[(keys[i['programIdIndex']],decode_base58(i['data']).hex()[:48],[keys[a] for a in i['accounts']],i.get('stackHeight')) for i in group['instructions']])
 print('DELTAS',[(i,k,meta['preBalances'][i],meta['postBalances'][i],meta['postBalances'][i]-meta['preBalances'][i]) for i,k in enumerate(keys) if meta['preBalances'][i]!=meta['postBalances'][i]])
 print('TOKEN',meta['preTokenBalances'],meta['postTokenBalances'])
 if q['reason']=='integer curve input/output mismatch':
  e=q['candidate']['anchor']; sign=1 if e['is_buy'] else -1
  pre={k:e[k]+(sign*e['token_amount'] if 'token' in k else -sign*e['quote_amount']) for k in ('virtual_token_reserves','virtual_quote_reserves','real_token_reserves','real_quote_reserves')}
  state={**ev['curve'],**pre}; rates=select_fees(ev['global'],ev['fee_config'],state,ev['supply']); print('PRE',pre,'RATES',rates,'ACTUAL',e['token_amount'],e['quote_amount'],'EXACT_TOKENS',buy_exact_tokens(state,e['token_amount'],rates))
  for ix in m['instructions']:
   if keys[ix['programIdIndex']]==PUMP_PROGRAM_ID:
    raw=decode_base58(ix['data']); print('FORWARD',buy_quote(state,int.from_bytes(raw[8:16],'little'),rates))
