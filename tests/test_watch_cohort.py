from datetime import UTC, datetime, timedelta

import pytest

from memebot.providers.solana.helius_evidence import HeliusTransactionEvidenceStream
from memebot.providers.solana.pump_idl import NATIVE_SOL_MINT, PUMP_PROGRAM_ID
from memebot.providers.solana.watch_cohort import WatchCohort
from test_candidate_proof import MINT


def admit(cohort, now, **changes):
    values = dict(
        now=now, standard=True, quote_mint=NATIVE_SOL_MINT, continuity="EXACT", multi_event=False
    )
    values.update(changes)
    return cohort.observe(MINT, **values)


def test_canonical_narrow_filter_and_no_deep_rpc():
    cohort = WatchCohort()
    assert admit(cohort, datetime.now(UTC))
    assert len(cohort.accounts()) == 4
    assert MINT in cohort.accounts() and PUMP_PROGRAM_ID not in cohort.accounts()


@pytest.mark.parametrize(
    "changes",
    [
        dict(standard=False),
        dict(multi_event=True),
        dict(cashback=True),
        dict(migrated=True),
        dict(complete=True),
        dict(continuity="DIVERGED"),
        dict(supported_fee_route=False),
    ],
)
def test_out_of_scope_removes_watch(changes):
    now = datetime.now(UTC)
    cohort = WatchCohort()
    assert admit(cohort, now)
    assert not admit(cohort, now, **changes)
    assert not cohort.accounts()


@pytest.mark.parametrize("seconds,reason", [(30, "CANDIDATE_IDLE"), (120, "TTL_EXPIRED")])
def test_watch_expiry_removes_filter(seconds, reason):
    now = datetime.now(UTC)
    cohort = WatchCohort()
    admit(cohort, now)
    cohort.expire(now + timedelta(seconds=seconds))
    assert not cohort.markets and cohort.removals[-1]["reason"] == reason


@pytest.mark.asyncio
@pytest.mark.parametrize("accounts", [(), (PUMP_PROGRAM_ID,)])
async def test_full_stream_never_subscribes_globally(accounts):
    stream = HeliusTransactionEvidenceStream("wss://unused.invalid", watched_accounts=accounts)
    with pytest.raises(ValueError, match="explicit_narrow_market_filter_required"):
        await anext(stream.transactions())
