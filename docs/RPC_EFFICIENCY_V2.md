# RPC efficiency V2 — scenarios, no production policy

Entire phase: 54 RPC requests, below 300. Native transaction
evidence uses 16 cached block reads plus three failed version-limited attempts. Both passive
pilots, five local-gap block reads and shared getSlot/global-config probes are included. No transaction lookup for every
trade, no new provider, no trading writes, no orders. Currency/CU costs remain UNKNOWN;
getBlock and notification costs cannot be inferred from request count alone.

Final pilot measured {'duration_seconds': 21.049838, 'requests': 9, 'reads_per_launch': 0.8181818181818182, 'reads_per_cheap_survivor': 4.5, 'reads_per_serious_candidate': 4.5, 'market_reads_per_serious_candidate': 1.0, 'reads_per_minute': 25.65340407845419, 'request_methods': {'getAccountInfo': 3, 'getSlot': 6}}. Shared health/config probes are separated
from market reads. Two sampled candidates in a short notification-limited window cannot
establish a universal requests-per-candidate requirement. The previous pilot had nine new
candidate tokens and 21 requests; its evidence is preserved separately. Candidate lifetimes,
venue mix, anomaly frequency, execution and exit duties determine real costs.

Original calibration pairing baseline: Pump.fun 173 reads (171 successes + two backward-slot
rejections), PumpSwap 18 (nine two-read snapshots), plus nine shared probes. Per-market
interval scenarios using recorded observation lifetimes and cached pool identity:
{
  "5": {
    "pump_fun": 11,
    "pump_swap": 2,
    "reduction_percent": {
      "pump_fun": 93.64161849710982,
      "pump_swap": 88.88888888888889
    }
  },
  "10": {
    "pump_fun": 8,
    "pump_swap": 2,
    "reduction_percent": {
      "pump_fun": 95.37572254335261,
      "pump_swap": 88.88888888888889
    }
  },
  "30": {
    "pump_fun": 7,
    "pump_swap": 2,
    "reduction_percent": {
      "pump_fun": 95.95375722543352,
      "pump_swap": 88.88888888888889
    }
  }
}

Every 10 / 25 retained market-event scenarios:
{
  "10": {
    "pump_fun": 21,
    "pump_swap": 2,
    "reduction_percent": {
      "pump_fun": 87.86127167630057,
      "pump_swap": 88.88888888888889
    }
  },
  "25": {
    "pump_fun": 12,
    "pump_swap": 2,
    "reduction_percent": {
      "pump_fun": 93.0635838150289,
      "pump_swap": 88.88888888888889
    }
  }
}

Event-count scenarios use 180 retained observations, not all 251 original tracked events:
their exact venue allocation is unavailable. These are request-count projections, not validated
freshness policies. Divergence-only lower bound: seven curve bootstraps plus one pool bootstrap
and vault batch (two reads); anomaly repair adds unknown reads. It cannot replace periodic,
execution-time or exit RPC without demonstrated complete mutation capture.
Local trade decoding and actual quote-transfer arithmetic replace repeated observation reads;
cache pool identity and vault addresses, invalidate on migration/config change. No permanent
safety values, monthly cost forecast or production interval has been invented.
