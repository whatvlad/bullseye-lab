import base64
import json

import httpx
import pytest

from memebot.providers.solana.rpc import JsonRpcSolanaClient, SolanaRpcError

ADDRESS = "So11111111111111111111111111111111111111112"
OWNER = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [None, [], "bad", {"result": "ok", "id": 99}])
async def test_rpc_rejects_malformed_or_mismatched_envelopes(payload: object) -> None:
    rpc = JsonRpcSolanaClient(
        "https://rpc.invalid",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)),
    )
    try:
        with pytest.raises(SolanaRpcError):
            await rpc.get_account(ADDRESS, "confirmed")
    finally:
        await rpc.close()


@pytest.mark.asyncio
async def test_rpc_429_honors_cooldown_and_recovers_with_one_probe() -> None:
    now = [0.0]
    calls = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "120"})
        payload = json.loads(request.content)
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": payload["id"], "result": "ok"})

    rpc = JsonRpcSolanaClient(
        "https://rpc.invalid", transport=httpx.MockTransport(respond), clock=lambda: now[0]
    )
    try:
        assert not (await rpc.health()).healthy
        assert not rpc.available
        assert not (await rpc.health()).healthy
        assert len(calls) == 1
        now[0] = 119
        assert not rpc.available
        now[0] = 120
        assert (await rpc.health()).healthy
        assert rpc.available
        assert rpc.metrics()["errors_by_code"] == {"http_429": 1, "circuit_open": 1}
    finally:
        await rpc.close()


@pytest.mark.asyncio
async def test_json_rpc_health_and_account_are_parsed() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        if payload["method"] == "getHealth":
            result: object = "ok"
        else:
            result = {
                "context": {"slot": 42},
                "value": {
                    "data": [base64.b64encode(b"account").decode(), "base64"],
                    "executable": False,
                    "lamports": 123,
                    "owner": OWNER,
                },
            }
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": payload["id"], "result": result})

    rpc = JsonRpcSolanaClient(
        "https://rpc.invalid",
        transport=httpx.MockTransport(handler),
    )
    try:
        health = await rpc.health()
        account = await rpc.get_account(ADDRESS, "confirmed")
    finally:
        await rpc.close()

    assert health.healthy is True
    assert account is not None
    assert account.slot == 42
    assert account.owner == OWNER


@pytest.mark.asyncio
async def test_json_rpc_marks_http_429_without_leaking_endpoint() -> None:
    seen_urls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return httpx.Response(429, json={"error": "limited"})

    rpc = JsonRpcSolanaClient(
        "https://secret-provider.invalid/?api-key=do-not-log",
        transport=httpx.MockTransport(handler),
    )
    try:
        with pytest.raises(SolanaRpcError) as captured:
            await rpc.get_transaction("1" * 88, "confirmed")
    finally:
        await rpc.close()

    assert captured.value.rate_limited is True
    assert str(captured.value) == "http_429"
    assert "do-not-log" not in str(captured.value)
    assert seen_urls == ["https://secret-provider.invalid/?api-key=do-not-log"]
