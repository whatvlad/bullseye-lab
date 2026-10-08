"""One existing-endpoint handshake; only non-secret status evidence is printed."""
import asyncio
import json
from urllib.parse import urlparse, urlsplit, urlunsplit
from websockets.asyncio.client import connect
from memebot.core.config import Settings

async def main():
    settings = Settings(pumpportal_api_key=None)
    result = {"host": urlparse(str(settings.solana_rpc_ws_url)).hostname}
    parsed = urlsplit(str(settings.solana_rpc_http_url))
    alternate = urlunsplit(("wss", parsed.netloc, parsed.path, parsed.query, ""))
    for label, url in (("configured_ws", str(settings.solana_rpc_ws_url)), ("existing_primary_rpc_ws", alternate)):
        result = {"endpoint_role": label, "host": urlparse(url).hostname}
        try:
            async with connect(url, open_timeout=10) as socket:
                await socket.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "logsSubscribe", "params": [{"mentions": ["So11111111111111111111111111111111111111112"]}, {"commitment": "confirmed"}]}))
                response = json.loads(await asyncio.wait_for(socket.recv(), 10))
                result.update(status="SUBSCRIPTION_ACK" if isinstance(response.get("result"), int) else "REJECTED", rpc_error_code=(response.get("error") or {}).get("code"))
        except Exception as error:
            result.update(error_type=type(error).__name__)
            response = getattr(error, "response", None)
            if response is not None:
                result["http_status"] = response.status_code
        print(json.dumps(result))

asyncio.run(main())
