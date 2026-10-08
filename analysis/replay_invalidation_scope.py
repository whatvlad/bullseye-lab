"""Same retained events and same native mutation coverage; change only scope."""
import json
from collections import Counter, defaultdict
from pathlib import Path

from memebot.market_state import InvalidationScope, MarketStateTracker
from memebot.providers.solana.pump_idl import PumpTrade, PumpSwapTrade

ROOT = Path(__file__).resolve().parents[1]
capture = json.loads((ROOT / "analysis/state_trust_validation.json").read_text())
scope = json.loads((ROOT / "analysis/invalidation_scope.json").read_text())
native = defaultdict(list)
ordering = []
for record in scope["ledger"]:
    if record["signature"] is None or record["scope_reason"] == "explicit_market":
        continue
    signature = record["signature"]
    if signature not in native:
        ordering.append(signature)
    native[signature].append(record)
events = defaultdict(list)
observed_order = []
for row in capture["observations"]:
    signature = row["last_signature"]
    if signature not in events:
        observed_order.append(signature)
    events[signature].append(row)
coverage_complete = all(signature in native for signature in observed_order)
ordering_complete = [signature for signature in ordering if signature in events] == observed_order
arms = {name: MarketStateTracker(capacity=100000) for name in ("same_coverage_global", "scoped")}
counts = {name: Counter() for name in arms}
removed = added = mismatches = 0
if coverage_complete and ordering_complete:
    for signature in ordering:
        for record in native[signature]:
            if not record["dimensions"]:
                continue
            for name, tracker in arms.items():
                tracker.invalidate(None, record["reason"], scope=InvalidationScope.GLOBAL if name == "same_coverage_global" else InvalidationScope(record["scope"]), program=record["program"], signature=signature, slot=record["slot"], affected_markets=set(tracker.states) if name == "same_coverage_global" else set(record["affected_markets"]), dimensions=tuple(record["dimensions"]), scope_reason=record["scope_reason"])
        for row in events[signature]:
            event = PumpTrade(**row["raw_event"]) if row["venue"] == "pump_fun" else PumpSwapTrade(**row["raw_event"])
            statuses = {}
            for name, tracker in arms.items():
                state = tracker.observe(event, market=row["market"], slot=row["state_slot"], signature=signature, ordinal=row["last_event_ordinal"], multi_event_unknown=row["multi_event"])
                statuses[name] = state.continuity_status
                counts[name][state.continuity_status] += 1
            mismatches += statuses["scoped"] != row["matched_status"]["scoped_mutations"]
            removed += statuses["same_coverage_global"] == "UNKNOWN" and statuses["scoped"] != "UNKNOWN"
            added += statuses["same_coverage_global"] != "UNKNOWN" and statuses["scoped"] == "UNKNOWN"
comparison = {"native_ledger_coverage_complete": coverage_complete, "transaction_order_complete": ordering_complete, "local_replay_status_mismatches": mismatches, "exact_held_trace_reproduction": coverage_complete and ordering_complete and mismatches == 0, "arms": {name: dict(counts[name]) for name in arms}, "same_events_and_mutation_coverage": True, "rpc_reconciliations": False, "unknown_removed_by_scope": removed, "unknown_added_by_scope": added, "net_unknown_reduction_due_to_scope": removed - added, "better_feed_reliability_claimed": False, "new_rpc_reads": 0}
capture["pure_scope_counterfactual"] = comparison
capture["matched_counterfactual"]["scope_only_label_valid"] = False
capture["matched_counterfactual"]["comparison_limitation"] = "Legacy versus new includes additional invocation-frame coverage. Use pure_scope_counterfactual for scope attribution."
scope["pure_scope_counterfactual"] = comparison
scope["matched_counterfactual"] = capture["matched_counterfactual"]
for path, report in (("state_trust_validation.json", capture), ("invalidation_scope.json", scope)):
    (ROOT / "analysis" / path).write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(comparison))
