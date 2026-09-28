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


## Implementation 002.3 unverified-read hardening

A storage read is not a verified state read.

`ProjectionStore.load_unverified()` now names the deliberately weaker operation: it validates the projection schema, disposable-state marker, JSON shape, and stored checksum, but it does not prove replay equivalence or freshness.

The old ambiguous `ProjectionStore.load()` path is retained only as a fail-closed trap and raises `ProjectionUnsafeReadError`. Consumers must choose either explicit low-level inspection or a `ProjectionRunner` verification method.

This prevents convenience from quietly becoming authority. The shadow brain may be inspected. It does not get a fake passport because somebody liked the short method name.

See `KIKI_MIND_v0.2.2_IMPLEMENTATION_002.3_REVIEW_PATCH.md`.


## Implementation 002.4 process-stable fingerprint hardening

Projector implementation fingerprints must survive ordinary process restarts.

The earlier fingerprint encoded `repr(code.co_consts)`. Nested code objects, such as those created by comprehensions or inner functions, can include process-specific memory addresses in their repr. That could falsely classify unchanged code as implementation drift after restart.

Implementation 002.4 serializes Python code constants structurally, including nested code objects, bytecode, names, variable metadata, defaults, and keyword defaults. The fingerprint remains a conservative tripwire rather than semantic proof, but it no longer depends on object addresses.

A subprocess probe verifies that the same dynamically defined projector containing a comprehension produces the same fingerprint across independent Python processes.

See `KIKI_MIND_v0.2.2_IMPLEMENTATION_002.4_REVIEW_PATCH.md`.


## Implementation 002.5 physical-file separation hardening

The canonical ledger and projection store must be different physical files, not merely different path strings.

Resolved-path comparison already rejected identical paths and symlink aliases. A hardlink can still give the same inode two different resolved names.

Implementation 002.5 uses an explicit same-file check when both paths exist, so a hardlink alias of the canonical ledger fails immediately with `ProjectionStoreSeparationError` rather than being rejected later only because the projection schema happens not to match.

See `KIKI_MIND_v0.2.2_IMPLEMENTATION_002.5_REVIEW_PATCH.md`.


## Implementation 002.6 projection-schema definition hardening

Projection schema verification now checks the normalized `CREATE TABLE projection_state` definition, not only the table name and column names.

A counterfeit table with the expected column labels but weakened constraints previously passed the column-name check. Implementation 002.6 rejects that schema as definition drift.

This repeats the lesson learned during 001.2 trigger hardening: names are labels, definitions are the mechanism.

See `KIKI_MIND_v0.2.2_IMPLEMENTATION_002.6_REVIEW_PATCH.md`.


## Implementation 002.7 supported-read-surface hardening

Low-level projection storage primitives are no longer exported from the package top-level API.

`ProjectionStore`, `ProjectionSnapshot`, and `ProjectionUnsafeReadError` remain available from the explicit `runtime.kiki_mind.projection` module for implementation work and hostile probes, but ordinary consumers see `ProjectionRunner` and its verified read contracts instead.

This does not create a security sandbox. Python code can still deliberately import internal modules. The goal is structural guidance: the easy path should also be the safe path.

See `KIKI_MIND_v0.2.2_IMPLEMENTATION_002.7_REVIEW_PATCH.md`.
