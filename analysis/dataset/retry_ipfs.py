"""Retry ipfs.io 429s through other public gateways (slower, round-robin)."""
import asyncio
import json
import sys

import httpx

FIELDS = ("twitter", "website", "telegram")

T = json.load(open("data/socials.json"))
L = json.load(open("data/socials_links.json"))
GATEWAYS = ["https://dweb.link/ipfs/", "https://w3s.link/ipfs/", "https://gateway.pinata.cloud/ipfs/",
            "https://ipfs.io/ipfs/"]


async def one(client, sem, i, tid, cid):
    async with sem:
        for attempt in range(len(GATEWAYS)):
            url = GATEWAYS[(i + attempt) % len(GATEWAYS)] + cid
            try:
                r = await client.get(url)
                if r.status_code == 200 and len(r.content) < 65536:
                    data = r.json()
                    L[tid] = {k: str(data.get(k) or "")[:200] for k in FIELDS}
                    L[tid]["has_description"] = bool(str(data.get("description") or "").strip())
                    return
            except Exception:  # noqa: BLE001
                pass
            await asyncio.sleep(0.5)


async def main():
    todo = []
    for tid, v in L.items():
        uri = (T[tid]["meta"] or {}).get("metadata_uri", "")
        if "error" in v and "/ipfs/" in uri:
            todo.append((tid, uri.split("/ipfs/", 1)[1]))
    print("retrying", len(todo), flush=True)
    sem = asyncio.Semaphore(int(sys.argv[1]) if len(sys.argv) > 1 else 12)
    async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
        for start in range(0, len(todo), 1000):
            await asyncio.gather(*(one(client, sem, start + j, tid, cid)
                                   for j, (tid, cid) in enumerate(todo[start:start + 1000])))
            ok = sum(1 for v in L.values() if "error" not in v)
            print("batch", start + 1000, "ok total", ok, flush=True)
            json.dump(L, open("data/socials_links.json", "w"))


asyncio.run(main())
