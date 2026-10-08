"""Pinned official schemas for account bootstrap and invalidation attribution."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .encoding import BorshDecodeError, BorshReader

SCHEMAS = {
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P": (
        "pump",
        "ffe966c42f1af41652ee753fe2f1e3f7cd4077d7e6f49faf3138959c8b56064b",
    ),
    "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA": (
        "pump_amm",
        "2091433899b07d003d98118ae6cd3c628960fd393b40710b6e15bce6d0e7f2d1",
    ),
    "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ": (
        "pump_fees",
        "d87b52305fd6b2ec487d4ba1e08a49990c23fa9b8b76092b2097df0164fa3859",
    ),
}


@lru_cache(maxsize=3)
def schema(program: str) -> dict[str, Any]:
    name, expected = SCHEMAS[program]
    raw = (Path(__file__).with_name("idl") / f"{name}.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise BorshDecodeError("unapproved IDL schema version")
    result: dict[str, Any] = json.loads(raw)
    return result


def decode_type(program: str, kind: Any, reader: BorshReader, depth: int = 0) -> Any:
    if depth > 16:
        raise BorshDecodeError("recursive type limit")
    if isinstance(kind, str):
        if kind == "pubkey":
            return reader.pubkey()
        if kind == "bool":
            return reader.boolean()
        if kind == "string":
            return reader.string()
        if kind in {"u8", "u16", "u32", "u64", "u128", "i64", "i128"}:
            return int.from_bytes(reader._read(int(kind[1:]) // 8), "little", signed=kind[0] == "i")
    if isinstance(kind, dict):
        if "defined" in kind:
            name = kind["defined"]["name"]
            definition = next(t["type"] for t in schema(program)["types"] if t["name"] == name)
            if definition["kind"] != "struct":
                raise BorshDecodeError("unsupported IDL enum")
            return {
                field["name"]: decode_type(program, field["type"], reader, depth + 1)
                for field in definition["fields"]
            }
        if "array" in kind or "vec" in kind:
            item, size = kind["array"] if "array" in kind else (kind["vec"], reader.u32())
            if size > 1024:
                raise BorshDecodeError("vector length exceeds safety cap")
            return [decode_type(program, item, reader, depth + 1) for _ in range(size)]
        if "option" in kind:
            return (
                decode_type(program, kind["option"], reader, depth + 1)
                if reader.boolean()
                else None
            )
    raise BorshDecodeError("unsupported IDL type")


def decode_record(
    program: str, data: bytes, *, collection: str, name: str | None = None
) -> tuple[str, dict[str, Any]]:
    record = next(
        (
            r
            for r in schema(program)[collection]
            if bytes(r["discriminator"]) == data[:8] and (name is None or r["name"] == name)
        ),
        None,
    )
    if record is None:
        raise BorshDecodeError("unknown IDL discriminator")
    values = decode_type(program, {"defined": {"name": record["name"]}}, BorshReader(data[8:]))
    if not isinstance(values, dict):
        raise BorshDecodeError("record not a struct")
    return record["name"], values


@lru_cache(maxsize=512)
def instruction_schema(program: str, name: str) -> dict[str, Any] | None:
    return next(
        (
            ix
            for ix in schema(program)["instructions"]
            if "".join(word.title() for word in ix["name"].split("_")) == name
        ),
        None,
    )
