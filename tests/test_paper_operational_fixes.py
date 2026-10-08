import asyncio
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy import select

from memebot.events.models import TradeSide
from memebot.intelligence.features.engine import RollingFeatureEngine
from memebot.market_state import NormalizedMarketState
from memebot.models.strategy import StrategyDecisionAction, StrategyRegime
from memebot.paper import exit_evidence
from memebot.paper.exits import exit_intent
from memebot.paper.models import PositionSnapshot
from memebot.providers.solana.pump import PumpDiscoveryProvider
from memebot.providers.solana.pump_idl import PumpTrade
from memebot.storage.database.control import TradingControlSnapshot
from memebot.storage.database.models import ExperimentRunRecord
from memebot.strategies.presets import initial_strategy_presets
from memebot.strategies.runner import MultiStrategyRunner
from memebot.strategies.scoring import TransparentScoreEngine
from test_current_paper_execution import current_market, quote, simulator
from test_feature_engine import WALLET_A, _trade
from test_paper_engine_pending import _sizing_engine
from test_pump_provider import FakeRpc
from test_strategies import NOW, _feature, _risk


@pytest.mark.parametrize(
    "change,missing",
    [
        ({"price_change_percent": None}, "rolling_price_change"),
        ({"price_sample_count": 0}, "price_window_coverage"),
        ({"missing_price_sample_count": 1}, "price_window_coverage"),
        ({"price_observation_span_seconds": D(2)}, "price_window_coverage"),
        ({"open_price_raw": None}, "price_window_coverage"),
        ({"flow_imbalance": None}, "flow_imbalance"),
    ],
)
def test_missing_required_subinput_cannot_be_averaged_away(change, missing):
    feature = _feature()
    feature = feature.model_copy(
        update={"windows": (feature.windows[0].model_copy(update=change), *feature.windows[1:])}
    )
    config = next(c for c in initial_strategy_presets() if c.key == "aggressive")
    score = TransparentScoreEngine().score(
        feature, _risk().result, config, regime=StrategyRegime.EARLY_MOMENTUM
    )
    momentum = next(c for c in score.components if c.name == "momentum")
    assert momentum.component_status == "INCOMPLETE"
    assert momentum.score is None
    assert missing in momentum.missing_required_inputs
    assert missing in score.missing_required_inputs
    assert score.overall_signal_completeness < 100
    decision = next(
        d
        for d in MultiStrategyRunner(initial_strategy_presets()).evaluate(
            _risk(), feature, token_created_at=NOW - timedelta(seconds=45)
        )
        if d.strategy_key == "aggressive"
    )
    assert decision.action != StrategyDecisionAction.ENTER_CANDIDATE
    if missing == "rolling_price_change":
        assert "UNKNOWN_REQUIRED_PRICE_CHANGE" in decision.reasons


@pytest.mark.parametrize(
    "change,missing",
    [
        ({"latest_price_raw": None}, "decision_price"),
        ({"price_evidence": {"data_quality": "INCOMPLETE"}}, "price_provenance"),
    ],
)
def test_fresh_execution_bank_does_not_replace_historical_signal(change, missing):
    feature = _feature().model_copy(update=change)
    config = next(c for c in initial_strategy_presets() if c.key == "aggressive")
    score = TransparentScoreEngine().score(
        feature, _risk().result, config, regime=StrategyRegime.EARLY_MOMENTUM
    )
    assert missing in score.missing_required_inputs


def test_gap_inside_window_invalidates_price_change_even_after_good_tick():
    engine = RollingFeatureEngine((10,))
    for number, second in enumerate((0, 3, 6), 1):
        event = _trade(
            second, event_number=number, side=TradeSide.BUY, token=10, quote=100, wallet=WALLET_A
        )
        if second == 3:
            event = event.model_copy(update={"normalized_state": NormalizedMarketState()})
        snapshot = engine.ingest_trade(event)
    metric = snapshot.windows[0]
    assert metric.price_sample_count == 2 and metric.missing_price_sample_count == 1
    assert metric.price_change_percent is None


def position(**changes):
    engine = _sizing_engine()
    p = PositionSnapshot(
        UUID(int=2),
        UUID(int=1),
        "So11111111111111111111111111111111111111112",
        "balanced",
        "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
        "pump_fun",
        "bonding_curve",
        D(1000),
        D(100),
        D(0),
        D(1),
        D(1),
        NOW,
        False,
    )
    return engine, replace(p, **changes)


def control():
    return TradingControlSnapshot(False, "balanced", D(30), D(40), 5, D(12), D(100), D(18), 1800)


def test_net_stop_triggers_before_gross_stop_without_changing_threshold():
    engine, p = position()
    assert exit_intent(p, D("0.90"), NOW, control(), engine._settings) is None
    intent = exit_intent(
        p,
        D("0.90"),
        NOW,
        control(),
        engine._settings,
        net_executable_pnl_percent=D(-13),
    )
    assert intent.reason == "stop_loss"
    assert control().stop_loss_percent == 12


@pytest.mark.asyncio
async def test_partial_fill_diagnostic_uses_full_remaining_liquidation_risk():
    engine, p = position()
    fresh, _ = await current_market()
    at = fresh.observed_at
    result = simulator().simulate_sell(
        fresh,
        quote(at),
        token_amount_raw=D(1000),
        position_effect="close",
        exit_reason="mark",
        signal_at=at,
        decision_at=at,
        executed_at=at,
    )
    fill = result.fill
    p = replace(p, remaining_cost_basis=D(50), token_quantity_raw=D(1000))
    full = fill.model_copy(update={"gross_portfolio_amount": D(49), "total_fee_portfolio": D(1)})
    half = fill.model_copy(update={"gross_portfolio_amount": D("24.5")})
    evidence = engine._exit_diagnostics(p, half, control(), {}, risk_fill=full)
    assert D(evidence.execution_diagnostics["net_executable_pnl_percent"]) == -4
    assert D(evidence.execution_diagnostics["net_liquidation_value"]) == 48


@pytest.mark.asyncio
async def test_unrelated_position_can_exit_while_other_market_waits():
    engine, first = position()
    second = replace(first, mint="11111111111111111111111111111111", position_id=UUID(int=3))
    positions = {first.mint: first, second.mint: second}
    started, release, finished = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def lookup(mint):
        return positions.get(mint)

    async def evaluate(p, **kwargs):
        if p.mint == first.mint:
            started.set()
            await release.wait()
        else:
            finished.set()

    engine._registry = SimpleNamespace(open_position=lookup)
    engine._evaluate_position = evaluate
    slow = asyncio.create_task(engine._protect_position(first))
    await started.wait()
    await asyncio.wait_for(engine._protect_position(second), 1)
    assert finished.is_set() and not slow.done()
    release.set()
    await slow


@pytest.mark.asyncio
async def test_same_position_rechecked_under_lock_prevents_duplicate_exit():
    engine, p = position()
    current, calls = p, []

    async def lookup(mint):
        return current

    async def evaluate(pos, **kwargs):
        nonlocal current
        calls.append(pos.position_id)
        await asyncio.sleep(0)
        current = None

    engine._registry = SimpleNamespace(open_position=lookup)
    engine._evaluate_position = evaluate
    await asyncio.gather(engine._protect_position(p), engine._protect_position(p))
    assert calls == [p.position_id]


def test_received_native_event_wakes_only_open_market_before_ordered_decode(monkeypatch):
    engine, p = position()
    provider = PumpDiscoveryProvider(engine._settings, FakeRpc())
    provider.seed_open_position(p.mint)
    calls = []
    provider.set_exit_wakeup(lambda *args: calls.append(args))
    monkeypatch.setattr(
        "memebot.providers.solana.pump.extract_anchor_events",
        lambda logs: [(0, SimpleNamespace(mint=p.mint))],
    )
    # Use a real decoded trade type without constructing unrelated instruction fields.
    trade = object.__new__(PumpTrade)
    object.__setattr__(trade, "mint", p.mint)
    monkeypatch.setattr(
        "memebot.providers.solana.pump.extract_anchor_events", lambda logs: [(0, trade)]
    )
    notification = {
        "params": {"result": {"context": {"slot": 101}, "value": {"err": None, "logs": []}}}
    }
    provider._wake_received_positions(notification, NOW)
    assert calls == [(p.mint, 101, NOW)]
    notification["params"]["result"]["value"]["err"] = {"InstructionError": [0, "test"]}
    provider._wake_received_positions(notification, NOW)
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_bounded_marks_and_three_shadows_survive_serialization_without_orders(monkeypatch):
    import json

    engine, p = position()
    fresh, _ = await current_market()
    at = fresh.observed_at
    result = simulator().simulate_sell(
        fresh,
        quote(at),
        token_amount_raw=D(1_000_000_000),
        position_effect="close",
        exit_reason="mark",
        signal_at=at,
        decision_at=at,
        executed_at=at,
    )
    fill = result.fill
    basis = (fill.gross_portfolio_amount - fill.total_fee_portfolio) * 2
    p = replace(p, token_quantity_raw=fill.token_amount_raw, remaining_cost_basis=basis)
    fill = engine._exit_diagnostics(p, fill, control(), {})
    monkeypatch.setattr(exit_evidence, "MAX_MARKS", 3)
    prior = {}
    for _ in range(5):
        path = exit_evidence.retain_exit_evidence(
            prior,
            fill,
            quantity=p.token_quantity_raw,
            cost_basis=basis,
            entry_price=p.entry_price_raw,
            opened_at=at,
        )
        prior = json.loads(json.dumps({"exit_evidence": path}))
    assert len(path["marks"]) == 3
    assert path["total_mark_count"] == 5 and path["dropped_mark_count"] == 2
    assert set(path["shadow_policies"]) == {
        "CURRENT_POLICY",
        "EARLIER_PROFIT_PROTECTION",
        "DEFENSIVE_PROFIT_PROTECTION",
    }
    assert all(len(s["exits"]) == 1 for s in path["shadow_policies"].values())
    assert all(s["closed_at"] for s in path["shadow_policies"].values())
    # A partial's smaller basis starts a separate peak segment.
    smaller = exit_evidence.retain_exit_evidence(
        prior,
        fill,
        quantity=p.token_quantity_raw / 2,
        cost_basis=basis / 2,
        entry_price=p.entry_price_raw,
        opened_at=at,
    )
    assert smaller["basis_segment"] != path["basis_segment"]


@pytest.mark.asyncio
async def test_shadow_partial_profit_then_collapse_tracks_whole_entry_cost():
    import copy

    engine, p = position()
    fresh, _ = await current_market()
    at = fresh.observed_at
    quantity = D(1_000_000_000)

    def make_fill(market, timestamp):
        return (
            simulator()
            .simulate_sell(
                market,
                quote(timestamp),
                token_amount_raw=quantity,
                position_effect="close",
                exit_reason="mark",
                signal_at=timestamp,
                decision_at=timestamp,
                executed_at=timestamp,
            )
            .fill
        )

    fill = make_fill(fresh, at)
    basis = (fill.gross_portfolio_amount - fill.total_fee_portfolio) / 2
    entry_price = fill.actual_fill_price_raw * D(2) / 3
    p = replace(
        p, token_quantity_raw=quantity, remaining_cost_basis=basis, entry_price_raw=entry_price
    )
    path = exit_evidence.retain_exit_evidence(
        {},
        engine._exit_diagnostics(p, fill, control(), {}),
        quantity=quantity,
        cost_basis=basis,
        entry_price=entry_price,
        opened_at=at,
    )
    policies = path["shadow_policies"]
    assert not policies["CURRENT_POLICY"]["partial_taken"]
    assert policies["DEFENSIVE_PROFIT_PROTECTION"]["partial_taken"]
    assert D(policies["DEFENSIVE_PROFIT_PROTECTION"]["cost_basis"]) == basis / 2
    state = copy.deepcopy(fresh.execution_state)
    state["curve"]["virtual_quote_reserves"] //= 3
    late = at + timedelta(seconds=1)
    fallen = replace(fresh, execution_state=state, observed_at=late)
    final = make_fill(fallen, late)
    path = exit_evidence.retain_exit_evidence(
        {"exit_evidence": path},
        engine._exit_diagnostics(p, final, control(), {}),
        quantity=quantity,
        cost_basis=basis,
        entry_price=entry_price,
        opened_at=at,
    )
    protected = path["shadow_policies"]["DEFENSIVE_PROFIT_PROTECTION"]
    assert protected["closed_at"]
    assert [e["reason"] for e in protected["exits"]] == ["partial_take_profit", "stop_loss"]
    assert D(protected["net_return_percent"]) == D(protected["realized_pnl"]) / basis * 100


@pytest.mark.asyncio
async def test_telegram_reset_creates_linked_cohort_and_keeps_entries_paused():
    from memebot.storage.database.control import ControlRepository
    from memebot.storage.database.engine import Database, create_database_engine
    from memebot.storage.database.experiments import ExperimentRepository
    from memebot.storage.database.registry import TokenRegistry

    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()
    registry = TokenRegistry(database.sessions)
    controls = ControlRepository(database.sessions)
    experiments = ExperimentRepository(database.sessions)
    await registry.ensure_strategy_configurations(initial_strategy_presets())
    await controls.ensure(
        active_strategy_key="aggressive",
        base_position_percent=D(30),
        max_position_percent=D(40),
        max_open_positions=5,
        stop_loss_percent=D(12),
        take_profit_percent=D(100),
        trailing_stop_percent=D(18),
        max_holding_seconds=1800,
    )
    await controls.set_paused(True, user_id=0)
    original = await experiments.start(
        name="original", initial_cash=D(1000), currency="USDT", settings_snapshot={}
    )
    await controls.set_paused(False, user_id=0)
    portfolio = await registry.create_paper_portfolio(
        name="reset",
        initial_cash=D(1000),
        currency="USDT",
        settings_snapshot={"source_fingerprint": "new", "database_url": "secret"},
    )
    active = await experiments.active()
    assert active["portfolio_id"] == str(portfolio.portfolio_id)
    assert (
        active["configuration_snapshot"]["portfolio_reset"]["parent_experiment_id"]
        == original["id"]
    )
    assert "database_url" not in active["configuration_snapshot"]["settings"]
    assert (await controls.get()).entries_paused
    async with database.sessions() as session:
        rows = (await session.scalars(select(ExperimentRunRecord))).all()
        assert sorted(r.status for r in rows) == ["active", "stopped"]
    await experiments.stop()
    reset_again = await registry.create_paper_portfolio(
        name="after stopped experiment",
        initial_cash=D(1000),
        currency="USDT",
        settings_snapshot={},
    )
    assert (await experiments.active())["portfolio_id"] == str(reset_again.portfolio_id)
    from memebot.storage.database.models import PaperPositionRecord, TokenRecord

    async with database.sessions() as session, session.begin():
        token = TokenRecord(mint="So11111111111111111111111111111111111111112")
        session.add(token)
        await session.flush()
        session.add(
            PaperPositionRecord(
                portfolio_id=reset_again.portfolio_id,
                token_id=token.id,
                mint=token.mint,
                strategy_key="aggressive",
                market_address=token.mint,
                venue="pump_fun",
                lifecycle="bonding_curve",
                status="open",
                token_quantity_raw=1000,
                remaining_cost_basis=100,
                realized_pnl=0,
                entry_price_raw=1,
                peak_price_raw=1,
                last_price_raw=1,
                opened_at=NOW,
                partial_take_profit_taken=False,
            )
        )
    with pytest.raises(ValueError, match="close all open paper positions"):
        await registry.create_paper_portfolio(
            name="unsafe reset", initial_cash=D(1000), currency="USDT"
        )
    assert (await registry.active_paper_portfolio()).portfolio_id == reset_again.portfolio_id
    await database.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", ["decision_price", "legacy_completeness", "provenance"])
async def test_entry_boundary_rejects_invalid_history_before_any_rpc(invalid):
    engine, p = position()
    config = initial_strategy_presets()
    decision = next(
        d
        for d in MultiStrategyRunner(config).evaluate(
            _risk(), _feature(), token_created_at=NOW - timedelta(seconds=45)
        )
        if d.strategy_key == "aggressive"
    )
    assert decision.action == StrategyDecisionAction.ENTER_CANDIDATE
    if invalid == "decision_price":
        decision = decision.model_copy(update={"decision_price": None})
    elif invalid == "provenance":
        decision = decision.model_copy(
            update={"price_evidence": {"observational_trust": "UNKNOWN"}}
        )
    else:
        decision = decision.model_copy(
            update={"score": decision.score.model_copy(update={"components": ()})}
        )
    published = []

    async def get_control():
        return control()

    async def get_portfolio():
        return SimpleNamespace(portfolio_id=p.portfolio_id, initial_cash=D(1000), currency="USDT")

    async def publish(event):
        published.append(event)

    engine._controls = SimpleNamespace(get=get_control)
    engine._registry = SimpleNamespace(active_paper_portfolio=get_portfolio)
    engine._publish = publish
    await engine.on_decision(decision)
    assert len(published) == 1
    assert published[0].result.rejection_reason == "REQUIRED_PRICE_SIGNAL_INCOMPLETE"


@pytest.mark.asyncio
async def test_watchdog_dispatch_does_not_wait_for_slow_other_market():
    engine, first = position()
    second = replace(first, mint="11111111111111111111111111111111", position_id=UUID(int=3))
    release, started = asyncio.Event(), asyncio.Event()
    calls = []

    async def positions():
        return [first, second]

    async def lookup(mint):
        return first if mint == first.mint else second

    async def evaluate(p, **kwargs):
        calls.append(p.mint)
        if p.mint == first.mint:
            started.set()
            await release.wait()

    engine._registry = SimpleNamespace(open_positions=positions, open_position=lookup)
    engine._evaluate_position = evaluate
    await engine.queue_position_watchdog()
    await started.wait()
    await asyncio.sleep(0)
    await engine.queue_position_watchdog()
    await asyncio.sleep(0)
    assert calls.count(first.mint) == 1 and calls.count(second.mint) == 2
    release.set()
    await asyncio.gather(*list(engine._exit_tasks.values()))
