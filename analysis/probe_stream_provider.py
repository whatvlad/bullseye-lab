"""Read-only capability probe; endpoints/credentials never enter output."""
import asyncio
import importlib.util
import json
from pathlib import Path
from urllib.parse import urlsplit

import websockets

from memebot.core.config import Settings
from memebot.providers.solana.pump_idl import PUMP_PROGRAM_ID


async def main():
    settings = Settings()
    result = {"provider": "helius", "method": "transactionSubscribe", "orders": 0}
    try:
        async with websockets.connect(str(settings.solana_rpc_ws_url), open_timeout=8) as ws:
            await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1,
                "method": "transactionSubscribe", "params": [
                    {"accountInclude": [PUMP_PROGRAM_ID], "vote": False, "failed": False},
                    {"commitment": "confirmed", "encoding": "base64",
                     "transactionDetails": "full", "maxSupportedTransactionVersion": 0}]}))
            raw = await asyncio.wait_for(ws.recv(), 8)
            message = json.loads(raw)
            result["accepted"] = "result" in message and "error" not in message
            result["error_code"] = message.get("error", {}).get("code")
            error_text = message.get("error", {}).get("message", "").lower()
            result["error_terms"] = [term for term in
                ("plan", "upgrade", "not available", "unsupported", "invalid", "paid", "enhanced")
                if term in error_text]
            result["response_bytes"] = len(raw)
    except Exception as error:
        result["error_type"] = type(error).__name__
    result["grpc_runtime_installed"] = importlib.util.find_spec("grpc") is not None
    result["h2_runtime_installed"] = importlib.util.find_spec("h2") is not None
    if result["grpc_runtime_installed"]:
        import grpc
        token = urlsplit(str(settings.solana_rpc_http_url)).path.rsplit("/", 1)[-1]
        async with grpc.aio.secure_channel(
            "solana-mainnet.streaming.alchemy.com:443", grpc.ssl_channel_credentials()
        ) as channel:
            try:
                call = channel.unary_unary("/geyser.Geyser/Ping")
                reply = await call(b"\x08\x01", metadata=(("x-token", token),), timeout=8)
                result["alchemy_grpc"] = {"accepted": True, "response_bytes": len(reply)}
            except grpc.aio.AioRpcError as error:
                result["alchemy_grpc"] = {"accepted": False, "status": error.code().name}
            # Small wire-format request follows the official geyser.proto fields:
            # transactions map=3; filter account_include=3; commitment=6.
            pump = PUMP_PROGRAM_ID.encode()
            tx_filter = b"\x08\x00\x10\x00\x1a" + bytes([len(pump)]) + pump
            entry = b"\x0a\x04pump\x12" + bytes([len(tx_filter)]) + tx_filter
            request = b"\x1a" + bytes([len(entry)]) + entry + b"\x30\x01"
            async def requests():
                yield request
                await asyncio.sleep(8)
            call = channel.stream_stream("/geyser.Geyser/Subscribe")(
                requests(), metadata=(("x-token", token),), timeout=8)
            try:
                reply = await call.read()
                result["alchemy_subscribe"] = {"received_update": True,
                    "response_bytes": len(reply)}
            except grpc.aio.AioRpcError as error:
                result["alchemy_subscribe"] = {"received_update": False,
                    "status": error.code().name}
            finally:
                call.cancel()
    Path("analysis/stream_provider_probe.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result))


asyncio.run(main())
