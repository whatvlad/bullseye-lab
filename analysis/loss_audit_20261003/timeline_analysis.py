"""Descriptive retained-event coverage; it does not certify provider completeness."""
from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal as D
import json
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent


def ts(value):
    return datetime.fromisoformat(value)


def percentile(values, fraction):
    return sorted(values)[int((len(values)-1)*fraction)] if values else None


def raw_price(row):
    # Diagnostic native event reserve ratio only, never relabeled an executable quote.
    return (D(row['virtual_quote_reserves'])/D(row['virtual_token_reserves'])
            if row['virtual_token_reserves'] and row['virtual_quote_reserves'] else None)


def main():
    source = json.loads((ROOT/'retained_timelines.json').read_text(encoding='utf-8'))
    report = []
    for timeline in source['timelines']:
        start, end = ts(timeline['entry_at']), ts(timeline['exit_at'])
        rows = sorted([row for row in timeline['retained_events'] if start <= ts(row['source_event_at']) <= end],
                      key=lambda row: (ts(row['source_event_at']), row['source_slot'] or 0,
                                       ts(row['provider_received_at'] or row['ingested_at']), row['event_id']))
        observed = sorted({ts(row['source_event_at']) for row in rows})
        gaps = [(b-a).total_seconds() for a,b in zip([start, *observed], [*observed, end])]
        received = sorted({ts(row['provider_received_at']) for row in rows if row['provider_received_at']})
        receives_gaps = [(b-a).total_seconds() for a,b in zip(received, received[1:])]
        decode_delay = [(ts(row['ingested_at'])-ts(row['provider_received_at'])).total_seconds()
                        for row in rows if row['provider_received_at']]
        states = Counter((row['normalized_state'] or {}).get('continuity_status', 'MISSING') for row in rows)
        largest_drop = None
        prices = [(row,raw_price(row)) for row in rows]
        for (previous,a),(current,b) in zip(prices,prices[1:]):
            if a and b:
                change = (b/a-1)*100
                if largest_drop is None or change < D(largest_drop['raw_reserve_change_pct']):
                    largest_drop = {'raw_reserve_change_pct': str(change),
                        'source_delta_seconds': (ts(current['source_event_at'])-ts(previous['source_event_at'])).total_seconds(),
                        'source_before': previous['source_event_at'], 'source_after': current['source_event_at'],
                        'received_before': previous['provider_received_at'], 'received_after': current['provider_received_at'],
                        'ingested_after': current['ingested_at'],
                        'previous_state': previous['normalized_state'], 'next_state': current['normalized_state']}
        item = {'cohort': timeline['cohort'], 'mint': timeline['mint'], 'trade_rows_while_open': len(rows),
                'record_limit_reached': timeline['record_limit_reached'], 'max_source_gap_seconds_including_edges': max(gaps),
                'max_received_gap_seconds_excluding_edges': max(receives_gaps) if receives_gaps else None,
                'received_to_ingested_median_seconds': median(decode_delay) if decode_delay else None,
                'received_to_ingested_p95_seconds': percentile(decode_delay, .95),
                'received_to_ingested_max_seconds': max(decode_delay) if decode_delay else None,
                'continuity_counts': dict(states), 'largest_adjacent_raw_reserve_drop': largest_drop,
                'last_5_seconds_rows': [{k:row[k] for k in ('source_event_at', 'provider_received_at', 'ingested_at',
                                             'source_slot', 'side', 'quote_amount_raw', 'virtual_quote_reserves', 'virtual_token_reserves')}
                                        for row in rows if ts(row['source_event_at']) >= end.replace(microsecond=0)-timedelta(seconds=5)]}
        report.append(item)
    (ROOT/'timeline_findings.json').write_text(json.dumps({'positions': report,
        'caveat': 'Retained event quiet periods do not prove feed outage or provider completeness. Same-slot transaction ordering is not proven. Raw unknown-continuity ratios and adjacent changes are diagnostic only.'}, indent=2), encoding='utf-8')
    for item in report:
        drop = item['largest_adjacent_raw_reserve_drop']
        print(json.dumps({key:item[key] for key in ('cohort', 'mint', 'trade_rows_while_open', 'max_source_gap_seconds_including_edges',
                        'max_received_gap_seconds_excluding_edges', 'received_to_ingested_max_seconds', 'continuity_counts')}
                         | {'largest_drop_pct': drop['raw_reserve_change_pct'] if drop else None,
                            'drop_source_delta_s': drop['source_delta_seconds'] if drop else None}))


if __name__ == '__main__':
    main()
