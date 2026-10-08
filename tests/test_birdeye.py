from decimal import Decimal

import httpx
import pytest
from pydantic import SecretStr

from memebot.providers.birdeye.client import BirdeyeClient
from memebot.providers.birdeye.market import BirdeyeMarketDataProvider

MINT = "So11111111111111111111111111111111111111112"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 401, 403, 404])
async def test_probe_does_not_claim_capabilities_from_http_errors(status: int) -> None:
    client = BirdeyeClient(
        "https://public-api.birdeye.so",
        SecretStr("secret"),
        minimum_interval_seconds=0,
        transport=httpx.MockTransport(lambda request: httpx.Response(status)),
    )
    try:
        report = await client.probe(MINT)
        assert not report.authenticated
        assert not report.available
        assert "token_market_data" in report.unavailable
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_birdeye_uses_header_auth_and_parses_market_data() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": {
                    "price": 93.5,
                    "liquidity": 1_000_000,
                    "market_cap": 2_000_000,
                    "volume_24h_usd": 500_000,
                },
            },
        )

    client = BirdeyeClient(
        "https://public-api.birdeye.so",
        SecretStr("test-secret"),
        minimum_interval_seconds=0,
        transport=httpx.MockTransport(handler),
    )
    provider = BirdeyeMarketDataProvider(client, cache_seconds=300)

    first = await provider.token_snapshot(MINT)
    second = await provider.token_snapshot(MINT)

    assert first == second
    assert first.price_usd == Decimal("93.5")
    assert first.liquidity_usd == Decimal("1000000")
    assert len(requests) == 1
    assert requests[0].headers["X-API-KEY"] == "test-secret"
    assert "test-secret" not in str(requests[0].url)
    assert requests[0].headers["x-chain"] == "solana"
    await provider.close()


@pytest.mark.asyncio
async def test_birdeye_capability_probe_degrades_per_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("credits"):
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "data": {"package": "Standard", "remaining": 29900},
                },
            )
        return httpx.Response(200, json={"success": True, "data": {}})

    client = BirdeyeClient(
        "https://public-api.birdeye.so",
        SecretStr("test-secret"),
        minimum_interval_seconds=0,
        transport=httpx.MockTransport(handler),
    )
    report = await client.probe(MINT)

    assert report.authenticated is True
    assert report.credits == {"package": "Standard", "remaining": Decimal(29900)}
    assert report.unavailable["token_exit_liquidity"] == "unsupported_chain_base_only"
    assert "token_market_data" in report.available
    await client.close()


@pytest.mark.asyncio
async def test_birdeye_holder_profile_is_candidate_scoped() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"success": True, "data": {"tags": {}}})

    client = BirdeyeClient(
        "https://public-api.birdeye.so",
        SecretStr("test-secret"),
        minimum_interval_seconds=0,
        transport=httpx.MockTransport(handler),
    )
    await client.holder_profile(MINT)

    assert requests[0].url.path == "/token/v1/holder-profile"
    assert requests[0].url.params["token_address"] == MINT
    assert requests[0].url.params["include_zero_balance"] == "false"
    await client.close()
