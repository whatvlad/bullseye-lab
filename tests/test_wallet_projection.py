import asyncio

import pytest

from memebot.intelligence.wallet_projection import DurableWalletProjector


@pytest.mark.asyncio
async def test_many_wakeups_do_not_overflow_or_interrupt_durable_projection():
    gate = asyncio.Event()
    entered = asyncio.Event()
    durable = list(range(10000))
    projected = []

    async def batch():
        entered.set()
        await gate.wait()
        items = durable[:25]
        del durable[:25]
        projected.extend(items)
        return len(items)

    projector = DurableWalletProjector(batch, lambda error: pytest.fail(str(type(error))))
    task = asyncio.create_task(projector.run())
    try:
        await asyncio.wait_for(entered.wait(), 1)
        for _ in range(10000):
            projector.wake()
        assert len(durable) == 10000
        gate.set()
        await asyncio.sleep(0.12)
        assert projected[:25] == list(range(25))
        assert projected + durable == list(range(10000))
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_projection_failure_retries_without_losing_durable_work():
    calls = 0
    complete = asyncio.Event()
    errors = []

    async def batch():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary DB failure")
        complete.set()
        return 0

    projector = DurableWalletProjector(batch, errors.append, poll_seconds=0.01)
    task = asyncio.create_task(projector.run())
    try:
        await asyncio.wait_for(complete.wait(), 1)
        assert calls >= 2
        assert len(errors) == 1
        assert not task.done()
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
