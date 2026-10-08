"""Read-only diagnostics; never print RPC URLs or credentials."""
import asyncio
import json
import base64
from dataclasses import asdict
from memebot.providers.solana.canonical import curve_address, pool_address, pool_authority
from memebot.providers.solana.pump_idl import decode_bonding_curve_account, decode_pool_account, WRAPPED_SOL_MINT
from memebot.core.clock import utc_now
from memebot.core.config import Settings
from memebot.eligibility import paper_candidate_rejection
from memebot.paper.candidate_proof import CandidateProofService, ProofFailure
from memebot.paper.market_refresh import CurrentPaperMarketRefresher
from memebot.providers.solana.rpc import JsonRpcSolanaClient
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.registry import TokenRegistry

async def main():
    settings = Settings()
    db = Database(create_database_engine(settings.database_url))
    try:
        market = await TokenRegistry(db.sessions).paper_market_context(
            '9cxR58NxPER4oemD83iVZU9cKH54NdhzbeNfosJkpump', as_of=utc_now())
        evidence = market.normalized_state.evidence() if market.normalized_state else {}
        print(json.dumps({'market': market.market, 'slot': market.source_slot,
            'precheck': paper_candidate_rejection(evidence, venue=market.venue.value,
                lifecycle=market.lifecycle.value, complete=market.curve_complete),
            'state_reason': evidence.get('state_reason'), 'invalidation_reason': evidence.get('invalidation_reason')}))
        for name, url in [('exit', settings.solana_exit_rpc_http_url), ('primary', settings.solana_rpc_http_url)]:
            rpc = JsonRpcSolanaClient(str(url), timeout_seconds=settings.solana_rpc_timeout_seconds)
            try:
                from pathlib import Path
                from memebot.paper.migration_exit import migration_addresses
                from memebot.providers.solana.bootstrap import decode_config
                from memebot.providers.solana.pump_idl import PUMP_PROGRAM_ID, PUMP_AMM_PROGRAM_ID, decode_mint_account
                _, _, addresses = migration_addresses(market.mint)
                raw = await rpc._call('getMultipleAccounts', [addresses, {'commitment': 'confirmed', 'encoding': 'base64'}])
                Path('analysis/aww_migration_atomic_raw.json').write_text(json.dumps({'mint': market.mint, 'raw': raw}, indent=2), encoding='utf-8')
                cv, _ = decode_config(PUMP_PROGRAM_ID, base64.b64decode(raw['value'][1]['data'][0]), 'BondingCurve')
                pl, _ = decode_config(PUMP_AMM_PROGRAM_ID, base64.b64decode(raw['value'][2]['data'][0]), 'Pool')
                mi = decode_mint_account(base64.b64decode(raw['value'][0]['data'][0]))
                qm = decode_mint_account(base64.b64decode(raw['value'][3]['data'][0]))
                print(json.dumps({'curve_fields': cv, 'pool_fields': pl, 'mint_state': asdict(mi), 'quote_state': asdict(qm)}))
                curve_account = await rpc.get_account(curve_address(market.mint), settings.solana_commitment)
                curve = decode_bonding_curve_account(base64.b64decode(curve_account.data_base64))
                pool_id = pool_address(0, pool_authority(market.mint), market.mint, WRAPPED_SOL_MINT)
                pool_account = await rpc.get_account(pool_id, settings.solana_commitment)
                print(json.dumps({'provider': name, 'curve_complete': curve.complete,
                    'mayhem': curve.is_mayhem_mode, 'pool_address': pool_id,
                    'pool': asdict(decode_pool_account(base64.b64decode(pool_account.data_base64))) if pool_account else None}))
                try:
                    bundle = await CandidateProofService(rpc)._bundle(None, mint=market.mint,
                        minimum_slot=market.source_slot or 0)
                    print(json.dumps({'provider': name, 'atomic': 'ok', 'slot': bundle['slot']}))
                except ProofFailure as exc:
                    print(json.dumps({'provider': name, 'failure': exc.status, 'detail': str(exc)}))
                except Exception as exc:
                    print(json.dumps({'provider': name, 'error_type': type(exc).__name__}))
                result = await CurrentPaperMarketRefresher(rpc, for_exit=True).refresh(market)
                print(json.dumps({'provider': name, 'refresh_quality': result.data_quality,
                                  'rpc_state': result.rpc_state}))
                if result.execution_state and result.execution_state.get('model') == 'canonical_pumpswap_exit':
                    from pathlib import Path
                    from memebot.paper.migration_exit import migration_sell_quote
                    Path('analysis/aww_migration_exit_atomic.json').write_text(json.dumps(result.execution_state, indent=2), encoding='utf-8')
                    print(json.dumps({'provider': name, 'sell_quote': migration_sell_quote(result.execution_state, 3214072554134)}))
            finally:
                await rpc.close()
    finally:
        await db.dispose()

asyncio.run(main())
