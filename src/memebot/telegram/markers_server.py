"""Loopback-only JSON endpoint for the Bullseye chart-markers browser extension.

GET /fills?address=<mint or bonding curve> returns the token's recent paper fills.
No CORS header is sent, so ordinary web pages cannot read it; the extension's
background worker reads it through its host permission.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import parse_qs, urlsplit

from memebot.core.logging import get_logger

_ADDRESS = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")

type MarkerLookup = Callable[[str], Awaitable[dict[str, Any] | None]]


async def start_markers_server(lookup: MarkerLookup, port: int) -> asyncio.Server:
    logger = get_logger("memebot.chart_markers")

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            request = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 5)
            status, body = await respond(request.split(b"\r\n", 1)[0].decode("latin-1"), lookup)
        except (TimeoutError, asyncio.IncompleteReadError, asyncio.LimitOverrunError):
            status, body = "400 Bad Request", {"error": "bad_request"}
        except Exception as error:
            logger.warning("chart_markers_failed", error_type=type(error).__name__)
            status, body = "500 Internal Server Error", {"error": "internal"}
        payload = json.dumps(body).encode()
        writer.write(
            f"HTTP/1.1 {status}\r\nContent-Type: application/json\r\n"
            f"Content-Length: {len(payload)}\r\nCache-Control: no-store\r\n"
            "Connection: close\r\n\r\n".encode()
            + payload
        )
        try:
            await writer.drain()
        finally:
            writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", port)
    logger.info("chart_markers_listening", port=port)
    return server


async def respond(request_line: str, lookup: MarkerLookup) -> tuple[str, dict[str, Any]]:
    parts = request_line.split(" ")
    if len(parts) != 3 or parts[0] != "GET":
        return "405 Method Not Allowed", {"error": "method"}
    url = urlsplit(parts[1])
    if url.path != "/fills":
        return "404 Not Found", {"error": "not_found"}
    address = (parse_qs(url.query).get("address") or [""])[0]
    if not _ADDRESS.match(address):
        return "400 Bad Request", {"error": "address"}
    result = await lookup(address)
    return "200 OK", result or {"mint": None, "fills": [], "open": None}
