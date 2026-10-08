import base64
import copy
import json
from pathlib import Path

import pytest
from sqlalchemy import func, select

from memebot.core.clock import utc_now
from memebot.events.models import TokenDiscovered
from memebot.market_state import MarketStateTracker
from memebot.models.market import LaunchVenue
from memebot.providers.solana.canonical import curve_address
from memebot.providers.solana.evidence_stream import normalize_transaction
from memebot.providers.solana.invalidation import (
    log_shape_event_cpi_frames,
    native_frames,
    scope_native_mutations,
    verified_event_cpi_frames,
)
from memebot.providers.solana.operational_evidence import OperationalEvidenceCache
from memebot.providers.solana.pump_idl import NATIVE_SOL_MINT, PUMP_PROGRAM_ID
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.models import DomainEventRecord
from memebot.storage.database.outcomes import OutcomeRecorder
from memebot.storage.database.registry import TokenRegistry

ROWS = json.loads((Path(__file__).parent / "fixtures/proof_rejections.json").read_text())


@pytest.mark.parametrize("index", range(17))
def test_real_executed_event_cpi_is_verified_but_not_silent_unknown(index):
    tx = ROWS[index]["tx"]
    logs = tx["meta"]["logMessages"]
    assert len(verified_event_cpi_frames(logs, tx)) == 1
    unverified = MarketStateTracker()
    verified = MarketStateTracker()
    scope_native_mutations(logs, unverified, signature="x", slot=1)
    scope_native_mutations(logs, verified, signature="x", slot=1, transaction=tx)
    # Logs alone now classify the strict emit-CPI shape exactly like the packet proof.
    assert [r.reason for r in unverified.invalidations] == [
        r.reason for r in verified.invalidations
    ]


def _shape_logs(*, parent: str = "Buy", events: int = 1, child: list[str] | None = None):
    data = base64.b64encode(bytes(8)).decode()
    return [
        f"Program {PUMP_PROGRAM_ID} invoke [1]",
        f"Program log: Instruction: {parent}",
        *[f"Program data: {data}"] * events,
        f"Program {PUMP_PROGRAM_ID} invoke [2]",
        *(child or []),
        f"Program {PUMP_PROGRAM_ID} consumed 2149 of 200000 compute units",
        f"Program {PUMP_PROGRAM_ID} success",
        f"Program {PUMP_PROGRAM_ID} success",
    ]


def _shaped(logs):
    frames = native_frames(logs)
    for frame in frames:
        frame.decoder_failure = False  # synthetic event bytes are not a real schema
    return log_shape_event_cpi_frames(frames)


def test_log_shape_event_cpi_accepts_only_the_strict_emit_shape():
    assert _shaped(_shape_logs()) == {1}


@pytest.mark.parametrize(
    "logs",
    [
        _shape_logs(parent="Unrecognized"),
        _shape_logs(parent="MultiHopCurveSwap"),
        _shape_logs(events=2),
        _shape_logs(events=0),
        _shape_logs(child=["Program log: Instruction: Sell"]),
        _shape_logs(child=["Program data: AAAAAAAAAAA="]),
        _shape_logs(
            child=[
                "Program 11111111111111111111111111111111 invoke [3]",
                "Program 11111111111111111111111111111111 success",
            ]
        ),
    ],
)
def test_log_shape_event_cpi_rejects_other_silent_frames(logs):
    assert _shaped(logs) == set()


V3_ROWS = json.loads((Path(__file__).parent / "fixtures/pump_v3_trades.json").read_text())


@pytest.mark.parametrize("index", range(len(V3_ROWS)))
def test_real_v3_trades_are_ordinary_with_and_without_a_packet(index):
    tx = V3_ROWS[index]
    logs = tx["meta"]["logMessages"]
    assert len(verified_event_cpi_frames(logs, tx)) == 1
    for packet in (None, tx):
        tracker = MarketStateTracker()
        scope_native_mutations(logs, tracker, signature="x", slot=1, transaction=packet)
        assert not any(r.reason == "UNKNOWN_NATIVE_INSTRUCTION" for r in tracker.invalidations)


def test_log_shape_is_not_used_for_truncated_logs_or_with_a_packet():
    tx = copy.deepcopy(ROWS[0]["tx"])
    logs = tx["meta"]["logMessages"]
    truncated = MarketStateTracker()
    scope_native_mutations([*logs, "Log truncated"], truncated, signature="x", slot=1)
    assert any(r.reason == "UNKNOWN_NATIVE_INSTRUCTION" for r in truncated.invalidations)
    del tx["meta"]["innerInstructions"]
    mismatching = MarketStateTracker()
    scope_native_mutations(logs, mismatching, signature="x", slot=1, transaction=tx)
    assert any(r.reason == "UNKNOWN_NATIVE_INSTRUCTION" for r in mismatching.invalidations)


@pytest.mark.parametrize(
    "change", ["missing_inner", "wrong_data", "wrong_authority", "height", "error", "logs"]
)
def test_incomplete_or_mismatching_packet_retains_unknown(change):
    tx = copy.deepcopy(ROWS[0]["tx"])
    logs = list(tx["meta"]["logMessages"])
    emitter = tx["meta"]["innerInstructions"][0]["instructions"][-1]
    if change == "missing_inner":
        del tx["meta"]["innerInstructions"]
    elif change == "wrong_data":
        emitter["data"] = "1"
    elif change == "wrong_authority":
        emitter["accounts"] = [0]
    elif change == "height":
        emitter["stackHeight"] = 3
    elif change == "error":
        tx["meta"]["err"] = {"InstructionError": [0, "x"]}
    else:
        tx["meta"]["logMessages"] = []
    assert verified_event_cpi_frames(logs, tx) == set()


def test_filtered_cache_lookup_is_immediate_and_matches_slot():
    row = ROWS[0]
    tx = row["tx"]
    cache = OperationalEvidenceCache("test")
    cache.observe(
        TokenDiscovered(
            provider="test",
            source_event_at=utc_now(),
            mint=row["mint"],
            bonding_curve=curve_address(row["mint"]),
            is_mayhem_mode=False,
            quote_mint=NATIVE_SOL_MINT,
            launch_venue=LaunchVenue.PUMP_FUN,
        )
    )
    packet = normalize_transaction(
        tx,
        slot=tx["slot"],
        signature=tx["transaction"]["signatures"][0],
        index=0,
        source="test",
        commitment="confirmed",
        received_at=utc_now(),
    )
    assert packet is not None
    cache.buffer.add(packet)
    assert cache.lookup(packet.signature, packet.slot) is not None
    assert cache.lookup(packet.signature, packet.slot + 1) is None
    assert cache.lookup("missing", packet.slot) is None


@pytest.mark.asyncio
async def test_outcomes_and_event_roll_back_together_on_projection_failure():
    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()

    class BrokenOutcomes(OutcomeRecorder):
        async def handle_in_session(self, session, event):
            raise RuntimeError("projection failure")

    registry = TokenRegistry(database.sessions, outcome_recorder=BrokenOutcomes(database.sessions))
    event = TokenDiscovered(provider="test", source_event_at=utc_now(), mint=ROWS[0]["mint"])
    with pytest.raises(RuntimeError, match="projection failure"):
        await registry.handle(event)
    async with database.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(DomainEventRecord)) == 0
    await database.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("race", [False, True])
async def test_existing_atomic_bank_reanchors_only_without_inflight_invalidation(race):
    from memebot.paper.market_refresh import CurrentPaperMarketRefresher
    from test_current_paper_execution import current_market

    market, rpc = await current_market()
    tracker = MarketStateTracker()
    tracker.states[market.market] = market.normalized_state.model_copy(
        update={
            "continuity_status": "UNKNOWN",
            "invalidation_reason": "UNKNOWN_NATIVE_INSTRUCTION",
        }
    )
    original = rpc._call

    async def read(method, params):
        result = await original(method, params)
        if race:
            tracker.invalidate(market.market, "STREAM_DISCONNECT")
        return result

    rpc._call = read
    result = await CurrentPaperMarketRefresher(rpc, state_tracker=tracker).refresh(market)
    assert result.rpc_state == "healthy"
    assert tracker.states[market.market].continuity_status == (
        "UNKNOWN" if race else "RPC_VALIDATED"
    )


@pytest.mark.asyncio
async def test_atomic_bank_cannot_overwrite_a_newer_stream_slot():
    from memebot.paper.market_refresh import CurrentPaperMarketRefresher
    from test_current_paper_execution import current_market

    market, rpc = await current_market()
    tracker = MarketStateTracker()
    newer = market.normalized_state.model_copy(update={"state_slot": market.source_slot + 1000})
    tracker.states[market.market] = newer
    await CurrentPaperMarketRefresher(rpc, state_tracker=tracker).refresh(market)
    assert tracker.states[market.market].state_slot == newer.state_slot
    assert tracker.invalidations[-1].reason == "RPC_SLOT_REGRESSION"


def test_delayed_old_mutation_cannot_poison_newer_atomic_anchor_but_gap_can():
    from standard_evidence import approved_state

    tracker = MarketStateTracker()
    state = approved_state().model_copy(
        update={"market": "curve", "state_slot": 100, "continuity_status": "RPC_VALIDATED"}
    )
    tracker.states["curve"] = state
    tracker.invalidate(
        "curve",
        "UNKNOWN_NATIVE_INSTRUCTION",
        slot=99,
        dimensions=("reserves", "identity", "config"),
    )
    assert tracker.states["curve"] == state
    assert tracker.invalidation_revisions.get("curve", 0) == 0
    tracker.invalidate("curve", "STREAM_DISCONNECT")
    assert tracker.states["curve"].continuity_status == "UNKNOWN"


@pytest.mark.asyncio
async def test_full_packet_and_native_copy_project_exactly_one_trade():
    import asyncio

    from memebot.core.config import Settings
    from memebot.events.models import TokenTrade
    from memebot.providers.solana.pump import PumpDiscoveryProvider
    from test_pump_provider import FakeRpc

    row = ROWS[0]
    tx = row["tx"]
    signature = tx["transaction"]["signatures"][0]
    provider = PumpDiscoveryProvider(Settings(), FakeRpc())
    provider.seed_bonding_curve(row["mint"], curve_address(row["mint"]), 793100000000000)
    provider.transaction_evidence_lookup = lambda sig, slot: tx if sig == signature else None
    provider.market_notification_locks[row["mint"]] = asyncio.Lock()
    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()
    registry = TokenRegistry(database.sessions, outcome_recorder=OutcomeRecorder(database.sessions))
    await registry.handle(
        TokenDiscovered(provider="test", source_event_at=utc_now(), mint=row["mint"])
    )
    accepted = []

    async def publish(event):
        if await registry.handle(event):
            accepted.append(event)

    message = {
        "params": {
            "result": {
                "context": {"slot": tx["slot"]},
                "value": {
                    "signature": signature,
                    "logs": tx["meta"]["logMessages"],
                    "err": None,
                },
            }
        }
    }
    await asyncio.gather(
        provider._handle_notification(message, publish, transaction_evidence=tx),
        provider._handle_notification(message, publish),
    )
    assert len([event for event in accepted if isinstance(event, TokenTrade)]) == 1
    assert provider.state_tracker.states[curve_address(row["mint"])].observational_price is not None
    await database.dispose()


@pytest.mark.asyncio
async def test_slow_watched_market_does_not_lock_another_market():
    import asyncio

    from memebot.core.config import Settings
    from memebot.events.models import TokenTrade
    from memebot.providers.solana.pump import PumpDiscoveryProvider
    from test_pump_provider import FakeRpc

    provider = PumpDiscoveryProvider(Settings(), FakeRpc())
    entered, release = asyncio.Event(), asyncio.Event()
    for row in ROWS[:2]:
        provider.seed_bonding_curve(row["mint"], curve_address(row["mint"]), 793100000000000)
        provider.market_notification_locks[row["mint"]] = asyncio.Lock()

    async def publish(event):
        if isinstance(event, TokenTrade) and event.mint == ROWS[0]["mint"]:
            entered.set()
            await release.wait()

    async def process(row):
        tx = row["tx"]
        message = {
            "params": {
                "result": {
                    "context": {"slot": tx["slot"]},
                    "value": {
                        "signature": tx["transaction"]["signatures"][0],
                        "logs": tx["meta"]["logMessages"],
                        "err": None,
                    },
                }
            }
        }
        await provider._handle_notification(message, publish, transaction_evidence=tx)

    slow = asyncio.create_task(process(ROWS[0]))
    await asyncio.wait_for(entered.wait(), 1)
    await asyncio.wait_for(process(ROWS[1]), 1)
    release.set()
    await slow
