"""Pin official upstream schemas and generate local research transport bindings."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import httpx
import grpc_tools

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "src/memebot/providers/solana/_yellowstone_generated"
DEST.mkdir(exist_ok=True)
with httpx.Client(timeout=20, follow_redirects=True) as client:
    response = client.get("https://api.github.com/repos/rpcpool/yellowstone-grpc/commits/master")
    response.raise_for_status()
    commit = response.json()["sha"]
    manifest = {"upstream_commit": commit, "sources": {}}
    for name in ("geyser.proto", "solana-storage.proto"):
        url = f"https://raw.githubusercontent.com/rpcpool/yellowstone-grpc/{commit}/yellowstone-grpc-proto/proto/{name}"
        response = client.get(url)
        response.raise_for_status()
        (DEST / name).write_bytes(response.content)
        manifest["sources"][name] = {"url": url, "sha256": hashlib.sha256(response.content).hexdigest()}
    response = client.get(f"https://raw.githubusercontent.com/rpcpool/yellowstone-grpc/{commit}/LICENSE")
    if response.status_code == 200:
        (DEST / "LICENSE.upstream").write_bytes(response.content)
include = Path(grpc_tools.__file__).parent / "_proto"
subprocess.run([sys.executable, "-m", "grpc_tools.protoc", f"-I{DEST}", f"-I{include}",
    f"--python_out={DEST}", f"--pyi_out={DEST}", str(DEST / "geyser.proto"),
    str(DEST / "solana-storage.proto")], check=True)
generated = DEST / "geyser_pb2.py"
generated.write_text(generated.read_text()
    .replace("import solana_storage_pb2 as", "from . import solana_storage_pb2 as")
    .replace("from solana_storage_pb2 import *", "from .solana_storage_pb2 import *"))
(DEST / "__init__.py").write_text('"""Generated official Yellowstone schemas; see SOURCE.json."""\n')
(DEST / "SOURCE.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps(manifest))
