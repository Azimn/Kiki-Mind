# Kiki Mind v0.2.2 - Implementation 002.2 Review Patch

## A successful catch-up must not return already-stale state

**Status:** hostile-review hardening  
**Architecture:** Kiki Mind v0.2.2 remains frozen  
**Base implementation:** 002.1  
**Scope:** projection freshness under concurrent canonical append

### Finding

Implementation 002.1 separated checkpoint verification from current verification.

A second freshness ambiguity remained in the default `run()` path.

The runner chooses a canonical target, advances the disposable projection to that target, verifies replay equivalence, and returns the state. Because the canonical ledger is independently append-only, a new canonical event can be committed after the target is chosen but before `run()` returns.

The returned projection is still correct for its prefix, but it is no longer current.

For a historical-prefix operation that is acceptable. For a default catch-up operation it is an authority hazard.

### Resolution

When `run()` or `rebuild()` is called without an explicit `through_sequence`, the runner performs a final canonical-head check after the persisted projection has passed replay verification.

If canonical history advanced during the operation, the runner raises `ProjectionStaleError`.

The persisted projection remains valid for its declared prefix and can be resumed safely. The caller may explicitly rerun to catch up.

When `through_sequence` is supplied, the operation is intentionally historical or prefix-bounded and therefore does not claim current-head freshness.

### New probe

A test store injects a legitimate canonical append during the projection checkpoint transaction.

The probe proves that:

1. the first default `run()` refuses to return the now-stale state;
2. the stored checkpoint remains replay-valid for its declared prefix;
3. a second `run()` catches up without duplication;
4. `current_verified()` succeeds only after the projection reaches the new head.

### Boundary

This is not a global transaction across the canonical ledger and projection store.

The guarantee is linearizable freshness at the final head observation made by the runner. A canonical append can always occur after that observation and after the method returns.

The architecture therefore does not claim timeless currentness. It claims that a default catch-up will not knowingly return state that was already stale at its final verification point.
