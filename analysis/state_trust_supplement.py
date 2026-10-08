"""At most 16 additional read-only RPC calls; no database/order imports."""
import asyncio
import base64
import gzip
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from memebot.core.config import Settings
from memebot.providers.solana.bootstrap import ReadOnlyConfigCache, bootstrap_pool, bootstrap_curve
from memebot.providers.solana.pump import extract_anchor_events
from memebot.providers.solana.pump_idl import PumpTrade, decode_pool_account, decode_bonding_curve_account
from memebot.research.market_calibration import RequestBudget
from memebot.research.reserve_sync import ForensicRpc

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "research_sessions/state-trust-20261001"


async def main():
    budget = RequestBudget(16)
    rpc = ForensicRpc(str(Settings().solana_rpc_http_url), budget)
    mismatches = json.loads((ROOT / "analysis/pumpfun_mismatch_classification.json").read_text())
    capture = json.loads((ROOT / "analysis/state_trust_validation.json").read_text())
    identity = json.loads((ROOT / "analysis/identity_bootstrap.json").read_text())
    predecessors = []
    proofs = []
    try:
        for case in sorted(mismatches["cases"], key=lambda c: abs(c["row"]["delta"]["virtual_quote"]), reverse=True)[:4]:
            previous = case["previous"]
            signature = previous["last_signature"]
            path = CACHE / f"transaction-{signature}.json.gz"
            if path.exists():
                tx = json.loads(gzip.decompress(path.read_bytes()))
            else:
                tx = await rpc._call("getTransaction", [signature, {"encoding": "json", "commitment": "finalized", "maxSupportedTransactionVersion": 127}])
                if tx is not None:
                    path.write_bytes(gzip.compress(json.dumps(tx).encode()))
            if tx is None:
                predecessors.append({"signature": signature, "status": "UNAVAILABLE"})
                continue
            logs = tx["meta"].get("logMessages") or []
            trades = [e for _, e in extract_anchor_events(logs) if isinstance(e, PumpTrade) and e.mint == case["row"]["base_mint"]] if "base_mint" in case["row"] else [e for _, e in extract_anchor_events(logs) if isinstance(e, PumpTrade)]
            predecessors.append({"signature": signature, "slot": tx["slot"], "events": [asdict(e) for e in trades], "instruction_logs": [l for l in logs if l.startswith("Program log: Instruction:")], "mayhem_invocation": any("Program MAyhSmz" in l for l in logs), "truncated": any("Log truncated" in l for l in logs)})
        cache = ReadOnlyConfigCache(rpc, "confirmed")
        await cache.ensure({})
        first = next(proof["identity"] for proof in identity["bootstrap_checks"].values() if proof.get("identity"))
        curve_account = await rpc.get_account(first["market"], "confirmed")
        if curve_account is not None:
            curve = decode_bonding_curve_account(base64.b64decode(curve_account.data_base64))
            curve_proof = await bootstrap_curve(rpc, "confirmed", mint=first["base_mint"], account=curve_account, curve=curve, config_version=cache.version("pump_fun"))
            identity["supplemental_pumpfun_bootstrap"] = {"source_slot": curve_account.slot, **asdict(curve_proof)}
        pools = Counter(row["market"] for row in capture["observations"] if row["venue"] == "pump_swap")
        for address, _ in pools.most_common(3):
            account = await rpc.get_account(address, "confirmed")
            if account is None:
                proofs.append({"market": address, "error": "ACCOUNT_UNAVAILABLE"})
                continue
            pool = decode_pool_account(base64.b64decode(account.data_base64))
            base, quote = await rpc.get_multiple_accounts([pool.pool_base_token_account, pool.pool_quote_token_account], "confirmed")
            if base is None or quote is None:
                proofs.append({"market": address, "error": "VAULT_UNAVAILABLE"})
                continue
            proof = await bootstrap_pool(rpc, "confirmed", account=account, pool=pool, base_vault=base, quote_vault=quote, config_version=cache.version("pump_swap"))
            proofs.append({"market": address, "source_slot": account.slot, **asdict(proof)})
    finally:
        await rpc.close()
    identity["supplemental_pumpswap_bootstrap"] = proofs
    identity["bootstrap_verified_by_venue"] = dict(Counter(proof["identity"]["venue"] for proof in identity["bootstrap_checks"].values() if proof.get("identity") and proof["identity"]["canonical_verified"]))
    identity["bootstrap_verified_by_venue"]["pump_swap"] = sum(bool(p.get("identity") and p["identity"]["canonical_verified"]) for p in proofs)
    identity["supplement_rpc_calls"] = identity.get("supplement_rpc_calls", []) + rpc.calls
    identity["current_trust_is_distinct_from_successful_bootstrap"] = True
    (ROOT / "analysis/identity_bootstrap.json").write_text(json.dumps(identity, indent=2) + "\n")
    mismatches["predecessor_native_sample"] = predecessors
    mismatches["supplement_rpc_calls"] = mismatches.get("supplement_rpc_calls", []) + [call for call in rpc.calls if call["method"] == "getTransaction"]
    (ROOT / "analysis/pumpfun_mismatch_classification.json").write_text(json.dumps(mismatches, indent=2) + "\n")
    print(json.dumps({"rpc_reads": budget.used, "predecessors": len(predecessors), "pool_proofs": [{"market": p["market"], "error": p.get("error"), "checks": p.get("checks")} for p in proofs]}))


asyncio.run(main())
