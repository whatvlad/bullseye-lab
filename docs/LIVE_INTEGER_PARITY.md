# Live integer and transfer parity

The strengthened validator compares each native instruction, full TradeEvent and physical account metadata from the same transaction. The applicable Global/FeeConfig and curve identity are taken from that candidate's atomic account packet. Virtual pre-reserves are reconstructed from native post-reserves and the trade amount; physical pre/post vault and curve balances independently constrain the transition. SDK-only parity remains separate from live evidence.

Two retained live buys and one retained live sell pass all strengthened checks. Five other sampled transactions remain unproven: two have instruction ambiguity and three have unexplained trader-wallet flow. These are rejection reasons, not evidence of a universal integer-model defect.

For the retained `4SC3...` buy_v2 sample: token output 1,744,020,782,044 raw units, net curve input 112,044,121 lamports, protocol 1,064,420, creator 336,133, gross input 113,444,674. Native System transfers within the Pump invocation sum exactly to gross input; config-approved fee destinations reconcile exactly. The complete candidate proof was separately invalidated, so this is a buy parity sample, not a buy candidate PASS.

For the `F57h...` complete sell PASS: token input 3,154,300,833,613 raw units, gross curve proceeds 98,765,430 lamports, protocol 938,272, creator 296,297, net trader proceeds 97,530,861. The trader's total balance change was 98,989,701 because the transaction also closed its token account. Adding the 55,000 network fee and subtracting the independently observed 1,513,840 rent refund gives exactly 97,530,861. The refund is not trading PnL. Reserve transitions and all fee destinations match exactly.

The PASS took six RPC reads and 353.2545 ms, with account age 170.625 ms. Its one-batch refresh arrived 110.563 ms later. Both batches have the same slot and identical account contents, giving zero state, marginal-price and simulated-quote movement. An intervening invalidation nevertheless removed the receipt and caused refresh rejection. No quote from that rejected refresh was approved.

The capture supplies one immediate state-staleness comparison, not an expiry distribution. The existing research freshness policy was retained; no permanent production expiry was chosen. Tests cover proof expiry, hard request/deadline exhaustion, successful synthetic passive refresh, invalidation races, known-signature anchoring, lagging history, missing bank transitions, complex-route rejection and replay of real buy/sell packets.

Machine evidence is in `analysis/live_integer_parity.json` and the refresh section of `analysis/live_candidate_proofs.json`. The runner remains blocked pending operational refresh recovery and representative calibration evidence.
