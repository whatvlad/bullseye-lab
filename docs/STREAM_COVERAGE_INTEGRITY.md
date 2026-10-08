# Stream coverage integrity

CONNECTED means transport connected. DEGRADED means completeness is not
established. GAP_DETECTED records loss/conflict/overflow. RECONNECTING and
RESUMED_WITH_GAP retain unproven history loss. COMPLETE_FOR_WINDOW is a normalized
capability state reserved for a reconciled closed evidence window; no currently
available adapter can assert it. Merely receiving monotonically increasing slots,
heartbeats or fresh accounts is insufficient.

The buffer detects slot jumps on the separate unfiltered slot subscription,
disconnects, subscription restart, duplicate/conflicting signatures, out-of-order
transaction indexes, account slot/write-version regression, overflow and expiration.
A slot jump is conservatively unproven: it might be a skipped chain slot rather
than provider loss. Jumps between filtered Pump transaction slots do not imply
missing Pump events. Same-slot index information is retained but the existing
RPC sequence proof still rejects unproven same-slot ordering; local transport does
not relax that invariant.

Gap serial and last-gap timestamp remain sticky even after the bounded diagnostic
ledger rolls over. A candidate whose retained anchor receipt or native observation
crosses a gap returns FAIL_CONTINUITY. Gaps arriving during proof reject it. A gap
after proof or during the awaited final atomic refresh loses STREAM_COVERAGE;
fresh current state cannot restore historical coverage or authorize execution.
Native config/reserve mutations and lifecycle invalidations are forwarded to both
paired proof services. Unknown invalidations remain conservative.

TTL expiry removes local evidence. Missing packets can fall back to original RPC
proof, including all four fences; absence is never converted into stable local
continuity. Duplicate packets are idempotent; conflicting duplicates create a gap.
Cached account packets are observational, never an atomic account bank.

To safely remove any history fence, a future provider integration must establish:

1. All relevant curve, vault, identity/config and lifecycle mutations are included,
   including System/SPL-only writes and unsupported transactions that invalidate trust.
2. Commitment/fork and transaction index order are consistent with the atomic bank.
3. Closed-slot or equivalent bank-bound delivery barriers reconcile the received
   transaction/account mutation set. A filtered global block count cannot certify
   a per-market subset; ordinary slot completion may arrive before all data.
4. Account write versions and transaction signatures reconcile to the sequence.
5. Disconnect replay/backfill covers the entire affected window and deduplicates
   exact packets. A resume promise is not evidence that local replay completed.
6. Buffer retention covers the candidate window without dropped packets, with
   explicit earliest boundary and no mutation crossing the bank/refresh boundary.

Curve-before and vault-before then become local sequence queries; curve-after
and vault-after become certified watermark/barrier checks. Until those equivalences
are demonstrated against real bytes, all four RPC fences remain necessary here.
The passive pilot delivered no complete transaction/account window. No automatic
reconnect/replay path was claimed or enabled; the bounded run ends and marks its
coverage loss. Production stream recovery remains a blocker.

Regression tests cover complete local packet proof, missing-packet RPC fallback,
gap/restart/ordering/duplicates, TTL/count overflow, account ordering, candidate
across gap, mandatory fresh execution bank, post-proof invalidation and gap arriving
during refresh. Historical exact BUY/SELL replays validate fee/math/transfer parity;
they do not establish live stream completeness. See tests/test_stream_evidence.py.
