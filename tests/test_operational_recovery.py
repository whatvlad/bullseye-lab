import asyncio
import copy
import json
from pathlib import Path

import pytest

from memebot.core.clock import utc_now
from memebot.core.config import Settings
from memebot.events.models import TokenTrade
from memebot.providers.solana.alchemy_evidence import FullStreamBudgetExceeded
from memebot.providers.solana.canonical import FEE_PROGRAM, curve_address
from memebot.providers.solana.evidence_stream import normalize_transaction
from memebot.providers.solana.invalidation import irrelevant_standard_fee_read
from memebot.providers.solana.operational_evidence import OperationalEvidenceCache
from memebot.providers.solana.pump import PumpDiscoveryProvider
from memebot.providers.solana.pump_idl import PUMP_PROGRAM_ID
from test_pump_provider import FakeRpc

ROW = json.loads((Path(__file__).parent / "fixtures/proof_rejections.json").read_text())[0]


def sample():
    tx = copy.deepcopy(ROW["tx"])
    signature = tx["transaction"]["signatures"][0]
    packet = normalize_transaction(
        tx,
        slot=tx["slot"],
        signature=signature,
        index=0,
        source="test",
        commitment="confirmed",
        received_at=utc_now(),
    )
    assert packet is not None
    message = {
        "method": "logsNotification",
        "params": {
            "result": {
                "context": {"slot": packet.slot},
                "value": {"signature": signature, "err": None, "logs": tx["meta"]["logMessages"]},
            }
        },
    }
    return packet, message


@pytest.mark.asyncio
@pytest.mark.parametrize("amount", ["token_amount", "quote_amount"])
async def test_nonpositive_trade_invalidates_only_affected_market_and_price_history(amount):
    from dataclasses import replace

    from memebot.providers.solana.pump import extract_anchor_events
    from memebot.providers.solana.pump_idl import PumpTrade

    packet, message = sample()
    provider = PumpDiscoveryProvider(Settings(_env_file=None), FakeRpc())
    provider.seed_bonding_curve(packet.mint, packet.curve, 793100000000000)
    accepted = []
    gaps = []
    provider.on_price_gap = gaps.append

    async def publish(event):
        accepted.append(event)

    await provider._handle_notification(message, publish, transaction_evidence=packet.transaction)
    before = provider.state_tracker.states[packet.curve]
    provider.state_tracker.states["another-market"] = before.model_copy(
        update={"market": "another-market"}
    )
    other = provider.state_tracker.states["another-market"]
    anchor = next(
        e
        for _, e in extract_anchor_events(packet.transaction["meta"]["logMessages"])
        if isinstance(e, PumpTrade)
    )
    accepted.clear()
    await provider._normalize_and_publish(
        replace(anchor, **{amount: 0}),
        signature="zero-value-event",
        slot=packet.slot + 1,
        ordinal=0,
        received_at=utc_now(),
        publish=publish,
    )
    assert accepted == []
    assert gaps == [packet.mint]
    assert provider.state_tracker.states[packet.curve].observational_price is None
    assert provider.state_tracker.states["another-market"] == other
    assert provider.native_instruction_metrics["NON_POSITIVE_TRADE_AMOUNT"] == 1


@pytest.mark.asyncio
async def test_late_native_copy_after_cache_expiry_does_not_invalidate_verified_trade():
    packet, message = sample()
    provider = PumpDiscoveryProvider(Settings(_env_file=None), FakeRpc())
    provider.seed_bonding_curve(packet.mint, packet.curve, 793100000000000)
    accepted = []

    async def publish(event):
        accepted.append(event)

    await provider._handle_notification(message, publish, transaction_evidence=packet.transaction)
    before = provider.state_tracker.states[packet.curve]
    await provider._handle_notification(message, publish)
    assert provider.state_tracker.states[packet.curve] == before
    assert before.observational_price is not None
    assert len([e for e in accepted if isinstance(e, TokenTrade)]) == 1
    assert provider.native_instruction_metrics["DUPLICATE_ALREADY_APPLIED"] == 1
    changed = copy.deepcopy(message)
    changed["params"]["result"]["value"]["logs"] += ["Log truncated"]
    await provider._handle_notification(changed, publish)
    assert provider.state_tracker.states[curve_address(packet.mint)].observational_price is None


@pytest.mark.asyncio
async def test_native_first_full_packet_wins_without_duplicate_native_projection():
    packet, message = sample()
    cache = OperationalEvidenceCache("test", native_wait_seconds=0)
    cache.watch.admit(packet.mint, utc_now())
    cache.status = "STREAMING"
    calls = []

    async def native(message, received):
        calls.append("native")

    async def full(packet):
        calls.append("full")

    cache.process_native = native
    cache.process_packet = full
    assert cache.defer_native(message, packet.received_at, packet.mint)
    cache.buffer.add(packet)
    cache.queue.put_nowait((packet, 0))
    task = asyncio.create_task(cache.process())
    try:
        await asyncio.wait_for(cache.queue.join(), 1)
        await cache._flush_native()
        assert calls == ["full"]
        assert not cache.pending_native
        assert cache.pending_native_bytes == 0
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_missing_full_packet_falls_back_with_original_receipt_and_unknown_guard():
    packet, message = sample()
    cache = OperationalEvidenceCache("test", native_wait_seconds=0)
    cache.watch.admit(packet.mint, utc_now())
    cache.status = "STREAMING"
    provider = PumpDiscoveryProvider(Settings(_env_file=None), FakeRpc())
    provider.seed_bonding_curve(packet.mint, packet.curve, 793100000000000)
    accepted = []

    async def publish(event):
        accepted.append(event)

    async def native(message, received):
        await provider._handle_notification(
            message, publish, received_at=received, allow_defer=False
        )

    provider.native_notification_router = cache.defer_native
    cache.process_native = native
    await provider._handle_notification(message, publish, transaction_evidence=packet.transaction)
    provider._applied_notifications.clear()
    assert cache.defer_native(message, packet.received_at, packet.mint)
    await cache._flush_native()
    # An ordinary trade's emit-CPI is recognised from its log shape, so the
    # packet-less fallback no longer invalidates the market's history.
    state = provider.state_tracker.states[packet.curve]
    assert state.invalidation_reason is None
    assert state.observational_price is not None
    assert provider.native_instruction_metrics["LOG_SHAPE_EVENT_CPI"] == 1
    assert accepted[-1].provider_received_at == packet.received_at
    assert cache.metrics["native_wait_expired"] == 1


@pytest.mark.asyncio
async def test_budget_exhaustion_is_explicit_and_does_not_restart_or_reset_spend():
    calls = []
    cache = OperationalEvidenceCache("test", on_gap=calls.append)

    async def exhausted():
        calls.append("connect")
        raise FullStreamBudgetExceeded("cap")
        yield

    cache.adapter.transactions = exhausted
    await cache.run()
    assert cache.status == "BUDGET_EXHAUSTED"
    assert cache.stream_stopped
    assert calls == ["connect", "FULL_STREAM_BUDGET_EXHAUSTED"]


@pytest.mark.asyncio
async def test_processor_failure_retains_bounded_non_secret_replay(tmp_path):
    packet, _ = sample()
    cache = OperationalEvidenceCache("secret-never-log", error_directory=tmp_path)
    cache.watch.admit(packet.mint, utc_now())

    async def broken(packet):
        raise RuntimeError("secret-never-log")

    cache.process_packet = broken
    cache.queue.put_nowait((packet, 0))
    task = asyncio.create_task(cache.process())
    try:
        await asyncio.wait_for(cache.queue.join(), 1)
        output = (tmp_path / "packet-1.json").read_text()
        assert "secret-never-log" not in output
        assert json.loads(output)["transaction"] == packet.transaction
        assert cache.metrics["processor_failures"] == 1
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


def test_excluded_fee_read_filter_preserves_unknown_writes_and_pump_transactions():
    read = [
        f"Program {FEE_PROGRAM} invoke [1]",
        "Program log: Instruction: GetFeesWithQuoteMint",
        f"Program {FEE_PROGRAM} success",
    ]
    assert irrelevant_standard_fee_read(read)
    assert not irrelevant_standard_fee_read([*read, "Log truncated"])
    assert not irrelevant_standard_fee_read(
        [f"Program {FEE_PROGRAM} invoke [1]", f"Program {FEE_PROGRAM} success"]
    )
    write = [
        f"Program {FEE_PROGRAM} invoke [1]",
        "Program log: Instruction: UpdateFeeShares",
        f"Program {FEE_PROGRAM} success",
    ]
    assert not irrelevant_standard_fee_read(write)
    assert not irrelevant_standard_fee_read(
        [*read, f"Program {PUMP_PROGRAM_ID} invoke [1]", f"Program {PUMP_PROGRAM_ID} success"]
    )


@pytest.mark.asyncio
async def test_bad_deferred_packet_is_diagnosed_and_next_packet_continues(tmp_path):
    from pydantic import BaseModel

    class Value(BaseModel):
        amount: int

    packet, message = sample()
    gaps = []
    cache = OperationalEvidenceCache(
        "secret", error_directory=tmp_path, native_wait_seconds=0, on_gap=gaps.append
    )
    cache.status = "STREAMING"
    cache.watch.admit(packet.mint, utc_now())
    calls = []

    async def native(message, received):
        calls.append(received)
        if len(calls) == 1:
            Value(amount="secret-input")

    cache.process_native = native
    assert cache.defer_native(message, packet.received_at, packet.mint)
    second = copy.deepcopy(message)
    second["params"]["result"]["value"]["signature"] = "second"
    assert cache.defer_native(second, packet.received_at, packet.mint)
    await cache._flush_native()
    assert len(calls) == 2
    assert gaps == ["DEFERRED_NATIVE_FAILURE"]
    assert cache.metrics["native_failures"] == 1
    assert cache.pending_native_bytes == 0
    output = (tmp_path / "packet-1.json").read_text()
    assert "secret-input" not in output
    assert json.loads(output)["fields"] == [{"loc": ["amount"], "type": "int_parsing"}]


@pytest.mark.asyncio
async def test_error_artifact_io_failure_does_not_stop_packet_processor(tmp_path):
    packet, _ = sample()
    directory = tmp_path / "not-a-directory"
    directory.write_text("existing file")
    cache = OperationalEvidenceCache("test", error_directory=directory)
    cache.watch.admit(packet.mint, utc_now())

    async def broken(packet):
        raise RuntimeError("do not log this")

    cache.process_packet = broken
    cache.queue.put_nowait((packet, 0))
    task = asyncio.create_task(cache.process())
    try:
        await asyncio.wait_for(cache.queue.join(), 1)
        assert not task.done()
        assert cache.metrics["processor_failures"] == 1
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


def test_alchemy_pubsub_endpoint_preserves_key_and_other_providers():
    settings = Settings(
        _env_file=None, solana_rpc_ws_url="wss://solana-mainnet.g.alchemy.com/v2/test"
    )
    assert str(settings.solana_rpc_ws_url) == "wss://solana-mainnet.streaming.alchemy.com/v2/test"
    assert str(Settings(_env_file=None).solana_rpc_ws_url) == "wss://api.mainnet-beta.solana.com/"


def test_gap_invalidates_price_window_until_new_samples_replace_it():
    from memebot.events.models import TradeSide
    from memebot.intelligence.features.engine import RollingFeatureEngine
    from test_feature_engine import MINT, WALLET_A, _trade

    engine = RollingFeatureEngine((5,))

    def trade(second):
        return _trade(
            second,
            event_number=100 + second,
            side=TradeSide.BUY,
            token=10,
            quote=100,
            wallet=WALLET_A,
        )

    engine.ingest_trade(trade(0))
    engine.invalidate_price_history(MINT)
    point = engine._states[MINT].trades[0]
    assert point.marginal_price is None and point.price_evidence["data_quality"] == "feed_gap"
    engine.ingest_trade(trade(1))
    assert engine._states[MINT].trades[0].marginal_price is None
    engine.ingest_trade(trade(7))
    assert all(p.marginal_price is not None for p in engine._states[MINT].trades)


def test_older_rejected_slot_cannot_pollute_rolling_features():
    from memebot.events.models import TradeSide
    from memebot.intelligence.features.engine import RollingFeatureEngine
    from test_feature_engine import MINT, WALLET_A, _trade

    engine = RollingFeatureEngine((5,))
    trade = _trade(0, event_number=201, side=TradeSide.BUY, token=10, quote=100, wallet=WALLET_A)
    engine.ingest_trade(trade)
    invalid = trade.model_copy(
        update={
            "normalized_state": trade.normalized_state.model_copy(
                update={"continuity_status": "SLOT_REGRESSION"}
            )
        }
    )
    assert engine.ingest_trade(invalid) is None
    assert len(engine._states[MINT].trades) == 1


@pytest.mark.asyncio
async def test_silent_transport_is_closed_by_idle_watchdog_even_with_long_ping_timeout():
    from memebot.providers.solana.pump import StreamIdleTimeout
    from test_pump_provider import FakeSocket

    class SilentSocket(FakeSocket):
        async def __anext__(self):
            await asyncio.Event().wait()

    provider = PumpDiscoveryProvider(
        Settings(_env_file=None, solana_ws_idle_timeout_seconds=0.02), FakeRpc()
    )

    async def publish(event):
        pass

    with pytest.raises(StreamIdleTimeout):
        await asyncio.wait_for(provider._consume(SilentSocket([]), publish), 1)


@pytest.mark.asyncio
async def test_failed_transaction_burst_cannot_fill_successful_event_queue():
    from test_pump_provider import FakeSocket

    _, message = sample()
    failed = copy.deepcopy(message)
    failed["params"]["result"]["value"]["err"] = {"InstructionError": [0, "Custom"]}
    provider = PumpDiscoveryProvider(Settings(_env_file=None), FakeRpc())
    consumed = []

    async def process(connection, messages, publish):
        async for raw, _received in messages:
            consumed.append(json.loads(raw))

    async def publish(event):
        pass

    provider._process_messages = process
    control = {"id": 1, "error": {"code": -1}}
    await provider._consume(
        FakeSocket([json.dumps(failed)] * 10000 + [json.dumps(control), json.dumps(message)]),
        publish,
    )
    assert consumed == [control, message]
    assert provider._failed_notifications_skipped == 10000
    assert provider._receive_queue_peak <= 2


@pytest.mark.asyncio
async def test_fee_account_subscription_invalidates_config_without_pumpswap_firehose():
    from test_pump_provider import FakeSocket
    from test_state_trust import CURVE, seed

    socket = FakeSocket(
        [
            json.dumps({"id": 1, "result": 10}),
            json.dumps({"id": 2, "result": 11}),
            json.dumps(
                {
                    "method": "accountNotification",
                    "params": {
                        "subscription": 11,
                        "result": {"context": {"slot": 99}, "value": None},
                    },
                }
            ),
        ]
    )
    provider = PumpDiscoveryProvider(Settings(_env_file=None), FakeRpc())
    provider.state_tracker = seed()

    async def publish(event):
        pass

    await provider._consume(socket, publish)
    requests = [json.loads(m) for m in socket.sent]
    assert [r["method"] for r in requests] == ["logsSubscribe", "accountSubscribe"]
    assert provider.state_tracker.states[CURVE].observational_price is not None
    assert not provider.state_tracker.states[CURVE].execution_config_verified
    assert provider.state_tracker.invalidations[-1].reason == "CONFIG_CHANGE"


def test_stream_budget_survives_restart_and_wall_clock_boundaries(tmp_path):
    from memebot.providers.solana.stream_budget import RollingStreamBudget

    now = [120000.0]
    path = tmp_path / "budget.json"
    budget = RollingStreamBudget(path, 128_000_000, clock=lambda: now[0])
    budget.charge(126_000_000)
    assert not budget.can_receive()
    restarted = RollingStreamBudget(path, 128_000_000, clock=lambda: now[0])
    assert not restarted.can_receive()
    now[0] += 3600
    assert not restarted.can_receive()  # Conservative boundary minute.
    now[0] += 60
    assert restarted.can_receive()
    assert restarted.usage()[1] >= 126_000_000  # Still counted for daily cap.


def test_corrupt_stream_budget_fails_closed(tmp_path):
    from memebot.providers.solana.stream_budget import RollingStreamBudget

    path = tmp_path / "budget.json"
    path.write_text("bad")
    with pytest.raises(ValueError):
        RollingStreamBudget(path, 128_000_000)


@pytest.mark.asyncio
async def test_rolling_budget_waits_then_resumes_without_resetting_ledger(tmp_path, monkeypatch):
    from memebot.providers.solana.stream_budget import RollingStreamBudget

    now = [120000.0]
    budget = RollingStreamBudget(tmp_path / "budget.json", 128_000_000, clock=lambda: now[0])
    budget.charge(126_000_000)
    charged = budget.usage()[1]
    cache = OperationalEvidenceCache("test", budget=budget)
    waits = []
    runs = []

    async def sleep(seconds):
        assert cache.status == "BUDGET_EXHAUSTED"
        waits.append(seconds)
        now[0] += 3660

    async def session():
        runs.append(budget.usage())
        cache.closed = True
        cache.status = "BUDGET_EXHAUSTED"

    monkeypatch.setattr(asyncio, "sleep", sleep)
    cache._run_once = session
    await cache.run()
    assert waits and runs == [(0, charged)]
    assert RollingStreamBudget(budget.path, 128_000_000, clock=lambda: now[0]).usage()[1] == charged


@pytest.mark.asyncio
async def test_healthy_full_sessions_reset_consecutive_failure_allowance(tmp_path, monkeypatch):
    from memebot.providers.solana.stream_budget import RollingStreamBudget

    budget = RollingStreamBudget(tmp_path / "budget.json", 128_000_000)
    cache = OperationalEvidenceCache("test", budget=budget)
    sessions = []

    async def sleep(seconds):
        pass

    async def session():
        sessions.append(True)
        cache.adapter.metrics["full_packets"] += 1
        if len(sessions) == 4:
            cache.closed = True

    monkeypatch.setattr(asyncio, "sleep", sleep)
    cache._run_once = session
    await cache.run()
    assert len(sessions) == 4


def test_stream_budget_enforces_daily_limit_independently(tmp_path):
    from memebot.providers.solana.stream_budget import RollingStreamBudget

    now = [200000.0]
    budget = RollingStreamBudget(tmp_path / "budget.json", 128_000_000, clock=lambda: now[0])
    minute = int(now[0] // 60)
    # A deliberately preloaded full daily ledger, outside the current hour.
    budget.buckets = {minute - 120: budget.daily_bytes}
    assert budget.usage()[0] == 0
    assert not budget.can_receive()
    with pytest.raises(ValueError):
        budget.charge(1)


def test_ack_can_arm_native_wait_before_first_packet_without_claiming_coverage():
    cache = OperationalEvidenceCache("test")
    cache.adapter.accounts = ("watched",)
    cache.adapter.revision = 2
    cache._control({"kind": "ack", "revision": 1})
    assert cache.status == "STARTING"
    cache._control({"kind": "ack", "revision": 2})
    assert cache.status == "STREAMING"
    assert cache.metrics["full_packets"] == 0


@pytest.mark.asyncio
async def test_routine_atomic_refresh_preserves_healthy_stream_history_but_repairs_gap():
    from memebot.market_state import MarketStateTracker
    from memebot.paper.market_refresh import CurrentPaperMarketRefresher
    from test_current_paper_execution import current_market

    market, rpc = await current_market()
    tracker = MarketStateTracker()
    refresher = CurrentPaperMarketRefresher(rpc, state_tracker=tracker)
    fresh = await refresher.refresh(market)
    anchor = tracker.states[market.market]
    current = anchor.model_copy(
        update={
            "state_slot": anchor.state_slot - 1,
            "last_signature": "stream",
            "continuity_status": "EXACT",
        }
    )
    tracker.states[market.market] = current
    result = await refresher.refresh(market)
    assert result.source_slot == fresh.source_slot
    assert result.execution_state is not None
    assert tracker.states[market.market] == current
    tracker.invalidate(market.market, "STREAM_DISCONNECT")
    await refresher.refresh(market)
    assert tracker.states[market.market].continuity_status == "RPC_VALIDATED"
