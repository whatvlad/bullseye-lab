# Live standard fee-route validation

Scope is standard non-Mayhem Pump.fun with SOL quote. `STANDARD_SIMPLE_FEE_ROUTE` permits verified ordinary protocol/creator fees and the documented config-bound protocol buyback destination. `STANDARD_COMPLEX_FEE_ROUTE` records CASHBACK, HOLDER_REWARD and SHARED_CREATOR separately and rejects them. The universe and strategy qualification were not broadened.

The five original FAIL_FEE attempts retained no account batches. A nine-read forensic pass retrieved their known native transactions where available:

| Mint | Native route evidence | Original rejecting account branch |
| --- | --- | --- |
| `3GYLP2uaJCbznu3Bd2Q1E4vTy3wvtq7xGQ4TmwwAFQ4z` | HOLDER_REWARD | Exact original OR-branch not retained. |
| `54L1gF5x4EuRrRC81aSFJzRZPajoxuW2HM2pzxPMYVuy` | HOLDER_REWARD | Exact original OR-branch not retained. |
| `jTJxUe6MA4czTXYj46vLrpJWSd7DsqAdm2kqqBzEiSm` | Transaction lookup RPC -32015 | UNKNOWN; original account packet absent. |
| `JBkyuTzdmuFZTiw1y21ijTZD7t1tVd7Lj7Vef3yrDdSr` | HOLDER_REWARD | Exact original OR-branch not retained. |
| `AFdeFFsvQKhLE7PG49ToiEUukXB5F6gTXa9fTxDB6iE8` | Transaction lookup RPC -32015 | UNKNOWN; original account packet absent. |

Current candidate packets explicitly retain mode flags, sharing-account presence and branch labels. Native creator identity, tier-selected protocol/creator bps, curve override, creator-zero handling, fee rounding, applicable canonical config accounts, instruction/event recipient equality and physical destination balance deltas must agree. No static 125 bps authorization was introduced. Creator override/zero combinations remain SDK/synthetic-tested; this capture does not establish representative live coverage of those variants.

The ordinary recorded routes selected 95 protocol bps and 30 creator bps. The Global buyback fraction was 5,000 bps of the protocol fee. Validation requires exact floor split, config-approved buyback recipients and physical destination deltas. The native buy transferred protocol 1,064,420 lamports as 532,210 primary + 532,210 buyback, with creator 336,133. The PASS sell transferred protocol 938,272 as 469,136 + 469,136, with creator 296,297.

This split is distinct from cashback, holder rewards and shared creator flows. Supporting those complex paths is deferred. Native fields and canonical account definitions are retained from the official [Pump IDL](https://github.com/pump-fun/pump-public-docs/blob/main/idl/pump.ts) and [buy instruction documentation](https://github.com/pump-fun/pump-public-docs/blob/main/docs/instructions/BUY.md); observed transfer amounts come from the stored transactions, not inferred documentation behavior.

See `analysis/live_fee_routes.json` and `analysis/live_historical_forensics.json` for exact fields, account packets and limitations. A valid fee-route sample alone does not approve a candidate whose continuity, freshness or config receipt failed.
