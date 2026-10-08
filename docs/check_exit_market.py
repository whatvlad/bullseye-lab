import asyncio
import base64
import json
from dataclasses import asdict

import httpx

from memebot.core.config import Settings
from memebot.providers.solana.rpc import JsonRpcSolanaClient
from memebot.providers.solana.pump_idl import decode_bonding_curve_account


async def main():
    settings = Settings()
    for name, endpoint in (("primary", settings.solana_rpc_http_url), ("fallback", settings.solana_exit_rpc_http_url)):
        rpc = JsonRpcSolanaClient(str(endpoint))
        try:
            account = await rpc.get_account("DgtDBqas667dsF5cZQ5HWHCzZCvQMQb8TYrb6t2yKS5Z", "confirmed")
            print(json.dumps({"rpc": name, "slot": account.slot, "owner": account.owner, "curve": asdict(decode_bonding_curve_account(base64.b64decode(account.data_base64)))}))
        except Exception as error:
            print(json.dumps({"rpc": name, "error": type(error).__name__}))
        finally:
            await rpc.close()
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get("https://api.dexscreener.com/token-pairs/v1/solana/8p7uhDVpe5Pw4fg2tfHXskHmCicfr7gTrnbRtzAopump")
        response.raise_for_status()
        print(json.dumps([{key: row.get(key) for key in ("pairAddress", "dexId", "baseToken", "quoteToken", "liquidity")} for row in response.json()]))


asyncio.run(main())
