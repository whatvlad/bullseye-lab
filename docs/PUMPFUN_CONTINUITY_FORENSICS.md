# Pump.fun continuity forensics

All **117** retained mismatches on **22 markets**, **117 signatures**, and **36 slots** have one integer residual: virtual quote. Real quote, real token and virtual token continuity match exactly. There are 60 positive and 57 negative virtual-quote residuals. Every case and every attempted category is recorded in `analysis/pumpfun_mismatch_classification.json`; zero counts in other categories mean not established, not ruled out.

Bounded native evidence covers 16 mismatch trades (largest residuals and market clusters), two deterministic random exact controls and four largest-mismatch predecessors: 22 transaction reads. All sampled mismatch trades and predecessors are Mayhem-mode; both exact controls are non-Mayhem. Sampled instructions are ordinary buy/sell variants, including a CreateV2 + BuyV2 predecessor. No selected predecessor/current instruction log proves an intervening SetMayhemVirtualParams call. The stored bytes support the decoded reserve values, but not the exact account-state boundary behind every change.

This supports a recurring **Mayhem-linked virtual-quote mechanism or semantics difference**, rather than evidence of 117 independent feed losses. The precise causal operation remains **UNKNOWN for all 117**. Token age, full unsampled transaction structure, graduation state, queue pressure and unsampled truncation evidence were not retained by the older collector; those fields are explicitly unavailable. The new capture retains direction/mode/instruction, source slot, receipt time, multi-event flag, truncation flag and local queue depth.

For an ordinary trade with direction d=+1 for buy and -1 for sell, integer quote movement Q and token movement T:

```
real_quote'    = real_quote    + d*Q
virtual_quote'= virtual_quote + d*Q
real_token'   = real_token    - d*T
virtual_token'= virtual_token - d*T
```

Therefore virtual_quote-real_quote and virtual_token-real_token stay constant under ordinary trades; token_total_supply also stays constant. Missing ordinary trades alone cannot produce the isolated virtual-quote residual while the other three ordinary invariants remain exact. Nonordinary virtual updates, Mayhem semantics and incorrect boundary interpretation remain plausible. No percentage tolerance is used.

Physical curve-vault inventory is distinct from real sellable reserves. `physical_vault - real_token` is an inventory offset only when bindings and a coherent state sequence are proven. It is not equal to `virtual_token - real_token`. Supply minus real reserves is not circulating supply without further mint/vault evidence. Completion is set when ordinary buying exhausts real sellable tokens; migration changes venue/authority and requires rebootstrap. Creator/config updates and native SetMayhemVirtualParams can invalidate other assumptions independently of trade flow.

Generic research reconstruction requires untruncated successful native metadata, canonical curve/vault binding, top-level ordinary instruction/event order, matching emit-CPI payloads, no other curve/vault top-level mutation, exact real/virtual transitions and physical token/lamport totals. Any missing proof remains UNKNOWN. The retained three-buy transaction at slot 452373150 passes with zero residuals and reserved inventory **206,900,000,000,000** raw tokens; its virtual-token offset is **279,900,000,000,000**, a different quantity. There is no special-case mint/signature logic. Production multi-event trades remain UNKNOWN until an instruction-aware stream or an equivalent bounded transaction-proof path supplies the metadata.

Research code: `research/pumpfun_sequence.py`; evidence: `analysis/pumpfun_multi_event_reconstruction.json`. Official semantics and pinned IDLs: [Pump documentation](https://github.com/pump-fun/pump-public-docs/blob/main/docs/PUMP_PROGRAM_README.md), [Pump IDL](https://github.com/pump-fun/pump-public-docs/blob/main/idl/pump.json). Mayhem attribution above is an inference from retained native evidence, not an official guarantee.
