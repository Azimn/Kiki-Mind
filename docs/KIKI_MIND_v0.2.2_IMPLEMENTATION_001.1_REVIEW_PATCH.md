# Kiki Mind v0.2.2  -  Implementation 001.1 Review Patch

**Status:** code-review patch after Calibos hostile review  
**Architecture:** unchanged; remains Kiki Mind v0.2.2  
**Base implementation:** 001 / commit `fc18222f9cffa9faf8e738075a58cf7ed438d0c2`

Implementation 001.1 fixes code-level gaps found during review without reopening architecture.

## 1. Lease-lapse recovery

Implementation 001 had a dead-end governance state:

- an expired lease could not be renewed;
- a new grant was blocked because a lease record already existed.

001.1 allows the **same operator identity** to renew after lapse. This is explicitly not operator succession.

A renewal must:

- be authored by the same operator ID named in the payload;
- name the latest prior lease event as `previous_lease_event_id`;
- create a new lease whose expiry is in the future.

A past-dated initial grant is rejected.

Canonical endorsement still requires an actually active lease.

## 2. Taint declaration trust boundary

Typed taint remains structural **over declared derivation modes**.

The gate can enforce:

- `CONTENT` ancestry inherits content restrictions;
- restricted content cannot enter forbidden claim domains;
- declared ancestry remains auditable.

The gate cannot mechanically prove that a proposer labeled semantic derivation correctly.

A malicious or buggy proposal constructor can relabel content use as `CAUSAL_PARENT` or `PROVENANCE_REFERENCE`. Therefore:

> quarantine-taint closure is consistency enforcement over declarations, not semantic proof of those declarations.

Proposal construction is now an explicit trusted-input boundary.

This limitation is retained rather than hidden behind a model-based semantic judge.

### Dual-role ancestry

If event B is both **content-derived from** and **caused by** event A, represent:

- an ancestry edge `A -> B` with `mode=CONTENT`; and
- `A` in `causal_parent_ids`.

Causality and content derivation are separate dimensions. Choosing only `CAUSAL_PARENT` changes taint semantics.

## 3. Gate authority moved inside the ledger

Implementation 001 accepted `commit(proposal, gate)`.

That made the most important invariant dependent on a caller supplying the correct gate.

001.1 changes the API to:

```python
ledger = EventLedger(path, now_fn=...)
ledger.commit(proposal, event_id=...)
```

`EventLedger` owns its `TransitionGate`.

A caller can no longer substitute `GateDecision.allow()` per commit through the public method signature.

Python process/code compromise remains outside this boundary; an attacker capable of rewriting live objects or source code can still defeat application logic.

## 4. Explicit event IDs are crash-idempotent

When an explicit `event_id` already exists:

- same proposal hash -> return the existing event;
- different proposal hash -> raise `IdempotencyConflict`.

This mirrors idempotency-key behavior and makes response-loss retries domain-safe.

## 5. Raw SQLite write trust boundary

SQLite triggers prevent update/delete through ordinary SQL, but SQLite cannot enforce the Python Transition Gate on arbitrary external INSERT statements.

001.1 therefore makes the boundary explicit:

> the database file is not an adversarial security boundary; the ledger is the canonical writer.

Hardening added:

- full schema verification on open;
- full hash-chain verification on open;
- schema verification before every commit;
- hash verification of the current tail before every commit;
- required append-only triggers are verified;
- the exact canonical-event column layout is verified;
- unexpected user tables are rejected.

A raw garbage insert is therefore detected on next open or next canonical commit.

An attacker with direct file access who can reconstruct a fully valid hash chain remains outside the 001.1 threat model. External signed/anchored integrity remains future Continuity Package work.

## 6. Activation version is now operative

`CountActivationV1` now ignores encounters whose
`activation_function_version` is not exactly `count-activation-v1`.

The version field is therefore no longer decorative in the reference projector.

## 7. Housekeeping becomes executable policy

Implementation 001 said continuity-affecting housekeeping must not hide outside the ledger but had no executable guard.

001.1 establishes an intentionally strict first rule:

- only the acknowledged `canonical_events` user table may exist;
- unacknowledged new tables fail schema validation.

This is deliberately inconvenient.

When a later implementation introduces caches, projections, indexes, or other persistence, the schema allow-list must be changed consciously and their canonical/noncanonical status documented.

"Just a table" is not allowed to become invisible state.

## 8. Dead ROOT_TYPES exemption removed

The unused provenance exemption was removed. Derived epistemic classes require ancestry directly.

## 9. Deferred findings

These remain intentionally deferred and visible:

- renderer deregistration/lifecycle;
- semantic verification of declared `DerivationMode`;
- cryptographic defense against a fully privileged raw-SQL writer;
- operator succession to a different operator identity.

## 10. Test result

Implementation 001.1 currently passes **22/22 tests**.

New tests specifically cover:

- lease lapse and recovery;
- invalid past lease expiry;
- latest-lease linkage;
- gate substitution rejection;
- event-ID crash retry;
- event-ID collision conflict;
- activation-function version filtering;
- unknown housekeeping-table rejection;
- forged raw-SQL insert detection on open;
- forged raw-SQL insert blocking the next commit;
- missing append-only trigger blocking the next commit.

## 11. Merge note

This patch changes the public commit API.

Old:

```python
ledger.commit(proposal, gate, event_id=...)
```

New:

```python
ledger.commit(proposal, event_id=...)
```

Any callers must remove the gate argument.

The original Implementation 001 specification should remain in repository history. This document is the review amendment rather than a silent rewrite.
