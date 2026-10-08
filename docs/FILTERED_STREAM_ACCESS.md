# Filtered full-transaction access prerequisite — 2 October 2026

Current status: **PAYG ACCESS WORKING**. The user enabled PAYG and the dashboard
confirmed **Active Plan: Pay As You Go**. Ping succeeded immediately. The corrected
filtered pilot received actual executed packets; see `FILTERED_STREAM_PILOT.md`.
Runner and calibration remain BLOCKED on execution/coverage evidence.

The following records the earlier Free prerequisite investigation, not a new
candidate pilot. Calibration and `runner-edge-prospective-v1` remain BLOCKED.
No orders, account upgrade, subscription purchase, or threshold changes occurred.

The signed-in Alchemy team billing dashboard showed **Active Plan: Free**.
The reviewed PAYG upgrade page said no monthly fee, base RPC price $0.525 per
million CUs, payment setup required, and a temporary $5 card authorization hold.
The agent did not submit the final Upgrade action. The user subsequently activated PAYG.
These are dashboard observations, not a paid billing agreement.

Alchemy's [official quickstart](https://www.alchemy.com/docs/reference/yellowstone-grpc-quickstart)
requires a PAYG or Enterprise team. The minimum documented account change is
upgrading this Free team to PAYG and completing payment setup. Use the mainnet
streaming endpoint `solana-mainnet.streaming.alchemy.com:443` with TLS and X-Token
authentication. A successful Ping and filtered Subscribe must follow activation;
the upgrade alone does not demonstrate working access. Published streaming pricing
is [$75/TB](https://www.alchemy.com/solana-grpc), subject to the account agreement.
No $499 tier is required for this Alchemy access prerequisite.

## Exact sanitized access evidence

`analysis/filtered_stream_access_probe.json` records the bounded probe at
2026-10-02T12:51:13Z. The transaction filter included only a previously observed
standard mint and its canonical curve, and required the Pump program. The inactive
historical market was a routing/access probe, not a qualified live candidate.

| Method | Result | Exact non-secret error |
| --- | --- | --- |
| Alchemy `/geyser.Geyser/Ping` | UNIMPLEMENTED | `/geyser.Geyser/Ping not found.` |
| Alchemy `/geyser.Geyser/Subscribe` | UNIMPLEMENTED | `/geyser.Geyser/Subscribe not found.` |
| Existing Helius `transactionSubscribe` | JSON-RPC -32600 | `transactionSubscribe is not available on the free plan` |

The Alchemy Free prerequisite is unmet. These errors do **not** establish that
correctly entitled PAYG streaming is broken. Helius's error explicitly identifies
Free access for the credential used; its account dashboard was not authenticated
in this investigation. The next fallback is the minimum documented Helius full
WebSocket access, not an automatic gRPC-tier purchase.

## Filter preparation and validation

`WatchCohort` derives mint, curve and possible legacy/Token-2022 curve vault
addresses without RPC enrichment. It bounds the watch set to eight markets,
120-second absolute TTL and 30-second inactivity expiry. These are configurable
watch/storage controls, not strategy qualification thresholds. Known non-standard,
unsupported quote, ambiguous, non-EXACT, cashback, completed, migrated or unsupported
fee-route markets are rejected and removed. Admission is observational: derivation
does not certify account ownership or fee configuration; the existing proof bank
still performs those checks.

The Helius adapter now refuses an empty filter or a Pump-program-wide include
filter before network access. Explicit watched accounts are OR-included and the
Pump program is required. The dynamic helper is prepared but is **not wired into
a demonstrated working provider/pilot yet**. The old global full-stream pilot path
therefore fails closed rather than silently subscribing globally. Provider-side
dynamic update/acknowledgment and removal still require implementation and live
verification after access is available. Four history fences and final atomic RPC
execution refresh remain unchanged.

Validation: **352 tests passed**, Ruff passed, mypy passed on 123 source files.
Tests include rejection before network, canonical narrow addresses, exclusions
and removal on TTL/inactivity. These tests do not certify live provider delivery.

## Requested pilot answers at this prerequisite boundary

1. Working provider/access: none demonstrated; Alchemy Free verified.
2. Required change: Alchemy PAYG/payment setup; reviewed cost above. No purchase made.
3. Full packets captured: none in this access probe; no candidate pilot run.
4. Serious candidates with complete local evidence: not measured in a new pilot.
5. New candidate PASSes: not measured.
6. Complete live BUY PASS: not obtained in this task.
7. Repeatable live SELL PASSes: not obtained in this task.
8. Transaction-availability failure reduction: untested; endpoint access is blocked.
9. RPC cost per serious candidate: not measured; no proof attempts in this probe.
10. Filtered pilot bandwidth: not measured. The Helius rejection was 115 response
    bytes; Alchemy returned errors. This is not a bandwidth benchmark. No previous
    global log-stream measurement is extrapolated.
11. Four history fences: still required; no evidence justifies removing them.
12. Synchronized calibration: not justified; remains BLOCKED.

At the Free prerequisite boundary, the next step was working entitled Ping + narrow Subscribe, followed by
actual complete executed packets, dynamic cohort integration, coverage accounting
and the bounded paired proof pilot. Only that live evidence can answer the
acquisition/RPC/bandwidth hypothesis.
