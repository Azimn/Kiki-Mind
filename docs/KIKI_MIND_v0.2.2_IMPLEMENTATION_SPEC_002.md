# Kiki Mind v0.2.2 - Implementation Specification 002

## Deterministic State Projectors + Accounting Invariants

**Status:** implementation branch candidate  
**Architecture:** Kiki Mind v0.2.2 remains frozen  
**Base implementation:** 001.2  
**Scope:** derived-state machinery only

Implementation 002 establishes the reverse path from canonical history into disposable state.

> Canonical history lives in events. Derived state lives in projections. Projections may be destroyed and rebuilt.

A projector may interpret canonical event structure deterministically. It may not invent unledgered history.

The canonical ledger and projection store are physically separate SQLite files. Ledger corruption is a continuity problem. Projection corruption is a rebuild problem.

Each projection checkpoint records projector name, version, implementation fingerprint, canonical JSON state, SHA-256 state hash, canonical sequence, canonical event hash, update time, and the marker `derived_disposable`.

The supported consumer path verifies that stored derived state equals a zero-based replay of the canonical prefix it claims to represent. A validly rehashed invented state therefore fails replay equivalence rather than becoming a second source of truth.

Incremental updates use compare-and-swap on the prior sequence and prior event hash. State, checkpoint, prefix hash, and checksum occupy one SQLite row and update in one transaction. A stale runner fails rather than overwriting newer projection progress.

Projector version changes refuse incremental continuation. A conservative implementation fingerprint also catches same-version code drift while prior projection metadata survives. The fingerprint is a tripwire, not semantic proof.

The reference projectors are intentionally unglamorous. `LedgerAccountingProjectorV1` derives event counts, renderer-mediated counts, encounter counts, event-type counts, and latest governance event identifiers. `EncounterIndexProjectorV1` derives per-representation encounter accounting keyed by representation, mode, and activation function version, including canonical source event IDs.

Implementation 002 adds read-only canonical prefix APIs to `EventLedger`: `get_event_by_sequence`, `head`, and bounded `iter_events`. These APIs do not mutate canonical history.

No LLM call, semantic memory, Subjective Frame, Renderer Adapter, autonomous thought, concern model, relationship model, self-model cognition, dream process, embedding store, or LoRA integration belongs in this slice.

The implementation gate for 003 remains hostile review. The review question is:

> Where can the shadow brain become the real brain?


## Implementation 002.1 review hardening

A replay-valid projection is not necessarily current. The supported read surface therefore distinguishes `checkpoint_verified()`, which proves equivalence to the projection's declared canonical prefix, from `current_verified()`, which additionally requires that prefix to equal the current canonical ledger head.

Staleness is not corruption. `repair()` does not silently convert a stale projection into a current one. Consumers that require current state must fail closed on `ProjectionStaleError` or explicitly advance the projector with `run()`.

See `KIKI_MIND_v0.2.2_IMPLEMENTATION_002.1_REVIEW_PATCH.md`.


## Implementation 002.2 concurrent-head hardening

A default `run()` or `rebuild()` now rechecks the canonical ledger head before returning. If canonical history advances after the runner chooses its target but before the derived state is returned, the operation raises `ProjectionStaleError` rather than returning a state that has already lost freshness.

Explicit historical-prefix operations using `through_sequence` retain checkpoint semantics and do not claim to be current.

See `KIKI_MIND_v0.2.2_IMPLEMENTATION_002.2_REVIEW_PATCH.md`.
