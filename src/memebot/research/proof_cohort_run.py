"""Bounded passive cohort. No calibration, orders or database writes."""

import argparse
import asyncio

from memebot.core.config import Settings
from memebot.research.candidate_proof_run import CandidateRpc, PassiveCandidateProof
from memebot.research.market_calibration import RequestBudget


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=1200)
    parser.add_argument("--requests", type=int, default=512)
    parser.add_argument("--messages", type=int, default=2_000_000)
    parser.add_argument("--candidates", type=int, default=64)
    parser.add_argument("--output", default="cohort")
    args = parser.parse_args()
    if not (
        0 < args.seconds <= 1200
        and 0 < args.requests <= 512
        and 0 < args.messages <= 2_000_000
        and 0 < args.candidates <= 64
    ):
        parser.error("capture limits exceed reviewed bounds")
    collector = PassiveCandidateProof(Settings())
    await collector.rpc.close()
    collector.rpc = CandidateRpc(
        str(collector.settings.solana_rpc_http_url), RequestBudget(args.requests)
    )
    collector.service.rpc = collector.rpc
    collector.seconds = args.seconds
    collector.native_message_cap = args.messages
    collector.candidate_cap = args.candidates
    collector.output_stem = args.output
    await collector.run_proofs()


if __name__ == "__main__":
    asyncio.run(main())
