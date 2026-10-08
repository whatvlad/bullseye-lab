# Reserve anomaly forensics — runner remains BLOCKED

Recovered all 21 selected trades: 18 distinct anomaly cases (top ten Pump.fun, every PumpSwap
>25%, top ten same-slot, deduplicated) plus three seeded random controls. Sixteen cached full
native blocks were read; three initial version-limited getBlock requests failed with -32015,
then a JSON version ceiling permitted the reads. All 19 requests are retained. No historic
signature was fabricated: slot+market+exact reserves identify a unique decoded native event.
Blocks, loaded addresses, signatures, event ordinal, transaction index, top/inner instructions
and transaction pre/post balances are preserved. Instruction index remains UNKNOWN where
event-to-instruction alignment is not independently unambiguous.

Pump.fun maximum 63.658493%: native target
state Q=38,840,000,000 / T=828,784,757,981,463 was followed by native trades reaching exactly
the RPC state Q=49,687,654,320 / T=647,847,044,526,129. The RPC state matches transaction
3YGtj3oeWgttegiwGJssRuKMwgy5faMVqMh5NgPCv4H76b6ruvRbPmvsgvSb38f5kFdJcJ2hdLsH2zjpURipTcXt at slot 452373114, index 708, although its
RPC observation context was 452373115. This is an intervening-state comparison, not proof of
simultaneous provider disagreement. SOL/token-vault deltas corroborate POST_TRADE event timing.

PumpSwap maximum 570.587037%: target signature G94T36ym85hayfUXeSuavDxPaD2zRaMJs76m7r5sHfDBBmyiMawXxATpTdG5d1jXEw3NbbxwqJ1aF7XEXA53AxP, slot 452373176,
transaction index 251, instruction 5. This transaction contains TWO buys. Instruction 2
moves base vault 206,900,000,000,000→204,523,279,829,579 and quote vault
67,405,853,768→68,393,705,619. Instruction 5 then buys 125,329,811,620,853 raw tokens
with a 137.7 SOL gross quote budget, reaching 79,193,468,208,726 tokens /
204,733,033,682 quote lamports. The event fields are PRE_TRADE for each instruction;
transaction-wide pre/post balances bracket both events, not each one independently.
Following native trades reach exactly the RPC state at slot 452373180, transaction index 827:
79,028,192,105,472 tokens / 205,198,909,168 quote lamports.
The same virtual quote offset 17,584,505,288 is present on both sides.

Identity evidence: AMM program pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA;
pool 9BgdrmQUaAeLuMiZ3FR6adkZZi1cTN683LeFudZdXu2b; base mint 4rYjpN6VY6VJACA5kjn2Lzw14fnQ4mCXJv2iHoCDpump; quote WSOL.
Base vault C7ES3jDWm7YrUy2nWPm6h8VpQEf9QHq9afLGemCC6g9r;
quote vault 97ToUd6M2FijFpyde5KpKiLmpvFnMbiA4MZcg2JM1obw. Both vault owners and
instruction mint/orientation references agree with that pool. No evidence of a wrong pool,
vault, token orientation or decoded virtual offset explains this maximum. Canonical authority
and migration identity continuity are not independently bootstrapped, so those remain UNKNOWN.
The isolated defect is treating AMM pre-trade fields as a contemporaneous post-state price.
This pass corrects the research model; production provider normalization remains a follow-up.

Intermediate slots 177–179 were not fetched. The endpoint match and instruction transition
explain the large movement, but do not prove a complete mutation history across those slots.
{'DIFFERENT_VALID_STATES_SUPPORTED': 19, 'SAME_REPORTED_STATE': 1, 'UNKNOWN': 1} across selected cases. One random control has no exact later-state match and
remains UNKNOWN; two Pump.fun multi-event transactions retain UNKNOWN event semantics.
No unexplained case is promoted into a simultaneous-state provider error.

| Venue | Original signed difference | Stream→RPC slot | Recovered signature | Semantics | Evidence conclusion |
|---|---:|---|---|---|---|
| pump_fun | 63.6585% | 452373114→452373115 | 4tXmr5pp6RgPPoQPi3aiDFMHffvfTBDXxGKEV12FKQx1f3nnLqsvAE8MkSppJzNF14y5dyaGkifRQ1uB5jkG3qWR | POST_TRADE | DIFFERENT_VALID_STATES_SUPPORTED |
| pump_fun | 58.8801% | 452373150→452373150 | dT9dxHa6WErqShJJAmQFZGxJdFjBakGzUQo7E5fD9TwuXMVDSUJBp3U61mebvuDLQUhaQwe3kPi9MQVqvHEyVwC | POST_TRADE | DIFFERENT_VALID_STATES_SUPPORTED |
| pump_fun | -56.3050% | 452373114→452373117 | 3YGtj3oeWgttegiwGJssRuKMwgy5faMVqMh5NgPCv4H76b6ruvRbPmvsgvSb38f5kFdJcJ2hdLsH2zjpURipTcXt | POST_TRADE | DIFFERENT_VALID_STATES_SUPPORTED |
| pump_fun | -54.5147% | 452373114→452373116 | 4N1ipEXuTti6y8x5DbRsUSrwckefQw7C6RtU4oEJbbPnppk88Jepk5HUNqgTUiiM4w6tQ23urJJkbV7aXEKxg9J5 | POST_TRADE | DIFFERENT_VALID_STATES_SUPPORTED |
| pump_fun | -52.1875% | 452373114→452373116 | 2s5aq3LKsoLwhafWKeyiKG3VAofT1q3HVuXp1Q5QKwEmJLeUumCKn6tgnjd6fQkR628aGeVFNEbSTBWdqdfGBAxG | POST_TRADE | DIFFERENT_VALID_STATES_SUPPORTED |
| pump_fun | 42.9275% | 452373150→452373150 | 5ZcMFdFPdt98Cg1hWzb9t9KDsbWdUMGKev1Tc49opLLzexJpjbMdtVvfFAmJxChtjYDfZkmuDWBvDfeWVdFAro8A | UNKNOWN | DIFFERENT_VALID_STATES_SUPPORTED |
| pump_fun | 36.5029% | 452373150→452373150 | 5ZcMFdFPdt98Cg1hWzb9t9KDsbWdUMGKev1Tc49opLLzexJpjbMdtVvfFAmJxChtjYDfZkmuDWBvDfeWVdFAro8A | UNKNOWN | DIFFERENT_VALID_STATES_SUPPORTED |
| pump_fun | -35.3866% | 452373116→452373117 | 5bGuuK3p7w3yPzbw4ZuZe7HoYw2a1dkVXq8YWJSpMuLVw35JnB3xdtecVj9MkzPBUDYziMSzmwZpQvYNNPvHQJT9 | POST_TRADE | DIFFERENT_VALID_STATES_SUPPORTED |
| pump_fun | 32.4747% | 452373114→452373115 | 4aeK5ccJdZqHhNSB3zU5u2rd69rqfnptsdkDk9ZKHGasDumjNrVW2GqWC6ChZzWvdKov59iTv9eX9bbHNt2LZHfT | POST_TRADE | DIFFERENT_VALID_STATES_SUPPORTED |
| pump_fun | 23.5615% | 452373116→452373118 | 66BBWZoz488QcFV6ZWcyMEm4P6Ragy7pZtGGvuaPLqET7CNWKGfzfjySm6Wg7o8o9ggM8NFhT3xX4W412RA8ZssU | POST_TRADE | DIFFERENT_VALID_STATES_SUPPORTED |
| pump_swap | 570.5870% | 452373176→452373180 | G94T36ym85hayfUXeSuavDxPaD2zRaMJs76m7r5sHfDBBmyiMawXxATpTdG5d1jXEw3NbbxwqJ1aF7XEXA53AxP | PRE_TRADE | DIFFERENT_VALID_STATES_SUPPORTED |
| pump_fun | 17.7903% | 452373142→452373142 | 7XJgGe6kyc36ytiHC2r2vEVyBaBpY6KHQAEKqa3us1nLpxhix5HzDN9UPdGLzQUzvdkS2oivjgky6Bzi6pbUtwa | POST_TRADE | DIFFERENT_VALID_STATES_SUPPORTED |
| pump_fun | 9.0335% | 452373157→452373157 | 5J2XmjRtYFLAifBLGSbXWXSYPRi1HhsVK4iESnpzD9Y3wVH6hVcrtqKZ1en5LzJ2x5dBiExS8xZyqQKu5MGUaEzH | POST_TRADE | DIFFERENT_VALID_STATES_SUPPORTED |
| pump_fun | 8.2795% | 452373157→452373157 | 2Shajvjv4WM7pcpLU5xKxP844meS92AEbyQCaaQtTThNJFig98nmTEUpcHKVPkzfTjNGj4me4XPhgxn7fszXNar7 | POST_TRADE | DIFFERENT_VALID_STATES_SUPPORTED |
| pump_fun | 7.6709% | 452373142→452373142 | 3SHw4boELx2qB7MRtuNs7juJytxKGiEhCJZLioio2CvhaD3VtnUmkZ3Mxw3ux6dbHYAcacj9cbo7Q3f6eMgPC4Cj | POST_TRADE | DIFFERENT_VALID_STATES_SUPPORTED |
| pump_fun | -6.9112% | 452373169→452373169 | 3uqjXxNPtvf4GhDaK5XHz5sgufNU9WT8Wk7HAWpg7xyWLz4k2az5PtdRhichAZcxzB9ZyZtbg3UQT3NXEXVnfiY4 | POST_TRADE | DIFFERENT_VALID_STATES_SUPPORTED |
| pump_fun | -6.9092% | 452373169→452373169 | 5xJjs9gRLFeEW9YNAraAgkVasko73A6HCKpDc4a7gxPXrsRiRJsKmEB2MeFrjuQHFpWfrvFJgJuXM3BpDCfKjz4Y | POST_TRADE | DIFFERENT_VALID_STATES_SUPPORTED |
| pump_fun | 4.5179% | 452373156→452373156 | ianMvWLqxxM8oBkY9d2gFZBeDbZghLF1XMiUh3dSqV1rUVhKFStNYi98MtZXm4FTyieETw4XfhunbmSoNbLvDZc | POST_TRADE | DIFFERENT_VALID_STATES_SUPPORTED |
| pump_fun | 0.0000% | 452373164→452373165 | 21FHnHPBau53jX9ShKmbWHf7ffPe4pLYazysYwyYwWjrtWG2HHvyfTyiZRWEaa2JSfTNuRRx8CNaKxif7p8kmT3w | POST_TRADE | SAME_REPORTED_STATE |
| pump_fun | 0.5399% | 452373170→452373172 | 2D59cEFVmKDW7Z6dFL4ztAEHwdrhpPfPks2torqiJMKmHm4WapJFvg4K21juvk4bkdvpobtt2RMC87RBcuU272ss | POST_TRADE | DIFFERENT_VALID_STATES_SUPPORTED |
| pump_fun | 0.1710% | 452373172→452373175 | 5713T2Z73n8gqFXhWvjmQEkhiAYa4Qsdf99cNt5F4PH8k5sLhsKRPn8UsnMxBvgUix15dTxi5WrxZdhfJNY5nbDW | POST_TRADE | UNKNOWN |

Full preceding/target/following timelines are in analysis/reserve_anomalies.json. Cached raw
blocks and SHA256 manifest are retained under research_sessions/reserve-sync-20261001.
