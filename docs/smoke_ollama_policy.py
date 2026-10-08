"""Read-only local Ollama check; never opens a paper or live order."""

from __future__ import annotations

import asyncio

from memebot.core.config import Settings
from memebot.intelligence.ollama_policy import EntryChoice, ExitChoice, OllamaPaperPolicy


async def main() -> None:
    settings = Settings()
    if not settings.ollama_model:
        raise SystemExit("BULLSEYE_OLLAMA_MODEL is unset")
    policy = OllamaPaperPolicy(
        str(settings.ollama_base_url),
        settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
    )
    try:
        await policy.warmup()
        entry_choice = await policy._ask(
            EntryChoice,
            {"task": "JSON protocol check only. No token or market facts are available."},
        )
        exit_choice = await policy._ask(
            ExitChoice,
            {"task": "JSON protocol check only. No position or market facts are available."},
        )
        print("entry:", entry_choice.model_dump_json())
        print("exit:", exit_choice.model_dump_json())
    finally:
        await policy.close()


if __name__ == "__main__":
    asyncio.run(main())
