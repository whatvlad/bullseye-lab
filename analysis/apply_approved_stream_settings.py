"""Apply only the user-approved stream allowance and diagnosed heartbeat settings."""
from pathlib import Path

path = Path('.env')
original = path.read_text(encoding='utf-8-sig')
updates = {
    'BULLSEYE_SOLANA_EXECUTED_STREAM_HOURLY_BYTES': '128000000',
    'BULLSEYE_SOLANA_WS_PING_TIMEOUT_SECONDS': '60',
    'BULLSEYE_SOLANA_WS_IDLE_TIMEOUT_SECONDS': '20',
}
lines = []
seen = set()
for line in original.splitlines():
    key = line.split('=', 1)[0].strip()
    if key in updates:
        lines.append(f'{key}={updates[key]}')
        seen.add(key)
    else:
        lines.append(line)
for key, value in updates.items():
    if key not in seen:
        lines.append(f'{key}={value}')
path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('Applied approved 128000000 bytes/hour; ping 60s; independent idle timeout 20s.')
