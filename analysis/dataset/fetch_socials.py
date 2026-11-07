"""Fetch each token's off-chain metadata JSON (public URI from its mint) and keep only social links.

Read-only GETs, 64 KB cap, short timeouts. Output: data/socials_links.json {token_id: {...}}.
"""
import asyncio
import json
import sys

import httpx

IN, OUT = sys.argv[1], sys.argv[2]
FIELDS = ("twitter", "website", "telegram")


def gateway(uri: str) -> str:
    if uri.startswith("ipfs://"):
        return "https://ipfs.io/ipfs/" + uri[7:]
    return uri


async def one(client, sem, token_id, uri, out):
    async with sem:
        try:
            async with client.stream("GET", gateway(uri)) as response:
                if response.status_code != 200:
                    out[token_id] = {"error": response.status_code}
                    return
                body = b""
                async for chunk in response.aiter_bytes():
                    body += chunk
                    if len(body) > 65536:
                        break
            data = json.loads(body)
            links = {k: str(data.get(k) or "")[:200] for k in FIELDS}
            links["has_description"] = bool(str(data.get("description") or "").strip())
            out[token_id] = links
        except Exception as error:  # noqa: BLE001 - research script; record and move on
            out[token_id] = {"error": type(error).__name__}


async def main():
    tokens = json.load(open(IN))
    out: dict = {}
    sem = asyncio.Semaphore(40)
    async with httpx.AsyncClient(timeout=6, follow_redirects=True) as client:
        jobs = [one(client, sem, tid, (v["meta"] or {}).get("metadata_uri") or "", out)
                for tid, v in tokens.items() if (v["meta"] or {}).get("metadata_uri")]
        for i in range(0, len(jobs), 2000):
            await asyncio.gather(*jobs[i:i + 2000])
            print("done", min(i + 2000, len(jobs)), "of", len(jobs), flush=True)
    json.dump(out, open(OUT, "w"))
    ok = [v for v in out.values() if "error" not in v]
    print("fetched", len(ok), "errors", len(out) - len(ok))
    for k in FIELDS:
        print(k, sum(1 for v in ok if v.get(k)))


asyncio.run(main())
