# Phase 7 outcome recorder

Status: implemented

Phase 7 records results without feeding future information back into entry decisions.
The recorder runs only after an immutable source event has been persisted.

## Decision outcomes

Every strategy decision receives an outcome row, including active, inactive, watch,
skip, rejected, and filled candidates. The row snapshots the decision-time feature,
risk, score decomposition, reasons, lifecycle, market, and price when available.

Subsequent event-time trades record the first observation at or after these horizons:

- 10 and 30 seconds;
- 1 and 2 minutes;
- 5, 10, 30, and 60 minutes.

Each horizon retains its actual observation timestamp and delay. This prevents a late
sample from being silently represented as an exact horizon price. The one-hour window
also records MFE, MAE, post-decision ATH, and ATH time. Lifecycle events independently
record graduation and deterministic `dead_or_illiquid` collapse outcomes.

## Taken trade outcomes

A filled paper buy creates a trade outcome linked to the paper position, entry order,
and originating decision when present. It stores:

- entry reasons and immutable feature/risk/score snapshots;
- expected and simulated entry prices;
- position cost, fees, slippage, and simulated latency;
- highest/lowest observed prices plus MFE and MAE while held;
- final exit price, reason, realized P&L, P&L percentage, and holding time;
- graduation and liquidity-collapse flags.

Partial exits retain the outcome as open. The final close completes it using the
reconciled position P&L.

## Queries

```powershell
bullseye outcome-summary
bullseye decision-outcomes --limit 20
bullseye trade-outcomes --limit 20
```

Telegram exposes the aggregate under **Outcomes**.

## Boundaries

- Outcome prices never create or modify a fill.
- Missing decision-time prices remain unknown; no future price is used as a baseline.
- A provider gap is visible through the recorded observation delay.
- Phase 7 provides research data; it does not optimize strategy parameters itself.
