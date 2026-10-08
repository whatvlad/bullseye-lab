"""Bounded access probe, never a pilot or evidence-window certificate.

The known historical standard mint is only a narrow routing probe. Receiving a
pong proves a live RPC stream, not transaction completeness or an active market.
"""

import argparse
import asyncio
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import grpc
import websockets

from memebot.core.config import Settings
from memebot.providers.solana.canonical import curve_address
from memebot.providers.solana.pump_idl import PUMP_PROGRAM_ID

ROOT = Path(__file__).resolve().parents[1]
MINT = "9FZrgdfLLm7FqYNPVimSvejCdLCC31DWZkM98MqFpump"


def varint(number):
    encoded = bytearray()
    while number >= 128:
        encoded.append((number & 127) | 128)
        number >>= 7
    encoded.append(number)
    return bytes(encoded)


def field(number, value):
    return varint(number * 8 + 2) + varint(len(value)) + value


def request():
    # Official geyser.proto: tx map=3, include=3, required=6, commitment=6.
    tx_filter = b"\x08\x00\x10\x00"
    for account in (MINT, curve_address(MINT)):
        tx_filter += field(3, account.encode())
    tx_filter += field(6, PUMP_PROGRAM_ID.encode())
    entry = field(1, b"access_probe") + field(2, tx_filter)
    return field(3, entry) + b"\x30\x01" + field(9, b"\x08\x01")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verified-dashboard-plan", choices=("FREE", "PAYG"), required=True)
    args = parser.parse_args()
    settings = Settings()
    http = urlsplit(str(settings.solana_rpc_http_url))
    ws_url = str(settings.solana_rpc_ws_url)
    token = http.path.rsplit("/", 1)[-1]
    secrets = [token]
    for url in (str(settings.solana_rpc_http_url), ws_url):
        secrets.extend(v for values in parse_qs(urlsplit(url).query).values() for v in values)

    def clean(value):
        text = str(value)
        for secret in secrets:
            if len(secret) >= 8:
                text = text.replace(secret, "[REDACTED]")
        return re.sub(r"alch_[A-Za-z0-9_-]+", "[REDACTED]", text)

    def failure(error):
        return {"status": error.code().name, "details": clean(error.details())}

    result = {
        "started_at": datetime.now(UTC).isoformat(),
        "runner": "BLOCKED", "calibration_started": False, "orders": 0,
        "purpose": "access_only_not_candidate_pilot",
        "alchemy_dashboard_plan_at_review": args.verified_dashboard_plan,
        "endpoint": "solana-mainnet.streaming.alchemy.com:443",
        "authentication": "X-Token",
        "filter": {"account_include": [MINT, curve_address(MINT)],
                   "account_required": [PUMP_PROGRAM_ID]},
        "complete_for_window": False,
    }
    async with grpc.aio.secure_channel(
        result["endpoint"], grpc.ssl_channel_credentials(),
        options=(("grpc.max_receive_message_length", 2_000_000),),
    ) as channel:
        try:
            reply = await channel.unary_unary("/geyser.Geyser/Ping")(
                b"\x08\x01", metadata=(("x-token", token),), timeout=8)
            result["ping"] = {"accepted": reply == b"\x08\x01", "response_bytes": len(reply)}
        except grpc.aio.AioRpcError as error:
            result["ping"] = {"accepted": False, **failure(error)}

        async def requests():
            yield request()
            await asyncio.sleep(8)

        call = channel.stream_stream("/geyser.Geyser/Subscribe")(
            requests(), metadata=(("x-token", token),), timeout=8)
        try:
            reply = await call.read()
            received = isinstance(reply, bytes)
            result["subscribe"] = {
                "received_update": received,
                "response_bytes": len(reply) if received else 0,
                "subscription_acknowledged": False,
                "note": "Raw update alone is not a decoded transaction or filter acknowledgment.",
            }
            if received:
                from memebot.providers.solana._yellowstone_generated import geyser_pb2
                update = geyser_pb2.SubscribeUpdate.FromString(reply)
                kind = update.WhichOneof("update_oneof")
                acknowledged = kind == "pong" and update.pong.id == 1
                result["subscribe"].update(
                    decoded_update=kind,
                    subscription_acknowledged=acknowledged,
                    note="Matching request-stream pong; no closed-window completeness certificate.")
        except grpc.aio.AioRpcError as error:
            result["subscribe"] = {"received_update": False, **failure(error)}
        finally:
            call.cancel()

    if not result["ping"]["accepted"]:
        # Existing Helius access only; no new account or plan purchase.
        fallback = {"method": "transactionSubscribe", "accepted": False}
        try:
            async with websockets.connect(ws_url, open_timeout=8, max_size=2_000_000) as ws:
                await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1,
                    "method": "transactionSubscribe", "params": [
                        {"accountInclude": result["filter"]["account_include"],
                         "accountRequired": [PUMP_PROGRAM_ID], "vote": False, "failed": False},
                        {"commitment": "confirmed", "encoding": "base64",
                         "transactionDetails": "full", "maxSupportedTransactionVersion": 0}]}))
                raw = await asyncio.wait_for(ws.recv(), 8)
                message = json.loads(raw)
                fallback.update(accepted="result" in message and "error" not in message,
                                response_bytes=len(raw.encode() if isinstance(raw, str) else raw))
                if "error" in message:
                    fallback["error"] = {"code": message["error"].get("code"),
                                         "message": clean(message["error"].get("message", ""))}
        except Exception as error:
            fallback["error_type"] = type(error).__name__
        result["helius_existing_access"] = fallback
    result["finished_at"] = datetime.now(UTC).isoformat()
    name = "filtered_stream_access_probe" + ("_payg" if args.verified_dashboard_plan == "PAYG" else "")
    (ROOT / f"analysis/{name}.json").write_text(
        json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    asyncio.run(main())
