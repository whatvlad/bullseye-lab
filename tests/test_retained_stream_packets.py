import base64
import hashlib
import json
from datetime import datetime
from pathlib import Path

import pytest

from memebot.providers.solana._yellowstone_generated import geyser_pb2 as proto
from memebot.providers.solana.alchemy_evidence import rpc_packet
from memebot.research.packet_forensics import inspect_packet

FIXTURES = Path(__file__).parent / "fixtures" / "early_watch"


def retained(name):
    row = json.loads((FIXTURES / f"{name}.json").read_text())
    raw = base64.b64decode(row["raw_protobuf_base64"], validate=True)
    assert hashlib.sha256(raw).hexdigest() == row["sha256"]
    return proto.SubscribeUpdate.FromString(raw), datetime.fromisoformat(row["received_timestamp"])


@pytest.mark.parametrize("name", ["v1", "legacy_v0"])
def test_retained_executed_packet_preserves_complete_native_inputs(name):
    update, at = retained(name)
    result = inspect_packet(update, at)
    assert result["category"] == "USABLE"
    packet = rpc_packet(update)
    meta = update.transaction.transaction.meta
    assert packet["meta"]["preBalances"] == list(meta.pre_balances)
    assert packet["meta"]["postBalances"] == list(meta.post_balances)
    assert packet["meta"]["logMessages"] == list(meta.log_messages)
    assert len(packet["meta"]["innerInstructions"]) == len(meta.inner_instructions)
    if name == "v1":
        assert packet["version"] == 1
        assert packet["transaction"]["message"]["transactionConfig"]["priority_fee"] == 1000


@pytest.mark.parametrize("damage", ["signature", "config", "instruction", "lookup", "missing_meta"])
def test_v1_damage_never_becomes_valid_evidence(damage):
    update, at = retained("v1")
    info = update.transaction.transaction
    if damage == "signature":
        info.transaction.signatures[0] = bytes(64)
    elif damage == "config":
        info.transaction.message.config.priority_fee += 1
    elif damage == "instruction":
        info.transaction.message.instructions[0].data += b"\x00"
    elif damage == "lookup":
        info.transaction.message.address_table_lookups.add(account_key=bytes(32))
    else:
        info.ClearField("meta")
    with pytest.raises(ValueError):
        rpc_packet(update)
    assert inspect_packet(update, at)["usable"] is False
