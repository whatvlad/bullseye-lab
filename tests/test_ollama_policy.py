from __future__ import annotations

import json

import httpx
import pytest

from memebot.intelligence.ollama_policy import EntryChoice, ExitChoice, OllamaPaperPolicy


@pytest.mark.asyncio
async def test_ollama_policy_validates_structured_entry_and_exit() -> None:
    replies = iter(
        [
            {"action": "buy", "allocation_percent": 35, "confidence": 72, "reason": "broad demand"},
            {"action": "partial_sell", "sell_percent": 40, "reason": "momentum fading"},
        ]
    )

    def respond(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == "qwen3:14b"
        assert payload["stream"] is False
        assert payload["format"]["type"] == "object"
        for name in ("confidence", "allocation_percent", "sell_percent"):
            if name in payload["format"]["properties"]:
                assert payload["format"]["properties"][name]["type"] == "number"
        return httpx.Response(200, json={"message": {"content": json.dumps(next(replies))}})

    policy = OllamaPaperPolicy("http://localhost:11434", "qwen3:14b")
    await policy.close()
    policy._client = httpx.AsyncClient(
        base_url="http://localhost:11434", transport=httpx.MockTransport(respond)
    )
    try:
        entry = await policy._ask(EntryChoice, {"risk": {"allowed": False}})
        exit_choice = await policy._ask(ExitChoice, {"return_percent": -8})
        assert entry.action == "buy" and entry.allocation_percent == 35
        assert exit_choice.action == "partial_sell" and exit_choice.sell_percent == 40
    finally:
        await policy.close()


@pytest.mark.asyncio
async def test_ollama_policy_rejects_inconsistent_allocation() -> None:
    def respond(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": json.dumps(
                        {
                            "action": "skip",
                            "allocation_percent": 40,
                            "confidence": 80,
                            "reason": "bad data",
                        }
                    )
                }
            },
        )

    policy = OllamaPaperPolicy("http://localhost:11434", "qwen3:14b")
    await policy.close()
    policy._client = httpx.AsyncClient(
        base_url="http://localhost:11434", transport=httpx.MockTransport(respond)
    )
    try:
        with pytest.raises(ValueError, match="inconsistent"):
            await policy._ask(EntryChoice, {})
    finally:
        await policy.close()
