"""Offline aggregate audit of console logs; excludes credentials and arbitrary log text."""
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import median


def main():
    reports = []
    for path in sorted(Path('logs').glob('*err.log')):
        rows = []
        for number, line in enumerate(path.read_text(encoding='utf-8-sig', errors='replace').splitlines(), 1):
            match = re.match(r'(\S+)\s+\[\w+\s*\]\s+(\w+)\s+(.*)', line)
            if not match:
                continue
            stamp, event, body = match.groups()
            fields = dict(re.findall(r'(\w+)=([^\s]+)', body))
            rows.append(dict(fields, timestamp=stamp, event=event, line=number))
        orders = [x for x in rows if x['event'] == 'paper_order_completed']
        filled = [x for x in orders if x.get('status') == 'filled']
        closed = [x for x in filled if x.get('position_effect') == 'close']
        subscribed = [x for x in rows if x['event'] == 'pumpportal_candidate_subscribed']
        discovered = {x.get('mint') for x in rows if x['event'] == 'token_discovered'}
        candidates = {x.get('mint') for x in subscribed}
        opened = {}
        matched = []
        for row in filled:
            key = (row.get('portfolio_id'), row.get('mint'))
            if row.get('position_effect') == 'open':
                opened[key] = row
            elif row.get('position_effect') == 'close' and key in opened:
                entry = opened.pop(key)
                seconds = (datetime.fromisoformat(row['timestamp']) - datetime.fromisoformat(entry['timestamp'])).total_seconds()
                matched.append({'mint': key[1], 'seconds_between_log_messages': seconds,
                                'entry_line': entry['line'], 'exit_line': row['line'],
                                'exit_reason': row.get('exit_reason')})
        delay = sorted(float(x['next_candidate_in_seconds']) for x in subscribed if 'next_candidate_in_seconds' in x)
        observation = [x for x in rows if x['event'] == 'pumpportal_candidate_observation_completed']
        report = {'file': str(path), 'parsed_lines': len(rows),
                  'start': rows[0]['timestamp'] if rows else None,
                  'end': rows[-1]['timestamp'] if rows else None,
                  'events': dict(Counter(x['event'] for x in rows)),
                  'discovered_unique': len(discovered), 'subscribed_unique': len(candidates),
                  'subscribed_discovered_intersection': len(candidates & discovered),
                  'candidate_delay_seconds': {'min': min(delay), 'median': median(delay), 'max': max(delay)} if delay else None,
                  'observation_end_reasons': dict(Counter(x.get('reason') for x in observation)),
                  'orders': dict(Counter(f"{x.get('side')}:{x.get('status')}" for x in orders)),
                  'filled_close_reasons': dict(Counter(x.get('exit_reason') for x in closed)),
                  'order_rejections': dict(Counter(x.get('rejection_reason') for x in orders if x.get('status') != 'filled')),
                  'matched_roundtrips': matched,
                  'matched_median_seconds': median(x['seconds_between_log_messages'] for x in matched) if matched else None,
                  'matched_closed_within_10_seconds': sum(x['seconds_between_log_messages'] <= 10 for x in matched),
                  'provider_errors': dict(Counter(x.get('error_code') for x in rows if x['event'] == 'provider_health'))}
        reports.append(report)
        print(json.dumps({k:v for k,v in report.items() if k not in ('events', 'matched_roundtrips')}, indent=2))
    Path('docs/audit-logs-2026-09-13.json').write_text(json.dumps(reports, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
