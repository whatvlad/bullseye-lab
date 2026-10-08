# Candidate proof cost

Two 120-second bounded passive captures observed **84 Pump launches**, of which
72 had an explicit standard mode. Only nine serious standard candidates incurred
proof work. No excluded market caused a deep proof read; observation used native
subscriptions and local arithmetic/features. Native subscription delivery still
has provider cost; no invoice/CU price was inferred.

| Measurement | Average | Median | p90 | Max |
|---|---:|---:|---:|---:|
| RPC requests per proof attempt | 2.444 | 2 | 3 | 3 |
| Active proof latency, ms | 274.783 | 262.818 | 381.954 | 381.954 |

All measured attempts rejected: five `FAIL_FEE` and four `FAIL_CONTINUITY`.
These costs describe **early rejected attempts**, not the expected cost of a
successful complete proof. There were no live successes to estimate that cost.
No percentile is presented as a permanent threshold or a disagreement band.

Total requests: **22**. Nine `getMultipleAccounts` calls served identity/config
roles together; thirteen address-history calls served the bounded continuity check.
There were **zero getTransaction/getBlock calls** and zero live execution refreshes.
Identity reads = 9 and config reads = 9 describe the same nine batches and must
not be added together. Per-candidate duties, rejected costs and timestamps are
retained in `analysis/candidate_proof_cost.json`.

The implemented successful path costs one atomic identity/config batch, four
history-fence requests and up to four relevant transaction reads: **6–9 proof
requests**, followed by **one execution refresh** if approved and still fresh.
This is a structural bound, not a live success measurement. Overall per-candidate
request cap is 12 including refresh; signature cap is four and deadline 12 seconds.
Budget exhaustion rejects; no timeout grants approval or extra implicit retries.

Refresh uses a single current-state batch and reuses cached config decoding. It
reads no transaction/block history and does not redo expensive wallet enrichment.
Tests verify this one-request behavior; live refresh cost remains unmeasured because
no live candidate passed. A repeat capture was made only after adding rejected
evidence retention; both runs and their bounds are preserved separately.

The later detailed attempt had current research buy/sell integer quotes and one
bank context, but address history did not contain the observed anchor. It therefore
remained rejected. The cost budget was not expanded to obtain approval.
