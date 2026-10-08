"""Bounded Alchemy endpoint comparison using slot-only subscriptions."""
import asyncio
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from websockets.asyncio.client import connect

from memebot.core.config import Settings
from memebot.providers.solana.pump import PumpDiscoveryProvider


async def probe(url):
    result = {'host': urlsplit(url).hostname, 'messages': 0, 'bytes': 0, 'pings': []}
    started = asyncio.get_running_loop().time()
    try:
        async with asyncio.timeout(185), connect(url, ping_interval=20, ping_timeout=20, close_timeout=2) as ws:
            await ws.send(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'slotSubscribe'}))
            async for raw in ws:
                result['messages'] += 1
                result['bytes'] += len(raw)
                if result['messages'] % 100 == 0:
                    result['pings'].append(ws.latency)
    except TimeoutError:
        result['status'] = 'bounded_complete'
    except Exception as error:
        result['status'] = type(error).__name__
        result.update(PumpDiscoveryProvider._close_diagnostics(error))
    result['seconds'] = round(asyncio.get_running_loop().time() - started, 2)
    return result


async def main():
    settings = Settings()
    url = str(settings.solana_rpc_ws_url)
    parts = urlsplit(url)
    assert parts.hostname in {'solana-mainnet.g.alchemy.com', 'solana-mainnet.streaming.alchemy.com'}
    streaming = urlunsplit(parts._replace(netloc='solana-mainnet.streaming.alchemy.com'))
    results = await asyncio.gather(*(probe(u) for u in dict.fromkeys([url, streaming])))
    Path('analysis/ws_health_comparison.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(results))


asyncio.run(main())
