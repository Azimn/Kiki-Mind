# Kiki Mind v0.2.2 — Implementation Specification 002

## Deterministic State Projectors + Accounting Invariants

**Status:** implementation candidate after 001.1 passed hostile re-probing  
**Architecture:** Kiki Mind v0.2.2 remains frozen  
**Base commit:** `f32082b194e291a44d671ffcb4262087672f4a65`  
**Scope:** derived-state machinery only  
**Out of scope:** semantic memory, Subjective Frame, renderer adapters, autonomous thought, concerns, relationships, self-model cognition, dreams, rich salience

---

## 1. Purpose

Implementation 001.1 established how a continuity-relevant event becomes canonical.

Implementation 002 establishes the opposite direction:

> **Canonical history lives in events. Derived state lives in projections. Projections may be destroyed and rebuilt.**

A projector may interpret canonical event structure deterministically. It may not become an independent source of historical truth.

The core replay invariant is:

```text
canonical ledger
      ↓
  projector vN
      ↓
   state A

delete projection storage

same canonical ledger
      ↓
  projector vN
      ↓
   state B

A == B
```

Incremental projection must also equal zero-based replay for the same canonical prefix and projector implementation.

---

## 2. Separate stores

Canonical events remain in the existing ledger database.

Derived state is stored in a **different SQLite file**.

Implementation 002 refuses to construct a `ProjectionRunner` with the projection store at the same resolved path as the canonical ledger.

This separation is intentional:

- ledger corruption is a continuity problem;
- projection corruption is a rebuild problem.

The projection database carries the explicit marker:

`canonicality = "derived_disposable"`

That marker does not make arbitrary derived state trustworthy. It identifies its intended status.

---

## 3. Projection state schema

Each projector has one materialized checkpoint containing:

- `projector_name`
- `projector_version`
- `projector_fingerprint`
- `state_json`
- `state_hash`
- `last_sequence`
- `last_event_hash`
- `updated_at`
- `canonicality`

The checkpoint is bound to a canonical ledger prefix by both sequence and event hash.

A projection whose checkpoint no longer matches the canonical ledger is rejected.

---

## 4. Projector contract

A projector supplies:

```python
name: str
version: str

initial_state() -> Mapping
apply(state, event) -> Mapping
```

Projector output must be JSON serializable.

Projectors receive committed `EventRecord` objects. Implementation 002 does not permit LLM calls inside the supplied reference projector.

The reference `LedgerAccountingProjectorV1` is deliberately unglamorous. It derives event counts, renderer-mediated counts, encounter counts, and latest governance-event identifiers.

It is a proof of the projection machinery, **not** Kiki's self-model.

---

## 5. Replay equivalence is mandatory

A self-consistent projection hash is not sufficient.

Someone can mutate derived state, recompute its hash, and still create a false materialized view.

Therefore the supported verified path checks:

> stored derived state == deterministic replay of the canonical prefix it claims to represent

`ProjectionRunner.run()` verifies replay equivalence before compounding existing state and again before returning state to the caller.

`ProjectionRunner.rebuild()` replays from zero and then verifies the saved result.

`ProjectionRunner.current_verified()` is the supported read path for consumers that require continuity-relevant derived state.

`ProjectionStore.load()` is a low-level storage operation and must not be treated as epistemic verification.

---

## 6. Crash and restart behavior

Incremental projection checkpoints one canonical event at a time.

Each checkpoint uses a compare-and-swap condition:

- expected prior canonical sequence;
- expected prior event hash.

If another projector runner advances the same projector concurrently, a stale runner fails with `ProjectionConflict` rather than overwriting newer progress.

A crash can leave the projection **behind** the ledger.

It should not leave a half-committed projection event.

On restart, the runner validates the checkpoint against the canonical prefix and continues.

---

## 7. Version changes

A stored projector version must match the projector version used for incremental projection.

Version mismatch raises `ProjectionVersionMismatch`.

Changing projection semantics therefore requires an explicit rebuild under a new projector version.

Rebuild may replace an older projector version.

It does not silently reinterpret a stored projection through a new version.

---

## 8. Projector implementation fingerprint

Version strings alone still depend on developer diligence.

Implementation 002 adds a conservative automatic `projector_fingerprint`.

The fingerprint combines:

- projector class identity;
- `initial_state` method bytecode;
- `apply` method bytecode;
- source-module bytes when available.

If projector code changes while retaining the same projector version and a prior projection survives, the runner raises `ProjectionImplementationMismatch`.

This is a **tripwire**, not semantic proof.

Limitations are intentional and explicit:

- equivalent code packaged differently may produce a different fingerprint;
- dependency behavior outside the fingerprint can still change;
- if all prior projection metadata is destroyed, no local witness remains to prove that an old implementation used a different fingerprint.

Future Continuity Package metadata should preserve projector fingerprints as part of identity-critical dynamics history.

---

## 9. Corruption behavior

### Self-inconsistent corruption

If `state_json` no longer matches `state_hash`, loading the projection raises `ProjectionCorruption`.

### Self-consistent invented state

If someone changes state and recomputes its state hash, replay equivalence detects the divergence.

### Checkpoint corruption

If `last_sequence` / `last_event_hash` no longer identify the canonical ledger prefix, the runner raises `ProjectionCheckpointMismatch`.

### Repair

Disposable projection state can be discarded or rebuilt from the canonical ledger.

Canonical history is not edited to make the projection look correct.

---

## 10. Projection schema policy

The projection database currently permits exactly one user table:

`projection_state`

This is the same "tiny supervillains sign the guest book" discipline introduced in 001.1.

New caches, materialized views, embeddings, or helper tables must be explicitly added to the derived-state schema contract.

No table becomes continuity-relevant merely by appearing in SQLite.

---

## 11. Canonical ledger read additions

Implementation 002 adds read-only ledger APIs needed by projectors:

- `get_event_by_sequence(sequence)`
- `head()`
- `iter_events(after_sequence=..., through_sequence=...)`

These do not mutate canonical history.

They provide stable canonical-prefix traversal for deterministic replay.

---

## 12. Accounting invariants introduced by 002

### 12.1 Canonical-source invariant

A projector consumes canonical ledger events. Projection state is not fed back as historical evidence.

### 12.2 Prefix-binding invariant

Every saved projection names the canonical sequence and event hash it represents.

### 12.3 Replay-equivalence invariant

Verified derived state must equal a zero-based replay under the same projector version and implementation fingerprint.

### 12.4 Disposable-state invariant

Deleting projection storage must not alter the canonical ledger and must be recoverable by replay.

### 12.5 Version invariant

Incremental projection cannot cross a projector-version change silently.

### 12.6 Implementation-witness invariant

Same-version projector code drift is rejected while a prior implementation fingerprint survives.

### 12.7 Monotonic-checkpoint invariant

Incremental checkpoints may move forward or remain at explicit GENESIS; they may not move backward or overwrite newer projector progress.

### 12.8 Serialization invariant

Projection state must have a deterministic canonical JSON representation and SHA-256 state hash.

### 12.9 Separation invariant

Canonical ledger storage and projection storage are physically separate files.

---

## 13. Determinism

The framework is intentionally hostile to nondeterministic projectors.

After projection, zero-based replay is performed before the result is returned.

A projector whose repeated replay produces different state raises `ProjectionDivergence`.

This makes randomness, hidden wall-clock dependence, or mutable hidden projector state visible instead of allowing it to become unexplained developmental state.

Future stochastic cognition can exist, but its randomness must enter through canonical events or another explicitly accounted mechanism rather than hiding inside a deterministic projector.

---

## 14. Performance trade-off

Implementation 002 is intentionally correctness-first.

The runner currently performs full canonical integrity verification and zero-based replay verification around projection operations.

That is O(n) work and will eventually become expensive.

This is accepted for Implementation 002.

A later optimization may introduce stronger checkpoint proofs, projection hash chains, snapshots, or verified sufficient statistics, but it must preserve the observable guarantees before removing replay.

Performance pressure is not permission to create an unverified second source of truth.

---

## 15. What 002 does not solve

Implementation 002 does **not** yet implement:

- semantic Kiki memory;
- concern or curiosity projectors;
- commitment trajectories;
- relationship state;
- self-model propositions;
- Identity Genome;
- Subjective Frame;
- renderer adapter;
- access/salience dynamics;
- encounter-log compaction;
- activation migration overlap;
- portable Continuity Package export;
- projector dependency graph;
- projection migration between schemas;
- distributed projectors.

Those come only after the projection substrate survives hostile review.

---

## 16. Tests

The complete suite currently passes **45/45 tests**:

- the 22 retained Implementation 001.1 tests;
- 23 Implementation 002 tests.

002-specific tests cover:

- explicit GENESIS projection;
- deterministic rebuild;
- incremental vs full-replay equivalence;
- restart/resume;
- delete-and-rebuild;
- canonical ledger nonmutation;
- physical store separation;
- projector version mismatch;
- same-version code fingerprint mismatch;
- state-hash corruption;
- validly rehashed invented-state detection;
- checkpoint-prefix corruption;
- compare-and-swap stale-writer rejection;
- non-JSON projector state rejection;
- unknown projection table rejection;
- backwards projection rejection;
- beyond-head rejection;
- encounter accounting;
- projection lag until rerun;
- semantic-state drift detection;
- ledger prefix traversal;
- nondeterministic projector rejection;
- monotonic checkpoint enforcement.

---

## 17. Hostile-review targets

Calibos should attack:

1. Can derived state influence canonical history without a new canonical event?
2. Can a caller obtain and use unverified projection state accidentally?
3. Can a projector hide nondeterminism that replay does not expose?
4. Can two runners race in a way that loses or rewrites projector progress?
5. Can projector code change without version/fingerprint detection?
6. Does the fingerprint create false confidence about dependency semantics?
7. Can projection checkpoint metadata be forged into a different canonical prefix?
8. Can `replace()` or `discard()` be abused in a way that makes derived state authoritative?
9. What happens at 20,000 / 2,000,000 events when replay verification becomes expensive?
10. Is the O(n) verification discipline safe to optimize later, or have I made it part of the subject accidentally?
11. Can schema evolution of `projection_state` manufacture continuity?
12. What derived-state field appears harmless now but will become a covert second source of truth once a Subjective Frame starts consuming it?

The desired review question is:

> **Where can the shadow brain become the real brain?**

---

## 18. Implementation gate for 003

Do not build semantic memory or subjective accessibility on top of Implementation 002 until:

- all tests pass in the canonical repository;
- hostile review finds no unacknowledged second source of truth;
- projection corruption can be repaired by replay;
- code/version drift is visible;
- incremental and full replay are equivalent;
- restart/resume behavior is demonstrated.

**Boring state first. Meaning later.**