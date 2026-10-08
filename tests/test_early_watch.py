from collections import defaultdict
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from solders.pubkey import Pubkey

from memebot.providers.solana.evidence_stream import EvidenceBuffer
from memebot.research.early_watch import EarlyWatch, ResearchStage
from memebot.research.early_watch_run import EarlyWatchPilot
from test_candidate_proof import MINT
from test_stream_evidence import packet


def test_early_watch_precedes_qualification_without_rpc():
    now = datetime.now(UTC)
    watch = EarlyWatch(8)
    assert watch.admit(MINT, now)
    watch.acknowledge(watch.accounts(), now + timedelta(milliseconds=100))
    row = watch.serious(MINT, now + timedelta(seconds=10))
    assert row["early_watch_before_serious"] and row["ack_before_serious"]
    assert row["watch_to_serious_ms"] == 10_000


def test_temporary_deterioration_has_grace_and_recovers_without_filter_churn():
    now = datetime.now(UTC)
    watch = EarlyWatch(8)
    watch.admit(MINT, now)
    accounts = watch.accounts()
    watch.touch(MINT, now + timedelta(seconds=1), favorable=False)
    watch.expire(now + timedelta(seconds=3))
    assert watch.accounts() == accounts
    watch.touch(MINT, now + timedelta(seconds=4))
    watch.expire(now + timedelta(seconds=7))
    assert MINT in watch.markets
    watch.touch(MINT, now + timedelta(seconds=8), favorable=False)
    watch.expire(now + timedelta(seconds=13))
    assert not watch.accounts()
    assert not watch.admit(MINT, now + timedelta(seconds=14))
    assert watch.stages[MINT] == ResearchStage.REJECTED


@pytest.mark.parametrize("capacity", [8, 16, 32])
def test_capacity_is_bounded_and_admission_loss_is_measured(capacity):
    now = datetime.now(UTC)
    watch = EarlyWatch(capacity)
    for n in range(capacity):
        assert watch.admit(str(Pubkey.from_bytes(bytes([n]) * 32)), now)
    assert not watch.admit(str(Pubkey.from_bytes(bytes([99]) * 32)), now)
    assert watch.metrics["capacity_admission_rejects"] == 1
    assert len(watch.markets) == capacity


def window():
    now = datetime.now(UTC)
    watch = EarlyWatch(8)
    watch.admit(MINT, now - timedelta(seconds=20))
    watch.acknowledge(watch.accounts(), now - timedelta(seconds=19))
    _, _, _, evidence = packet()
    evidence = replace(evidence, received_at=now - timedelta(seconds=1))
    buffer = EvidenceBuffer()
    buffer.add(evidence)
    pilot = object.__new__(EarlyWatchPilot)
    pilot.early = watch
    pilot.buffer = buffer
    pilot.executed_stream = SimpleNamespace(connected=True)
    pilot.global_faults = []
    pilot.previous_slot = 102
    pilot.relevant_failures = defaultdict(list)
    pilot.packet_inventory = defaultdict(list)
    pilot.feed_inventory = defaultdict(list)
    pilot.feed_inventory[MINT] = [
        {"signature": evidence.signature, "at": (now - timedelta(seconds=1)).isoformat()}
    ]
    candidate = SimpleNamespace(
        mint=MINT,
        detected_at=now,
        anchor_signature=evidence.signature,
        anchor_slot=100,
        quality_evidence={"metric": {"window_seconds": 10, "observation_span_seconds": "5"}},
    )
    return pilot, candidate, now


def test_practical_window_requires_ack_retained_inventory_and_later_slot():
    pilot, candidate, now = window()
    assert pilot.certificate(candidate, now)["status"] == "COMPLETE_FOR_WINDOW"


def test_short_observed_span_never_shortens_the_required_feature_window():
    pilot, candidate, now = window()
    pilot.early.markets[MINT].acknowledged = now - timedelta(seconds=7)
    assert "ACK_AFTER_REQUIRED_START" in pilot.certificate(candidate, now)["reasons"]


@pytest.mark.parametrize(
    "fault", ["ack", "gap", "decoder", "overflow", "filter", "order", "slot", "missing"]
)
def test_every_window_integrity_failure_blocks_certification(fault):
    pilot, candidate, now = window()
    at = (now - timedelta(seconds=1)).isoformat()
    if fault == "ack":
        pilot.early.markets[MINT].acknowledged = now
    elif fault == "gap":
        pilot.global_faults.append({"at": at})
    elif fault == "decoder":
        pilot.relevant_failures[MINT].append({"at": at})
    elif fault == "overflow":
        pilot.buffer.evictions.append({"mint": MINT, "received_at": at})
    elif fault == "filter":
        pilot.early.remove(MINT, "REMOVED", now)
    elif fault == "order":
        pilot.packet_inventory[MINT] = [
            {"at": at, "slot": 100, "index": 2},
            {"at": at, "slot": 100, "index": 1},
        ]
    elif fault == "slot":
        pilot.previous_slot = 100
    else:
        pilot.buffer.items.clear()
    assert pilot.certificate(candidate, now)["status"] == "INCOMPLETE"
