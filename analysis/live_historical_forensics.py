"""Read nine already-known standard anchors; never substitute current state for history."""
import asyncio
import base64
import json
from pathlib import Path

from memebot.core.config import Settings
from memebot.providers.solana.idl_schema import decode_record
from memebot.providers.solana.pump_idl import PUMP_PROGRAM_ID
from memebot.research.candidate_proof_run import CandidateRpc
from memebot.research.market_calibration import RequestBudget


async def main():
    rpc = CandidateRpc(str(Settings().solana_rpc_http_url), RequestBudget(9))
    rows = []
    try:
        for filename in ("candidate_execution_proofs_run1.json", "candidate_execution_proofs_run2.json"):
            for proof in json.loads((Path("analysis") / filename).read_text())["candidate_proofs"]:
                candidate = proof["candidate"]
                row = {"mint": candidate["mint"], "signature": candidate["anchor_signature"],
                       "original_status": proof["status"], "original_reason": proof["reason"],
                       "original_rejection_branch": "UNKNOWN_MISSING_HISTORICAL_ACCOUNT_PACKET",
                       "historical_causality_proven": False}
                try:
                    tx = await rpc._call("getTransaction", [candidate["anchor_signature"],
                        {"encoding": "json", "commitment": "confirmed", "maxSupportedTransactionVersion": 0}])
                    row["transaction"] = tx
                    fields = []
                    for line in (tx or {}).get("meta", {}).get("logMessages", []):
                        if line.startswith("Program data: "):
                            try:
                                name, event = decode_record(PUMP_PROGRAM_ID, base64.b64decode(line[14:]), collection="events")
                                if name == "TradeEvent" and event["mint"] == candidate["mint"]:
                                    fields.append(event)
                            except ValueError:
                                pass
                    row["native_fee_events"] = fields
                    row["native_route_branches"] = sorted({branch for event in fields for branch, active in (
                        ("CASHBACK", event.get("cashback_fee_basis_points", 0) or event.get("cashback", 0)),
                        ("HOLDER_REWARD", event.get("holder_rewards_bps", 0) or event.get("holder_rewards", 0)),
                        ("SHARED_CREATOR", event.get("shareholders")),
                        ("CREATOR_ZERO", event.get("creator") == "11111111111111111111111111111111"),
                    ) if active})
                except Exception as error:
                    row["error"] = type(error).__name__
                rows.append(row)
    finally:
        await rpc.close()
    Path("analysis/live_historical_forensics.json").write_text(json.dumps({
        "rpc_cap": 9, "rpc_reads": rpc.budget.used, "rows": rows, "calls": rpc.calls,
        "caution": "Native fee branches do not prove which historical account OR branch rejected; original packets absent.",
    }, indent=2, default=str) + "\n")
    print([(r["mint"], r.get("native_route_branches"), r.get("error")) for r in rows])


asyncio.run(main())
