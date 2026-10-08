from datetime import UTC, datetime

import pytest

from memebot.providers.solana._yellowstone_generated import geyser_pb2 as proto
from memebot.providers.solana.alchemy_evidence import AlchemyTransactionEvidenceStream, rpc_packet
from memebot.providers.solana.encoding import decode_base58
from memebot.providers.solana.evidence_stream import normalize_transaction
from memebot.providers.solana.pump_idl import PUMP_PROGRAM_ID
from memebot.research.filtered_stream_run import simple_fee_event
from test_candidate_proof import CURVE, MINT, fixture


def executed_update():
    candidate, _, tx, _, _ = fixture()
    tx["meta"]["fee"] = 0
    update = proto.SubscribeUpdate()
    update.transaction.slot = candidate.anchor_slot
    info = update.transaction.transaction
    info.signature = decode_base58(candidate.anchor_signature)
    info.index = 3
    info.transaction.signatures.extend(decode_base58(s) for s in tx["transaction"]["signatures"])
    message = info.transaction.message
    message.account_keys.extend(
        decode_base58(k) for k in tx["transaction"]["message"]["accountKeys"]
    )
    message.recent_blockhash = bytes(32)
    for i in tx["transaction"]["message"]["instructions"]:
        message.instructions.add(
            program_id_index=i["programIdIndex"],
            accounts=bytes(i["accounts"]),
            data=decode_base58(i["data"]),
        )
    meta = info.meta
    meta.fee = tx["meta"]["fee"]
    meta.pre_balances.extend(tx["meta"]["preBalances"])
    meta.post_balances.extend(tx["meta"]["postBalances"])
    meta.log_messages.extend(tx["meta"]["logMessages"])
    for group in tx["meta"]["innerInstructions"]:
        inner = meta.inner_instructions.add(index=group["index"])
        for i in group["instructions"]:
            inner.instructions.add(
                program_id_index=i["programIdIndex"],
                accounts=bytes(i["accounts"]),
                data=decode_base58(i["data"]),
            )
    for source, target in (
        (tx["meta"]["preTokenBalances"], meta.pre_token_balances),
        (tx["meta"]["postTokenBalances"], meta.post_token_balances),
    ):
        for item in source:
            value = target.add(account_index=item["accountIndex"], mint=item["mint"])
            value.ui_token_amount.amount = item["uiTokenAmount"]["amount"]
            value.ui_token_amount.decimals = item["uiTokenAmount"].get("decimals", 6)
    return candidate, tx, update


def test_executed_packet_preserves_native_proof_inputs():
    candidate, tx, update = executed_update()
    converted = rpc_packet(update)
    for key in ("fee", "preBalances", "postBalances", "innerInstructions", "logMessages"):
        assert converted["meta"][key] == tx["meta"][key]
    assert (
        converted["transaction"]["message"]["instructions"]
        == tx["transaction"]["message"]["instructions"]
    )
    evidence = normalize_transaction(
        converted,
        slot=candidate.anchor_slot,
        signature=candidate.anchor_signature,
        index=3,
        source="fixture_not_live",
        commitment="confirmed",
        received_at=datetime.now(UTC),
    )
    assert evidence is not None and evidence.index == 3
    assert simple_fee_event(converted["meta"]["logMessages"], MINT)


@pytest.mark.parametrize("missing", ["transaction", "meta"])
def test_missing_executed_fields_are_rejected(missing):
    _, _, update = executed_update()
    update.transaction.transaction.ClearField(missing)
    with pytest.raises(ValueError, match="missing_executed"):
        rpc_packet(update)


def test_truncated_execution_meta_does_not_become_complete_packet():
    candidate, _, update = executed_update()
    update.transaction.transaction.meta.inner_instructions_none = True
    converted = rpc_packet(update)
    assert (
        normalize_transaction(
            converted,
            slot=candidate.anchor_slot,
            signature=candidate.anchor_signature,
            index=3,
            source="fixture",
            commitment="confirmed",
            received_at=datetime.now(UTC),
        )
        is None
    )


def test_dynamic_filter_update_and_removal_never_enable_global_transactions():
    stream = AlchemyTransactionEvidenceStream("unused")
    stream.update_filter((MINT, CURVE))
    request, revision = stream.updates.get_nowait()
    assert revision == 1 and not request.HasField("ping")
    assert request.transactions["watch_1"].account_include == [MINT, CURVE]
    assert request.transactions["watch_1"].account_required == [PUMP_PROGRAM_ID]
    stream.update_filter(())
    request, revision = stream.updates.get_nowait()
    assert revision == 2 and not request.transactions and not request.HasField("ping")
    with pytest.raises(ValueError, match="narrow"):
        stream.update_filter((PUMP_PROGRAM_ID,))


@pytest.mark.asyncio
async def test_rejected_message_format_retains_complete_provider_packet(monkeypatch):
    import grpc

    _, _, update = executed_update()
    update.transaction.transaction.transaction.message.config.priority_fee = 1
    archived = []

    class Call:
        def __aiter__(self):
            async def packets():
                yield update

            return packets()

        def cancel(self):
            pass

    class Channel:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def unary_unary(self, *args, **kwargs):
            async def ping(*args, **kwargs):
                return proto.PongResponse(count=1)

            return ping

        def stream_stream(self, *args, **kwargs):
            return lambda *args, **kwargs: Call()

    monkeypatch.setattr(grpc.aio, "secure_channel", lambda *args, **kwargs: Channel())
    stream = AlchemyTransactionEvidenceStream("unused", on_packet=archived.append)
    assert [item async for item in stream.transactions()] == []
    assert len(archived) == 1 and archived[0]["raw_protobuf_base64"]
    assert stream.metrics["decoder_rejection_malformed_v1_message"] == 1
    assert stream.metrics["full_packets"] == 1
