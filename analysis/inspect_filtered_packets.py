"""Ten-second packet-format diagnosis on the last natural serious candidate.

No discovery, retrospective reads, proof attempts or account enrichment.
"""
import asyncio
import base64
from collections import Counter
import json
from pathlib import Path
from urllib.parse import urlsplit

import grpc

from memebot.core.config import Settings
from memebot.providers.solana._yellowstone_generated import geyser_pb2 as proto
from memebot.providers.solana.alchemy_evidence import rpc_packet
from memebot.providers.solana.canonical import curve_address
from memebot.providers.solana.pump_idl import PUMP_PROGRAM_ID

ROOT = Path(__file__).resolve().parents[1]


async def main():
    report = json.loads((ROOT / "analysis/filtered_stream_pilot.json").read_text())
    mint = report["pairs"][-1]["mint"]
    token = urlsplit(str(Settings().solana_rpc_http_url)).path.rsplit("/", 1)[-1]
    counts = Counter()
    packets = []
    async with grpc.aio.secure_channel("solana-mainnet.streaming.alchemy.com:443", grpc.ssl_channel_credentials()) as channel:
        async def requests():
            request = proto.SubscribeRequest(commitment=proto.CONFIRMED)
            request.transactions["diagnosis"].CopyFrom(proto.SubscribeRequestFilterTransactions(
                vote=False, failed=False, account_include=[mint, curve_address(mint)], account_required=[PUMP_PROGRAM_ID]))
            yield request
            await asyncio.sleep(10)
        call = channel.stream_stream("/geyser.Geyser/Subscribe", request_serializer=proto.SubscribeRequest.SerializeToString,
            response_deserializer=proto.SubscribeUpdate.FromString)(requests(), metadata=(("x-token", token),), timeout=10)
        try:
            async for update in call:
                counts["decoded_protobuf_bytes"] += update.ByteSize()
                if counts["decoded_protobuf_bytes"] > 500_000:
                    break
                if update.WhichOneof("update_oneof") != "transaction":
                    continue
                info = update.transaction.transaction
                counts["packets"] += 1
                record = {"protobuf": base64.b64encode(update.SerializeToString()).decode(),
                          "has_transaction": info.HasField("transaction"), "has_meta": info.HasField("meta"),
                          "message_config_present": info.transaction.message.HasField("config")}
                try:
                    record["packet"] = rpc_packet(update)
                    counts["converted"] += 1
                except ValueError as error:
                    record["rejection"] = str(error)
                    counts[str(error)] += 1
                packets.append(record)
        except grpc.aio.AioRpcError as error:
            counts[error.code().name] += 1
        finally:
            call.cancel()
    result = {"runner": "BLOCKED", "orders": 0, "rpc_reads": 0, "purpose": "packet_format_diagnosis_not_pilot",
              "mint": mint, "counts": dict(counts), "packets": packets}
    (ROOT / "analysis/filtered_packet_diagnosis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "packets"}))


asyncio.run(main())
