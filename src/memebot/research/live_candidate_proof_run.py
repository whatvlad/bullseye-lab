"""Ten-minute passive capture, unchanged qualification and request/message caps."""

import asyncio

from memebot.core.config import Settings
from memebot.research.candidate_proof_run import PassiveCandidateProof


async def main() -> None:
    collector = PassiveCandidateProof(Settings())
    collector.seconds = 600
    collector.native_message_cap = 600000
    collector.output_stem = "live"
    await collector.run_proofs()


if __name__ == "__main__":
    asyncio.run(main())
