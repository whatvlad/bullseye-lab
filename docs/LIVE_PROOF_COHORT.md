# Bounded live proof cohort

The passive collection retains the unchanged aggressive preset, scoring and serious-candidate constraints. Scope remains standard non-Mayhem Pump.fun, SOL quote and the existing simple fee route. No calibration, order, position, experiment or disagreement-band activation occurs.

Collection is bounded to 1,200 seconds, 64 natural candidate attempts, 512 HTTP reads and 2,000,000 native messages. Each proof retains the 12-read/four-signature/deadline/freshness limits. A refresh consumes the same proof's budget. No candidate is constructed from a failed quality signal to satisfy sample targets.

The machine report `analysis/live_proof_cohort.json` separates additional complete live PASSes, BUY/SELL anchors, unique tokens, fee tiers, latency/request distributions, account age and each refresh's outcome, slot/reserve/quote deltas. Zero-success cohorts have null successful distributions; rejected cost is not used as an estimate of success cost. The previous one-PASS phase remains a separate historical sample.

A complete BUY fixture validates native instruction bounds, gross input, selected protocol/creator fees, net curve input, actual System transfers, canonical destinations, token output and physical pre/post reserves. A fixture or retained partial buy parity sample does not count as a new live BUY PASS.

Final result: 74 natural serious attempts across two bounded captures, 239 actual HTTP reads, zero additional PASSes, zero complete live BUY PASSes and zero new refresh rehearsals. Successful-cohort distributions therefore have N=0 and null mean/median/p90/max. The previous single sell PASS remains a historical point (353.2545 ms, six proof reads plus one refresh), not a representative success distribution.

The first episode stopped on a zero-quote, one-raw-token sell that violated the feature event's positive-amount model: 62 attempts / 199 reads / 875,615 messages. The collector now records such trades as unpriceable native observations, without awarding qualification or stopping the stream. The corrected follow-up handled that dust case and stopped on ConnectionClosedError: 12 attempts / 40 reads / 203,865 messages. Both terminations are recorded separately from market and strategy evidence. No thresholds were lowered to compensate.

Of the 74 rejections, 25 were direct transaction availability failures, two were RPC response errors, and 47 were proof-evidence failures. The latter include 14 excluded complex routes, nine unexplained sell transfer/refund cases, ten unproven native/physical reconstructions, eight bounded history-window failures, two integer curve parity mismatches, three bank/fence synchronization failures and one invalidation during proof. These observed deficits, rather than a shortage of serious candidates, prevented repeatable success.

The collector now limits mutation dispatch to records created by the current notification instead of rescanning all retained history for each transaction. The running cohort's source fingerprints were preserved before that processing optimization; live evidence is attributed to the captured version rather than silently relabeled as a later version.

Read-only calibration readiness requires repeated live proof/refresh success and complete native BUY and SELL paths, with current canonical/config snapshots and bounded measurable costs. Ten PASSes are a preferred sampling goal, not a relaxed candidate threshold. The exact result and unmet checks are recorded in `analysis/proof_cohort_gate.json`. Calibration must not start during this task, even if its readiness checks pass. The runner remains blocked by calibration and downstream gates.
