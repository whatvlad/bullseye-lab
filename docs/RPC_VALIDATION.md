# RPC validation — short pilot only

Confirmed slot probes ran four times on each configured HTTP endpoint. All were successful.
{
  "solana-mainnet.g.alchemy.com#70faa9f208": {
    "requests": 196,
    "slot_sequence": [
      452373082,
      452373120,
      452373157,
      452373197
    ],
    "duplicate_slots": 0,
    "regressions": 0,
    "latency_distribution_ms": {
      "N": 196,
      "median": 64.2790999263525,
      "p75": 75.31632506288588,
      "p90": 98.44694996718317,
      "p95": 148.94449996063486,
      "p99": 346.47278487682377,
      "max": 437.7363999374211
    }
  },
  "api.mainnet-beta.solana.com#6fe2b1790f": {
    "requests": 4,
    "slot_sequence": [
      452373083,
      452373121,
      452373157,
      452373197
    ],
    "duplicate_slots": 0,
    "regressions": 0,
    "latency_distribution_ms": {
      "N": 4,
      "median": 160.11089994572103,
      "p75": 177.37935000332072,
      "p90": 179.1943799937144,
      "p95": 179.79938999051228,
      "p99": 180.2833979879506,
      "max": 180.40439998731017
    }
  }
}

Near-concurrent primary-minus-exit slots: [-1, -1, 0, 0].
Receipt deltas are retained in provider_costs.json; this is relative endpoint comparison,
not lag against an independently proven chain tip. A fast HTTP response does not prove freshness.
Two paired reads were rejected as rpc_slot_regressed relative to their stream slot, despite
monotonically progressing getSlot probes. No HTTP 429, timeout or transport error occurred.
PumpSwap pool and vault reads can span distinct context slots and are explicitly flagged;
they must not be silently treated as an atomic snapshot. No transaction-specific historical
state query was made. The public endpoint was used only for four independent slot probes.
Its reserve/quote accuracy and long-term exit capacity are not established by this run.
RPC timing is SLOT_ONLY; block time/source wall-clock time and absolute price age remain unknown.
Endpoint identities contain hostname and digest, never credential-bearing URL paths.
