from decimal import Decimal

import pytest

from memebot.intelligence.risk.insider import (
    WalletFunderResolver,
    WalletOrigin,
    first_sol_sender,
    summarize,
)

NOW = 1_800_000_000


def _tx(kind: str, source: str, target: str, *, inner: bool = False):
    key = "destination" if kind == "transfer" else "newAccount"
    item = {"program": "system", "parsed": {"type": kind, "info": {"source": source, key: target}}}
    outer = [] if inner else [item]
    inner_groups = [{"index": 0, "instructions": [item]}] if inner else []
    return {
        "transaction": {"message": {"instructions": outer}},
        "meta": {"innerInstructions": inner_groups},
    }


def test_first_sol_sender_reads_transfers_and_account_creation():
    assert first_sol_sender(_tx("transfer", "funder", "wallet"), "wallet") == "funder"
    assert (
        first_sol_sender(_tx("createAccount", "funder", "wallet", inner=True), "wallet") == "funder"
    )
    assert first_sol_sender(_tx("transfer", "funder", "someone-else"), "wallet") is None
    assert first_sol_sender(None, "wallet") is None


def test_summary_counts_big_holders_linked_clusters_and_fresh_wallets():
    holders = [
        ("a", Decimal(6)),
        ("b", Decimal(4)),
        ("c", Decimal(3)),
        ("d", Decimal(1)),
        ("e", Decimal("0.5")),
    ]
    origins = [
        WalletOrigin("boss", NOW - 600, aged=False),  # fresh, linked
        WalletOrigin("boss", NOW - 7200, aged=False),  # fresh, linked
        WalletOrigin("binance", NOW - 600, aged=False),  # hub funder: not a link
        WalletOrigin("binance", NOW - 86400 * 9, aged=False),
        None,  # unresolved
    ]
    facts = summarize(holders, origins, now=NOW, hubs={"binance"})
    assert facts.holders_over["3"] == (3, Decimal(13))
    assert facts.holders_over["5"] == (1, Decimal(6))
    assert facts.linked_supply_percent == Decimal(10) and facts.linked_cluster_count == 1
    assert facts.fresh_holder_count == 3 and facts.fresh_supply_percent == Decimal(13)
    assert facts.resolved_holders == 4


class _Rpc:
    def __init__(self, signatures, transaction=None):
        self.signatures, self.transaction, self.calls = signatures, transaction, []

    async def _call(self, method, params=None):
        self.calls.append(method)
        return self.signatures if method == "getSignaturesForAddress" else self.transaction


@pytest.mark.asyncio
async def test_resolver_finds_funder_once_and_marks_busy_wallets_aged():
    fresh = _Rpc(
        [{"signature": "s2"}, {"signature": "s1", "blockTime": NOW}], _tx("transfer", "f", "w")
    )
    resolver = WalletFunderResolver(fresh, requests_per_second=1000)
    assert await resolver.origin("w") == WalletOrigin("f", NOW, aged=False)
    assert await resolver.origin("w") == WalletOrigin("f", NOW, aged=False)
    assert fresh.calls == ["getSignaturesForAddress", "getTransaction"]  # cached afterwards
    busy = WalletFunderResolver(_Rpc([{"signature": str(i)} for i in range(100)]))
    assert await busy.origin("w") == WalletOrigin(None, None, aged=True)
