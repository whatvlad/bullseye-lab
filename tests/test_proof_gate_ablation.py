"""Adversarial shadow tests; no result is an execution receipt."""

import json
from pathlib import Path

import pytest

from memebot.providers.solana.execution_accounting import execution_accounting
from memebot.research.proof_gate_ablation import (
    POLICIES,
    evaluate,
    scoped_invalidation,
    transaction_write_scope,
)
from test_candidate_proof import fixture


def complete_contract():
    return {key: True for policy in POLICIES.values() for key in policy.requirements}


@pytest.mark.parametrize("policy", POLICIES)
def test_every_shadow_verdict_has_no_authorization(policy):
    result = evaluate(complete_contract(), policy)
    assert result["shadow_pass"]
    assert not result["authorizes_orders"]
    assert not result["authorizes_live"]
    assert not result["authorizes_experiment"]


@pytest.mark.parametrize("policy", POLICIES)
def test_missing_refresh_and_stale_refresh_are_not_replaced_by_history(policy):
    facts = {**complete_contract(), "refresh_retained": None}
    assert not evaluate(facts, policy)["shadow_pass"]
    facts = {**complete_contract(), "refresh_fresh": False}
    assert not evaluate(facts, policy)["shadow_pass"]


@pytest.mark.parametrize("policy", POLICIES)
def test_real_packet_balance_corruption_still_blocks_every_policy(policy):
    candidate, _, tx, _, _ = fixture()
    tx["meta"]["postBalances"][0] += 1
    with pytest.raises(ValueError, match="PHYSICAL_BALANCE_MISMATCH"):
        execution_accounting(tx, candidate.mint)
    facts = {**complete_contract(), "exact_physical_accounting": False}
    assert not evaluate(facts, policy)["shadow_pass"]


def envelope(writable, readonly, loaded=None):
    return {
        "transaction": {
            "message": {
                "accountKeys": [*writable, *readonly],
                "header": {
                    "numRequiredSignatures": 1,
                    "numReadonlySignedAccounts": 0,
                    "numReadonlyUnsignedAccounts": len(readonly),
                },
            }
        },
        "meta": {"err": None, "logMessages": [], "loadedAddresses": loaded or {}},
    }


def test_shared_readonly_config_does_not_create_collateral_write_reach():
    scope = transaction_write_scope(
        envelope(["user", "other_curve"], ["Global", "FeeConfig"]),
        {"candidate_curve", "vault", "Global", "FeeConfig"},
    )
    assert scope["scope"] == "PROVEN_NO_PROTECTED_WRITES"
    assert scoped_invalidation(scope, "GLOBAL_VENUE_INVALIDATION")
    assert not scoped_invalidation(scope, "ACCOUNT_SCOPED_INVALIDATION")
    assert not scoped_invalidation(scope, "MARKET_SCOPED_INVALIDATION")


def test_loaded_writable_global_cannot_be_exempted_by_another_market_binding():
    scope = transaction_write_scope(
        envelope(
            ["user", "other_curve"], [], {"writable": ["Global"], "readonly": ["candidate_curve"]}
        ),
        {"Global", "candidate_curve"},
    )
    assert scope["protected_writable"] == ["Global"]
    assert scoped_invalidation(scope, "ACCOUNT_SCOPED_INVALIDATION")
    assert scoped_invalidation(scope, "MARKET_SCOPED_INVALIDATION", target_market_bound=False)


@pytest.mark.parametrize(
    "mode",
    ["GLOBAL_VENUE_INVALIDATION", "ACCOUNT_SCOPED_INVALIDATION", "MARKET_SCOPED_INVALIDATION"],
)
def test_absent_or_corrupt_write_scope_remains_conservative(mode):
    assert scoped_invalidation(transaction_write_scope(None, {"curve"}), mode)
    tx = envelope(["user"], ["curve"])
    tx["transaction"]["message"]["header"]["numReadonlyUnsignedAccounts"] = 99
    assert scoped_invalidation(transaction_write_scope(tx, {"curve"}), mode)


def test_readonly_envelope_is_not_reused_after_a_writable_protected_change():
    tx = envelope(["user"], ["curve"])
    before = transaction_write_scope(tx, {"curve"})
    tx["transaction"]["message"]["header"]["numReadonlyUnsignedAccounts"] = 0
    after = transaction_write_scope(tx, {"curve"})
    assert before["scope"] == "PROVEN_NO_PROTECTED_WRITES"
    assert after["scope"] == "MAY_WRITE_PROTECTED"


def test_missing_lookup_resolution_cannot_prove_no_protected_writes():
    tx = envelope(["user"], ["curve"])
    tx["transaction"]["message"]["addressTableLookups"] = [
        {"writableIndexes": [0], "readonlyIndexes": []}
    ]
    scope = transaction_write_scope(tx, {"Global"})
    assert scope["scope"] == "UNKNOWN"
    assert scoped_invalidation(scope, "ACCOUNT_SCOPED_INVALIDATION")


def test_actual_retained_sole_sell_is_not_safely_preserved_by_scoped_modes():
    root = Path(__file__).parents[1]
    data = json.loads((root / "analysis/invalidation_scope_ablation.json").read_text())
    assert len(data["trigger_instructions"]) == 2
    for trigger in data["trigger_instructions"]:
        assert trigger["scope_evidence"]["scope"] == "UNKNOWN"
        assert all(mode["revoke"] for mode in trigger["safe_modes"].values())
    assert data["paper_policy_D_result"]["shadow_pass"]
    assert not data["paper_policy_D_result"]["authorizes_orders"]


def test_guard_removal_can_admit_known_unprovable_state_without_a_safety_claim():
    facts = {
        **complete_contract(),
        "bounded_continuity": False,
        "terminal_bank_equal": False,
        "relevant_mutation_window_closed": None,
    }
    assert not evaluate(facts, "STRICT")["shadow_pass"]
    assert not evaluate(facts, "STREAM_CURRENT_STATE")["shadow_pass"]
    result = evaluate(facts, "CURRENT_STATE_ONLY_RESEARCH")
    assert result["shadow_pass"] and not result["safety_proven"]


def test_raw_original_sell_refresh_is_not_invented_as_a_strict_approval():
    root = Path(__file__).parents[1]
    data = json.loads((root / "analysis/proof_gate_ablation.json").read_text())
    original = data["original_live_SELL"][0]
    assert original["recorded_refresh_failure"]
    assert original["facts"]["strict_refresh_approved"] is None
    assert not original["policies"]["STRICT"]["shadow_pass"]
    assert original["policies"]["CURRENT_STATE_ONLY_RESEARCH"]["shadow_pass"]
