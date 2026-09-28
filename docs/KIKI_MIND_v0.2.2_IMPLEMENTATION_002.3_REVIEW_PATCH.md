# Kiki Mind v0.2.2 - Implementation 002.3 Review Patch

## Convenience is not authority

**Status:** hostile-review hardening  
**Architecture:** Kiki Mind v0.2.2 remains frozen  
**Base implementation:** 002.2  
**Scope:** unverified projection reads

### Finding

Implementation 002.1 separated checkpoint-valid state from current state. Implementation 002.2 closed the concurrent-head return race.

One smaller authority hazard remained: `ProjectionStore.load()` returned stored projection state after local checksum validation, but its name did not advertise that the result was still unverified against canonical replay.

That is a convenience trap.

A future subsystem could discover the shorter read path, use it because it is fast, and gradually treat disposable projection bytes as if they were verified Kiki state.

### Resolution

The low-level storage read is now named `load_unverified()`.

It validates only:

- projection schema;
- disposable canonicality marker;
- JSON object shape;
- stored state checksum.

It does not claim:

- replay equivalence;
- freshness;
- canonical authority;
- psychological truth.

The old `load()` method now fails closed with `ProjectionUnsafeReadError` and directs callers toward either `load_unverified()` for explicit inspection or `ProjectionRunner.checkpoint_verified()` / `current_verified()` for supported state consumption.

### New probes

Implementation 002.3 proves that:

1. ambiguous `load()` calls are refused;
2. explicit `load_unverified()` remains available for tests and storage inspection;
3. verified runner reads remain the authority-bearing path.

### Architectural consequence

Ease of access is not allowed to become a source of truth.

Or, in Kiki terms: the shadow brain can totally use the dressing-room mirror. It does not get a passport.
