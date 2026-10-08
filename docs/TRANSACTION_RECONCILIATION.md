# Transaction reconciliation — partial methodology validation

Matched 21 original stream snapshots to native signatures by exact
market/reserve fields, retaining transaction slot, block transaction index, event ordinal and
instruction index where proven. The historical native metadata supports {'POST_TRADE': 18, 'UNKNOWN': 2, 'PRE_TRADE': 1}.
Pump.fun quote and token account deltas corroborate post-trade observations; inferred rent and
reserved-inventory offsets are disclosed and not independently bootstrapped. Multi-event
transactions require instruction-level reconstruction; whole-transaction balances alone do
not identify intermediate states. PumpSwap's two-buy maximum provides that reconstruction:
first event pre→second event pre→final native vault balances, with exact actual quote transfers.

Use the raw event's quote_amount_in_with_lp_fee (buy) or quote_amount_out_without_lp_fee (sell)
for vault movement. Gross quote_amount may differ substantially from that transfer; gross
budget plus an assumed LP fee is not equivalent. Existing pinned event decoding discards
those fields; the research decoder now captures them from the verified prefix without
changing production event classes or strategy settings.

The five synchronization classes are TRANSACTION_CORRELATED, STATE_SEQUENCE_RECONCILED,
SLOT_ONLY, RECEIPT_ONLY, UNSYNCHRONIZED. Only the first two are potentially eligible to
calibrate thresholds, and they still require verified identity, matching state boundary and
complete relevant mutations. Correlating the stream event to its transaction does NOT promote
the original later RPC comparison. All 180 original pairs remain SLOT_ONLY and ineligible.
There are zero validated simultaneous stream/RPC calibration residuals in this phase.
Finding a native event that exactly matches a later RPC state supports state evolution;
post-selecting such matches cannot produce a representative zero-disagreement distribution.

The fresh passive pilot captures signatures and log order, but confirmed-stream receipt order
does not prove block transaction order for every event. Its periodic RPC checks remain
SLOT_ONLY. Native snapshots also have virtual liquidity and token inventory distinct from
withdrawable vault balances. Pump.fun and PumpSwap statistics remain separate in
reconciliation_distribution.json. No disagreement bands or entry safety limit were set.
