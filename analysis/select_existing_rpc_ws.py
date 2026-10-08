"""Select the acknowledged WSS of the already configured RPC; never print keys."""
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from memebot.core.config import Settings

settings = Settings()
parsed = urlsplit(str(settings.solana_rpc_http_url))
assert parsed.hostname == "solana-mainnet.g.alchemy.com"
value = urlunsplit(("wss", parsed.netloc, parsed.path, parsed.query, ""))
path = Path(".env")
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
matches = [i for i, line in enumerate(lines) if line.strip().startswith("BULLSEYE_SOLANA_RPC_WS_URL=")]
assert len(matches) == 1
lines[matches[0]] = "BULLSEYE_SOLANA_RPC_WS_URL=" + value + "\n"
path.write_text("".join(lines), encoding="utf-8")
print("Native WSS now uses the acknowledged existing Alchemy RPC. Thresholds and API budgets unchanged; credentials omitted.")
