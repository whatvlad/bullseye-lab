"""Run one SQL query on Dune and save the result as CSV (research only; read-only on our side).

The key is read from DUNE_API_KEY in .env and is never printed.

Usage:
  .venv\\Scripts\\python.exe analysis\\dune_pull.py path\\to\\query.sql analysis\\dune\\out.csv [--performance medium]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.dune.com/api/v1"


def api_key() -> str:
    for raw in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("DUNE_API_KEY="):
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            if value:
                return value
    sys.exit("DUNE_API_KEY is missing in .env")


def call(method: str, path: str, key: str, body: dict | None = None) -> dict:
    request = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"X-Dune-Api-Key": key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        # The body is Dune's error message; it never contains our key.
        sys.exit(f"Dune {method} {path} -> HTTP {error.code}: {error.read()[:500]!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("sql_file")
    parser.add_argument("out_csv")
    parser.add_argument("--performance", default="medium", choices=["medium", "large"])
    parser.add_argument("--name", default="bullseye research pull")
    args = parser.parse_args()
    key = api_key()
    sql = Path(args.sql_file).read_text(encoding="utf-8")

    query_id = call("POST", "/query", key, {"name": args.name, "query_sql": sql, "is_private": True})[
        "query_id"
    ]
    execution = call("POST", f"/query/{query_id}/execute", key, {"performance": args.performance})
    execution_id = execution["execution_id"]
    print(f"query {query_id}, execution {execution_id}", flush=True)
    while True:
        status = call("GET", f"/execution/{execution_id}/status", key)
        state = status.get("state")
        if state == "QUERY_STATE_COMPLETED":
            break
        if state in {"QUERY_STATE_FAILED", "QUERY_STATE_CANCELLED", "QUERY_STATE_EXPIRED"}:
            sys.exit(f"execution {state}: {json.dumps(status.get('error'))[:800]}")
        time.sleep(5)
    print("cost:", {k: status.get(k) for k in ("execution_cost_credits", "result_metadata")}, flush=True)

    out = Path(args.out_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    offset, writer, rows = 0, None, 0
    with out.open("w", newline="", encoding="utf-8") as handle:
        while True:
            page = call("GET", f"/execution/{execution_id}/results?limit=10000&offset={offset}", key)
            result = page.get("result") or {}
            batch = result.get("rows") or []
            if writer is None:
                columns = (result.get("metadata") or {}).get("column_names") or (
                    list(batch[0].keys()) if batch else []
                )
                writer = csv.DictWriter(handle, fieldnames=columns)
                writer.writeheader()
            writer.writerows(batch)
            rows += len(batch)
            if not page.get("next_offset"):
                break
            offset = page["next_offset"]
    print(f"saved {rows} rows to {out}")


if __name__ == "__main__":
    main()
