# Standard Pump.fun fee and integer quote validation

The candidate proof uses current canonical Pump Global/FeeConfig, current mint
supply and virtual reserves. It does not authorize execution using static 125 bps.
The implementation is `src/memebot/paper/standard_math.py`; candidate/native binding
checks are in `src/memebot/paper/candidate_proof.py`.

The primary reference is official [`@pump-fun/pump-sdk` 2.0.0](https://www.npmjs.com/package/@pump-fun/pump-sdk),
whose source/version/tarball hash were retained in `analysis/pump_sdk_reference`.
The official [fee documentation](https://github.com/pump-fun/pump-public-docs/blob/main/docs/FEE_PROGRAM_README.md)
also describes reserve/supply market-cap selection and fee tiers. Current SDK source
was used for creator overrides and exact quote arithmetic rather than treating
older documentation's example values as current configuration.

For the supported standard SOL path, market capitalization is integer virtual
quote reserves × supply ÷ virtual token reserves. The applicable tier is selected
at its inclusive threshold, with the first tier below the first threshold. Creator
override replaces the schedule rate only when enabled and nonzero; a zero override
uses the schedule. A zero creator receives zero creator fee. Configured override
limits, supported quote, nonempty ordered tiers and zero curve LP fees are checked.
The standard SDK's supported supply invariant is verified instead of silently
mixing inconsistent supply conventions between quote functions.

Each fee amount rounds upward independently. Exact-token buys use floor of the
curve ratio plus one, then add protocol and creator ceilings. Budget buys preserve
the SDK's `(budget - 1)` adjustment, integer fee denominator, output floor and real
token reserve cap; the resulting exact-token quote must stay within budget. Sells
floor the gross curve output, check real quote coverage and subtract each ceiling.
All arithmetic uses integers. External costs remain separate estimates.

| Component | Evidence classification |
|---|---|
| Supported protocol tier bound to the candidate's atomic config/state | VERIFIED_AT_CANDIDATE_STATE |
| Supported creator schedule/override/zero rule bound to that state | VERIFIED_AT_CANDIDATE_STATE |
| Cashback, holder rewards or shared-creator routing not yet validated | UNKNOWN; FAIL_FEE |
| Config/curve fields missing or native fee/rounding mismatch | UNKNOWN; proof rejects |
| Network, priority, service cost and future latency/slippage | ESTIMATED |

Canonical config ownership/PDA/hash and native Global/FeeConfig account references
are checked. Supported native fee events must agree with selected rates, independent
rounded amounts, creator identity/destination and normal protocol recipients.
Native instruction token/gross-budget/minimum arguments and curve inputs/outputs
must match the integer model. Any mismatch rejects proof. Cashbacks/rewards/sharing
are not approximated into an execution approval.

`analysis/validate_standard_sdk.py` extracts unmodified compiled SDK pure functions
and executes them locally with BigInt/BN and key-equality adapters. No package
initialization, wallet, RPC or package script runs. **36 cases / 108 quote comparisons
passed with zero mismatches**, covering tier boundaries below/equal/above, creator
override and creator zero, multiple buy budgets, exact-token buy rounding and sell
rounding. Full encoded native buy and sell fixtures also pass the proof engine.

These are SDK and synthetic-native validations, **not live on-chain parity**.
The nine live attempts all rejected before eligible transaction reconstruction;
there were zero live native parity samples and zero execution-ready candidates.
Ordinary cashback/reward/shared-fee branches and successful live both-side parity
remain blockers. Machine-readable results: `analysis/standard_fee_validation.json`.
