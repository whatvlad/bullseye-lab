# Live continuity anchoring

The old algorithm fetched address histories before the known native transaction and required both indexes to rediscover its signature. That made an eventually consistent index an existence authority.

The revised candidate-only path directly requests the native signature, checks returned signature and slot, reconstructs native instruction/event/physical metadata, and requires the observed event to match. It makes at most three transaction availability probes, separated by 150 ms after null replies, within the unchanged request/deadline cap. Errors remain failures; no unbounded retry is allowed.

Address history discovers successors, cross-checks the direct anchor and fences the bank snapshot. It does not fetch older signatures merely to consume the four-signature allowance. The anchor transaction's independently recorded pre/post physical balances establish its transaction boundary; virtual pre-reserves are reconstructed from the native post-state and trade delta. No predecessor RPC is required for this boundary. Missing successor boundaries, same-slot order ambiguity, missing physical metadata, mismatched inter-transaction reserves, changed fences and terminal account disagreement reject.

A lagging history can be accepted only when the known native sequence terminates at exactly the atomic current curve state, with matching physical inventory and quote offsets. This certifies the stated sequence and current state; it does not assert complete knowledge of every unseen intervening transaction or historical round trip.

The live sell PASS demonstrates this path with the anchor absent from all address-index fences. Direct availability was observed no later than 61.684 ms after candidate receipt. The exact availability instant is interval-censored by polling. In two extended-capture cases, direct lookup remained unavailable through 1,283.037 and 1,255.480 ms respectively; both rejected. Poll observations and bounds are stored in `analysis/live_continuity_lag.json`.

The four older rejects all used absent history anchors as their immediate failure condition. Only the fourth retained an explicit history packet showing the index head two slots behind the native observation. Later successful transaction retrieval cannot prove transaction availability at the original instant. The evidence does not establish that index lag caused a majority of those failures.

PumpSwap-only generation changes no longer cancel standard Pump.fun candidate proofs in the passive collector. Pump.fun config uncertainty and unresolved shared fee-program mutations still invalidate. A receipt invalidated during refresh remains unusable even if that refresh's account bytes are unchanged.
