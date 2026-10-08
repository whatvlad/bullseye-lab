# Prospective full proof validation

**Runner and calibration BLOCKED. No orders or trading.** One new passive Alchemy
Yellowstone capture: 2026-10-02T19:44:22.805126+00:00 to 2026-10-02T19:47:04.523297+00:00,
161.72 seconds including bounded teardown/drain.
Bounds: 300 seconds capture, 20 natural candidates, 32 watched markets,
150,000 discovery messages, 96 total RPC reads, 128 MB raw archive, existing
512-event / 120-second / 32 MB transaction buffer. No qualification, provider,
watch eligibility, execution semantics or proof-budget changes were made.
Only corrected stream-first proofs ran; there was no retrospective A/B delay.
The capture retained every attempted stage response; stages after early rejection
are explicitly unattempted, rather than invented missing responses. Later raw
packets are diagnostic only and cannot retroactively authorize a proof.

20 natural serious candidates; 16 provisionally supported cohort;
4 explicit unsupported. Proof-before-refresh PASS 1;
**full PASS 0, BUY 0, SELL 0**.
Actual RPC reads 85/96. Failure distribution: {'REFRESH': 1, 'HISTORY_BOUNDARY': 6, 'BUDGET': 1, 'INVALIDATION': 2, 'UNSUPPORTED_ROUTE': 4, 'STATE_SYNC': 5, 'PROVIDER': 1}.

| Stage | Supported passes / N | Percent |
|---|---:|---:|
| reconstruction | 15/16 | 93.75% |
| anchor_parity | 15/16 | 93.75% |
| history_closure | 3/16 | 18.75% |
| bank_sync | 9/16 | 56.25% |
| proof_before_refresh | 1/16 | 6.25% |
| refresh | 0/16 | 0.00% |
| full_pass | 0/16 | 0.00% |

Full successful latency (milliseconds): {'qualification_to_proof': {'N': 0, 'mean': None, 'median': None, 'p90': None, 'max': None}, 'proof_to_refresh': {'N': 0, 'mean': None, 'median': None, 'p90': None, 'max': None}, 'qualification_to_execution_ready': {'N': 0, 'mean': None, 'median': None, 'p90': None, 'max': None}}.
Successful RPC cost: {'failed_attempts': {'N': 20, 'mean': 4.25, 'median': 4.0, 'p90': 6, 'max': 6}, 'successful_before_refresh': {'N': 1, 'mean': 5, 'median': 5, 'p90': 5, 'max': 5}, 'full_success_including_refresh': {'N': 0, 'mean': None, 'median': None, 'p90': None, 'max': None}}.
An empty successful sample is unavailable, not zero latency/cost; early rejected
attempts do not estimate successful proof speed. Percentages use the provisional
supported denominator stated in the JSON, not fully verified canonical markets.

Detailed outputs: [funnel](PROSPECTIVE_PROOF_FUNNEL.md),
[history](PROSPECTIVE_HISTORY_BOUNDARIES.md), [refresh](PROSPECTIVE_EXECUTION_REFRESH.md),
and `analysis/prospective_full_proofs.json`. Full packets, stage RPC parameters/
responses, atomic banks, exact ledgers/parity and qualifications are retained.

## Readiness answers

1. Natural full candidate PASSes: **0**.
2. Complete live BUY PASSes: **0**.
3. Complete live SELL PASSes: **0**; repeated success requires at least two.
4. Corrected issues were exercised where exact parity/accounting reached; individual
   live native variants and refunds/tips are recorded below. No unsupported
   redistribution was rescued and no fixture/replay counted toward this run.
5. Dominant blocker: **[('HISTORY_BOUNDARY', 6)]**.
6. Stage percentages: table above, with denominator caveat.
7. Successful latency: successful-only distributions above; unavailable if N=0.
8. Successful RPC cost: distributions above; pre-refresh success is reported separately.
9. Final refresh approval: **0/1** attempts.
10. Four-fence operational evidence: 3 unchanged
    closed fence pairs. Changing fences/lag/same-slot limitations remain explicit.
11. Targeted synchronization/fence and invalidation-scope work is warranted.
    All five divergent banks match a captured later market mutation (four packets
    arrived after proof; one arrived during proof). One moving final fence added
    only failed transactions. The sole refresh was blocked by venue-wide unknown
    instruction invalidations despite an unchanged bank. These are concrete
    correctness questions, not authority to relax standards or increase budgets.
12. Standard-only synchronized calibration remains **not justified** unless
    natural full BUY and repeatable full SELL evidence pass. Calibration was not started.

Prospective exact parity variants: {'sell': 5, 'buy_v2': 1, 'buy': 7, 'buy_exact_sol_in': 1, 'buy_exact_quote_in_v2': 1}.
Ancillary movements accepted with exact accounting: {'UNRELATED_SYSTEM_TRANSFER': 7, 'TOKEN_ACCOUNT_CLOSE_REFUND': 1}.
Buffer/coverage gaps: {'MARKET_BUFFER_OVERFLOW': 62, 'OUT_OF_ORDER_TRANSACTION': 1, 'DISCONNECT': 1}; the final disconnect is teardown. No capacity increase or rescue was attempted.
The signature-budget case had five successful vault signatures including its anchor, so the four-signature rejection is real; it is distinct from failed-row pollution.
