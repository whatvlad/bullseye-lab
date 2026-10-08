"""Validate report arithmetic using already-retained fills; no new API/research calls."""
import json
from decimal import Decimal as D
from pathlib import Path
from export_corrected_paper import decompose

root = Path(__file__).resolve().parent
checks = 0
for folder in ("current_1248", "current_1250"):
    snapshot = json.loads((root / "loss_audit_20261003" / folder / "snapshot.json").read_text(encoding="utf-8"))
    for trade in snapshot["outcomes"]:
        fills = [{**o["fill_json"], "side": o["side"]} for o in snapshot["filled_orders"]
                 if o["mint"] == trade["mint"] and (o["side"] == "buy" and o["event_id"] == trade["entry_order_event_id"]
                    or o["side"] == "sell" and trade["entry_at"] <= o["filled_at"] <= trade["exit_at"])]
        values = decompose(fills)
        assert abs(values["ledger_net_pnl"] - D(trade["realized_pnl"])) < D("0.0000001")
        assert abs(values["curve_price_pnl_before_fees_friction"] - values["friction_cost"] - values["fees"] - values["ledger_net_pnl"]) < D("0.0000001")
        checks += 1
for name in ("paper_corrected_trades.json", "paper_exit_latency.json", "paper_cost_model.json", "paper_shadow_exits.json", "paper_corrected_performance.json"):
    json.loads((root / name).read_text(encoding="utf-8"))
print(json.dumps({"historical_fill_arithmetic_checks": checks, "required_json_artifacts_valid": 5}))
