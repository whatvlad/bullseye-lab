import base64
import json
import struct
from collections import Counter
from pathlib import Path
from solders.hash import Hash
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.instruction import CompiledInstruction
from solders.message import Message, MessageV0, MessageHeader, MessageAddressTableLookup
from solders.transaction import VersionedTransaction
from memebot.providers.solana._yellowstone_generated import geyser_pb2 as proto

counts = Counter()
examples = []
for line in Path('analysis/early_watch_8_packets.jsonl').read_text().splitlines():
    row = json.loads(line)
    if row.get('record_kind') != 'provider_protobuf':
        continue
    update = proto.SubscribeUpdate.FromString(base64.b64decode(row['raw_protobuf_base64']))
    tx = update.transaction.transaction.transaction
    m = tx.message
    if not m.HasField('config'):
        continue
    keys = [Pubkey.from_bytes(k) for k in m.account_keys]
    instructions = [CompiledInstruction(i.program_id_index, i.data, i.accounts) for i in m.instructions]
    h = m.header
    if m.versioned:
        message = MessageV0(MessageHeader(h.num_required_signatures, h.num_readonly_signed_accounts, h.num_readonly_unsigned_accounts), keys, Hash.from_bytes(m.recent_blockhash), instructions, [MessageAddressTableLookup(Pubkey.from_bytes(a.account_key), a.writable_indexes, a.readonly_indexes) for a in m.address_table_lookups])
    else:
        message = Message.new_with_compiled_instructions(h.num_required_signatures, h.num_readonly_signed_accounts, h.num_readonly_unsigned_accounts, keys, Hash.from_bytes(m.recent_blockhash), instructions)
    try:
        signed = VersionedTransaction.populate(message, [Signature.from_bytes(s) for s in tx.signatures])
        signed.verify_and_hash_message()
        outcome = 'VALID_V0' if m.versioned else 'VALID_LEGACY'
    except Exception as error:
        outcome = type(error).__name__ + ':' + str(error)
    config = m.config
    mask = 0
    values = b''
    for name, bits, fmt in [('priority_fee', 3, '<Q'), ('compute_unit_limit', 4, '<I'), ('loaded_accounts_data_size_limit', 8, '<I'), ('heap_size', 16, '<I')]:
        if config.HasField(name):
            mask |= bits
            values += struct.pack(fmt, getattr(config, name))
    raw_v1 = bytes([129, h.num_required_signatures, h.num_readonly_signed_accounts, h.num_readonly_unsigned_accounts]) + struct.pack('<I', mask) + m.recent_blockhash + bytes([len(m.instructions), len(keys)]) + b''.join(m.account_keys) + values
    raw_v1 += b''.join(struct.pack('<BBH', i.program_id_index, len(i.accounts), len(i.data)) for i in m.instructions)
    raw_v1 += b''.join(i.accounts + i.data for i in m.instructions)
    if all(Signature.from_bytes(s).verify(keys[n], raw_v1) for n, s in enumerate(tx.signatures)):
        outcome = 'VALID_SIGNED_V1'
    counts[outcome] += 1
    if len(examples) < 3:
        examples.append({'signature':row['signature'], 'config': str(m.config), 'versioned':m.versioned, 'outcome':outcome})
print(json.dumps({'counts':dict(counts), 'examples':examples}, indent=2))
