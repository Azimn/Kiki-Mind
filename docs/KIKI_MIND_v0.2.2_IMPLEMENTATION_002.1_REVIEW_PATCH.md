# Kiki Mind v0.2.2 - Implementation 002.1 Review Patch

## Freshness must not masquerade as verification

**Status:** hostile-review hardening  
**Architecture:** Kiki Mind v0.2.2 remains frozen  
**Base implementation:** 002  
**Scope:** projection read authority only

### Finding

Implementation 002 correctly proved that a stored projection could equal deterministic replay of the canonical prefix it claimed to represent.

The public method name `current_verified()`, however, did not require that claimed prefix to equal the current canonical ledger head. A projection could therefore be perfectly replay-valid and still be stale.

That is not data corruption. It is an authority ambiguity.

A future cognition layer could reasonably interpret "current verified" as "safe current mind-state" and consume a projection that had not incorporated newer canonical events. That would let disposable derived state quietly become an authoritative substitute for canonical history.

### Resolution

Implementation 002.1 separates two claims:

- `checkpoint_verified()` means the projection is replay-equivalent to the exact canonical prefix recorded by its checkpoint.
- `current_verified()` means the projection is replay-equivalent and its checkpoint equals the current canonical ledger head.

If a projection is replay-valid but behind the ledger head, `current_verified()` raises `ProjectionStaleError`.

Partial replay and historical-prefix work remain supported, but callers must request checkpoint semantics explicitly.

### Repair boundary

Staleness is not corruption.

`repair()` continues to rebuild corrupt, mismatched, or divergent derived state from canonical history. It does not silently treat lag as damage and does not automatically advance a stale projection.

A caller that requires fresh state must call `run()` explicitly.

### New probes

Implementation 002.1 adds tests proving that:

1. a stale but replay-valid projection is rejected by `current_verified()`;
2. the same state remains available through the explicitly weaker `checkpoint_verified()` contract;
3. a partial rebuild can be verified at its checkpoint without being mislabeled current;
4. `repair()` does not launder ordinary staleness into corruption recovery.

### Architectural consequence

"Verified" now names a proof about provenance and replay.

"Current" additionally names a proof about freshness.

Those claims are no longer allowed to collapse into one another.

The shadow brain may be behind. It may not pretend that behind means current.
