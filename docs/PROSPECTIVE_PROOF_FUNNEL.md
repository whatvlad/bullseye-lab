# Prospective proof funnel

| Stage | Supported passes / N | Percent |
|---|---:|---:|
| reconstruction | 15/16 | 93.75% |
| anchor_parity | 15/16 | 93.75% |
| history_closure | 3/16 | 18.75% |
| bank_sync | 9/16 | 56.25% |
| proof_before_refresh | 1/16 | 6.25% |
| refresh | 0/16 | 0.00% |
| full_pass | 0/16 | 0.00% |

Denominator: standard/non-Mayhem/supported SOL/simple-event cohort minus explicit unsupported routes; bank-unverified routes remain provisional

```json
{
  "serious_candidates": 20,
  "supported_observational_cohort": 16,
  "explicit_unsupported": 4,
  "denominator_scope": "standard/non-Mayhem/supported SOL/simple-event cohort minus explicit unsupported routes; bank-unverified routes remain provisional",
  "bank_verified_simple_routes": 15,
  "BUY_SELL": {
    "SELL": 9,
    "BUY": 11
  },
  "supported_BUY_SELL": {
    "SELL": 6,
    "BUY": 10
  },
  "stages": {
    "reconstruction": {
      "passed": 15,
      "denominator": 16,
      "percent": 93.75
    },
    "anchor_parity": {
      "passed": 15,
      "denominator": 16,
      "percent": 93.75
    },
    "history_closure": {
      "passed": 3,
      "denominator": 16,
      "percent": 18.75
    },
    "bank_sync": {
      "passed": 9,
      "denominator": 16,
      "percent": 56.25
    },
    "proof_before_refresh": {
      "passed": 1,
      "denominator": 16,
      "percent": 6.25
    },
    "refresh": {
      "passed": 0,
      "denominator": 16,
      "percent": 0.0
    },
    "full_pass": {
      "passed": 0,
      "denominator": 16,
      "percent": 0.0
    }
  },
  "full_candidate_PASS": 0,
  "full_BUY_PASS": 0,
  "full_SELL_PASS": 0,
  "unique_tokens_passing": 0,
  "final_blockers": {
    "REFRESH": 1,
    "HISTORY_BOUNDARY": 6,
    "BUDGET": 1,
    "INVALIDATION": 2,
    "UNSUPPORTED_ROUTE": 4,
    "STATE_SYNC": 5,
    "PROVIDER": 1
  },
  "latency_ms_successful_only": {
    "qualification_to_proof": {
      "N": 0,
      "mean": null,
      "median": null,
      "p90": null,
      "max": null
    },
    "proof_to_refresh": {
      "N": 0,
      "mean": null,
      "median": null,
      "p90": null,
      "max": null
    },
    "qualification_to_execution_ready": {
      "N": 0,
      "mean": null,
      "median": null,
      "p90": null,
      "max": null
    }
  },
  "RPC_requests": {
    "failed_attempts": {
      "N": 20,
      "mean": 4.25,
      "median": 4.0,
      "p90": 6,
      "max": 6
    },
    "successful_before_refresh": {
      "N": 1,
      "mean": 5,
      "median": 5,
      "p90": 5,
      "max": 5
    },
    "full_success_including_refresh": {
      "N": 0,
      "mean": null,
      "median": null,
      "p90": null,
      "max": null
    }
  },
  "refresh_attempted": 1,
  "refresh_approved": 0,
  "refresh_approval_percent": 0.0,
  "pre_refresh_success_latency_ms": {
    "N": 1,
    "mean": 575.736,
    "median": 575.736,
    "p90": 575.736,
    "max": 575.736
  },
  "total_RPC_reads": 85,
  "policy": {
    "max_requests": 12,
    "max_signatures": 4,
    "timeout_seconds": 12,
    "max_proof_age_ms": 2000
  },
  "capture_seconds": 161.71871160017326,
  "raw_full_packets": 2030,
  "coverage_gap_reasons": {
    "MARKET_BUFFER_OVERFLOW": 62,
    "OUT_OF_ORDER_TRANSACTION": 1,
    "DISCONNECT": 1
  }
}
```
