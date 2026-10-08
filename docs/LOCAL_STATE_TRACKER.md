# Passive local reserve tracker

Implemented in src/memebot/research/reserve_sync.py, with no trading database or order publisher.
For Pump.fun, previous observed post-state plus signed quote/token changes predicts the next
post-state. A mismatch flags missing/other mutation evidence; it never silently declares a
stable price. For PumpSwap, use reported PRE state plus actual instruction quote-vault transfer
and signed base quantity to infer POST. Compare prior inferred post to next reported pre.
Duplicate signature/event pairs do not update state. Regressing slots do not overwrite latest
state. Unknown raw quote transfer yields UNKNOWN reconstructed post, rather than a guessed fee.

Final fresh pilot: 5827 trade events across
465 market keys, but only
2 new-token candidates required account reads. Candidate RPC:
bootstrap then at most once every ten receipt seconds, at most three checks/market and thirty
tokens; fair per-market quotas. The native notification cap of 25,000 stopped the pilot after
21.050s; no automatic reconnect/retry spending.

{'swap_physical_exact': 4627, 'swap_physical_break': 3} for physical AMM reserve continuity. Three full-state continuity
breaks are retained with exact deltas in transaction_reconciliation.json. Five additional native
block reads investigated these gaps: two have intervening native trades absent from the retained
stream capture; one remains UNKNOWN after examining adjacent blocks. This does not locate the
loss at the provider rather than buffering, decoding or collection cutoff. Virtual offsets can
change independently of ordinary trades; unexplained changes stay UNKNOWN. Fee, LP, boost,
deposit/withdraw, migration, direct vault transfers, burn/supply changes and missed messages
can invalidate a trade-only model. coverage_complete stays false. Tracker state is never
declared authoritative or used to open/close a position in this pass.

Future RPC duties: initial identity/reserve bootstrap, periodic reconciliation, anomaly repair,
execution-time refresh and exit recovery. Discovery/event ticks should update local evidence
without an account read each time. No production reconciliation interval is selected.
